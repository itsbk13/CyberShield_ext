from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ScannedMessage
from .serializers import ScannedMessageSerializer
from .utils import predict_spam, enrich_with_cve_kev
from decouple import config
from django.http import HttpResponse
from django.views.decorators.http import require_GET


@require_GET
@csrf_exempt
def get_mistral_key(request):
    mistral_key = config('MISTRAL_API_KEY')
    if not mistral_key:
        return HttpResponse("API key not configured", status=500)
    return HttpResponse(mistral_key, content_type="text/plain")


@csrf_exempt
@api_view(['POST', 'OPTIONS'])
def analyze_text(request):
    # Handle preflight OPTIONS request for CORS
    if request.method == 'OPTIONS':
        response = Response()
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type, Accept'
        return response

    if request.method != 'POST':
        response = Response({"error": "Method not allowed—use POST"}, status=405)
        response['Access-Control-Allow-Origin'] = '*'
        return response

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
        if not text or text == "0":
            response = Response({"error": "No text provided"}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

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
            enrichment = enrich_with_cve_kev(text)
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
        response['Access-Control-Allow-Origin'] = '*'
        return response

    except ValueError as e:
        print(f"JSON parse error: {str(e)}")
        response = Response({"error": f"Invalid JSON: {str(e)}"}, status=400)
        response['Access-Control-Allow-Origin'] = '*'
        return response
    except Exception as e:
        print(f"Error in analyze_text: {str(e)}")
        response = Response({"error": f"Server error: {str(e)}"}, status=500)
        response['Access-Control-Allow-Origin'] = '*'
        return response
