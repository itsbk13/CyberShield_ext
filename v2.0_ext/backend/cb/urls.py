from django.urls import path
from .views import analyze_text
from .views import get_mistral_key

urlpatterns = [
    path('analyze/', analyze_text, name='analyze-text'),
    path('analyze/api/get-mistral-key/', get_mistral_key, name='get_mistral_key'),
]