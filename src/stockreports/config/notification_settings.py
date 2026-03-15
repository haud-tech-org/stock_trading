# src/stockreports/config/notification_settings.py
"""
Configuration settings for all alert notification channels (Email, ntfy, Twilio SMS).

SECURITY NOTE:
All sensitive credentials are loaded from secure sources in the following priority order:
1. Environment Variables (production deployments)
2. Secret Management Services (Azure KeyVault, Google Secret Manager)
3. .env File (local development only - NEVER committed to Git)
4. Default values (non-sensitive configuration only)

DO NOT hardcode credentials in this file.
Use environment variables or .env file for local development.
See docs/SECURE_CREDENTIALS_MANAGEMENT.md for detailed setup instructions.
"""

import logging
import os
from src.stockreports.config.secrets_loader import SecretsLoader

logger = logging.getLogger(__name__)

# Initialize secrets loader
_secrets_loader = SecretsLoader()
_secrets_loader.log_environment_info()

# --- Email Configuration ---

# Email Enabled
# Meaning: A master switch to enable or disable all email notifications.
# Guidance: Set to `False` to quickly turn off all emails without sending.
# Range: `True` or `False`.
# Load from: EMAIL_ENABLED environment variable
EMAIL_ENABLED = os.getenv("EMAIL_ENABLED", "False").lower() == "true"

# Email SMTP Server / Port
# Non-sensitive configuration - can be hardcoded
# Guidance: For Gmail use "smtp.gmail.com" and 587. Check your provider's documentation.
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# Email Sender (SECURED)
# Meaning: The email address from which alerts are sent
# Load from: EMAIL_SENDER environment variable or secret manager
# Example: EMAIL_SENDER = "your-email@gmail.com"
EMAIL_SENDER = _secrets_loader.get_secret(
    "EMAIL_SENDER",
    default="",
    required=EMAIL_ENABLED,
    is_sensitive=False
) or ""

# Email App Password (SECURED - CRITICAL)
# Meaning: An "App Password" generated from your email account settings (NOT your regular password)
# For Gmail: Enable 2FA, then generate at Google Account → Security → App Passwords
# Load from: EMAIL_APP_PASSWORD environment variable or secret manager
# WARNING: Never hardcode this value
EMAIL_APP_PASSWORD = _secrets_loader.get_secret(
    "EMAIL_APP_PASSWORD",
    default="",
    required=EMAIL_ENABLED,
    is_sensitive=True
) or ""

# Email Sender Display Name (SECURED)
# Meaning: A friendly name displayed in email clients (e.g., "VN30 Alerter (No-Reply)")
# Load from: EMAIL_SENDER_DISPLAY_NAME environment variable
EMAIL_SENDER_DISPLAY_NAME = _secrets_loader.get_secret(
    "EMAIL_SENDER_DISPLAY_NAME",
    default="Stock Alerter (No-Reply)",
    required=False,
    is_sensitive=False
) or "Stock Alerter (No-Reply)"

# Email Recipients (Non-sensitive - can be in .env or environment)
# Meaning: Email addresses that receive public notifications (To field)
# Load from: EMAIL_RECEIVERS environment variable (comma-separated)
# Example: EMAIL_RECEIVERS = "user1@example.com,user2@example.com"
EMAIL_RECEIVERS_STR = os.getenv("EMAIL_RECEIVERS", "")
EMAIL_RECEIVERS = [e.strip() for e in EMAIL_RECEIVERS_STR.split(",") if e.strip()] if EMAIL_RECEIVERS_STR else []

# Email BCC Recipients (Non-sensitive - can be in .env or environment)
# Meaning: Email addresses that receive notifications privately (BCC field)
# Load from: EMAIL_BCC_RECEIVERS environment variable (comma-separated)
EMAIL_BCC_RECEIVERS_STR = os.getenv("EMAIL_BCC_RECEIVERS", "")
EMAIL_BCC_RECEIVERS = [e.strip() for e in EMAIL_BCC_RECEIVERS_STR.split(",") if e.strip()] if EMAIL_BCC_RECEIVERS_STR else []

# --- ntfy Push Notification Configuration ---

# ntfy Enabled
# Meaning: A master switch to enable or disable push notifications via ntfy.sh
# Load from: NTFY_ENABLED environment variable
NTFY_ENABLED = os.getenv("NTFY_ENABLED", "False").lower() == "true"

