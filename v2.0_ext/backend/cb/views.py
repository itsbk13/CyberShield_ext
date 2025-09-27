from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import ScannedMessage
from .serializers import ScannedMessageSerializer
from .utils import predict_spam
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
        print(f"Request data: {data}")  # Debug log
        if isinstance(data, str):
            text = data.strip()
        else:
            # Try to get 'url', 'amount', or 'text'
            text_value = data.get("url", data.get("amount", data.get("text", "")))
            if isinstance(text_value, (int, float)):
                # Convert numeric amount to string with $ prefix
                text = f"${float(text_value)}" if text_value != 0 else "0"  # Handle zero explicitly
            else:
                text = str(text_value).strip() if text_value is not None else ""

        print(f"Extracted text: '{text}'")  # Debug log
        if not text or text == "0":  # Treat "0" as invalid input
            response = Response({"error": "No text provided"}, status=400)
            response['Access-Control-Allow-Origin'] = '*'
            return response

        prediction = predict_spam(text)
        is_phishing = prediction['is_phishing']
        is_fraud = prediction['is_fraud']
        is_spam = is_phishing or is_fraud

        # Save to model
        message = ScannedMessage.objects.create(
            text=text,
            is_phishing=is_phishing,
            is_fraud=is_fraud
        )

        # Serialize (optional, for logging)
        response_serializer = ScannedMessageSerializer(message)

        # Format response for extension
        probability = prediction.get('phishing_prob', 0.0) if is_phishing else prediction.get('fraud_prob', 0.0)
        alert = "🚨 Phishing Alert!" if is_phishing else "🚨 Fraud Alert!" if is_fraud else "✅ Safe"
        advice = "Avoid interacting with this message." if is_spam else "No threats detected."

        response = Response({
            "alert": alert,
            "probability": float(probability),
            "advice": advice
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