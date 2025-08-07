# models.py
from django.db import models

class PushSubscription(models.Model):
    user_uid = models.CharField(max_length=100)
    subscription_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user_uid', 'subscription_data')