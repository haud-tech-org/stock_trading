# Local Development Setup Guide

This guide walks through setting up the Stock Alerter application for local development with proper credential management.

## Prerequisites

- Python 3.10+
- pip and venv
- Git
- Docker (optional, for containerized development)

## Step 1: Clone Repository and Setup

```bash
# Clone the repository
git clone https://github.com/haudtech/stock_trading.git
cd trending_and_summary

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# For Azure integration (optional)
pip install azure-identity azure-keyvault-secrets

# For Google Cloud integration (optional)
pip install google-cloud-secret-manager
```

## Step 2: Create .env File for Local Development

```bash
# Copy the example file
cp .env.example .env

# Edit with your credentials
nano .env  # or use your preferred editor
```

### Fill in Your Credentials

Edit `.env` with your actual values:

```bash
# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

EMAIL_ENABLED=true

# Your email account (e.g., Gmail)
EMAIL_SENDER=your-email@gmail.com

# For Gmail:
# 1. Enable 2-Factor Authentication in Google Account
# 2. Go to: https://myaccount.google.com/apppasswords
# 3. Select "Mail" and "Windows Computer" (or your device type)
# 4. Generate and copy the 16-character password
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

EMAIL_SENDER_DISPLAY_NAME=Stock Alerter (No-Reply)

# Recipients (comma-separated)
EMAIL_RECEIVERS=recipient1@example.com
EMAIL_BCC_RECEIVERS=admin@example.com

# ============================================================================
# NTFY CONFIGURATION (Optional)
# ============================================================================

NTFY_ENABLED=false
NTFY_TOPICS=vn30_alerts_f8a9b2c1

# ============================================================================
# TWILIO CONFIGURATION (Optional)
# ============================================================================

TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890
SMS_RECEIVER_PHONE_NUMBER=+84983794189
```

## Step 3: Verify Configuration

```bash
# Test that the configuration loads correctly
python -c "from src.stockreports.config.notification_settings import *; print('✓ Configuration loaded successfully')"

# If you see "✓ Configuration loaded successfully", you're good to go!

# If you see errors, check:
# 1. .env file is in the correct location
# 2. Environment variable names are correct
# 3. Values are not quoted (unless needed for special characters)
```

## Step 4: Test Email Functionality

```bash
# Create a test script
cat > test_email.py << 'EOF'
#!/usr/bin/env python
"""Test email configuration"""

from src.stockreports.config import notification_settings
from src.stockreports.utils.notification.email_utils import send_email

# Check configuration
print(f"Email Enabled: {notification_settings.EMAIL_ENABLED}")
print(f"Email Sender: {notification_settings.EMAIL_SENDER}")
print(f"Email Receivers: {notification_settings.EMAIL_RECEIVERS}")
print(f"Email BCC Receivers: {notification_settings.EMAIL_BCC_RECEIVERS}")

if notification_settings.EMAIL_ENABLED:
    try:
        # Send test email
        send_email(
            subject="Test Email from Stock Alerter",
            body="This is a test email to verify configuration."
        )
        print("✓ Test email sent successfully!")
    except Exception as e:
        print(f"✗ Error sending test email: {e}")
else:
    print("Email is not enabled. Set EMAIL_ENABLED=true in .env to test.")
EOF

# Run the test
python test_email.py

# Clean up
rm test_email.py
```

## Step 5: Development Workflow

### Option A: Direct Python Execution

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run the application
python -m src.stockreports.cli

# Run specific module
python -m src.stockreports.web
```

### Option B: Using Docker (Optional)

```bash
# Build Docker image
docker build -t stock-alerter:dev .

# Run container with .env file
docker run \
  --env-file .env \
  -v $(pwd)/src:/app/src \
  -p 5000:5000 \
  stock-alerter:dev

# Or use docker-compose
docker-compose up

# Run in background
docker-compose up -d

# View logs
docker-compose logs -f

# Stop and clean up
docker-compose down
```

## Step 6: Debugging and Troubleshooting

### Enable Debug Logging

```bash
# Create a debug script
cat > debug_config.py << 'EOF'
#!/usr/bin/env python
"""Debug configuration loading"""

import logging
import os

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# Import after setting logging
from src.stockreports.config.secrets_loader import SecretsLoader

loader = SecretsLoader()
loader.log_environment_info()

print("\n=== Loaded Environment Variables ===")
for key in ["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_ENABLED"]:
    value = os.getenv(key)
    if value and len(value) > 10:
        value = value[:5] + "****" + value[-5:]
    print(f"{key}: {value}")
EOF

# Run debug script
python debug_config.py

