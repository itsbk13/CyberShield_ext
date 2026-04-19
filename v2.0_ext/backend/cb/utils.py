import os
import re
import joblib
import numpy as np
import requests as req_lib
from urllib.parse import urlparse
from django.conf import settings

# ── Model Paths ──────────────────────────────────────────────────────────────
PHISHING_MODEL_PATH       = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_model.pkl')
PHISHING_SCALER_PATH      = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_scaler.pkl')
FRAUD_TEXT_MODEL_PATH     = os.path.join(settings.BASE_DIR, 'cb', 'model', 'fraud_text_model.pkl')
FRAUD_TEXT_VECTORIZER_PATH= os.path.join(settings.BASE_DIR, 'cb', 'model', 'fraud_text_vectorizer.pkl')

# ── Load All Models at Startup ───────────────────────────────────────────────
try:
    PHISHING_MODEL    = joblib.load(PHISHING_MODEL_PATH)
    PHISHING_SCALER   = joblib.load(PHISHING_SCALER_PATH)
    FRAUD_TEXT_MODEL  = joblib.load(FRAUD_TEXT_MODEL_PATH)
    FRAUD_VECTORIZER  = joblib.load(FRAUD_TEXT_VECTORIZER_PATH)
    print("✅ All models loaded successfully")
except Exception as e:
    raise Exception(f"Model load failed: {str(e)}")


# ── URL Feature Extractor (matches PhiUSIIL column order) ───────────────────
def extract_url_features(url):
    """
    Extract numeric features from a URL to match PhiUSIIL training schema.
    Returns a pandas DataFrame with correct column names to avoid sklearn warning.
    """
    import pandas as pd

    if not url.lower().startswith("http"):
        url = "http://" + url

    parsed  = urlparse(url)
    domain  = parsed.netloc or ""
    path    = parsed.path or ""
    tld     = domain.split('.')[-1] if '.' in domain else ""
    full    = url.lower()

    features = {
        'URLLength':                    len(url),
        'DomainLength':                 len(domain),
        'IsDomainIP':                   1 if re.match(r'^\d{1,3}(\.\d{1,3}){3}(:\d+)?$', domain) else 0,
        'URLSimilarityIndex':           sum(c.isdigit() for c in url),
        'CharContinuationRate':         len(re.findall(r'(.)\1+', url)),
        'TLDLegitimateProb':            1 if tld in ['com','org','net','edu','gov','in','io'] else 0,
        'URLCharProb':                  round(len(set(url)) / len(url), 4) if url else 0,
        'TLDLength':                    len(tld),
        'NoOfSubDomain':                max(domain.count('.') - 1, 0),
        'HasObfuscation':               1 if '%' in url or '0x' in url.lower() else 0,
        'NoOfObfuscatedChar':           url.count('%'),
        'ObfuscationRatio':             round(url.count('%') / len(url), 4) if url else 0,
        'NoOfLettersInURL':             sum(c.isalpha() for c in url),
        'LetterRatioInURL':             round(sum(c.isalpha() for c in url) / len(url), 4) if url else 0,
        'NoOfDegitsInURL':              sum(c.isdigit() for c in url),
        'DegitRatioInURL':              round(sum(c.isdigit() for c in url) / len(url), 4) if url else 0,
        'NoOfEqualsInURL':              url.count('='),
        'NoOfQMarkInURL':               url.count('?'),
        'NoOfAmpersandInURL':           url.count('&'),
        'NoOfOtherSpecialCharsInURL':   sum(1 for c in url if not c.isalnum() and c not in ['.','/','?','=','&',':','-','_','%']),
        'SpacialCharRatioInURL':        round(sum(1 for c in url if not c.isalnum()) / len(url), 4) if url else 0,
        'IsHTTPS':                      1 if parsed.scheme == 'https' else 0,
        # Page-level features — 0 at inference (no page fetch)
        'LineOfCode': 0, 'LargestLineLength': 0, 'HasTitle': 0,
        'DomainTitleMatchScore': 0, 'URLTitleMatchScore': 0,
        'HasFavicon': 0, 'Robots': 0, 'IsResponsive': 0,
        'NoOfURLRedirect': 0, 'NoOfSelfRedirect': 0,
        'HasDescription': 0, 'NoOfPopup': 0, 'NoOfiFrame': 0,
        'HasExternalFormSubmit': 0, 'HasSocialNet': 0,
        'HasSubmitButton': 0, 'HasHiddenFields': 0, 'HasPasswordField': 0,
        'Bank':   1 if 'bank'   in full else 0,
        'Pay':    1 if 'pay'    in full else 0,
        'Crypto': 1 if 'crypto' in full or 'bitcoin' in full else 0,
        'HasCopyrightInfo': 0, 'NoOfImage': 0, 'NoOfCSS': 0,
        'NoOfJS': 0, 'NoOfSelfRef': 0, 'NoOfEmptyRef': 0,
        'NoOfExternalRef': 0,
    }

    # Build DataFrame in exact trained column order → no sklearn warning
    cols = PHISHING_MODEL.feature_columns_
    return pd.DataFrame([[features.get(c, 0) for c in cols]], columns=cols)


