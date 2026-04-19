import requests, json
resp = requests.post('http://127.0.0.1:8000/cb/analyze_text/', 
  json={'text': 'http://jenkins-vulnerability-scanner.com/cli'})
data = json.loads(resp.text)
ti = data.get('threat_intelligence', {})
print('=== TEST 3: Jenkins URL ===')
print(f'Alert: {data.get("alert")}')
if ti and ti.get('related_cves'):
    cves = ti['related_cves']
    print(f'CVEs: {len(cves)}')
    for cve in cves:
        print(f'  • {cve["id"]} (CVSS: {cve["cvss_score"]})')
else:
    print('No CVEs found (may be too generic)')