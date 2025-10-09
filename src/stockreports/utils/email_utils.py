# src/stockreports/utils/email_utils.py
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

# --- Settings Loader ---
from src.stockreports.config import loader
notification_settings = loader.get_notification_settings()

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
    all_recipients = receiver_emails + bcc_receiver_emails

    if not all([sender_email, all_recipients, app_password]):
        logging.warning("Email credentials or recipients are not fully configured. Skipping email.")
        return

    message = MIMEMultipart()
    # Format the "From" header to show a display name instead of just the email
    message['From'] = formataddr((sender_display_name, sender_email))
    message['To'] = ", ".join(receiver_emails)
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
            logging.info(f"Email sent successfully to: {', '.join(receiver_emails)} (BCC: {', '.join(bcc_receiver_emails)})")
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
        raise  # Re-raise the exception to be handled by the caller

