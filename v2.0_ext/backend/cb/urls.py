from django.urls import path
from .views import analyze_text, get_mistral_key

urlpatterns = [
    path('analyze_text/', analyze_text, name='analyze-text'),
    path('get_mistral_key/', get_mistral_key, name='get_mistral_key'),
]