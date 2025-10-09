# src/stockreports/utils/sms_utils.py
import logging
from src.stockreports.config import loader

# It's good practice to handle the case where the library might not be installed.
try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
    IS_TWILIO_AVAILABLE = True
except ImportError:
    IS_TWILIO_AVAILABLE = False

def send_sms(message_body: str):
    """
    Sends an SMS notification using the Twilio API.
    """
    # Dynamically load the latest notification settings
    notification_settings = loader.get_notification_settings()

    # --- Pre-flight Checks ---
    if not notification_settings.TWILIO_ENABLED:
        return  # Silently exit if not enabled

    if not IS_TWILIO_AVAILABLE:
        logging.error("Twilio library is not installed. Please run 'pip install twilio' to send SMS.")
        return

    # Check for placeholder credentials
    if "ACxxxxxxxx" in notification_settings.TWILIO_ACCOUNT_SID or "your_auth_token" in notification_settings.TWILIO_AUTH_TOKEN:
        logging.warning("Twilio is enabled, but credentials appear to be placeholders. Skipping SMS.")
        return

    # --- Send SMS ---
    try:
        client = Client(notification_settings.TWILIO_ACCOUNT_SID, notification_settings.TWILIO_AUTH_TOKEN)
        
        message = client.messages.create(
            to=notification_settings.SMS_RECEIVER_PHONE_NUMBER,
            from_=notification_settings.TWILIO_PHONE_NUMBER,
            body=message_body
        )
        
        logging.info(f"Successfully sent SMS to {notification_settings.SMS_RECEIVER_PHONE_NUMBER} (Message SID: {message.sid})")

    except TwilioRestException as e:
        logging.error(f"Failed to send SMS via Twilio: {e}", exc_info=True)
    except Exception as e:
        logging.error(f"An unexpected error occurred during SMS sending: {e}", exc_info=True)

