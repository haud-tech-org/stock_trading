# src/stockreports/config/notification_settings.py
"""
Configuration settings for all alert notification channels (Email, ntfy, etc.).
"""

# --- Notification Configuration ---

# Email Enabled
# Meaning: A master switch to enable or disable all email notifications.
# Guidance: Set to `False` to quickly turn off all emails without removing your credentials.
# Range: `True` or `False`.
# Example: `EMAIL_ENABLED = True`
EMAIL_ENABLED = False

# Email SMTP Server / Port
# Meaning: The server and port for your email provider's SMTP service.
# Guidance: These values are standard for major providers. For Gmail, it's "smtp.gmail.com" and 587. Check your email provider's documentation for others.
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# Email Sender / Receiver
# Meaning: The email address that sends the alerts and the list of addresses that receive them.
# Guidance: Ensure the sender email is the one associated with the `EMAIL_APP_PASSWORD`. `EMAIL_RECEIVERS` is for the public 'To' field, and `EMAIL_BCC_RECEIVERS` is for private recipients.
EMAIL_SENDER = "haud.tech@gmail.com"
EMAIL_RECEIVERS = []
EMAIL_BCC_RECEIVERS = ["haud.tech@gmail.com"]

# Email Sender Display Name
# Meaning: A friendly name for the sender that appears in the email client (e.g., "VN30 Alerter").
# Guidance: You can set this to something like "My Stock Alerts (No-Reply)" to discourage replies.
# Example: `EMAIL_SENDER_DISPLAY_NAME = "Stock Alerter (No-Reply)"`
EMAIL_SENDER_DISPLAY_NAME = "[DEV] Stock Alerter Services (No-Reply)"

# Email App Password
# Meaning: An "App Password" generated from your email account (e.g., Google Account settings). This is NOT your regular login password.
# Guidance: Using an App Password is more secure. It's highly recommended to load this from an environment variable instead of hardcoding it.
# Example: `EMAIL_APP_PASSWORD = "your_generated_app_password"`
EMAIL_APP_PASSWORD = "hqtlxfixexiudmcu"

# ntfy Push Notification Enabled
# Meaning: A master switch to enable or disable push notifications via the ntfy.sh service.
# Guidance: Set to `False` to turn off push notifications.
# Range: `True` or `False`.
# Example: `NTFY_ENABLED = True`
NTFY_ENABLED = False

# ntfy Topic
# Meaning: The name of the ntfy.sh topic to publish alerts to. You will subscribe to this same topic in the ntfy app on your phone.
# Guidance: Use a random, hard-to-guess string for privacy. Anyone who knows the topic name can see your alerts.
# Example: `NTFY_TOPICS = ["stock_alerts_a1b2c3d4", "another_topic"]`
NTFY_TOPICS = ["vn30_alerts_f8a9b2c1"]

# --- Twilio SMS Notifications ---
# You will need a Twilio account for this to work.
# https://www.twilio.com/try-twilio
TWILIO_ENABLED = False  # Set to True to enable SMS
TWILIO_ACCOUNT_SID = "AC90a88f8ecdc64f9c09b8663d9e80fd2c"  # Your Account SID from Twilio
TWILIO_AUTH_TOKEN = "2cb9b86c37bee74a5a0387a5c1e01587"                     # Your Auth Token from Twilio
TWILIO_PHONE_NUMBER = "+12182202918"                      # Your Twilio phone number
SMS_RECEIVER_PHONE_NUMBER = "+84983794189"                      # The destination phone number (e.g., +84912345678)
