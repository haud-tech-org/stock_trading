# src/stockreports/notification/notification_manager.py
import logging
import json
import pandas as pd

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification, AlertResult
from src.stockreports.utils.notification.email_utils import send_email, format_email_subject, format_email_body
from src.stockreports.utils.notification.sms_utils import send_sms, format_sms_body
from src.stockreports.utils.notification.ntfy_utils import send_ntfy_notification
from src.stockreports.utils.alert_utils import get_primary_suggested_price
from src.stockreports.notification.close_position_scheduler import update_latest_signal
from src.stockreports.alert.common.constants import Approach

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
        self.alerts_sent_in_session = set()

    def process_and_notify(self, result: AlertResult, symbol: str):
        """
        Processes the latest alert from a result and sends notifications if applicable.
        This method checks for duplicates before sending and does not modify the input result.
        The 'suggested_price' is expected to be pre-calculated in the result.
        """
        if not result.has_alerts:
            return

        latest_alert_row = result.alerts.sort_values(by='alert_time', ascending=False).iloc[0]
        alert_key = (result.approach_name, latest_alert_row['alert_time'])

        if alert_key in self.alerts_sent_in_session:
            self.logger.info(f"Alert for {result.approach_name} at {latest_alert_row['alert_time']} already sent. Skipping.")
            return

        self.logger.info(f"Latest alert from {result.approach_name}: {latest_alert_row['signal']} at {latest_alert_row['alert_price']:.2f}")
        
        details_dict = {}
        if pd.notna(latest_alert_row.get('details')) and isinstance(latest_alert_row.get('details'), str):
            try:
                details_dict = json.loads(latest_alert_row['details'])
            except json.JSONDecodeError:
                self.logger.warning(f"Could not decode details JSON: {latest_alert_row['details']}")

        # Use the new utility function to get the single, correct price for the notification.
        suggested_price = get_primary_suggested_price(latest_alert_row)

        suggested_profit_threshold = latest_alert_row['suggested_profit_threshold'] if 'suggested_profit_threshold' in latest_alert_row else None

        # Ensure alert_time is a datetime object before creating the notification
        alert_time_obj = pd.to_datetime(latest_alert_row['alert_time'])

        notification = AlertNotification(
            symbol=symbol,
            signal=latest_alert_row['signal'],
            alert_price=latest_alert_row['alert_price'],
            alert_time=alert_time_obj,
            approach=latest_alert_row['approach'],
            details=details_dict,
            suggested_price=suggested_price,
            suggested_profit_threshold=suggested_profit_threshold
        )
        
        self._send_alert(notification)
        
        # Add to session after successful dispatch to avoid re-sending
        self.alerts_sent_in_session.add(alert_key)

    def _send_alert(self, notification: AlertNotification):
        """
        Sends an alert notification through all configured and enabled channels.

        Args:
            notification (AlertNotification): The alert notification object to send.
        """
        # --- Update the close position scheduler ---
        # This will store the latest signal and reset the timer if a new one comes in.
        # We check if the notification's approach is one of the valid trading strategies.
        valid_approaches = [value for key, value in vars(Approach).items() if not key.startswith('__')]
        if notification.approach in valid_approaches:
            update_latest_signal(notification)

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
