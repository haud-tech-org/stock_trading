# src/stockreports/utils/email_utils.py
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.stockreports.config import settings

def send_email(subject: str, body: str):
    """
    Sends an email using the configuration from the settings file.
    """
    if not settings.EMAIL_ENABLED:
        logging.info("Email notifications are disabled. Skipping email.")
        return

    # It's highly recommended to use environment variables for credentials
    # For example, os.environ.get('EMAIL_PASSWORD')
    password = settings.EMAIL_APP_PASSWORD 
    if not password or password == "your_app_password_here":
        logging.error("Email password is not configured in settings.py. Cannot send email.")
        return

    sender_email = settings.EMAIL_SENDER
    receiver_email = settings.EMAIL_RECEIVER

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = subject
    message.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP(settings.EMAIL_SMTP_SERVER, settings.EMAIL_SMTP_PORT)
        server.starttls()
        server.login(sender_email, password)
        text = message.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        logging.info(f"Email sent successfully to {receiver_email}")
    except Exception as e:
        logging.error(f"Failed to send email: {e}", exc_info=True)
