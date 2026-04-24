"""
SMSNotificationChannel - SMS notification channel implementation.
"""

# --- Python Standard Library ---
import logging

# --- Third-Party Libraries ---

# --- Project Imports ---
from .base_channel import BaseNotificationChannel
from src.stockreports.alert.model.models import AlertNotification

class SMSNotificationChannel(BaseNotificationChannel):
    def _send(self, notification: AlertNotification) -> None:
        # TODO: Integrate actual SMS sending logic here
        logging.info(f"[SMS] Sending notification: {notification}")

    def validate_config(self) -> None:
        # TODO: Validate SMS config (Twilio credentials, phone numbers)
        pass
