from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ScannedMessage
from .serializers import ScannedMessageSerializer
from .utils import predict_spam, enrich_with_cve_kev
from decouple import config
from django.http import JsonResponse
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

    if not re.match(r'^[\w\s\-._~:/?#\[\]@!$&\'()*+,;=%.]+$', text):
        raise ValueError("Text contains invalid characters")

    return text


@require_GET
@require_api_token
def get_gemini_key(request):
    gemini_key = config('GEMINI_API_KEY', default=None)
    if not gemini_key:
        return JsonResponse({"error": "Gemini API key not configured"}, status=500)
    return JsonResponse({"key": gemini_key}, status=200)


@api_view(['POST', 'OPTIONS'])
def analyze_text(request):
    if request.method == 'OPTIONS':
        return Response(status=200)

    if request.method != 'POST':
        return Response({"error": "Method not allowed—use POST"}, status=405)

    try:
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

        try:
            text = validate_text_input(text)
        except ValueError as e:
            return Response(
                {"error": f"Invalid input: {str(e)}"},
                status=400
            )

        if not text or text == "0":
            return Response({"error": "No text provided"}, status=400)

        # ── Step 1: ML-based threat classification ────────────────────────
        prediction  = predict_spam(text)
        is_phishing = prediction['is_phishing']
        is_fraud    = prediction['is_fraud']
        is_spam     = is_phishing or is_fraud

        # Save to DB
        message = ScannedMessage.objects.create(
            text=text,
            is_phishing=is_phishing,
            is_fraud=is_fraud
        )
        ScannedMessageSerializer(message)

        # Base response
        probability = prediction.get('phishing_prob', 0.0) if is_phishing else prediction.get('fraud_prob', 0.0)
        alert  = "🚨 Phishing Alert!" if is_phishing else "🚨 Fraud Alert!" if is_fraud else "✅ Safe"
        advice = "Avoid interacting with this message." if is_spam else "No threats detected."

        response_data = {
            "alert":       alert,
            "probability": float(probability),
            "advice":      advice
        }

        # ── Step 2: Safe — return early, no threat_intelligence ───────────
        if not is_spam:
            print("[VIEWS] Safe input detected — no threat_intelligence")
            return Response(response_data)

        # ── Step 3: Threat detected — run CVE/KEV enrichment ─────────────
        threat_intelligence = {
            "related_cves": [],
            "kev_matched":  False,
            "kev_details":  None,
            "risk_level":   "MEDIUM",
            "panel_color":  "green",
            "analyst_note": ""
        }

        print(f"[VIEWS] Threat detected — calling enrich_with_cve_kev for: {text}")
        enrichment = enrich_with_cve_kev(text)
        print(f"[VIEWS] Enrichment result: {enrichment}")

        related_cves = enrichment.get("related_cves", [])
        kev_matched  = enrichment.get("kev_matched", False)

        threat_intelligence["related_cves"] = related_cves
        threat_intelligence["kev_matched"]  = kev_matched

        if kev_matched:
            # 🔴 RED — CVE found AND on CISA KEV (actively exploited)
            threat_intelligence["panel_color"]  = "red"
            threat_intelligence["risk_level"]   = "CRITICAL"
            threat_intelligence["kev_details"]  = enrichment.get("kev_details")
            threat_intelligence["analyst_note"] = (
                "🚨 KEV MATCH CRITICAL: This vulnerability is actively exploited in the wild. "
                "Immediate patching required. Do not delay remediation."
            )
            print("[VIEWS] Panel color: RED (KEV match found)")

        elif related_cves:
            # 🟠 ORANGE — CVEs found but NOT on KEV
            highest_cvss = max([c.get('cvss_score') or 0 for c in related_cves], default=0)
            cve_count    = len(related_cves)

            threat_intelligence["panel_color"]  = "orange"
            threat_intelligence["risk_level"]   = "HIGH"
            threat_intelligence["kev_details"]  = {
                "status":          "CVE_FOUND_NO_KEV",
                "message":         f"Found {cve_count} related CVE(s) with highest CVSS {highest_cvss}",
                "cve_details":     "These CVEs are NOT in the CISA Known Exploited Vulnerabilities catalog",
                "recommendation":  "Apply patches based on CVE risk assessment. Monitor for exploit activity.",
                "highest_cvss":    highest_cvss,
                "cve_count":       cve_count
            }
            threat_intelligence["analyst_note"] = (
                f"⚠️ WARNING: {cve_count} CVE(s) detected but NOT actively exploited. "
                f"Highest CVSS: {highest_cvss}. Review and patch according to risk tolerance."
            )
            print("[VIEWS] Panel color: ORANGE (CVE found, no KEV match)")

        else:
            # 🟢 GREEN — No CVE, no KEV (generic phishing/fraud)
            threat_intelligence["panel_color"]  = "green"
            threat_intelligence["risk_level"]   = "MEDIUM"
            threat_intelligence["kev_details"]  = {
                "status":         "NO_KEV_MATCH",
                "message":        "No CVEs found in NVD for this threat pattern",
                "recommendation": "Monitor and apply available patches based on CVE risk assessment"
            }
            threat_intelligence["analyst_note"] = (
                "No known CVEs or active exploits detected. Generic threat with lower risk profile."
            )
            print("[VIEWS] Panel color: GREEN (no CVE match)")

        response_data["threat_intelligence"] = threat_intelligence
        return Response(response_data)

    except ValueError as e:
        print(f"Validation error: {str(e)}")
        return Response({"error": f"Invalid input: {str(e)}"}, status=400)

    except Exception as e:
        print(f"Error in analyze_text: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return Response({"error": "Internal server error: Analysis failed"}, status=500)