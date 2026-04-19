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
PHISHING_MODEL_PATH        = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_model.pkl')
PHISHING_SCALER_PATH       = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_scaler.pkl')
FRAUD_TEXT_MODEL_PATH      = os.path.join(settings.BASE_DIR, 'cb', 'model', 'fraud_text_model.pkl')
FRAUD_TEXT_VECTORIZER_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'fraud_text_vectorizer.pkl')

# ── Load All Models at Startup ───────────────────────────────────────────────
try:
    PHISHING_MODEL   = joblib.load(PHISHING_MODEL_PATH)
    PHISHING_SCALER  = joblib.load(PHISHING_SCALER_PATH)
    FRAUD_TEXT_MODEL = joblib.load(FRAUD_TEXT_MODEL_PATH)
    FRAUD_VECTORIZER = joblib.load(FRAUD_TEXT_VECTORIZER_PATH)
    print("✅ All models loaded successfully")
except Exception as e:
    raise Exception(f"Model load failed: {str(e)}")


# ── URL Feature Extractor (matches PhiUSIIL column order) ───────────────────
def extract_url_features(url):
    import pandas as pd

    if not url.lower().startswith("http"):
        url = "http://" + url

    parsed = urlparse(url)
    domain = parsed.netloc or ""
    path   = parsed.path or ""
    tld    = domain.split('.')[-1] if '.' in domain else ""
    full   = url.lower()

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

    cols = PHISHING_MODEL.feature_columns_
    return pd.DataFrame([[features.get(c, 0) for c in cols]], columns=cols)


# ── Main Prediction Function ─────────────────────────────────────────────────
def predict_spam(text):
    try:
        print(f"\n[predict_spam] Input: {text}")
        is_phishing   = False
        is_fraud      = False
        phishing_prob = 0.0
        fraud_prob    = 0.0

        is_url = ("." in text and " " not in text) or "http" in text.lower()

        if is_url:
            features_df   = extract_url_features(text)
            scaled        = PHISHING_SCALER.transform(features_df)
            pred          = PHISHING_MODEL.predict(scaled)[0]
            proba         = PHISHING_MODEL.predict_proba(scaled)[0]
            phishing_prob = round(float(proba[0]) * 100, 2)
            is_phishing   = (pred == 0)
            print(f"[phishing] pred={pred}, phishing_prob={phishing_prob}%")

        fraud_vec   = FRAUD_VECTORIZER.transform([text])
        fraud_pred  = FRAUD_TEXT_MODEL.predict(fraud_vec)[0]
        fraud_proba = FRAUD_TEXT_MODEL.predict_proba(fraud_vec)[0]
        fraud_prob  = round(float(fraud_proba[1]) * 100, 2)
        is_fraud    = bool(fraud_pred == 1)
        print(f"[fraud] pred={fraud_pred}, fraud_prob={fraud_prob}%")

        return {
            'is_phishing':   is_phishing,
            'is_fraud':      is_fraud,
            'phishing_prob': phishing_prob,
            'fraud_prob':    fraud_prob
        }

    except Exception as e:
        print(f"[predict_spam ERROR] {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")


