import requests
import json
import time

time.sleep(1)
BASE_URL = 'http://127.0.0.1:8000/cb/analyze_text/'

tests = [
    {'name': 'SCENARIO 1 - Safe Email (no phishing)', 'text': 'Check your account at our official secure website: https://bank.com'},
    {'name': 'SCENARIO 2 - Generic Phishing (no CVE, no KEV)', 'text': 'http://phishing-fake-bank-login.com/verify'},
    {'name': 'SCENARIO 3 - Phishing WITH CVE but NO KEV match', 'text': 'http://phishing-struts-rce-server.com/api'},
    {'name': 'SCENARIO 4 - Phishing WITH BOTH CVE AND KEV match', 'text': 'http://phishing-log4j-jndi-exploit.com/api'},
]

for i, test in enumerate(tests, 1):
    print(f'\n{"="*80}')
    print(test['name'])
    print(f'{"="*80}')
    print(f"Request: {test['text']}")
    try:
        resp = requests.post(BASE_URL, json={'text': test['text']}, timeout=10)
        data = resp.json()
        print(f"panel_color: {data.get('panel_color', 'N/A')}")
        print(f"risk_level: {data.get('risk_level', 'N/A')}")
        print(f"kev_matched: {data.get('kev_matched', 'N/A')}")
        print(f"alert: {data.get('alert', 'N/A')}")
        print(f"related_cves: {data.get('related_cves', 'N/A')}")
        if 'threat_intelligence' in data:
            print(f"threat_intelligence: PRESENT")
            if data['threat_intelligence']:
                print(json.dumps(data['threat_intelligence'], indent=2))
        else:
            print(f"threat_intelligence: NOT PRESENT")
    except Exception as e:
        print(f'Error: {e}')
