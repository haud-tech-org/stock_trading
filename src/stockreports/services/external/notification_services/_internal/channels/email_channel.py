"""
EmailNotificationChannel - Email notification channel implementation.
"""




# --- Python Standard Library ---
import logging
import smtplib
import ssl
import json
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional, List

# --- Third-Party Libraries ---

# --- Project Imports ---
from .base_channel import BaseNotificationChannel
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.config import loader as config_loader

logger = logging.getLogger(__name__)


class EmailNotificationChannel(BaseNotificationChannel):
    def _send(self, notification: AlertNotification) -> bool:
        """
        Send an email notification for the given AlertNotification.
        """
        notification_settings = config_loader.get_notification_settings()
        subject = self.format_email_subject(notification)
        body = self.format_email_body(notification)
        sender_email: Optional[str] = notification_settings.EMAIL_SENDER
        sender_display_name: Optional[str] = notification_settings.EMAIL_SENDER_DISPLAY_NAME
        receiver_emails: List[str] = notification_settings.EMAIL_RECEIVERS or []
        bcc_receiver_emails: List[str] = notification_settings.EMAIL_BCC_RECEIVERS or []
        app_password: Optional[str] = notification_settings.EMAIL_APP_PASSWORD
        smtp_server: Optional[str] = notification_settings.EMAIL_SMTP_SERVER
        smtp_port: Optional[int] = notification_settings.EMAIL_SMTP_PORT

        all_recipients = receiver_emails + bcc_receiver_emails
        if not all([sender_email, all_recipients, app_password]):
            logger.warning("Email credentials or recipients are not fully configured. Skipping email.")
            return False

        message = MIMEMultipart()
        message['From'] = formataddr((sender_display_name, sender_email))
        to_header = ", ".join(receiver_emails) if receiver_emails else sender_email
        message['To'] = to_header
        message['Subject'] = subject
        message.add_header('Reply-To', sender_email)
        message.attach(MIMEText(body, 'plain'))

        return self._send_email_with_retry(
            sender_email=sender_email,
            receiver_emails=receiver_emails,
            bcc_receiver_emails=bcc_receiver_emails,
            app_password=app_password,
            smtp_server=smtp_server,
            smtp_port=smtp_port,
            message=message,
            max_retries=3,
            initial_delay=1.0
        )

    def validate_config(self) -> None:
        notification_settings = config_loader.get_notification_settings()
        sender: Optional[str] = notification_settings.EMAIL_SENDER
        app_password: Optional[str] = notification_settings.EMAIL_APP_PASSWORD
        if not all([sender, app_password]):
            raise ValueError("EmailNotificationChannel: EMAIL_SENDER and EMAIL_APP_PASSWORD must be set in notification_settings.py or environment.")

    @staticmethod
    def format_email_subject(notification: AlertNotification) -> str:
        suggested: str = "N/A"
        if notification.suggested_price is not None:
            try:
                suggested = f"{notification.suggested_price:.2f}"
            except Exception:
                suggested = str(notification.suggested_price)
        alert_price: str = "N/A"
        if notification.alert_price is not None:
            try:
                alert_price = f"{notification.alert_price:.2f}"
            except Exception:
                alert_price = str(notification.alert_price)
        profit_thresh: str = ""
        if notification.suggested_profit_threshold is not None:
            profit_thresh = f" | Profit Threshold: {notification.suggested_profit_threshold:.2f}"
        return f"{notification.signal} - {notification.symbol} - Suggest: {suggested} - {profit_thresh} - at signal price {alert_price} ({notification.approach})"

    @staticmethod
    def format_email_body(notification: AlertNotification) -> str:
        body = f"A new trading signal has been generated for {notification.symbol}.\n\n"
        alert_price: str = "N/A"
        if notification.alert_price is not None:
            try:
                alert_price = f"{notification.alert_price:.2f}"
            except Exception:
                alert_price = str(notification.alert_price)
        suggested_price: Optional[str] = None
        if notification.suggested_price is not None:
            try:
                suggested_price = f"{notification.suggested_price:.2f}"
            except Exception:
                suggested_price = str(notification.suggested_price)
        body += f"Signal:     {notification.signal}\nPrice:      {alert_price}\n"
        if suggested_price is not None:
            body += f"Suggested:  {suggested_price}\n"
        if notification.suggested_profit_threshold is not None:
            body += f"Profit Threshold: {notification.suggested_profit_threshold:.2f}\n"
        alert_time_str: str = "N/A"
        if notification.alert_time is not None:
            try:
                alert_time_str = notification.alert_time.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                alert_time_str = str(notification.alert_time)
        body += f"Time:       {alert_time_str}\nApproach:   {notification.approach}\n"
        if notification.details:
            body += "\n--- Details (JSON) ---\n"
            try:
                details_json = json.dumps(notification.details, indent=2, ensure_ascii=False)
                logger.debug(f"[EMAIL DEBUG] Alert details JSON for {notification.symbol}:\n{details_json}")
                body += details_json + "\n"
            except Exception as e:
                logger.debug(f"[EMAIL DEBUG] Could not format details as JSON for {notification.symbol}: {e}\nDetails: {notification.details}")
                body += f"[Could not format details as JSON: {e}]\n{str(notification.details)}\n"
        return body

    @staticmethod
    def _send_email_with_retry(
        sender_email: str,
        receiver_emails: List[str],
        bcc_receiver_emails: List[str],
        app_password: str,
        smtp_server: str,
        smtp_port: int,
        message: MIMEMultipart,
        max_retries: int = 3,
        initial_delay: float = 1.0
    ) -> bool:
        all_recipients = receiver_emails + bcc_receiver_emails
        retry_count = 0
        delay = initial_delay
        while retry_count <= max_retries:
            try:
                context = ssl.create_default_context()
                with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                    server.starttls(context=context)
                    server.login(sender_email, app_password)
                    server.sendmail(sender_email, all_recipients, message.as_string())
                    logger.info(f"Email sent successfully to: {', '.join(receiver_emails) if receiver_emails else ''} (BCC: {', '.join(bcc_receiver_emails) if bcc_receiver_emails else ''})")
                    return True
            except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
                retry_count += 1
                if retry_count <= max_retries:
                    logger.warning(f"Email send attempt {retry_count} failed with transient error: {type(e).__name__}: {e}. Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2
                else:
                    logger.error(f"Email send failed after {max_retries} retries. Last error: {type(e).__name__}: {e}", exc_info=True)
                    return False
            except Exception as e:
                logger.error(f"Email send failed with non-transient error: {type(e).__name__}: {e}", exc_info=True)
                return False
        return False