# ── Vendor Keyword Map (keyword → NVD search term) ───────────────────────────
# mode "direct" → inject CVE ID directly, skip NVD (for famous/deferred CVEs)
# mode "nvd"    → search NVD API dynamically
VENDOR_MAP = {

    # ── Famous Named Exploits → Direct CVE (bypass NVD) ──────────────────────
    "log4j":          {"mode": "direct", "cve": "CVE-2021-44228", "nvd_kw": "log4j"},
    "log4shell":      {"mode": "direct", "cve": "CVE-2021-44228", "nvd_kw": "log4j"},
    "eternalblue":    {"mode": "direct", "cve": "CVE-2017-0144",  "nvd_kw": "SMBv1"},
    "wannacry":       {"mode": "direct", "cve": "CVE-2017-0144",  "nvd_kw": "SMBv1"},
    "ms17-010":       {"mode": "direct", "cve": "CVE-2017-0144",  "nvd_kw": "SMBv1"},
    "proxylogon":     {"mode": "direct", "cve": "CVE-2021-26855", "nvd_kw": "microsoft exchange"},
    "proxyshell":     {"mode": "direct", "cve": "CVE-2021-34473", "nvd_kw": "microsoft exchange"},
    "zerologon":      {"mode": "direct", "cve": "CVE-2020-1472",  "nvd_kw": "netlogon"},
    "netlogon":       {"mode": "direct", "cve": "CVE-2020-1472",  "nvd_kw": "netlogon"},
    "bluekeep":       {"mode": "direct", "cve": "CVE-2019-0708",  "nvd_kw": "remote desktop"},
    "heartbleed":     {"mode": "direct", "cve": "CVE-2014-0160",  "nvd_kw": "openssl"},
    "shellshock":     {"mode": "direct", "cve": "CVE-2014-6271",  "nvd_kw": "bash"},
    "printnightmare": {"mode": "direct", "cve": "CVE-2021-34527", "nvd_kw": "windows print spooler"},
    "spring4shell":   {"mode": "direct", "cve": "CVE-2022-22965", "nvd_kw": "spring framework"},
    "springshell":    {"mode": "direct", "cve": "CVE-2022-22965", "nvd_kw": "spring framework"},
    "pwnkit":         {"mode": "direct", "cve": "CVE-2021-4034",  "nvd_kw": "polkit"},
    "polkit":         {"mode": "direct", "cve": "CVE-2021-4034",  "nvd_kw": "polkit"},
    "dirtyc0w":       {"mode": "direct", "cve": "CVE-2016-5195",  "nvd_kw": "linux kernel"},
    "dirtypipe":      {"mode": "direct", "cve": "CVE-2022-0847",  "nvd_kw": "linux kernel"},
    "sunburst":       {"mode": "direct", "cve": "CVE-2020-10148", "nvd_kw": "solarwinds orion"},
    "solarwinds":     {"mode": "direct", "cve": "CVE-2020-10148", "nvd_kw": "solarwinds"},
    "hafnium":        {"mode": "direct", "cve": "CVE-2021-26855", "nvd_kw": "microsoft exchange"},
    "equifax":        {"mode": "direct", "cve": "CVE-2017-5638",  "nvd_kw": "apache struts"},
    "struts":         {"mode": "direct", "cve": "CVE-2017-5638",  "nvd_kw": "apache struts"},
    "follina":        {"mode": "direct", "cve": "CVE-2022-30190", "nvd_kw": "microsoft support diagnostic"},
    "log4jshell":     {"mode": "direct", "cve": "CVE-2021-44228", "nvd_kw": "log4j"},
    "text4shell":     {"mode": "direct", "cve": "CVE-2022-42889", "nvd_kw": "apache commons text"},
    "commonstext":    {"mode": "direct", "cve": "CVE-2022-42889", "nvd_kw": "apache commons text"},
    "cve-2021-44228": {"mode": "direct", "cve": "CVE-2021-44228", "nvd_kw": "log4j"},
    "cve-2017-0144":  {"mode": "direct", "cve": "CVE-2017-0144",  "nvd_kw": "SMBv1"},
    "cve-2020-1472":  {"mode": "direct", "cve": "CVE-2020-1472",  "nvd_kw": "netlogon"},
    "cve-2021-26855": {"mode": "direct", "cve": "CVE-2021-26855", "nvd_kw": "microsoft exchange"},
    "cve-2019-0708":  {"mode": "direct", "cve": "CVE-2019-0708",  "nvd_kw": "remote desktop"},

    # ── Vendor/Product Keywords → NVD API search ─────────────────────────────
    "exchange":       {"mode": "nvd", "nvd_kw": "microsoft exchange"},
    "confluence":     {"mode": "nvd", "nvd_kw": "atlassian confluence"},
    "atlassian":      {"mode": "nvd", "nvd_kw": "atlassian"},
    "jira":           {"mode": "nvd", "nvd_kw": "atlassian jira"},
    "apache":         {"mode": "nvd", "nvd_kw": "apache"},
    "tomcat":         {"mode": "nvd", "nvd_kw": "apache tomcat"},
    "solr":           {"mode": "nvd", "nvd_kw": "apache solr"},
    "openssl":        {"mode": "nvd", "nvd_kw": "openssl"},
    "spring":         {"mode": "nvd", "nvd_kw": "spring framework"},
    "citrix":         {"mode": "nvd", "nvd_kw": "citrix"},
    "fortinet":       {"mode": "nvd", "nvd_kw": "fortinet"},
    "fortigate":      {"mode": "nvd", "nvd_kw": "fortinet"},
    "fortissl":       {"mode": "nvd", "nvd_kw": "fortinet ssl vpn"},
    "pulse":          {"mode": "nvd", "nvd_kw": "pulse secure"},
    "vmware":         {"mode": "nvd", "nvd_kw": "vmware"},
    "cisco":          {"mode": "nvd", "nvd_kw": "cisco ios"},
    "weblogic":       {"mode": "nvd", "nvd_kw": "oracle weblogic"},
    "oracle":         {"mode": "nvd", "nvd_kw": "oracle"},
    "f5":             {"mode": "nvd", "nvd_kw": "f5 big-ip"},
    "bigip":          {"mode": "nvd", "nvd_kw": "f5 big-ip"},
    "gitlab":         {"mode": "nvd", "nvd_kw": "gitlab"},
    "jenkins":        {"mode": "nvd", "nvd_kw": "jenkins"},
    "wordpress":      {"mode": "nvd", "nvd_kw": "wordpress"},
    "drupal":         {"mode": "nvd", "nvd_kw": "drupal"},
    "joomla":         {"mode": "nvd", "nvd_kw": "joomla"},
    "phpmyadmin":     {"mode": "nvd", "nvd_kw": "phpmyadmin"},
    "nginx":          {"mode": "nvd", "nvd_kw": "nginx"},
    "openssh":        {"mode": "nvd", "nvd_kw": "openssh"},
    "docker":         {"mode": "nvd", "nvd_kw": "docker"},
    "kubernetes":     {"mode": "nvd", "nvd_kw": "kubernetes"},
    "redis":          {"mode": "nvd", "nvd_kw": "redis"},
    "elasticsearch":  {"mode": "nvd", "nvd_kw": "elasticsearch"},
    "microsoft":      {"mode": "nvd", "nvd_kw": "microsoft windows"},
    "sharepoint":     {"mode": "nvd", "nvd_kw": "microsoft sharepoint"},
    "outlook":        {"mode": "nvd", "nvd_kw": "microsoft outlook"},
    "teams":          {"mode": "nvd", "nvd_kw": "microsoft teams"},
    "zoom":           {"mode": "nvd", "nvd_kw": "zoom client"},
    "chrome":         {"mode": "nvd", "nvd_kw": "google chrome"},
    "firefox":        {"mode": "nvd", "nvd_kw": "mozilla firefox"},
    "safari":         {"mode": "nvd", "nvd_kw": "apple webkit"},
    "android":        {"mode": "nvd", "nvd_kw": "android"},
    "samba":          {"mode": "nvd", "nvd_kw": "samba"},
    "sudo":           {"mode": "nvd", "nvd_kw": "sudo"},
    "bash":           {"mode": "nvd", "nvd_kw": "bash"},
    "php":            {"mode": "nvd", "nvd_kw": "php"},
    "python":         {"mode": "nvd", "nvd_kw": "python"},
    "node":           {"mode": "nvd", "nvd_kw": "nodejs"},
    "jquery":         {"mode": "nvd", "nvd_kw": "jquery"},
    "log4net":        {"mode": "nvd", "nvd_kw": "log4net"},
    "paypal":         {"mode": "nvd", "nvd_kw": "paypal"},
    "amazon":         {"mode": "nvd", "nvd_kw": "amazon aws"},
    "rdp":            {"mode": "nvd", "nvd_kw": "remote desktop services"},
    "smb":            {"mode": "nvd", "nvd_kw": "SMBv1 microsoft"},
    "printer":        {"mode": "nvd", "nvd_kw": "windows print spooler"},
}


