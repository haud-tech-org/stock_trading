# src/stockreports/utils/email_utils.py
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
import pandas as pd

# --- Settings Loader ---
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification
notification_settings = loader.get_notification_settings()


def format_email_subject(notification: AlertNotification) -> str:
    """Formats the subject for an email alert."""
    suggested = "N/A"
    try:
        if notification.suggested_price is not None:
            suggested = f"{notification.suggested_price:.2f}"
    except Exception:
        suggested = str(notification.suggested_price)

    alert_price = "N/A"
    try:
        if notification.alert_price is not None:
            alert_price = f"{notification.alert_price:.2f}"
    except Exception:
        alert_price = str(notification.alert_price)

    

    profit_thresh = ""
    if notification.suggested_profit_threshold is not None:
            profit_thresh = f" | Profit Threshold: {notification.suggested_profit_threshold:.2f}"
    return f"{notification.signal} - {notification.symbol} - Suggest: {suggested} - {profit_thresh} - at signal price {alert_price} ({notification.approach})"


def format_email_body(notification: AlertNotification) -> str:
    """Formats the body for an email alert."""
    body = f"A new trading signal has been generated for {notification.symbol}.\n\n"

    # Safely format numeric fields
    try:
        alert_price = f"{notification.alert_price:.2f}" if notification.alert_price is not None else "N/A"
    except Exception:
        alert_price = str(notification.alert_price)

    try:
        suggested_price = f"{notification.suggested_price:.2f}" if notification.suggested_price is not None else None
    except Exception:
        suggested_price = str(notification.suggested_price)

    body += f"Signal:     {notification.signal}\nPrice:      {alert_price}\n"
    if suggested_price is not None:
        body += f"Suggested:  {suggested_price}\n"
    if notification.suggested_profit_threshold is not None:
        body += f"Profit Threshold: {notification.suggested_profit_threshold:.2f}\n"

    # Handle alert_time safely (could be pd.Timestamp, datetime, or already a string)
    alert_time_str = "N/A"
    try:
        if hasattr(notification, 'alert_time') and notification.alert_time is not None:
            if hasattr(notification.alert_time, 'strftime'):
                alert_time_str = notification.alert_time.strftime('%Y-%m-%d %H:%M:%S')
            else:
                alert_time_str = str(notification.alert_time)
    except Exception:
        alert_time_str = str(notification.alert_time)

    body += f"Time:       {alert_time_str}\nApproach:   {notification.approach}\n"
    if notification.details:
        body += "\n--- Details ---\n"
        for key, value in notification.details.items():
            try:
                if hasattr(value, 'strftime'):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            body += f"{key.replace('_', ' ').title()}: {value}\n"
    return body


def send_email(subject: str, body: str):
    """
    Sends an email using the credentials and settings from the notification_settings module.
    """
    # These are now accessed via the loaded notification_settings module
    sender_email = notification_settings.EMAIL_SENDER
    sender_display_name = notification_settings.EMAIL_SENDER_DISPLAY_NAME
    receiver_emails = notification_settings.EMAIL_RECEIVERS
    bcc_receiver_emails = notification_settings.EMAIL_BCC_RECEIVERS
    app_password = notification_settings.EMAIL_APP_PASSWORD
    smtp_server = notification_settings.EMAIL_SMTP_SERVER
    smtp_port = notification_settings.EMAIL_SMTP_PORT

    # Combine all recipients for the sendmail command, but keep them separate for headers
    all_recipients = (receiver_emails or []) + (bcc_receiver_emails or [])

    if not all([sender_email, all_recipients, app_password]):
        logging.warning("Email credentials or recipients are not fully configured. Skipping email.")
        return

    message = MIMEMultipart()
    # Format the "From" header to show a display name instead of just the email
    message['From'] = formataddr((sender_display_name, sender_email))
    # Ensure To header is non-empty to avoid spam filters and formatting issues
    to_header = ", ".join(receiver_emails) if receiver_emails else sender_email
    message['To'] = to_header
    # The 'Bcc' header is not actually added to the message to ensure privacy
    message['Subject'] = subject
    # Add a "Reply-To" header to guide replies to the correct address
    message.add_header('Reply-To', sender_email)

    message.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, all_recipients, message.as_string())
            logging.info(f"Email sent successfully to: {', '.join(receiver_emails) if receiver_emails else ''} (BCC: {', '.join(bcc_receiver_emails) if bcc_receiver_emails else ''})")
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
        raise  # Re-raise the exception to be handled by the caller

