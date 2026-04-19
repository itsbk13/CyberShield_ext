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
GEMINI_API_KEY=your_gemini_api_key_here
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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push and open a Pull Request

Please follow existing code style and add tests for new functionality.