# ── API Response Caching Layer ────────────────────────────────────────────────
class APICache:
    def __init__(self, ttl_hours=24):
        self.cache       = {}
        self.ttl_seconds = ttl_hours * 3600

    def _hash_key(self, keyword):
        return hashlib.sha256(keyword.encode()).hexdigest()

    def get(self, keyword):
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
        key = self._hash_key(keyword)
        self.cache[key] = (data, datetime.now())
        print(f"[CACHE] STORE: {keyword}")

    def clear(self):
        self.cache.clear()
        print("[CACHE] Cleared all entries")


# Global cache instance
cve_cache = APICache(ttl_hours=24)


# ── CVE/KEV Enrichment ───────────────────────────────────────────────────────
def enrich_with_cve_kev(text):
    """
    Enrich threat with CVE/KEV intelligence.

    Flow:
    1. Match text against VENDOR_MAP
       - mode=direct  → inject CVE ID directly, skip NVD
       - mode=nvd     → query NVD API (CRITICAL CVSS 9.0+ only)
    2. Check cache (24h TTL)
    3. Cross-reference CVEs against CISA KEV list
    4. Cache and return enrichment
    """
    enrichment = {
        "related_cves": [],
        "kev_matched":  False,
        "kev_details":  None,
        "risk_level":   "LOW"
    }

    try:
        text_lower = text.lower()

        # ── Step 1: Match vendor/exploit keyword ──────────────────────────
        matched_key = None
        matched_cfg = None

        for key, cfg in VENDOR_MAP.items():
            if key in text_lower:
                matched_key = key
                matched_cfg = cfg
                print(f"[CVE/KEV] ✅ Matched: '{key}' → mode={cfg['mode']}")
                break

        # Fallback: extract raw domain/text keyword
        if not matched_key:
            domain_match = re.search(r'(?:https?://)?(?:www\.)?([^/\s.\-]+)', text)
            if domain_match:
                fallback = domain_match.group(1).lower()
                generic  = {'http','www','com','net','org','io','co','app',
                            'login','secure','mail','smtp','dns','api','web',
                            'site','host','the','and','for'}
                if fallback not in generic and len(fallback) >= 3:
                    matched_key = fallback
                    matched_cfg = {"mode": "nvd", "nvd_kw": fallback}
                    print(f"[CVE/KEV] Fallback keyword: '{fallback}'")

            if not matched_key:
                print(f"[CVE/KEV] No keyword matched for: '{text[:50]}'")
                return enrichment

        # ── Step 2: Cache check ───────────────────────────────────────────
        cached = cve_cache.get(matched_key)
        if cached:
            return cached

        # ── Step 3a: Direct CVE injection (skip NVD for known exploits) ───
        if matched_cfg["mode"] == "direct":
            direct_cve = matched_cfg["cve"]
            print(f"[CVE/KEV] 💉 Direct CVE inject: {direct_cve} (skipping NVD)")
            enrichment["related_cves"].append({
                "id":          direct_cve,
                "description": f"Known actively exploited vulnerability linked to '{matched_key}'. Cross-referencing CISA KEV.",
                "cvss_score":  9.8
            })

        # ── Step 3b: NVD API search (CRITICAL CVEs only, CVSS 9.0+) ───────
        elif matched_cfg["mode"] == "nvd":
            search_term = matched_cfg["nvd_kw"]
            try:
                nvd_url = (
                    f"https://services.nvd.nist.gov/rest/json/cves/2.0"
                    f"?keywordSearch={search_term}"
                    f"&cvssV3Severity=CRITICAL"
                    f"&resultsPerPage=20"
                )
                print(f"[CVE/KEV] → NVD API (CRITICAL only): {nvd_url}")
                nvd_resp = req_lib.get(nvd_url, timeout=15)
                print(f"[CVE/KEV] ← NVD Response: {nvd_resp.status_code}")

                if nvd_resp.status_code == 200:
                    vulnerabilities = nvd_resp.json().get('vulnerabilities', [])
                    print(f"[CVE/KEV] ✅ NVD Found {len(vulnerabilities)} CRITICAL CVE(s) for '{search_term}'")

                    for item in vulnerabilities:
                        try:
                            cve_id  = item['cve']['id']
                            descs   = item['cve'].get('descriptions', [])
                            desc    = descs[0]['value'][:200] if descs else "No description available"
                            metrics = item['cve'].get('metrics', {})
                            cvss    = None

                            if 'cvssMetricV31' in metrics and metrics['cvssMetricV31']:
                                cvss = metrics['cvssMetricV31'][0]['cvssData']['baseScore']
                            elif 'cvssMetricV2' in metrics and metrics['cvssMetricV2']:
                                cvss = metrics['cvssMetricV2'][0]['cvssData']['baseScore']

                            enrichment['related_cves'].append({
                                'id':          cve_id,
                                'description': desc,
                                'cvss_score':  cvss
                            })
                            print(f"[CVE/KEV]   • {cve_id} (CVSS: {cvss})")

                        except (KeyError, IndexError, TypeError) as ke:
                            print(f"[CVE/KEV]   ⚠ Skipping malformed CVE: {str(ke)}")
                            continue
                else:
                    print(f"[CVE/KEV] ⚠ NVD returned {nvd_resp.status_code}")

            except req_lib.Timeout:
                print(f"[CVE/KEV] ⚠ NVD timeout (>15s)")
            except req_lib.RequestException as e:
                print(f"[CVE/KEV] ⚠ NVD connection error: {type(e).__name__}")
            except json.JSONDecodeError:
                print(f"[CVE/KEV] ⚠ NVD returned invalid JSON")
            except Exception as e:
                print(f"[CVE/KEV] ⚠ NVD error: {str(e)[:100]}")

        # ── Step 4: CISA KEV cross-reference ─────────────────────────────
        if enrichment['related_cves']:
            try:
                print(f"[CVE/KEV] → CISA KEV API: fetching known exploited vulnerabilities")
                kev_resp = req_lib.get(
                    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                    timeout=15
                )
                print(f"[CVE/KEV] ← CISA Response: {kev_resp.status_code}")

                if kev_resp.status_code == 200:
                    kev_vulns = kev_resp.json().get('vulnerabilities', [])
                    cve_ids   = [c['id'] for c in enrichment['related_cves']]
                    print(f"[CVE/KEV] ✅ CISA returned {len(kev_vulns)} KEV entries")
                    print(f"[CVE/KEV] Checking {len(cve_ids)} CVE(s) against KEV list...")

                    kev_match = next((v for v in kev_vulns if v['cveID'] in cve_ids), None)

                    if kev_match:
                        print(f"[CVE/KEV] 🔴 KEV MATCH: {kev_match['cveID']} — ACTIVELY EXPLOITED")
                        enrichment['kev_matched'] = True
                        enrichment['risk_level']  = "CRITICAL"
                        enrichment['kev_details'] = {
                            'cve_id':            kev_match['cveID'],
                            'vendor':            kev_match.get('vendorProject', 'Unknown'),
                            'product':           kev_match.get('product', 'Unknown'),
                            'date_added':        kev_match.get('dateAdded', 'Unknown'),
                            'short_description': kev_match.get('shortDescription', 'Actively exploited CVE'),
                            'required_action':   kev_match.get('requiredAction', 'Apply vendor patches immediately.')
                        }
                    else:
                        print(f"[CVE/KEV] 🟠 No KEV match — CVEs found but not actively exploited")
                        enrichment['risk_level'] = "HIGH"
                else:
                    print(f"[CVE/KEV] ⚠ CISA returned {kev_resp.status_code}")

            except req_lib.Timeout:
                print(f"[CVE/KEV] ⚠ CISA timeout (>15s)")
            except req_lib.RequestException as e:
                print(f"[CVE/KEV] ⚠ CISA connection error: {type(e).__name__}")
            except json.JSONDecodeError:
                print(f"[CVE/KEV] ⚠ CISA returned invalid JSON")
            except Exception as e:
                print(f"[CVE/KEV] ⚠ CISA error: {str(e)[:100]}")

        # ── Step 5: Cache and return ──────────────────────────────────────
        cve_cache.set(matched_key, enrichment)

    except Exception as e:
        print(f"[CVE/KEV ERROR] {str(e)}")
        import traceback
        print(f"[CVE/KEV] Traceback: {traceback.format_exc()[:500]}")

    return enrichment