<div align="center">

# 🛡️ CyberShield v2.0
### AI-Powered Scam & Threat Detection Browser Extension

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Django](https://img.shields.io/badge/Django-4.x-092E20?style=flat-square&logo=django&logoColor=white)](https://djangoproject.com)
[![Gemini](https://img.shields.io/badge/Gemini-2.5_Flash-4285F4?style=flat-square&logo=google&logoColor=white)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-red?style=flat-square)](https://github.com/itsbk13/CyberShield_ext)

**CyberShield** is a Chrome browser extension that detects phishing, fraud, and scams in real-time using a custom ML model, Google Gemini 2.5 Flash AI, CISA KEV intelligence, and live NVD CVE enrichment — all through a conversational chat interface.

</div>

---

## 📋 Table of Contents

- [What's New in v2.0](#-whats-new-in-v20)
- [How It Works](#-how-it-works)
- [Architecture](#-architecture)
- [Repository Structure](#-repository-structure)
- [Tech Stack](#-tech-stack)
- [Setup & Installation](#-setup--installation)
- [API Endpoints](#-api-endpoints)
- [CVE/KEV Intelligence Engine](#-cvekev-intelligence-engine)
- [VENDOR_MAP Reference](#-vendor_map-reference)
- [Threat Risk Levels](#-threat-risk-levels)
- [Multi-Language Support](#-multi-language-support)
- [ML Model](#-ml-model)
- [Extension Features](#-extension-features)
- [Testing](#-testing)
- [Environment Variables](#-environment-variables)
- [Documentation Files](#-documentation-files)
- [Contributing](#-contributing)
- [License](#-license)

---

## 🚀 What's New in v2.0

| Feature | v1.0 | v2.0 |
|---|---|---|
| Fraud Detection | ✅ Basic ML | ✅ ML + Gemini refinement |
| AI Chat | ❌ | ✅ Gemini 2.5 Flash |
| CVE Intelligence | ❌ | ✅ Live NVD API (CRITICAL only) |
| KEV Cross-Reference | ❌ | ✅ CISA KEV live feed |
| Direct CVE Injection | ❌ | ✅ 30+ named exploits (Log4Shell, EternalBlue…) |
| Threat Panel UI | ❌ | ✅ Collapsible color-coded panel |
| Multi-Language | ❌ | ✅ 15 languages via Google Translate |
| Response Caching | ❌ | ✅ 24h TTL CVE cache |
| Token Auth | ❌ | ✅ Bearer token on all endpoints |

---

## ⚙️ How It Works

```
User Input (Extension)
        │
        ▼
  Translate to English (if non-English)
        │
        ▼
  POST /cb/analyze_text/  ──────────────────────────────────────────┐
        │                                                               │
        ▼                                                               ▼
  ML Model Prediction                              enrich_with_cve_kev(text)
   (phishing / fraud / safe)                                  │
        │                                           ┌──────────────────┤
        │                                           ▼                  ▼
        │                                 VENDOR_MAP match          fallback
        │                                 mode=direct           domain extract
        │                                 │     mode=nvd
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
  Gemini 2.5 Flash refinement (adjust probability)
                               │
                               ▼
  Gemini conversational response (chat)
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
        ├── ML Model (joblib)  ←── TF-IDF + Logistic Regression
        │
        └── enrich_with_cve_kev()
                │
                ├── VENDOR_MAP lookup  (direct CVE inject / NVD search)
                ├── cve_cache (24h TTL)
                ├── NVD API  ← services.nvd.nist.gov
                └── CISA KEV ← cisa.gov/known_exploited_vulnerabilities.json
```

---

## 📁 Repository Structure

```
CyberShield_ext/
│
├── README.md                         ← You are here
├── LICENSE                           ← MIT License
│
├── API_RESPONSE_EXAMPLES.md          ← Full JSON response samples
├── COLOR_CODED_PANEL_GUIDE.md        ← UI threat panel colour spec
├── FINAL_SUMMARY.md                  ← Complete v2.0 feature summary
├── KEV_ENRICHMENT_GUIDE.md           ← CVE/KEV engine deep-dive
├── KEV_RESPONSE_COMPARISON.md        ← Before/after KEV response diff
├── KEV_VERIFICATION_SUMMARY.md       ← KEV accuracy verification
├── QUICK_REFERENCE.md                ← Dev cheat-sheet
├── SECURITY_FIXES.md                 ← Security hardening notes
│
├── response_details.py               ← Advice/response text builder
├── test1.py                          ← Basic phishing tests
├── test2.py                          ← Fraud tests
├── test3.py                          ← Safe message tests
├── test_kev.py                       ← KEV pipeline unit tests
├── test_kev_full.py                  ← Full KEV flow integration
├── test_kev_panel.py                 ← UI panel rendering tests
├── test_multiple_cves.py             ← Multi-CVE response tests
├── test_orange_panel.py              ← HIGH-risk (non-KEV) panel tests
├── test_scenarios.py                 ← End-to-end scenario tests
├── test_summary.py                   ← Test result summary runner
│
├── v1_ext/                           ← Legacy v1.0 (reference only)
│
└── v2.0_ext/
    ├── CyberShield_ML(Model).ipynb   ← Model training notebook
    │
    ├── Datasets/
    │   ├── phishing_dataset.csv
    │   ├── fraud_dataset.csv
    │   └── safe_dataset.csv
    │
    ├── backend/                      ← Django REST API
    │   ├── manage.py
    │   ├── .env                      ← GEMINI_API_KEY, SECRET_KEY
    │   ├── requirements.txt
    │   ├── cybershield/              ← Django project config
    │   │   ├── settings.py
    │   │   ├── urls.py               ← Root URL config
    │   │   └── wsgi.py
    │   └── cb/                       ← Main app
    │       ├── views.py              ← All API logic + CVE/KEV engine
    │       ├── urls.py               ← App URL routing
    │       ├── models.py
    │       ├── model.pkl             ← Trained ML model (joblib)
    │       ├── vectorizer.pkl        ← TF-IDF vectorizer (joblib)
    │       └── migrations/
    │
    └── extension/                    ← Chrome Extension
        ├── manifest.json             ← MV3 permissions & config
        ├── popup.html                ← Extension UI
        ├── popup.js                  ← Full chat + Gemini + threat logic
        ├── popup.css                 ← Threat panel + chat styles
        └── icons/
            ├── icon16.png
            ├── icon48.png
            └── icon128.png
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Extension | Chrome MV3, Vanilla JS |
| AI / Chat | Google Gemini 2.5 Flash (`gemini-2.5-flash-preview-04-17`) |
| Backend | Django 4.x, Python 3.10+ |
| ML Model | Scikit-learn (TF-IDF + Logistic Regression) |
| CVE Data | NIST NVD API v2.0 |
| KEV Data | CISA Known Exploited Vulnerabilities Feed |
| Translation | Google Translate (free API) |
| Auth | Bearer Token |
| Caching | In-memory Django cache (24h TTL) |

---

## 🔧 Setup & Installation

### 1. Clone the repo

```bash
git clone https://github.com/itsbk13/CyberShield_ext.git
cd CyberShield_ext/v2.0_ext/backend
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

Create `v2.0_ext/backend/.env`:

```env
SECRET_KEY=your_django_secret_key
DEBUG=True
GEMINI_API_KEY=your_gemini_api_key_here
EXTENSION_API_TOKEN=cybershield_extension_token
```

### 4. Run migrations and start server

```bash
python manage.py migrate
python manage.py runserver
```

Backend runs at `http://127.0.0.1:8000`

### 5. Load extension in Chrome

1. Open `chrome://extensions/`
2. Enable **Developer Mode**
3. Click **Load unpacked**
4. Select `v2.0_ext/extension/`

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
- `spring4shell` → `CVE-2022-22965`
- `pwnkit` / `polkit` → `CVE-2021-4034`
- `dirtypipe` → `CVE-2022-0847`
- `sunburst` → `CVE-2020-10148`
- `follina` → `CVE-2022-30190`
- `text4shell` → `CVE-2022-42889`
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
    "exchange":    {"mode": "nvd",    "nvd_kw": "microsoft exchange"},
    # ... 80+ entries covering major vendors and CVEs
}
```

**Covered vendors (nvd mode):** Apache, Atlassian, Citrix, Cisco, Docker, Drupal, Elasticsearch, F5 BIG-IP, Firefox, Fortinet, GitLab, Jenkins, jQuery, Joomla, Kubernetes, Microsoft (Exchange, SharePoint, Outlook, Teams, Windows), Nginx, OpenSSL, OpenSSH, Oracle WebLogic, PayPal/Amazon, PHP, phpMyAdmin, Pulse Secure, Redis, Safari/WebKit, Samba, SolarWinds, Spring, Sudo, Tomcat, VMware, WordPress, Zoom

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

## 🌍 Multi-Language Support

CyberShield v2.0 supports **15 languages** via Google Translate:

| Language | Code | Language | Code |
|---|---|---|---|
| English | `en` | Hindi | `hi` |
| Tamil | `ta` | Deutsch | `de` |
| Telugu | `te` | Español | `es` |
| Malayalam | `ml` | Português | `pt` |
| Kannada | `kn` | Japanese | `ja` |
| Chinese | `zh` | Russian | `ru` |
| Arabic | `ar` | Korean | `ko` |
| Thai | `th` | | |

Input is translated → English for analysis → response translated back to the selected language.

---

## 🤖 ML Model

- **Algorithm:** Logistic Regression with TF-IDF vectorization
- **Training Notebook:** `v2.0_ext/CyberShield_ML(Model).ipynb`
- **Datasets:** `v2.0_ext/Datasets/` (phishing, fraud, safe CSVs)
- **Saved artifacts:** `cb/model.pkl` + `cb/vectorizer.pkl` (joblib)
- **Gemini Refinement:** Post-prediction, Gemini 2.5 Flash reviews the ML output and adjusts probability if context warrants it (format: `Refined Prediction: <type> with probability <X>%`)

---

## 🧩 Extension Features

| Feature | Description |
|---|---|
| **Analyse Mode Toggle** | ON = full ML + CVE/KEV scan. OFF = pure Gemini chat |
| **`@` Force Prefix** | Type `@your text` to force fraud detection even in chat mode |
| **Threat Intelligence Panel** | Collapsible panel showing CVE list + KEV details |
| **Scanning Indicator** | Animated pulse while backend is processing |
| **Typing Animation** | Bot responses render word-by-word |
| **Threat Level Badge** | Header badge + chat border colour changes with risk level |
| **Language Selector** | Dropdown to switch UI+analysis language |
| **Conversation History** | Full context sent to Gemini on every message |
| **Timestamp per message** | Every chat bubble shows HH:MM time |

---

## 🧪 Testing

Run individual test scripts from the repo root:

```bash
# Basic detection tests
python test1.py      # Phishing scenarios
python test2.py      # Fraud scenarios
python test3.py      # Safe message scenarios

# CVE/KEV pipeline tests
python test_kev.py            # KEV match / no-match unit test
python test_kev_full.py       # Full pipeline integration test
python test_kev_panel.py      # UI panel data structure test
python test_multiple_cves.py  # Multi-CVE response validation
python test_orange_panel.py   # HIGH risk (no KEV) panel test

# Scenario + summary
python test_scenarios.py      # End-to-end named exploit scenarios
python test_summary.py        # Aggregated test results
```

---

## 🔐 Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | ✅ | Django secret key |
| `DEBUG` | ✅ | `True` for dev, `False` for prod |
| `GEMINI_API_KEY` | ✅ | Google Gemini API key |
| `EXTENSION_API_TOKEN` | ✅ | Bearer token for extension auth |

---

## 📄 Documentation Files

| File | Contents |
|---|---|
| [`API_RESPONSE_EXAMPLES.md`](API_RESPONSE_EXAMPLES.md) | Full JSON response samples for all risk levels |
| [`COLOR_CODED_PANEL_GUIDE.md`](COLOR_CODED_PANEL_GUIDE.md) | Threat panel UI colour spec & CSS guide |
| [`FINAL_SUMMARY.md`](FINAL_SUMMARY.md) | Complete v2.0 feature inventory |
| [`KEV_ENRICHMENT_GUIDE.md`](KEV_ENRICHMENT_GUIDE.md) | Deep-dive into the CVE/KEV engine design |
| [`KEV_RESPONSE_COMPARISON.md`](KEV_RESPONSE_COMPARISON.md) | Before/after diff for KEV enrichment |
| [`KEV_VERIFICATION_SUMMARY.md`](KEV_VERIFICATION_SUMMARY.md) | Accuracy & reliability verification of KEV matching |
| [`QUICK_REFERENCE.md`](QUICK_REFERENCE.md) | Dev cheat-sheet (endpoints, tokens, test keywords) |
| [`SECURITY_FIXES.md`](SECURITY_FIXES.md) | Auth hardening, token validation, CORS notes |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push and open a Pull Request

Please follow existing code style and add tests for new functionality.

---

## 📜 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with 🛡️ by [@itsbk13](https://github.com/itsbk13)
