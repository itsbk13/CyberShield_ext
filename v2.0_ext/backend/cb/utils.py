import os
import re
import joblib
import numpy as np
import requests as req_lib
from urllib.parse import urlparse
from django.conf import settings
from datetime import datetime, timedelta
import threading
import hashlib
import json

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
# REMOVED: Hardcoded EXPLOIT_THREAT_DB - Now using real-time API calls only


# ── API Response Caching Layer ────────────────────────────────────────────────
class APICache:
    """
    Simple in-memory cache for API responses with 24-hour TTL.
    Avoids rate limiting and improves performance for repeated lookups.
    """
    def __init__(self, ttl_hours=24):
        self.cache = {}
        self.ttl_seconds = ttl_hours * 3600
        
    def _hash_key(self, keyword):
        """Generate cache key from keyword"""
        return hashlib.sha256(keyword.encode()).hexdigest()
    
    def get(self, keyword):
        """Retrieve cached CVE data if available and not expired"""
        key = self._hash_key(keyword)
        if key not in self.cache:
            return None
        
        cached_data, timestamp = self.cache[key]
        elapsed = (datetime.now() - timestamp).total_seconds()
        
        if elapsed > self.ttl_seconds:
            del self.cache[key]
            print(f"[CACHE] Expired: {keyword}")
            return None
        
        print(f"[CACHE] HIT: {keyword} (age: {elapsed/60:.0f}m)")
        return cached_data
    
    def set(self, keyword, data):
        """Cache CVE data with timestamp"""
        key = self._hash_key(keyword)
        self.cache[key] = (data, datetime.now())
        print(f"[CACHE] STORE: {keyword}")
    
    def clear(self):
        """Clear all cached data"""
        self.cache.clear()
        print("[CACHE] Cleared all entries")


# Global cache instance
cve_cache = APICache(ttl_hours=24)



