# portal/services/notification_service.py
from django.conf import settings
from pywebpush import webpush, WebPushException
import json


class NotificationService:
    def __init__(self):
        self.vapid_private_key = settings.VAPID_PRIVATE_KEY
        self.vapid_public_key = settings.VAPID_PUBLIC_KEY
        self.vapid_claims = {
            "sub": "mailto:imranounamir@gmail.com"  # Replace with your email
        }

    def send_push_notification(self, subscription_info, intervention_data):
        """Send push notification to a subscribed client"""
        try:
            intervention_title = intervention_data.get('title', 'New Intervention')
            intervention_time = intervention_data.get('time_from', '')

            notification_data = {
                "title": "New Intervention Assigned",
                "body": f"{intervention_title} at {intervention_time}",
                "icon": "/static/images/notification-icon.png",
                "data": {
                    "url": f"/interventions/{intervention_data.get('uid', '')}"
                }
            }

            webpush(
                subscription_info=subscription_info,
                data=json.dumps(notification_data),
                vapid_private_key=self.vapid_private_key,
                vapid_claims=self.vapid_claims
            )
            return True
        except WebPushException as e:
            print(f"Push notification failed: {str(e)}")
            return False
