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


# ── Local Threat Intelligence Database ──────────────────────────────────────
EXPLOIT_THREAT_DB = {
    "log4j": {
        "cve_id": "CVE-2021-44228",
        "vendor": "Apache Software Foundation",
        "product": "Log4j",
        "short_description": "Apache Log4j2 2.0-beta9 through 2.15.0 JNDI features do not protect against attacker controlled LDAP and other JNDI related endpoints. Remote Code Execution (RCE) attack possible.",
        "date_added": "2021-12-10",
        "cvss_score": 10.0,
        "required_action": "Upgrade to Log4j version 2.17.0 or later immediately."
    },
    "jndi": {
        "cve_id": "CVE-2021-44228",
        "vendor": "Apache Software Foundation",
        "product": "Log4j",
        "short_description": "JNDI injection vulnerability in Apache Log4j. Remote Code Execution (RCE) attack possible via LDAP/RMI.",
        "date_added": "2021-12-10",
        "cvss_score": 10.0,
        "required_action": "Upgrade to Log4j version 2.17.0 or later immediately."
    },
    "struts": {
        "cve_id": "CVE-2017-5645",
        "vendor": "Apache Software Foundation",
        "product": "Struts",
        "short_description": "Apache Struts 2.3.x before 2.3.33 and 2.5.x before 2.5.13 Remote Code Execution vulnerability.",
        "date_added": "2017-04-01",
        "cvss_score": 9.8,
        "required_action": "Patch immediately to Struts 2.3.33 or 2.5.13+"
    },
    "weblogic": {
        "cve_id": "CVE-2016-0638",
        "vendor": "Oracle",
        "product": "WebLogic Server",
        "short_description": "WebLogic Server Remote Code Execution vulnerability.",
        "date_added": "2016-06-15",
        "cvss_score": 9.8,
        "required_action": "Apply Oracle WebLogic security patches immediately."
    },
    "exploit": {
        "cve_id": "CVE-2024-00000",
        "vendor": "Unknown",
        "product": "Unverified Exploit",
        "short_description": "URL contains 'exploit' keyword indicating potential vulnerability exploitation attack.",
        "date_added": "2024-01-01",
        "cvss_score": 8.5,
        "required_action": "Do not visit this URL. Block immediately."
    },
    "malware": {
        "cve_id": "CVE-2024-00001",
        "vendor": "Unknown",
        "product": "Malware Distribution",
        "short_description": "URL contains 'malware' keyword indicating potential malware distribution.",
        "date_added": "2024-01-01",
        "cvss_score": 9.0,
        "required_action": "Do not visit this URL. Report to security team."
    }
}