def enrich_with_cve_kev(text):
    """
    Enrich threat analysis with CVE/KEV data from external APIs only.
    NO hardcoded logic - uses real-time data from NVD and CISA.
    
    Flow:
    1. Extract keyword from URL
    2. Check cache first (24-hour TTL)
    3. Query NVD API for related CVEs
    4. Query CISA KEV list to check if actively exploited
    5. Cache result for future queries
    
    Returns:
        dict: related_cves, kev_matched, kev_details, risk_level
    """
    enrichment = {
        "related_cves": [],
        "kev_matched":  False,
        "kev_details":  None,
        "risk_level":   "LOW"
    }
    
    try:
        # ── Step 1: Extract keyword from URL ──────────────────────────────
        domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s]+)', text)
        if not domain_match:
            print(f"[CVE/KEV] No domain found in text, returning base enrichment")
            return enrichment

        domain  = domain_match.group(1)
        keyword = domain.split('.')[0]
        
        print(f"[CVE/KEV] Extracted domain: {domain}, keyword: {keyword}")

        # ── Step 2: Check cache first ─────────────────────────────────────
        cached_result = cve_cache.get(keyword)
        if cached_result:
            return cached_result

        # ── Step 3: Skip very generic or short keywords to avoid API noise ─
        generic_words = {'http','www','com','net','org','io','co','app','login','secure','mail','smtp','dns','api','web','site','host'}
        if keyword.lower() in generic_words or len(keyword) < 2:
            print(f"[CVE/KEV] Keyword '{keyword}' is too generic, skipping API calls")
            cve_cache.set(keyword, enrichment)  # Cache empty result
            return enrichment
        
        print(f"[CVE/KEV] Keyword '{keyword}' eligible for API lookup, proceeding with real-time data...")

        # ── Step 4: Query NVD API for CVEs ───────────────────────────────
        try:
            nvd_url = (
                f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                f"?keywordSearch={keyword}&resultsPerPage=5"
            )
            print(f"[CVE/KEV] → NVD API: GET {nvd_url}")
            
            nvd_resp = req_lib.get(nvd_url, timeout=15)
            print(f"[CVE/KEV] ← NVD Response: {nvd_resp.status_code}")

            if nvd_resp.status_code == 200:
                nvd_data = nvd_resp.json()
                vulnerabilities = nvd_data.get('vulnerabilities', [])
                print(f"[CVE/KEV] ✅ NVD Found {len(vulnerabilities)} CVE(s) for '{keyword}'")
                
                for item in vulnerabilities:
                    try:
                        cve_id = item['cve']['id']
                        descs  = item['cve'].get('descriptions', [])
                        desc   = descs[0]['value'][:200] if descs else "No description available"
                        metrics= item['cve'].get('metrics', {})
                        cvss   = None
                        
                        # Try to get CVSS 3.1 first, then 2.0 as fallback
                        if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                            cvss = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                        elif 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                            cvss = metrics['cvssMetricV2'][0]['cvssData']['baseScore']
                        
                        enrichment['related_cves'].append({
                            'id': cve_id, 
                            'description': desc, 
                            'cvss_score': cvss
                        })
                        print(f"[CVE/KEV]   • {cve_id} (CVSS: {cvss})")
                    except (KeyError, IndexError, TypeError) as ke:
                        print(f"[CVE/KEV]   ⚠ Skipping malformed CVE entry: {str(ke)}")
                        continue
            else:
                print(f"[CVE/KEV] ⚠ NVD API returned {nvd_resp.status_code}")
                
        except req_lib.Timeout:
            print(f"[CVE/KEV] ⚠ NVD API timeout (>15s)")
        except req_lib.RequestException as e:
            print(f"[CVE/KEV] ⚠ NVD API connection error: {type(e).__name__}")
        except json.JSONDecodeError:
            print(f"[CVE/KEV] ⚠ NVD API returned invalid JSON")
        except Exception as e:
            print(f"[CVE/KEV] ⚠ NVD API error: {str(e)[:100]}")

        # ── Step 5: Query CISA KEV list for active exploits ──────────────
        if enrichment['related_cves']:
            try:
                print(f"[CVE/KEV] → CISA KEV API: GET known exploited vulnerabilities list")
                
                kev_resp = req_lib.get(
                    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                    timeout=15
                )
                print(f"[CVE/KEV] ← CISA Response: {kev_resp.status_code}")
                
                if kev_resp.status_code == 200:
                    kev_data = kev_resp.json()
                    kev_vulns = kev_data.get('vulnerabilities', [])
                    cve_ids = [c['id'] for c in enrichment['related_cves']]
                    
                    print(f"[CVE/KEV] ✅ CISA returned {len(kev_vulns)} known exploited CVE(s)")
                    print(f"[CVE/KEV] Checking {len(cve_ids)} CVE(s) against KEV list...")
                    
                    # Check if any of our CVEs are in the KEV list
                    kev_match = next((v for v in kev_vulns if v['cveID'] in cve_ids), None)

                    if kev_match:
                        print(f"[CVE/KEV] 🔴 KEV MATCH FOUND: {kev_match['cveID']} - ACTIVELY EXPLOITED")
                        enrichment['kev_matched'] = True
                        enrichment['kev_details'] = {
                            'cve_id':            kev_match['cveID'],
                            'vendor':            kev_match.get('vendorProject', 'Unknown Vendor'),
                            'product':           kev_match.get('product', 'Unknown Product'),
                            'date_added':        kev_match.get('dateAdded', 'Unknown'),
                            'short_description': kev_match.get('shortDescription', 'Actively exploited CVE'),
                            'required_action':   kev_match.get('requiredAction', 'Apply vendor patches immediately.')
                        }
                        enrichment['risk_level'] = "CRITICAL"
                    else:
                        print(f"[CVE/KEV] 🟠 No KEV match - {len(cve_ids)} CVEs found but NOT actively exploited")
                        enrichment['risk_level'] = "HIGH" if cve_ids else "LOW"
                else:
                    print(f"[CVE/KEV] ⚠ CISA API returned {kev_resp.status_code}")
                    
            except req_lib.Timeout:
                print(f"[CVE/KEV] ⚠ CISA KEV API timeout (>15s)")
            except req_lib.RequestException as e:
                print(f"[CVE/KEV] ⚠ CISA KEV API connection error: {type(e).__name__}")
            except json.JSONDecodeError:
                print(f"[CVE/KEV] ⚠ CISA KEV API returned invalid JSON")
            except Exception as e:
                print(f"[CVE/KEV] ⚠ CISA KEV API error: {str(e)[:100]}")

        # ── Step 6: Cache result for future queries ──────────────────────
        cve_cache.set(keyword, enrichment)

    except Exception as e:
        print(f"[CVE/KEV ERROR] {str(e)}")
        import traceback
        print(f"[CVE/KEV] Traceback: {traceback.format_exc()[:500]}")

    return enrichment