# ntfy Topics (Non-sensitive - can be hardcoded or in environment)
# Meaning: Topics to publish alerts to (will be visible to anyone who knows the topic name)
# Load from: NTFY_TOPICS environment variable (comma-separated)
# Example: NTFY_TOPICS = "stock_alerts_a1b2c3d4,another_topic"
NTFY_TOPICS_STR = os.getenv("NTFY_TOPICS", "vn30_alerts_f8a9b2c1")
NTFY_TOPICS = [t.strip() for t in NTFY_TOPICS_STR.split(",") if t.strip()] if NTFY_TOPICS_STR else []

# --- Twilio SMS Notifications Configuration ---

# Twilio Enabled
# Meaning: A master switch to enable or disable SMS notifications via Twilio
# Guidance: Set to `True` only if you have a Twilio account
# Load from: TWILIO_ENABLED environment variable
TWILIO_ENABLED = os.getenv("TWILIO_ENABLED", "False").lower() == "true"

# Twilio Account SID (SECURED - CRITICAL)
# Meaning: Unique identifier for your Twilio account
# Load from: TWILIO_ACCOUNT_SID environment variable or secret manager
# See: https://www.twilio.com/console (look for Account SID)
TWILIO_ACCOUNT_SID = _secrets_loader.get_secret(
    "TWILIO_ACCOUNT_SID",
    default="",
    required=TWILIO_ENABLED,
    is_sensitive=True
) or ""

# Twilio Auth Token (SECURED - CRITICAL)
# Meaning: Authentication token for Twilio API
# Load from: TWILIO_AUTH_TOKEN environment variable or secret manager
# WARNING: Never hardcode this value
# See: https://www.twilio.com/console (look for Auth Token)
TWILIO_AUTH_TOKEN = _secrets_loader.get_secret(
    "TWILIO_AUTH_TOKEN",
    default="",
    required=TWILIO_ENABLED,
    is_sensitive=True
) or ""

# Twilio Phone Number (Non-sensitive)
# Meaning: Your Twilio phone number (from which SMS will be sent)
# Load from: TWILIO_PHONE_NUMBER environment variable
# Example: TWILIO_PHONE_NUMBER = "+1234567890"
TWILIO_PHONE_NUMBER = os.getenv("TWILIO_PHONE_NUMBER", "")

# SMS Receiver Phone Number (Non-sensitive)
# Meaning: The phone number that receives SMS alerts
# Load from: SMS_RECEIVER_PHONE_NUMBER environment variable
# Example: SMS_RECEIVER_PHONE_NUMBER = "+84983794189"
SMS_RECEIVER_PHONE_NUMBER = os.getenv("SMS_RECEIVER_PHONE_NUMBER", "")

# --- Configuration Validation ---

def validate_configuration() -> None:
    """
    Validate that required credentials are configured.
    Called on module import to catch configuration errors early.
    """
    errors = []
    
    # Validate Email Configuration
    if EMAIL_ENABLED:
        if not EMAIL_SENDER:
            errors.append("EMAIL_ENABLED=True but EMAIL_SENDER not configured")
        if not EMAIL_APP_PASSWORD:
            errors.append("EMAIL_ENABLED=True but EMAIL_APP_PASSWORD not configured")
        if not (EMAIL_RECEIVERS or EMAIL_BCC_RECEIVERS):
            errors.append("EMAIL_ENABLED=True but no EMAIL_RECEIVERS or EMAIL_BCC_RECEIVERS configured")
    
    # Validate Twilio Configuration
    if TWILIO_ENABLED:
        if not TWILIO_ACCOUNT_SID:
            errors.append("TWILIO_ENABLED=True but TWILIO_ACCOUNT_SID not configured")
        if not TWILIO_AUTH_TOKEN:
            errors.append("TWILIO_ENABLED=True but TWILIO_AUTH_TOKEN not configured")
        if not TWILIO_PHONE_NUMBER:
            errors.append("TWILIO_ENABLED=True but TWILIO_PHONE_NUMBER not configured")
        if not SMS_RECEIVER_PHONE_NUMBER:
            errors.append("TWILIO_ENABLED=True but SMS_RECEIVER_PHONE_NUMBER not configured")
    
    # Log warnings or raise errors
    if errors:
        for error in errors:
            logger.warning(f"Configuration warning: {error}")
        if EMAIL_ENABLED or TWILIO_ENABLED:
            logger.warning("Some notification channels are enabled but not fully configured")

# Run validation on module import
validate_configuration()

# Log loaded configuration (non-sensitive only)
logger.info(f"Notification settings loaded - Email: {EMAIL_ENABLED}, Twilio: {TWILIO_ENABLED}, ntfy: {NTFY_ENABLED}")
