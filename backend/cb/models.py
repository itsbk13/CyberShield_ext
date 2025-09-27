from django.db import models

# Create your models here.


class ScannedMessage(models.Model):
    text = models.TextField()
    is_phishing = models.BooleanField(default=False)
    is_fraud = models.BooleanField(default=False)
    scanned_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Phishing: {self.is_phishing}, Fraud: {self.is_fraud}"
