import requests, json
resp = requests.post("http://127.0.0.1:8000/cb/analyze_text/",
  json={"text": "http://log4j-cve-2021-44228-rce-exploit.com/jndi/ldap"})
data = json.loads(resp.text)
print("=== TEST 1: Log4j Phishing ===")
print(f"Status: {resp.status_code}")
print(f"Alert: {data.get(\"alert\")}")
ti = data.get("threat_intelligence", {})
print(f"Has threat_intelligence: {ti is not None}")
if ti:
    print(f"  CVEs: {len(ti.get(\"related_cves\", []))}")
    if ti.get("related_cves"):
        print(f"  First CVE: {ti[\"related_cves\"][0][\"id\"]}")