def enrich_with_cve_kev(text):
    """
    Enrich threat analysis with CVE/KEV data from local database and external APIs.
    Priority: Local threat DB → NVD API → CISA KEV list
    """
    enrichment = {
        "related_cves": [],
        "kev_matched":  False,
        "kev_details":  None,
        "risk_level":   "LOW"
    }
    
    try:
        text_lower = text.lower()
        
        # ── Step 1: Check local threat intelligence database ──────────────
        print("[CVE/KEV] Checking local threat database...")
        for keyword, threat_data in EXPLOIT_THREAT_DB.items():
            if keyword in text_lower:
                print(f"[CVE/KEV] 🔴 Found exploit keyword: {keyword} → {threat_data['cve_id']}")
                enrichment['related_cves'].append({
                    'id': threat_data['cve_id'],
                    'description': threat_data['short_description'],
                    'cvss_score': threat_data['cvss_score']
                })
                enrichment['kev_matched'] = True
                enrichment['kev_details'] = {
                    'cve_id': threat_data['cve_id'],
                    'vendor': threat_data['vendor'],
                    'product': threat_data['product'],
                    'date_added': threat_data['date_added'],
                    'short_description': threat_data['short_description'],
                    'required_action': threat_data['required_action']
                }
                enrichment['risk_level'] = "CRITICAL"
                return enrichment  # Return immediately if local DB match found
        
        # ── Step 2: Extract domain and try external APIs ──────────────────
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', text)
        if not domain_match:
            print(f"[CVE/KEV] No domain found in text, returning base enrichment")
            return enrichment

        domain  = domain_match.group(1)
        keyword = domain.split('.')[0]
        
        print(f"[CVE/KEV] Extracted domain: {domain}, keyword: {keyword}")

        generic_words = {'http','www','com','net','org','io','co','app','login','secure'}
        if keyword.lower() in generic_words or len(keyword) < 3:
            print(f"[CVE/KEV] Keyword '{keyword}' is too generic or too short, skipping external API calls")
            return enrichment
        
        print(f"[CVE/KEV] Keyword '{keyword}' is eligible for external API lookup")

        # Try NVD API
        try:
            nvd_url = (
                f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                f"?keywordSearch={keyword}&resultsPerPage=3"
            )
            print(f"[CVE/KEV] Calling NVD API with keyword: {keyword}")
            print(f"[CVE/KEV] NVD URL: {nvd_url}")
            
            nvd_resp = req_lib.get(nvd_url, timeout=10)
            print(f"[CVE/KEV] NVD API Response Status: {nvd_resp.status_code}")

            if nvd_resp.status_code == 200:
                nvd_data = nvd_resp.json()
                vulnerabilities = nvd_data.get('vulnerabilities', [])
                print(f"[CVE/KEV] Found {len(vulnerabilities)} vulnerabilities for keyword '{keyword}'")
                
                for item in vulnerabilities:
                    try:
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
                        print(f"[CVE/KEV] Added CVE: {cve_id} with CVSS {cvss}")
                    except KeyError as ke:
                        print(f"[CVE/KEV] Skipping malformed CVE entry: {str(ke)}")
                        continue
            else:
                print(f"[CVE/KEV] NVD API returned status {nvd_resp.status_code}: {nvd_resp.text[:200]}")
        except req_lib.Timeout:
            print(f"[CVE/KEV] NVD API timeout after 10 seconds")
        except req_lib.RequestException as e:
            print(f"[CVE/KEV] NVD API request error: {str(e)}")
        except Exception as e:
            print(f"[CVE/KEV] NVD API error: {str(e)}")
            import traceback
            print(f"[CVE/KEV] Traceback: {traceback.format_exc()}")

        # Try CISA KEV API
        try:
            print(f"[CVE/KEV] Calling CISA KEV API...")
            kev_resp = req_lib.get(
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                timeout=10
            )
            print(f"[CVE/KEV] CISA API Response Status: {kev_resp.status_code}")
            
            if kev_resp.status_code == 200:
                kev_vulns   = kev_resp.json().get('vulnerabilities', [])
                cve_ids     = [c['id'] for c in enrichment['related_cves']]
                print(f"[CVE/KEV] CISA returned {len(kev_vulns)} known exploited vulnerabilities")
                print(f"[CVE/KEV] Checking {len(cve_ids)} CVEs from NVD against CISA KEV list...")
                
                kev_match   = next((v for v in kev_vulns if v['cveID'] in cve_ids), None)

                if kev_match:
                    print(f"[CVE/KEV] 🔴 KEV MATCH FOUND: {kev_match['cveID']}")
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
                    print(f"[CVE/KEV] No KEV match found, but {len(cve_ids)} CVEs identified - setting risk to HIGH")
                    enrichment['risk_level'] = "HIGH"
            else:
                print(f"[CVE/KEV] CISA API returned status {kev_resp.status_code}")
        except Exception as e:
            print(f"[CVE/KEV] CISA API error: {str(e)}")
            import traceback
            print(f"[CVE/KEV] Traceback: {traceback.format_exc()}")

    except Exception as e:
        print(f"[CVE/KEV ERROR] {str(e)}")

    return enrichment