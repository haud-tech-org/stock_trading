# tests/manual/test_email.py
import sys
import logging
from pathlib import Path

# Add project root to Python path to allow imports from src
project_root = Path(__file__).resolve().parents[2]
sys.path.append(str(project_root))

# It's important to add the project root before importing local modules
from src.stockreports.config import settings
from src.stockreports.utils.email_utils import send_email

logging.basicConfig(level="INFO", format="%(asctime)s - %(levelname)s - %(message)s")

def run_test_email():
    """Sends a simple test email to verify configuration."""
    logging.info(f"Attempting to send a test email to {settings.EMAIL_RECEIVER}...")
    
    if not settings.EMAIL_ENABLED:
        logging.warning("Email is disabled in settings.py. Skipping test.")
        return

    if "your_email@gmail.com" in settings.EMAIL_SENDER or \
       "receiver_email@example.com" in settings.EMAIL_RECEIVER or \
       "your_app_password_here" in settings.EMAIL_APP_PASSWORD:
        logging.error("Default configuration found in settings.py. Please update your email details before testing.")
        return

    subject = "Test Email from Stock Monitoring Script"
    body = (
        "Hello,\n\n"
        "This is a test message to confirm that the email notification system for your stock monitor is working correctly.\n\n"
        "If you received this, your configuration is successful.\n\n"
        "Regards,\n"
        "Stock Monitoring Bot"
    )

    try:
        send_email(subject, body)
        logging.info("Test email script finished. The email should arrive shortly.")
    except Exception as e:
        logging.error(f"An error occurred while trying to send the test email: {e}", exc_info=True)

if __name__ == "__main__":
    run_test_email()
