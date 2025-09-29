'''import os
import joblib
from django.conf import settings

# Paths to the model files
PHISHING_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_model.pkl')
PHISHING_VECTORIZER_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_vectorizer.pkl')
FRAUD_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'ieee_fraud_model.pkl')

# Load the phishing model and vectorizer
try:
    with open(PHISHING_MODEL_PATH, 'rb') as f:
        PHISHING_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_model.pkl: {str(e)}")

try:
    with open(PHISHING_VECTORIZER_PATH, 'rb') as f:
        PHISHING_VECTORIZER = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_vectorizer.pkl: {str(e)}")

# Load the fraud model (optional, for future use)
try:
    with open(FRAUD_MODEL_PATH, 'rb') as f:
        FRAUD_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load ieee_fraud_model.pkl: {str(e)}")

def predict_spam(text):
    """
    Predict if the text is phishing or fraud.
    Args:
        text (str): The input text to analyze (e.g., URL or message).
    Returns:
        dict: {'is_phishing': bool, 'is_fraud': bool, 'phishing_prob': float, 'fraud_prob': float}
    """
    try:
        is_phishing = False
        is_fraud = False
        phishing_prob = 0.0
        fraud_prob = 0.0

        # Check for phishing (URL-based)
        if "http" in text.lower():
            text_vectorized = PHISHING_VECTORIZER.transform([text])
            phishing_pred_proba = PHISHING_MODEL.predict_proba(text_vectorized)[0]
            phishing_prob = phishing_pred_proba[1] * 100  # Probability of phishing (class 1)
            is_phishing = bool(PHISHING_MODEL.predict(text_vectorized)[0])  # 1 (bad) -> True, 0 (good) -> False

        # Check for fraud-related patterns (keyword-based)
        fraud_keywords = [
            "transfer", "investment", "overdue", "upi", "bank", "return on investment",
            "pay immediately", "unknown person", "too good to be true"
        ]
        text_lower = text.lower()
        has_fraud_keywords = any(keyword in text_lower for keyword in fraud_keywords)

        if has_fraud_keywords:
            fraud_prob = 90.0  # Heuristic probability
            is_fraud = True

        return {
            'is_phishing': is_phishing,
            'is_fraud': is_fraud,
            'phishing_prob': phishing_prob,
            'fraud_prob': fraud_prob
        }
    except Exception as e:
        raise Exception(f"Prediction error: {str(e)}")
'''
import os
import joblib
from django.conf import settings

# Paths to the model files
PHISHING_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_model.pkl')
PHISHING_VECTORIZER_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'phishing_vectorizer.pkl')
FRAUD_MODEL_PATH = os.path.join(settings.BASE_DIR, 'cb', 'model', 'ieee_fraud_model.pkl')

# Load the phishing model and vectorizer
try:
    with open(PHISHING_MODEL_PATH, 'rb') as f:
        PHISHING_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_model.pkl: {str(e)}")

try:
    with open(PHISHING_VECTORIZER_PATH, 'rb') as f:
        PHISHING_VECTORIZER = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load phishing_vectorizer.pkl: {str(e)}")

# Load the fraud model (optional, for future use)
try:
    with open(FRAUD_MODEL_PATH, 'rb') as f:
        FRAUD_MODEL = joblib.load(f)
except Exception as e:
    raise Exception(f"Failed to load ieee_fraud_model.pkl: {str(e)}")

def predict_spam(text):
    """
    Predict if the text is phishing or fraud.
    Args:
        text (str): The input text to analyze (e.g., URL or message).
    Returns:
        dict: {'is_phishing': bool, 'is_fraud': bool, 'phishing_prob': float, 'fraud_prob': float}
    """
    try:
        print(f"Predicting for text: {text}")  # Debug log
        is_phishing = False
        is_fraud = False
        phishing_prob = 0.0
        fraud_prob = 0.0

        # Check for phishing (URL-based)
        if "http" in text.lower():
            print("Processing as URL for phishing check")
            text_vectorized = PHISHING_VECTORIZER.transform([text])
            print("Text vectorized successfully")
            phishing_pred_proba = PHISHING_MODEL.predict_proba(text_vectorized)[0]
            print(f"Phishing prediction: {phishing_pred_proba}")
            phishing_prob = phishing_pred_proba[1] * 100  # Probability of phishing (class 1)
            is_phishing = bool(PHISHING_MODEL.predict(text_vectorized)[0])  # 1 (bad) -> True, 0 (good) -> False

        # Check for fraud-related patterns (keyword-based)
        fraud_keywords = [
            "transfer", "investment", "overdue", "upi", "bank", "return on investment",
            "pay immediately", "unknown person", "too good to be true", "sent", "received",
            "payment", "money", "claim", "prize", "fee"
        ]
        text_lower = text.lower()
        has_fraud_keywords = any(keyword in text_lower for keyword in fraud_keywords)

        # Check if the text is just a numeric amount (e.g., "$500")
        is_numeric_amount = text_lower.startswith("$") and text_lower[1:].replace(".", "").isdigit()

        if has_fraud_keywords or is_numeric_amount:
            print("Fraud keywords detected:", [kw for kw in fraud_keywords if kw in text_lower] if has_fraud_keywords else "Numeric amount detected")
            fraud_prob = 90.0  # Heuristic probability
            is_fraud = True

        return {
            'is_phishing': is_phishing,
            'is_fraud': is_fraud,
            'phishing_prob': phishing_prob,
            'fraud_prob': fraud_prob
        }
    except Exception as e:
        print(f"Prediction error: {str(e)}")
        raise Exception(f"Prediction error: {str(e)}")