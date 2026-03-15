"""
Command Line Interface for stockreports alerter system.

This module provides CLI commands for managing the stock trading alert system
with support for secure credential management across multiple deployment
environments (Local, Docker, Google Cloud, Azure, Kubernetes).
"""

import argparse
import sys
import logging
import os
from pathlib import Path
from typing import Optional

# --- Secure Credentials & Settings ---
from src.stockreports.config import loader
from src.stockreports.config.secrets_loader import SecretsLoader
from src.stockreports.alert.common.environment import EnvironmentType

# --- Core Alert Modules ---
from src.stockreports.alert.symbol_alerter import SymbolAlerter


def setup_logging(verbose: bool = False):
    """Configure logging for the application."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


def verify_credentials():
    """Verify that all required credentials are properly configured."""
    try:
        # Load secrets
        secrets_loader = SecretsLoader()
        
        # Check environment detection
        env_type = secrets_loader.env_type
        print(f"✅ Environment detected: {EnvironmentType.get_display_name(env_type)}")
        
        # Load notification settings to verify credentials
        notification_settings = loader.get_notification_settings()
        
        # Check email configuration
        if notification_settings.EMAIL_ENABLED:
            email_sender = getattr(notification_settings, 'EMAIL_SENDER', None)
            email_password = secrets_loader.get_secret('EMAIL_APP_PASSWORD', required=False, is_sensitive=True)
            
            if email_sender and email_password:
                print(f"✅ Email configured: {email_sender}")
            else:
                print("⚠️  Email not fully configured")
        else:
            print("⚠️  Email is disabled")
        
        # Check Twilio configuration
        if notification_settings.TWILIO_ENABLED:
            twilio_account = secrets_loader.get_secret('TWILIO_ACCOUNT_SID', required=False, is_sensitive=True)
            if twilio_account:
                print(f"✅ Twilio configured")
            else:
                print("⚠️  Twilio not fully configured")
        else:
            print("⚠️  Twilio is disabled")
        
        print("\n✅ Credential verification completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Credential verification failed: {e}")
        return False


def run_alerter():
    """CLI command for running the real-time stock alerter."""
    parser = argparse.ArgumentParser(
        description='Run stock trading alert system with secure credentials',
        prog='stockreports-alerter'
    )
    
    parser.add_argument(
        '--symbols',
        type=str,
        default=None,
        help='Comma-separated list of symbols to monitor (e.g., AAPL,GOOGL,MSFT)'
    )
    
    parser.add_argument(
        '--approach',
        type=str,
        default='VRA',
        help='Trading approach to use (default: VRA)'
    )
    
    parser.add_argument(
        '--mode',
        type=str,
        choices=['live', 'development', 'backtest'],
        default='live',
        help='Execution mode (default: live)'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('stockreports-alerter')
    
    try:
        # Verify credentials first
        print("🔐 Verifying secure credentials...")
        if not verify_credentials():
            print("\n❌ Credential verification failed. Cannot proceed with alerter.")
            sys.exit(1)
        
        print("\n🚀 Starting stock alerter system...\n")
        
        # Load settings
        settings = loader.get_settings()
        logger.info(f"Mode: {args.mode}, Approach: {args.approach}")
        
        # Parse symbols
        if args.symbols:
            symbols = [s.strip().upper() for s in args.symbols.split(',')]
        else:
            # Load from configuration
            symbols = getattr(settings, 'SYMBOLS', ['AAPL', 'GOOGL', 'MSFT'])
        
        print(f"📊 Monitoring symbols: {', '.join(symbols)}\n")
        
        # Run alerter for each symbol
        for symbol in symbols:
            try:
                print(f"📈 Processing {symbol}...")
                alerter = SymbolAlerter(symbol)
                alerter.run_alert_cycle()
                print(f"✅ {symbol} processed successfully\n")
            except Exception as e:
                logger.error(f"Error processing {symbol}: {e}", exc_info=args.verbose)
                print(f"❌ Error processing {symbol}: {e}\n")
        
        print("✅ Alerter cycle completed successfully!")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Alerter error: {e}", exc_info=args.verbose)
        print(f"❌ Alerter error: {e}")
        sys.exit(1)


def test_credentials():
    """CLI command for testing credential loading and environment detection."""
    parser = argparse.ArgumentParser(
        description='Test credential loading and environment detection',
        prog='stockreports-test-credentials'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    
    logger = logging.getLogger('stockreports-test-credentials')
    
    try:
        print("🧪 Testing Secure Credentials System\n")
        print("=" * 70)
        
        # Initialize secrets loader
        logger.info("Initializing SecretsLoader...")
        secrets_loader = SecretsLoader()
        
        # Check environment detection
        env_type = secrets_loader.env_type
        is_prod = EnvironmentType.is_production(env_type)
        is_cloud = EnvironmentType.is_cloud_environment(env_type)
        is_containerized = EnvironmentType.is_containerized(env_type)
        
        print(f"\n🌍 Environment Detection:")
        print(f"   Environment Type: {EnvironmentType.get_display_name(env_type)}")
        print(f"   Is Production: {is_prod}")
        print(f"   Is Cloud: {is_cloud}")
        print(f"   Is Containerized: {is_containerized}")
        
        # Test credential loading
        print(f"\n🔐 Testing Credential Loading:")
        
        test_keys = [
            ('EMAIL_SENDER', False),
            ('EMAIL_APP_PASSWORD', True),
            ('TWILIO_ACCOUNT_SID', True),
            ('TWILIO_AUTH_TOKEN', True),
        ]
        
        for key, is_sensitive in test_keys:
            try:
                value = secrets_loader.get_secret(key, required=False, is_sensitive=is_sensitive)
                if value:
                    display_value = '***' if is_sensitive else value
                    print(f"   ✅ {key}: {display_value}")
                else:
                    print(f"   ⚠️  {key}: Not configured")
            except Exception as e:
                logger.debug(f"Error loading {key}: {e}")
                print(f"   ❌ {key}: Error - {e}")
        
        print(f"\n" + "=" * 70)
        print("✅ Credential test completed!\n")
        sys.exit(0)
        
    except Exception as e:
        logger.error(f"Credential test error: {e}", exc_info=args.verbose)
        print(f"\n❌ Credential test failed: {e}\n")
        sys.exit(1)


def show_config():
    """CLI command for displaying current configuration."""
    parser = argparse.ArgumentParser(
        description='Display current configuration and environment',
        prog='stockreports-config'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show verbose configuration details'
    )
    
    args = parser.parse_args()
    
    try:
        print("\n📋 Stock Trading Alerter Configuration\n")
        print("=" * 70)
        
        # Environment
        secrets_loader = SecretsLoader()
        env_type = secrets_loader.env_type
        print(f"\n🌍 Environment:")
        print(f"   Deployment: {EnvironmentType.get_display_name(env_type)}")
        print(f"   Python: {sys.version.split()[0]}")
        print(f"   Project Root: {os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))}")
        
        # Settings
        settings = loader.get_settings()
        notification_settings = loader.get_notification_settings()
        print(f"\n⚙️  Settings:")
        print(f"   Mode: {settings.MODE}")
        print(f"   Email Enabled: {notification_settings.EMAIL_ENABLED}")
        print(f"   Twilio Enabled: {notification_settings.TWILIO_ENABLED}")
        
        if args.verbose:
            print(f"\n📊 Verbose Details:")
            print(f"   Settings Mode: {getattr(settings, 'MODE', 'N/A')}")
            print(f"   Log Level: {getattr(settings, 'LOG_LEVEL', 'N/A')}")
            
        print(f"\n" + "=" * 70 + "\n")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Error displaying configuration: {e}")
        sys.exit(1)


def main():
    """Main CLI entry point that dispatches to appropriate command."""
    if len(sys.argv) < 2:
        print("\n" + "=" * 70)
        print("📊 Stock Trading Alerter CLI")
        print("=" * 70)
        print("\nUsage: stockreports <command> [options]\n")
        print("Available commands:")
        print("  alerter           - Run real-time stock alerter system")
        print("  test-credentials  - Test credential loading and environment detection")
        print("  verify-config     - Display current configuration")
        print("\nUse 'stockreports <command> --help' for more information.")
        print("\n" + "=" * 70 + "\n")
        sys.exit(1)
    
    command = sys.argv[1]
    # Remove command from sys.argv so subcommands parse correctly
    sys.argv = [sys.argv[0]] + sys.argv[2:]
    
    if command == 'alerter':
        run_alerter()
    elif command == 'test-credentials':
        test_credentials()
    elif command == 'verify-config':
        show_config()
    else:
        print(f"❌ Unknown command: {command}")
        print("Available commands: alerter, test-credentials, verify-config")
        sys.exit(1)


if __name__ == "__main__":
    main()
