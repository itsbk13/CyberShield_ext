from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ScannedMessage
from .serializers import ScannedMessageSerializer
from .utils import predict_spam, enrich_with_cve_kev
from decouple import config
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_GET
from functools import wraps
import re


def require_api_token(view_func):
    """Decorator to require Bearer token authentication for sensitive endpoints"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {"error": "Unauthorized: Bearer token required"},
                status=401
            )
        return view_func(request, *args, **kwargs)
    return wrapper


def validate_text_input(text, max_length=2000):
    """Validate and sanitize text input"""
    if not isinstance(text, str):
        raise ValueError("Text must be a string")
    
    text = text.strip()
    
    if not text:
        raise ValueError("Text cannot be empty")
    
    if len(text) > max_length:
        raise ValueError(f"Text exceeds maximum length of {max_length} characters")
    
    # Basic sanitization - allow alphanumeric, common URL characters, and punctuation
    if not re.match(r'^[\w\s\-._~:/?#\[\]@!$&\'()*+,;=%.]+$', text):
        raise ValueError("Text contains invalid characters")
    
    return text


@require_GET
@require_api_token
def get_mistral_key(request):
    """Protected endpoint to retrieve Mistral API key - requires Bearer token"""
    mistral_key = config('MISTRAL_API_KEY', default=None)
    if not mistral_key:
        return JsonResponse(
            {"error": "API key not configured"},
            status=500
        )
    # Return key for authenticated requests (extension will provide Bearer token)
    return JsonResponse(
        {"key": mistral_key},
        status=200
    )


@api_view(['POST', 'OPTIONS'])
def analyze_text(request):
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        return Response(status=200)

    if request.method != 'POST':
        return Response({"error": "Method not allowed—use POST"}, status=405)

    try:
        # Handle request data
        data = request.data
        print(f"Request data: {data}")
        if isinstance(data, str):
            text = data.strip()
        else:
            text_value = data.get("url", data.get("amount", data.get("text", "")))
            if isinstance(text_value, (int, float)):
                text = f"${float(text_value)}" if text_value != 0 else "0"
            else:
                text = str(text_value).strip() if text_value is not None else ""

        print(f"Extracted text: '{text}'")
        
        # Validate and sanitize input
        try:
            text = validate_text_input(text)
        except ValueError as e:
            return Response(
                {"error": f"Invalid input: {str(e)}"},
                status=400
            )
        
        if not text or text == "0":
            return Response({"error": "No text provided"}, status=400)

        # Step 1: ML-based threat classification
        prediction = predict_spam(text)
        is_phishing = prediction['is_phishing']
        is_fraud = prediction['is_fraud']
        is_spam = is_phishing or is_fraud

        # Save to DB
        message = ScannedMessage.objects.create(
            text=text,
            is_phishing=is_phishing,
            is_fraud=is_fraud
        )
        ScannedMessageSerializer(message)  # Serialize for logging

        # Format base response
        probability = prediction.get('phishing_prob', 0.0) if is_phishing else prediction.get('fraud_prob', 0.0)
        alert = "🚨 Phishing Alert!" if is_phishing else "🚨 Fraud Alert!" if is_fraud else "✅ Safe"
        advice = "Avoid interacting with this message." if is_spam else "No threats detected."

        # Step 2: CVE/KEV threat intelligence enrichment (only for phishing URLs)
        # This layer maps detected phishing URLs to known CVEs and checks
        # the CISA KEV list to identify actively exploited vulnerabilities.
        # Designed for SOC analysts performing phishing triage.
        threat_intelligence = {
            "related_cves": [],
            "kev_matched": False,
            "kev_details": None,
            "risk_level": "LOW",
            "analyst_note": ""
        }

        if is_phishing and "http" in text.lower():
            print(f"[VIEWS] Calling enrich_with_cve_kev for phishing URL: {text}")
            enrichment = enrich_with_cve_kev(text)
            print(f"[VIEWS] Enrichment result: {enrichment}")
            threat_intelligence["related_cves"] = enrichment.get("related_cves", [])
            threat_intelligence["kev_matched"] = enrichment.get("kev_matched", False)
            threat_intelligence["kev_details"] = enrichment.get("kev_details", None)
            threat_intelligence["risk_level"] = enrichment.get("risk_level", "LOW")

            if enrichment.get("kev_matched"):
                threat_intelligence["analyst_note"] = (
                    "KEV MATCH: This vulnerability is actively exploited in the wild. "
                    "Immediate patching required. Do not delay remediation."
                )
            elif enrichment.get("related_cves"):
                threat_intelligence["analyst_note"] = (
                    "Related CVEs found. Review CVSS scores and apply patches "
                    "according to your organization's risk tolerance."
                )

        response = Response({
            "alert": alert,
            "probability": float(probability),
            "advice": advice,
            "threat_intelligence": threat_intelligence
        })
        return response

    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return Response(
            {"error": f"Invalid input: {str(e)}"},
            status=400
        )
    except Exception as e:
        print(f"Error in analyze_text: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        # Don't expose detailed error messages in production
        return Response(
            {"error": "Internal server error: Analysis failed"},
            status=500
        )
