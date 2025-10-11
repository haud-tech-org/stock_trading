# src/stockreports/notification/notification_manager.py
import logging

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.utils.email_utils import send_email, format_email_subject, format_email_body
from src.stockreports.utils.sms_utils import send_sms, format_sms_body
from src.stockreports.utils.ntfy_utils import send_ntfy_notification

class NotificationManager:
    """
    Manages the sending of all types of notifications (Email, SMS, Ntfy).
    """
    def __init__(self):
        """
        Initializes the NotificationManager.
        """
        self.notification_settings = loader.get_notification_settings()
        self.logger = logging.getLogger(__name__)

    def send_alert(self, notification: AlertNotification):
        """
        Sends an alert notification through all configured and enabled channels.

        Args:
            notification (AlertNotification): The alert notification object to send.
        """
        # --- Send Ntfy Notification ---
        if self.notification_settings.NTFY_ENABLED:
            try:
                send_ntfy_notification(notification)
            except Exception as e:
                self.logger.error(f"An unexpected error occurred while sending ntfy notification: {e}", exc_info=True)

        # --- Send Email Notification ---
        if self.notification_settings.EMAIL_ENABLED:
            if all([self.notification_settings.EMAIL_SENDER, (self.notification_settings.EMAIL_RECEIVERS or self.notification_settings.EMAIL_BCC_RECEIVERS), self.notification_settings.EMAIL_APP_PASSWORD]):
                try:
                    subject = format_email_subject(notification)
                    body = format_email_body(notification)
                    send_email(subject, body)
                    self.logger.info(f"Successfully dispatched email for {notification.approach} signal.")
                except Exception as e:
                    self.logger.error(f"Failed to send email for {notification.approach} signal: {e}", exc_info=True)
            else:
                self.logger.warning("Email is enabled, but sender/receiver/password is not fully configured. Skipping email.")

        # --- Send SMS Notification ---
        if self.notification_settings.TWILIO_ENABLED:
            try:
                sms_body = format_sms_body(notification)
                send_sms(sms_body)
            except Exception as e:
                self.logger.error(f"An unexpected error occurred while sending SMS: {e}", exc_info=True)
