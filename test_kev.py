import requests
import json
import time

# Give server a moment to fully initialize
time.sleep(3)

print("="*80)
print("CYBERSHIELD KEV ENRICHMENT TEST RESULTS")
print("="*80)

# Test 1: Log4j Known Exploit
print("\n" + "─"*80)
print("TEST 1: Log4j Known Exploit (CVE-2021-44228)")
print("─"*80)
print("Input URL: http://phishing-log4j-jndi.com/api\n")

try:
    resp1 = requests.post(
        'http://127.0.0.1:8000/cb/analyze_text/',
        json={'text': 'http://phishing-log4j-jndi.com/api'},
        timeout=10
    )
    data1 = resp1.json()
    print("Response Status:", resp1.status_code)
    print("\nThreat Intelligence Details:")
    if 'threat_intelligence' in data1:
        ti = data1['threat_intelligence']
        print(f"  kev_matched: {ti.get('kev_matched', 'N/A')}")
        print(f"  kev_details: {json.dumps(ti.get('kev_details', {}), indent=4)}")
        print(f"  risk_level: {ti.get('risk_level', 'N/A')}")
        print(f"  analyst_note: {ti.get('analyst_note', 'N/A')}")
    else:
        print(json.dumps(data1, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Test 2: Regular Phishing URL (NO KEV MATCH)
print("\n" + "─"*80)
print("TEST 2: Regular Phishing URL (NO KEV Match)")
print("─"*80)
print("Input URL: http://regular-phishing-bank.com/login\n")

try:
    resp2 = requests.post(
        'http://127.0.0.1:8000/cb/analyze_text/',
        json={'text': 'http://regular-phishing-bank.com/login'},
        timeout=10
    )
    data2 = resp2.json()
    print("Response Status:", resp2.status_code)
    print("\nThreat Intelligence Details:")
    if 'threat_intelligence' in data2:
        ti = data2['threat_intelligence']
        print(f"  kev_matched: {ti.get('kev_matched', 'N/A')}")
        print(f"  kev_details: {json.dumps(ti.get('kev_details', {}), indent=4)}")
        print(f"  risk_level: {ti.get('risk_level', 'N/A')}")
        print(f"  analyst_note: {ti.get('analyst_note', 'N/A')}")
    else:
        print(json.dumps(data2, indent=2))
except Exception as e:
    print(f"Error: {e}")

# Test 3: Struts Known Exploit
print("\n" + "─"*80)
print("TEST 3: Apache Struts Known Exploit (CVE-2017-5645)")
print("─"*80)
print("Input URL: http://phishing-struts-cve.com\n")

try:
    resp3 = requests.post(
        'http://127.0.0.1:8000/cb/analyze_text/',
        json={'text': 'http://phishing-struts-cve.com'},
        timeout=10
    )
    data3 = resp3.json()
    print("Response Status:", resp3.status_code)
    print("\nThreat Intelligence Details:")
    if 'threat_intelligence' in data3:
        ti = data3['threat_intelligence']
        print(f"  kev_matched: {ti.get('kev_matched', 'N/A')}")
        print(f"  kev_details: {json.dumps(ti.get('kev_details', {}), indent=4)}")
        print(f"  risk_level: {ti.get('risk_level', 'N/A')}")
        print(f"  analyst_note: {ti.get('analyst_note', 'N/A')}")
    else:
        print(json.dumps(data3, indent=2))
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("TEST EXECUTION COMPLETED")
print("="*80)
