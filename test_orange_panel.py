import requests
import json
import time

# Wait a moment for server to be fully ready
time.sleep(2)

base_url = 'http://127.0.0.1:8000/cb/analyze_text/'

# Test B REVISED - Phishing with CVE but NO KEV
test_data = {
    'name': 'TEST B REVISED - Phishing with CVE but NO KEV (trying to trigger ORANGE)',
    'text': 'http://phishing-tomcat-cve-2023.com/manager'
}

try:
    print(f"Testing: {test_data['name']}")
    print(f"Input: {test_data['text']}")
    print(f"{'='*80}")
    
    response = requests.post(base_url, json={'text': test_data['text']}, timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(json.dumps(data, indent=2))
        
        # Extract and highlight key fields
        print(f"\n{'='*80}")
        print("KEY FIELDS:")
        print(f"  panel_color: {data.get('panel_color', 'NOT FOUND')}")
        print(f"  risk_level: {data.get('risk_level', 'NOT FOUND')}")
        print(f"  kev_matched: {data.get('kev_matched', 'NOT FOUND')}")
        related_cves = data.get('related_cves', [])
        print(f"  related_cves: {related_cves}")
        if 'threat_intelligence' in data:
            print(f"  threat_intelligence.status: {data['threat_intelligence'].get('status', 'NOT FOUND')}")
            print(f"  threat_intelligence.kev_details: {data['threat_intelligence'].get('kev_details', 'NOT FOUND')}")
        print(f"  analyst_note: {data.get('analyst_note', 'NOT FOUND')}")
    else:
        print(f"ERROR: HTTP {response.status_code}")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"ERROR: {str(e)}")
