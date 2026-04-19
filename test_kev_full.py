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

# Run all three tests
for i, test in enumerate(tests, 1):
    try:
        print(f"\n{'='*70}")
        print(f"{test['name']}")
        print(f"Input: {test['text']}")
        print(f"{'='*70}")
        
        response = requests.post(base_url, json={'text': test['text']}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(json.dumps(data, indent=2))
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"ERROR: {str(e)}")

