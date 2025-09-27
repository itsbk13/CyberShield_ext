

from django.urls import path
from .views import analyze_text

urlpatterns = [
    path('analyze/', analyze_text, name='analyze-text'),
]
