from django.urls import path
from .views import analyze_text, get_gemini_key

urlpatterns = [
    path('analyze_text/', analyze_text, name='analyze-text'),
    path('get_gemini_key/', get_gemini_key, name='get_gemini_key'),
]