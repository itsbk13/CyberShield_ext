<div align="center">

# 🛡️ CyberShield v2.0
### AI-Powered Scam & Threat Detection Browser Extension

[![Python](https://img.shields.io/badge/Python-3.13.1-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-5.2.6-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![Gemini](https://img.shields.io/badge/Gemini-3.1_Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-red?style=flat-square)](https://github.com/itsbk13/CyberShield_ext)

**CyberShield** is a Chrome browser extension that detects phishing, fraud, and scams in real-time using a custom ML model, Google Gemini 3.1 Flash AI, CISA KEV intelligence, and live NVD CVE enrichment — all through a conversational chat interface.

</div>

---

## 📋 Table of Contents

- [What's New in v2.0](#-whats-new-in-v20)
- [How It Works](#-how-it-works)
- [Architecture](#-architecture)
- [CVE/KEV Intelligence Engine](#-cvekev-intelligence-engine)
- [VENDOR_MAP Reference](#-vendor_map-reference)
- [Repository Structure](#-repository-structure)
- [Tech Stack](#-tech-stack)
- [Setup & Installation](https://github.com/itsbk13/CyberShield_ext/blob/main/CONTRIBUTING.md)
- [API Endpoints](#-api-endpoints)
- [Threat Risk Levels](#-threat-risk-levels)
- [Extension Features](#-extension-features)
- [Contributing](https://github.com/itsbk13/CyberShield_ext/blob/main/CONTRIBUTING.md)
- [License](#-license)

---

## 🚀 What's New in v2.0

| Feature | v2.0 |
|---|---|
| Fraud Detection | ✅ ML + Enhanced Datasets + Gemini refinement |
| AI Chat | ✅ New Gemini 3.1 Flash |
| CVE Intelligence | ✅ Live NVD API (CRITICAL only) |
| KEV Cross-Reference | ✅ CISA KEV live feed |
| Direct CVE Injection | ✅ 30+ named exploits (Log4Shell, EternalBlue…) |
| Threat Panel UI | ✅ Collapsible color-coded panel |
| Multi-Language  | ✅ 15 languages via Google Translate |
| Response Caching | ✅ 24h TTL CVE cache |
| Token Auth  | ✅ Bearer token on all endpoints |

---

## ⚙️ How It Works

```
User Input (Extension)
        │
        ▼
  Translate to English (if non-English)
        │
        ▼
  POST /cb/analyze_text/  ────────────────────────────────────┐
        │                                                     │
        ▼                                                     ▼
  ML Model Prediction                              enrich_with_cve_kev(text)
   (phishing / fraud / safe)                                  │
        │                                         ┌────────────────────┐
        │                                         ▼                    ▼
        │                               VENDOR_MAP match          fallback
        │                                      │                domain extract
        │                          mode=direct    mode=nvd       
        │                                 │          │ 
        │                                 ▼          ▼
        │                          inject CVE    NVD API (CRITICAL)
        │                                 │          │
        │                                 └────┬─────┘
        │                                      ▼
        │                               CISA KEV cross-ref
        │                                      │
        └──────────────────────┬───────────────┘
                               ▼
                    Combined JSON Response
                               │
                               ▼
            Gemini 3.1 Flash conversational response (chat)
                               │
                               ▼
              Translate response back (if non-English)
                               │
                               ▼
            Threat Panel + Chat UI rendered in popup
```

---

## 🏗️ Architecture

```
Browser Extension (popup.js)
        │  Bearer Token Auth
        │  POST /cb/analyze_text/
        │  GET  /cb/get_gemini_key/
        ▼
Django REST Backend (views.py)
        │
        ├── ML Model (joblib)  ←── TF-IDF + SGD (Logistic Regression)
        │
        └── enrich_with_cve_kev()
                │
                ├── VENDOR_MAP lookup  (direct CVE inject / NVD search)
                ├── cve_cache (24h TTL)
                ├── NVD API  ← services.nvd.nist.gov
                └── CISA KEV ← cisa.gov/known_exploited_vulnerabilities.json
```

---

## 🔍 CVE/KEV Intelligence Engine

The `enrich_with_cve_kev()` function in `cb/views.py` runs two parallel intelligence flows:

### Flow 1 — Direct CVE Injection (`mode: direct`)
For famous named exploits, the CVE is **injected directly** without calling NVD, since NVD sometimes defers or delays these entries:

- `log4shell` / `log4j` → `CVE-2021-44228`
- `eternalblue` / `wannacry` / `ms17-010` → `CVE-2017-0144`
- `proxylogon` → `CVE-2021-26855`
- `zerologon` → `CVE-2020-1472`
- `bluekeep` → `CVE-2019-0708`
- `heartbleed` → `CVE-2014-0160`
- `shellshock` → `CVE-2014-6271`
- `printnightmare` → `CVE-2021-34527`
- Direct CVE ID input (e.g. `CVE-2021-44228`) also supported

### Flow 2 — NVD API Search (`mode: nvd`)
For vendor/product keywords (e.g. `confluence`, `citrix`, `vmware`), queries NVD API with `cvssV3Severity=CRITICAL` (CVSS ≥ 9.0 only).

### CISA KEV Cross-Reference
After CVEs are collected (either flow), **every CVE is cross-checked** against the live CISA KEV feed. A match triggers:
- `kev_matched: true`
- `risk_level: CRITICAL`
- Full KEV metadata returned (`vendor`, `product`, `date_added`, `required_action`)

### Caching
All results are cached per keyword with a **24-hour TTL** to avoid hammering NVD/CISA on repeated queries.

---

## 🗺️ VENDOR_MAP Reference

The `VENDOR_MAP` dictionary in `views.py` maps text keywords to CVE lookup strategy:

```python
# mode=direct  → skip NVD, inject CVE ID
# mode=nvd     → search NVD API with keyword

VENDOR_MAP = {
    "log4j":      {"mode": "direct", "cve": "CVE-2021-44228", "nvd_kw": "log4j"},
    "confluence":  {"mode": "nvd",    "nvd_kw": "atlassian confluence"},
    # ... 80+ entries covering major vendors and CVEs
}
```

**Covered vendors (nvd mode):** Apache, Atlassian, Citrix, Cisco, Docker, Drupal, Elasticsearch, F5 BIG-IP, Firefox, Fortinet, GitLab, Jenkins, jQuery, Joomla, Kubernetes, Microsoft (Exchange, SharePoint, Outlook, Teams, Windows), Nginx, OpenSSL, OpenSSH, Oracle WebLogic, PayPal/Amazon, PHP, phpMyAdmin, Pulse Secure, Redis, Safari/WebKit, Samba, SolarWinds, Spring, Sudo, Tomcat, VMware, WordPress, Zoom

---

## 📁 Repository Structure

```
CyberShield_ext/
│
├── README.md                         ← You are here
├── LICENSE                           ← MIT License
│
├── v1_ext/                           ← Legacy v1.0 (reference only)
│
└── v2.0_ext/
    ├── CyberShield_ML(Model).ipynb   ← Model training notebook
    │
    ├── Datasets/
    │   ├── PhiUSIIL phishing dataset (Direct Fetch)
    │   └── spam_ham_dataset.csv
    │
    ├── backend/                      ← Django REST API
    │   ├── manage.py
    │   ├── .env                      ← GEMINI_API_KEY, SECRET_KEY
    │   ├── requirements.txt
    │   ├── backend/              ← Django project config
    │   │   ├── settings.py
    │   │   ├── urls.py               ← Root URL config
    │   │   └── wsgi.py
    │   └── cb/                       ← Main app
    │       ├── views.py              ← All API logic + CVE/KEV engine
    │       ├── urls.py               ← App URL routing
    │       ├── models.py
    │       ├── models/             ← Trained ML model (joblib)
    │       └── migrations/
    │
    └── extension/                    ← Chrome Extension
        ├── manifest.json             ← MV3 permissions & config
        ├── popup.html                ← Extension UI
        ├── popup.js                  ← Full chat + Gemini + threat logic
        ├── popup.css                 ← Threat panel + chat styles
        └── icons/

```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Extension | Chrome MV3, Vanilla JS |
| AI / Chat | Google Gemini 3.1 Flash (`gemini-3.1-flash-lite-preview`) |
| Backend | Django 5.2.6, Python 3.13.1 |
| ML Model | Scikit-learn (TF-IDF + SGDClassifier) |
| Datasets | [PhiUSIIL phishing dataset](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset) , [spam_ham_dataset.csv](https://www.kaggle.com/datasets/meruvulikith/190k-spam-ham-email-dataset-for-classification)|
| CVE Data | NIST NVD API v2.0 |
| KEV Data | CISA Known Exploited Vulnerabilities Feed |
| Translation | Google Translate (free API) |
| Auth | Bearer Token |
| Caching | In-memory Django cache (24h TTL) |

---

## 🎨 Threat Risk Levels

| Level | Trigger | Panel Colour | Badge |
|---|---|---|---|
| **LOW** | No threats / chat mode | Green | `SAFE` |
| **MEDIUM** | ML probability 34–66% | Amber | `MEDIUM` |
| **HIGH** | ML probability 67%+ or CRITICAL CVEs (no KEV match) | Red | `HIGH` |
| **CRITICAL** | CISA KEV match found | Deep Red | `CRITICAL` |

The header badge, chat container border, and Threat Intelligence Panel all respond to the risk level in real-time.

---

## 🧩 Extension Features

| Feature | Description |
|---|---|
| **Analyse Mode Toggle** | ON = full ML + CVE/KEV scan. OFF = pure Gemini chat |
| **Threat Intelligence Panel** | Collapsible panel showing CVE list + KEV details |
| **Threat Level Badge** | Header badge + chat border colour changes with risk level |
| **Language Selector** | Dropdown to switch UI+analysis language |
| **Timestamp per message** | Every chat bubble shows HH:MM time |

---

## 📡 API Endpoints

All endpoints require:
```
Authorization: Bearer cybershield_extension_token
```

### `POST /cb/analyze_text/`

Analyze text for phishing/fraud + CVE/KEV enrichment.

**Request:**
```json
{
  "text": "Urgent: Your PayPal account has been compromised. Click here to verify."
}
```

**Response:**
```json
{
  "is_phishing": true,
  "is_fraud": false,
  "probability": 92,
  "advice": "Do not click any links. Contact PayPal directly.",
  "threat_intelligence": {
    "related_cves": [
      {
        "id": "CVE-2021-44228",
        "description": "Apache Log4j2 RCE vulnerability...",
        "cvss_score": 10.0
      }
    ],
    "kev_matched": true,
    "kev_details": {
      "cve_id": "CVE-2021-44228",
      "vendor": "Apache",
      "product": "Log4j2",
      "date_added": "2021-12-10",
      "short_description": "Apache Log4j2 allows RCE...",
      "required_action": "Apply vendor patches immediately."
    },
    "risk_level": "CRITICAL"
  }
}
```

### `GET /cb/get_gemini_key/`

Returns the Gemini API key for the extension to use directly.

**Response:**
```json
{ "key": "AIza..." }
```

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with ❤️ by [@itsbk13](https://github.com/itsbk13)
