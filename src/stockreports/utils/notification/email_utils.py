# src/stockreports/utils/email_utils.py
import smtplib
import ssl
import logging
import json
import time
from src.stockreports.utils.conversion_data_utils import default_serializer
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
        body += "\n--- Details (JSON) ---\n"
        try:
            details_json = json.dumps(notification.details, indent=2, ensure_ascii=False, default=default_serializer)
            logging.debug(f"[EMAIL DEBUG] Alert details JSON for {notification.symbol}:\n{details_json}")
            body += details_json + "\n"
        except Exception as e:
            logging.debug(f"[EMAIL DEBUG] Could not format details as JSON for {notification.symbol}: {e}\nDetails: {notification.details}")
            body += f"[Could not format details as JSON: {e}]\n{str(notification.details)}\n"
    return body


def _send_email_with_retry(sender_email: str, receiver_emails: list, bcc_receiver_emails: list, 
                           app_password: str, smtp_server: str, smtp_port: int, message, 
                           max_retries: int = 3, initial_delay: float = 1.0) -> bool:
    """
    Send email with exponential backoff retry logic.
    
    Args:
        sender_email: Sender email address
        receiver_emails: List of recipient email addresses
        bcc_receiver_emails: List of BCC recipient email addresses
        app_password: Email app password for authentication
        smtp_server: SMTP server hostname
        smtp_port: SMTP server port
        message: MIME message object to send
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds (default: 1.0)
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    all_recipients = receiver_emails + bcc_receiver_emails
    retry_count = 0
    delay = initial_delay
    
    while retry_count <= max_retries:
        try:
            # Use SSL context to avoid SSL negotiation issues in container environments
            context = ssl.create_default_context()
            
            # Try with explicit TLS configuration (port 587)
            # Increased timeout from 10 to 20 seconds to handle slow SMTP servers
            with smtplib.SMTP(smtp_server, smtp_port, timeout=20) as server:
                server.starttls(context=context)
                server.login(sender_email, app_password)
                server.sendmail(sender_email, all_recipients, message.as_string())
                logging.info(f"Email sent successfully to: {', '.join(receiver_emails) if receiver_emails else ''} (BCC: {', '.join(bcc_receiver_emails) if bcc_receiver_emails else ''})")
                return True
                
        except (smtplib.SMTPServerDisconnected, TimeoutError, OSError) as e:
            # These are transient errors that might resolve on retry
            retry_count += 1
            if retry_count <= max_retries:
                logging.warning(f"Email send attempt {retry_count} failed with transient error: {type(e).__name__}: {e}. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff: 1s, 2s, 4s, etc.
            else:
                logging.error(f"Email send failed after {max_retries} retries. Last error: {type(e).__name__}: {e}", exc_info=True)
                return False
                
        except Exception as e:
            # Non-transient errors should fail immediately
            logging.error(f"Email send failed with non-transient error: {type(e).__name__}: {e}", exc_info=True)
            return False
    
    return False


def send_email(subject: str, body: str):
    """
    Sends an email using the credentials and settings from the notification_settings module.
    Implements retry logic with exponential backoff for transient network errors.
    
    Args:
        subject: Email subject line
        body: Email body content
        
    Returns:
        bool: True if email sent successfully, False otherwise
        
    Raises:
        No exceptions are raised; errors are logged and function returns False
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
        return False

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

    # Use retry logic with exponential backoff for transient network errors
    return _send_email_with_retry(
        sender_email=sender_email,
        receiver_emails=receiver_emails or [],
        bcc_receiver_emails=bcc_receiver_emails or [],
        app_password=app_password,
        smtp_server=smtp_server,
        smtp_port=smtp_port,
        message=message,
        max_retries=3,
        initial_delay=1.0
    )

