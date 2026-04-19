import requests
import json
import time

# Wait a moment for server to be fully ready
time.sleep(2)

base_url = 'http://127.0.0.1:8000/cb/analyze_text/'

# Test scenarios
tests = [
    {
        'name': 'TEST A - Generic Phishing (GREEN panel expected)',
        'text': 'http://phishing-generic-bank.com/login'
    },
    {
        'name': 'TEST B - Phishing with CVE but NO KEV (ORANGE panel expected)',
        'text': 'http://phishing-wordpress-vulnerability.com/plugin'
    },
    {
        'name': 'TEST C - Phishing with CVE + KEV Match (RED panel expected)',
        'text': 'http://phishing-log4j-jndi.com/api'
    }
]

def extract_relevant_fields(response_data, test_name):
    """Extract and display relevant fields from response"""
    print(f"\n{'='*70}")
    print(f"{test_name}")
    print(f"{'='*70}")
    
    # Display relevant fields
    fields_to_show = [
        'alert',
        'panel_color',
        'risk_level',
        'kev_matched'
    ]
    
    for field in fields_to_show:
        if field in response_data:
            print(f"{field}: {response_data[field]}")
    
    # Show related_cves count if present
    if 'related_cves' in response_data:
        print(f"related_cves count: {len(response_data['related_cves'])}")
    
    # Show threat_intelligence info
    if 'threat_intelligence' in response_data:
        ti = response_data['threat_intelligence']
        print(f"threat_intelligence.status: {ti.get('status', 'N/A')}")
        if 'message' in ti:
            print(f"threat_intelligence.message: {ti.get('message', 'N/A')}")
        if 'vendor' in ti or 'product' in ti:
            print(f"threat_intelligence.vendor: {ti.get('vendor', 'N/A')}")
            print(f"threat_intelligence.product: {ti.get('product', 'N/A')}")
    
    # Show CVE info if present
    if 'cves' in response_data and response_data['cves']:
        print(f"CVEs found: {len(response_data['cves'])}")
        if response_data['cves']:
            print(f"First CVE: {response_data['cves'][0]}")

# Run all three tests
for i, test in enumerate(tests, 1):
    try:
        response = requests.post(base_url, json={'text': test['text']}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            extract_relevant_fields(data, test['name'])
        else:
            print(f"\n{test['name']}")
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"\n{test['name']}")
        print(f"ERROR: {str(e)}")

print(f"\n{'='*70}")
print("SUMMARY: Panel Color Progression")
print(f"{'='*70}")
print("Expected progression: GREEN -> ORANGE -> RED")
print("Based on threat severity: Generic -> CVE but no KEV -> CVE + KEV")
