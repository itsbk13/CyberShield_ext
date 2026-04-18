import os
import re
import joblib
import requests as req_lib
from django.conf import settings

# Paths to the model files
PHISHING_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_model.pkl')
PHISHING_VECTORIZER_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_vectorizer.pkl')
FRAUD_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'ieee_fraud_model.pkl')

# Load the phishing model and vectorizer
try:
    with open(PHISHING_MODEL_PATH, 'rb') as f:
        PHISHING_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_model.pkl: {str(e)}")

try:
    with open(PHISHING_VECTORIZER_PATH, 'rb') as f:
        PHISHING_VECTORIZER = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_vectorizer.pkl: {str(e)}")

# Load the fraud model (optional, for future use)
try:
    with open(FRAUD_MODEL_PATH, 'rb') as f:
        FRAUD_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load ieee_fraud_model.pkl: {str(e)}")


def predict_spam(text):
    """
    Predict if the text is phishing or fraud.
    Args:
        text (str): The input text to analyze (e.g., URL or message).
    Returns:
        dict: {'is_phishing': bool, 'is_fraud': bool, 'phishing_prob': float, 'fraud_prob': float}
    """
    try:
        print(f"Predicting for text: {text}")  # Debug log
        is_phishing = False
        is_fraud = False
        phishing_prob = 0.0
        fraud_prob = 0.0

        # Check for phishing (URL-based)
        if "http" in text.lower():
            print("Processing as URL for phishing check")
            text_vectorized = PHISHING_VECTORIZER.transform([text])
            print("Text vectorized successfully")
            phishing_pred_proba = PHISHING_MODEL.predict_proba(text_vectorized)[0]
            print(f"Phishing prediction: {phishing_pred_proba}")
            phishing_prob = phishing_pred_proba[1] * 100  # Probability of phishing (class 1)
            is_phishing = bool(PHISHING_MODEL.predict(text_vectorized)[0])  # 1 (bad) -> True, 0 (good) -> False

        # Check for fraud-related patterns (keyword-based weighted scoring)
        fraud_keywords = [
            "transfer", "investment", "overdue", "upi", "bank", "return on investment",
            "pay immediately", "unknown person", "too good to be true", "sent", "received",
            "payment", "money", "claim", "prize", "fee"
        ]
        text_lower = text.lower()

        # Check if the text is just a numeric amount (e.g., "$500")
        is_numeric_amount = text_lower.startswith("$") and text_lower[1:].replace(".", "").isdigit()

        # Weighted fraud scoring: 15% per matched keyword, max 95%
        matched_keywords = [kw for kw in fraud_keywords if kw in text_lower]
        if matched_keywords or is_numeric_amount:
            fraud_prob = min(len(matched_keywords) * 15.0, 95.0) if matched_keywords else 60.0
            is_fraud = fraud_prob >= 45.0  # 3+ keywords triggers fraud flag
            print(f"Fraud keywords matched: {matched_keywords}, score: {fraud_prob}")

        return {
            'is_phishing': is_phishing,
            'is_fraud': is_fraud,
            'phishing_prob': phishing_prob,
            'fraud_prob': fraud_prob
        }
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")


def enrich_with_cve_kev(text):
    """
    Extract domain/vendor keyword from a URL and cross-reference:
    - NVD API for related CVEs with CVSS scores
    - CISA KEV list to flag actively exploited vulnerabilities

    This enrichment layer converts a raw phishing detection into actionable
    threat intelligence — identifying not just that a URL is malicious, but
    WHICH known vulnerability it may be exploiting and whether it is
    actively being weaponized in the wild (KEV status).

    Used by SOC analysts for phishing triage and remediation prioritization.

    Args:
        text (str): The phishing URL to enrich.
    Returns:
        dict: {
            'related_cves': list of CVE dicts with id, description, cvss_score,
            'kev_matched': bool,
            'kev_details': dict or None,
            'risk_level': str ('LOW' | 'HIGH' | 'CRITICAL')
        }
    """
    enrichment = {
        "related_cves": [],
        "kev_matched": False,
        "kev_details": None,
        "risk_level": "LOW"
    }

    try:
        # Extract domain keyword from URL (e.g., "paypal" from fake-paypal.com)
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', text)
        if not domain_match:
            return enrichment

        domain = domain_match.group(1)
        keyword = domain.split('.')[0]  # e.g., "fake-paypal" -> "fake-paypal"

        # Skip generic/noise keywords
        generic_words = {'http', 'www', 'com', 'net', 'org', 'io', 'co', 'app', 'login', 'secure'}
        if keyword.lower() in generic_words or len(keyword) < 3:
            return enrichment

        # Step 1: Query NVD API for related CVEs (free, no auth required)
        nvd_url = (
            f"https://services.nvd.nist.gov/rest/json/cves/2.0"
            f"?keywordSearch={keyword}&resultsPerPage=3"
        )
        nvd_resp = req_lib.get(nvd_url, timeout=6)

        if nvd_resp.status_code == 200:
            cves_data = nvd_resp.json().get('vulnerabilities', [])
            for item in cves_data:
                cve_id = item['cve']['id']
                descriptions = item['cve'].get('descriptions', [])
                desc = descriptions[0]['value'][:150] if descriptions else "No description available."

                # Extract CVSS score (prefer v3.1, fallback to v2)
                metrics = item['cve'].get('metrics', {})
                cvss_score = None
                if 'cvssMetricV31' in metrics:
                    cvss_score = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                elif 'cvssMetricV2' in metrics:
                    cvss_score = metrics['cvssMetricV2'][0]['cvssData']['baseScore']

                enrichment['related_cves'].append({
                    'id': cve_id,
                    'description': desc,
                    'cvss_score': cvss_score
                })

        # Step 2: Cross-reference with CISA KEV (Known Exploited Vulnerabilities)
        # KEV = vulnerabilities being actively exploited in the wild RIGHT NOW
        kev_resp = req_lib.get(
            "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
            timeout=6
        )
        if kev_resp.status_code == 200:
            kev_vulns = kev_resp.json().get('vulnerabilities', [])
            cve_ids_found = [c['id'] for c in enrichment['related_cves']]

            # Check if any of our CVEs are on the KEV list
            kev_match = next(
                (v for v in kev_vulns if v['cveID'] in cve_ids_found),
                None
            )

            if kev_match:
                enrichment['kev_matched'] = True
                enrichment['kev_details'] = {
                    'cve_id': kev_match['cveID'],
                    'vendor': kev_match['vendorProject'],
                    'product': kev_match['product'],
                    'date_added': kev_match['dateAdded'],
                    'short_description': kev_match['shortDescription'],
                    'required_action': kev_match.get('requiredAction', 'Apply vendor patch immediately.')
                }
                enrichment['risk_level'] = "CRITICAL"
            elif enrichment['related_cves']:
                enrichment['risk_level'] = "HIGH"

    except Exception as e:
        print(f"CVE/KEV enrichment error: {str(e)}")

    return enrichment