# Clean up
rm debug_config.py
```

### Check .env File

```bash
# Verify .env file exists and is readable
ls -la .env

# Check file permissions (should be readable by user only)
chmod 600 .env

# View non-sensitive values (carefully!)
grep -v "PASSWORD\|TOKEN" .env

# Count environment variables
grep "^[A-Z]" .env | wc -l
```

### Test SMTP Connection

```bash
# Test Gmail SMTP connection
python -c "
import smtplib
import ssl

EMAIL_SENDER = input('Email: ')
APP_PASSWORD = input('App Password: ')

try:
    context = ssl.create_default_context()
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=10) as server:
        server.starttls(context=context)
        server.login(EMAIL_SENDER, APP_PASSWORD)
        print('✓ SMTP authentication successful!')
except Exception as e:
    print(f'✗ SMTP authentication failed: {e}')
"
```

## Step 7: Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=src/stockreports --cov-report=html

# Run specific test file
pytest tests/test_email_utils.py -v

# Run with debug output
pytest -vv --tb=short
```

## Step 8: Security Best Practices for Development

### Never Commit Credentials

```bash
# Verify .env is in .gitignore
grep "\.env" .gitignore

# Check if .env is already tracked (should be empty)
git ls-files | grep ".env"

# If accidentally tracked, remove it
git rm --cached .env
git commit -m "Remove .env from version control"
```

### Protect Your .env File

```bash
# Set restrictive permissions (user read/write only)
chmod 600 .env

# Never share your .env file
# Never paste credential values in chat/email/documents
# Rotate credentials regularly, especially if shared
```

### Audit Log Changes

```bash
# Check what's in git (use carefully)
git log --all --grep="password\|token\|secret\|credential" -i

# Review recent commits for accidental credential exposure
git log -p --all -S "password\|token\|secret" -i | head -50
```

## Step 9: Common Issues and Solutions

### Issue: Module Not Found Error

```python
ModuleNotFoundError: No module named 'src.stockreports'
```

**Solution:**
```bash
# Ensure you're in the project root directory
pwd  # Should end in /trending_and_summary

# Add project root to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or run Python with module syntax
python -m src.stockreports.cli
```

### Issue: EMAIL_APP_PASSWORD Not Found

```python
ValueError: Required secret 'EMAIL_APP_PASSWORD' not found
```

**Solution:**
```bash
# 1. Verify .env file exists
ls -la .env

# 2. Check email is enabled in .env
grep EMAIL_ENABLED .env

# 3. Check password is set
grep EMAIL_APP_PASSWORD .env

# 4. Test SecretsLoader directly
python -c "
from src.stockreports.config.secrets_loader import SecretsLoader
loader = SecretsLoader()
pwd = loader.get_secret('EMAIL_APP_PASSWORD')
print('Password loaded:', 'Yes' if pwd else 'No')
"
```

### Issue: Email Sending Fails

```python
smtplib.SMTPAuthenticationError: (535, b'5.7.8 Username and password not accepted')
```

**Solution:**
```bash
# 1. Verify email sender matches Gmail account
# 2. Check App Password is correct (16 characters, no spaces when used)
# 3. Verify 2-Factor Authentication is enabled in Google Account
# 4. Generate new App Password in Google Account settings
# 5. Check SMTP server and port are correct (smtp.gmail.com:587)

# Test with explicit credentials
python test_email.py
```

## Step 10: Setup IDE Integration (VS Code)

### Create .vscode/settings.json

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": [
    "tests"
  ],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  }
}
```

### Create .vscode/launch.json

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: CLI",
      "type": "python",
      "request": "launch",
      "module": "src.stockreports.cli",
      "console": "integratedTerminal",
      "env": {
        "PYTHONPATH": "${workspaceFolder}"
      }
    },
    {
      "name": "Python: Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "tests",
        "-v"
      ],
      "console": "integratedTerminal"
    }
  ]
}
```

## Summary

You now have:

- ✅ Secure credential management using SecretsLoader
- ✅ Local .env file for development (excluded from Git)
- ✅ Email configuration ready to test
- ✅ Docker setup for containerized development
- ✅ Debugging and troubleshooting tools

**Next Steps:**
1. Test your email configuration
2. Run the application locally
3. Review the deployment guides for cloud deployment
4. Set up CI/CD pipeline for automated testing

**Support:**
- See `docs/SECURE_CREDENTIALS_MANAGEMENT.md` for detailed credential management
- See `docs/EMAIL_CONFIGURATION_ANALYSIS.md` for email configuration details
- See deployment guides in `deployment/` directory for cloud-specific setup
