import requests, json
resp = requests.post('http://127.0.0.1:8000/cb/analyze_text/', 
  json={'text': 'http://cve-2017-5645-struts-rce.com/action'})
data = json.loads(resp.text)
ti = data.get('threat_intelligence', {})
print('=== TEST 2: Struts Phishing ===')
print(f'Alert: {data.get("alert")}')
if ti:
    cves = ti.get('related_cves', [])
    print(f'CVEs: {len(cves)}')
    for cve in cves[:2]:
        print(f'  • {cve["id"]}')
else:
    print('No threat intelligence')