# ── Main Prediction Function ─────────────────────────────────────────────────
def predict_spam(text):
    """
    Predict if input is phishing (URL-based) or fraud/spam (text-based).
    Uses two fully ML-trained models — no hardcoded logic.

    Returns:
        dict: is_phishing, is_fraud, phishing_prob, fraud_prob
    """
    try:
        print(f"\n[predict_spam] Input: {text}")
        is_phishing  = False
        is_fraud     = False
        phishing_prob = 0.0
        fraud_prob    = 0.0

        # ── Phishing check (URL input → PhiUSIIL feature model) ─────────
        is_url = ("." in text and " " not in text) or "http" in text.lower()

        if is_url:
            features_df  = extract_url_features(text)
            scaled       = PHISHING_SCALER.transform(features_df)
            pred         = PHISHING_MODEL.predict(scaled)[0]
            proba        = PHISHING_MODEL.predict_proba(scaled)[0]

            # PhiUSIIL: classes_=[0,1] → 0=phishing, 1=legit
            # proba[0] = probability of being phishing (class 0)
            phishing_prob = round(float(proba[0]) * 100, 2)
            is_phishing   = (pred == 0)
            print(f"[phishing] pred={pred}, phishing_prob={phishing_prob}%")

        # ── Fraud check (any text → TF-IDF spam model) ───────────────────
        fraud_vec  = FRAUD_VECTORIZER.transform([text])
        fraud_pred = FRAUD_TEXT_MODEL.predict(fraud_vec)[0]
        fraud_proba= FRAUD_TEXT_MODEL.predict_proba(fraud_vec)[0]

        # classes_=[0,1] → 0=ham, 1=spam/fraud
        fraud_prob = round(float(fraud_proba[1]) * 100, 2)
        is_fraud   = bool(fraud_pred == 1)
        print(f"[fraud] pred={fraud_pred}, fraud_prob={fraud_prob}%")

        return {
            'is_phishing':  is_phishing,
            'is_fraud':     is_fraud,
            'phishing_prob': phishing_prob,
            'fraud_prob':    fraud_prob
        }

    except Exception as e:
        print(f"[predict_spam ERROR] {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")


# ── CVE / KEV Enrichment (unchanged) ────────────────────────────────────────
def enrich_with_cve_kev(text):
    enrichment = {
        "related_cves": [],
        "kev_matched":  False,
        "kev_details":  None,
        "risk_level":   "LOW"
    }
    try:
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', text)
        if not domain_match:
            return enrichment

        domain  = domain_match.group(1)
        keyword = domain.split('.')[0]

        generic_words = {'http','www','com','net','org','io','co','app','login','secure'}
        if keyword.lower() in generic_words or len(keyword) < 3:
            return enrichment

        nvd_url = (
            f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            f"?keywordSearch={keyword}&resultsPerPage=3"
        )
        nvd_resp = req_lib.get(nvd_url, timeout=6)

        if nvd_resp.status_code == 200:
            for item in nvd_resp.json().get('vulnerabilities', []):
                cve_id = item['cve']['id']
                descs  = item['cve'].get('descriptions', [])
                desc   = descs[0]['value'][:150] if descs else "No description."
                metrics= item['cve'].get('metrics', {})
                cvss   = None
                if 'cvssMetricV31' in metrics:
                    cvss = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                elif 'cvssMetricV2' in metrics:
                    cvss = metrics['cvssMetricV2'][0]['cvssData']['baseScore']
                enrichment['related_cves'].append({'id': cve_id, 'description': desc, 'cvss_score': cvss})

        kev_resp = req_lib.get(
            "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            timeout=6
        )
        if kev_resp.status_code == 200:
            kev_vulns   = kev_resp.json().get('vulnerabilities', [])
            cve_ids     = [c['id'] for c in enrichment['related_cves']]
            kev_match   = next((v for v in kev_vulns if v['cveID'] in cve_ids), None)

            if kev_match:
                enrichment['kev_matched'] = True
                enrichment['kev_details'] = {
                    'cve_id':            kev_match['cveID'],
                    'vendor':            kev_match['vendorProject'],
                    'product':           kev_match['product'],
                    'date_added':        kev_match['dateAdded'],
                    'short_description': kev_match['shortDescription'],
                    'required_action':   kev_match.get('requiredAction', 'Apply vendor patch immediately.')
                }
                enrichment['risk_level'] = "CRITICAL"
            elif enrichment['related_cves']:
                enrichment['risk_level'] = "HIGH"

    except Exception as e:
        print(f"[CVE/KEV ERROR] {str(e)}")

    return enrichment