from rest_framework import serializers
from .models import ScannedMessage

class ScannedMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScannedMessage
        fields = ['id', 'text', 'is_phishing', 'is_fraud', 'scanned_at']
