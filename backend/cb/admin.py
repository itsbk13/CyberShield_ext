from django.contrib import admin

# Register your models here.

from .models import ScannedMessage

admin.site.register(ScannedMessage)
