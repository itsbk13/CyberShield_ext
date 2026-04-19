import requests
import json
import time

time.sleep(2)

base_url = 'http://127.0.0.1:8000/cb/analyze_text/'

# Test multiple CVE patterns to find ORANGE trigger
test_urls = [
    'http://example.com/cve-2024-1234',
    'http://jenkins.com/cve-2024-12345',
    'http://tomcat-cve-2024.com/manager',
    'http://log4j.com/cve-2021-44228',
    'http://vulnerability-cve-2023-1234.com',
]

for text in test_urls:
    try:
        print(f"\nTesting: {text}")
        print("="*80)
        
        response = requests.post(base_url, json={'text': text}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            
            # Show nested panel_color
            panel_color = data.get('threat_intelligence', {}).get('panel_color', 'NOT FOUND')
            risk_level = data.get('threat_intelligence', {}).get('risk_level', 'NOT FOUND')
            kev_matched = data.get('threat_intelligence', {}).get('kev_matched', 'NOT FOUND')
            related_cves = data.get('threat_intelligence', {}).get('related_cves', [])
            analyst_note = data.get('threat_intelligence', {}).get('analyst_note', 'NOT FOUND')
            
            print(f"  panel_color: {panel_color}")
            print(f"  risk_level: {risk_level}")
            print(f"  kev_matched: {kev_matched}")
            print(f"  related_cves: {related_cves}")
            print(f"  analyst_note: {analyst_note}")
        else:
            print(f"  ERROR: HTTP {response.status_code}")
    except Exception as e:
        print(f"  ERROR: {str(e)}")
