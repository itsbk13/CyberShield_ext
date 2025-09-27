# CyberShield V2.0

**CyberShield V2.0** is a comprehensive cybersecurity project that includes a browser extension and a backend system for detecting phishing attacks and fraudulent activities in real-time. It leverages an AI-powered chatbot with Mistral AI for advanced fraud detection and conversational support, making it a powerful tool for personal security.

---

## Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Folder Structure](#folder-structure)
- [Usage](#usage)
- [Technologies](#technologies)
- [License](#license)

---

## Features
- **Browser Extension**: Detects phishing attempts in real-time via a user-friendly popup interface.
- **Backend AI Models**: Powered by machine learning for fraud detection, including datasets:
  - Phishing detection [Learn more](https://www.kaggle.com/datasets/taruntiwarihp/phishing-site-urls/data)
  - IEEE fraud detection [Learn more](https://www.kaggle.com/c/ieee-fraud-detection)
- **AI Chatbot**: Integrates Mistral AI for conversational analysis, refining fraud predictions and providing natural language responses in over 100 languages.
- **Multilingual Support**: Supports detection and interaction in multiple languages using Google Translate API.
- **Easy-to-Use Interface**: Intuitive design with threat level indicators and scanning animations.
- **Structured, Modular Codebase**: Designed for easy maintenance and future enhancements.

---

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/itsbk13/Project_CyberShield_ext.git
cd Project_CyberShield_ext
```
### 2. Backend Setup
```bash
cd v2.0_ext/backend
# Install required Python packages
pip install -r requirements.txt
# Apply database migrations
python manage.py migrate
# Run Django server
python manage.py runserver
```
### 3. Extension Setup

- Open **Chrome/Edge** and go to **chrome://extensions/**
- Enable Developer mode
- Click Load unpacked and select the **v2.0_ext/extension** folder


## Folder Structure
```bash
v2.0_ext/
├── backend/       # Django backend with AI models and Mistral API integration
├── extension/     # Browser extension files (HTML, JS, CSS, icons)
└── README.md
```
## Usage

- Start the backend server.
- Load the browser extension.
- Interact with the extension:
  - Toggle the "Analyse" button to enable threat level analysis with the backend-trained model.
  - If "Analyse" is on, the AI chatbot will scan and respond with threat levels (Safe, Medium, High) and advice otherwise it will reply conversationally.
  - Switch languages using the dropdown to test multilingual support.
- Monitor the scanning indicator and threat level UI for real-time feedback when analysis is active.

## Technologies

- **Python, Django**: Backend framework with REST API for fraud analysis.
- **Machine Learning Models**: Pickle-based models for phishing and IEEE fraud detection.
- **Mistral AI**: Powers the chatbot for conversational fraud refinement and natural language processing.
- **Google Translate API**: Enables multilingual support for over 100 languages.
- **HTML, CSS, JavaScript**: Frontend for the browser extension with dynamic UI.
- **SQLite**: Lightweight database for backend storage.

## License
- This project is licensed under the GNU Affero General Public License v3.0.
- You may use and modify it for personal, non-commercial purposes, but any distribution (including as a service) requires the source code to be made available under the same license.
- Commercial use or sale is prohibited without explicit permission from the authors.
