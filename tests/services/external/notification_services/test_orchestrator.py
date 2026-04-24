# --- Third-Party Libraries ---
import pytest

# --- Project Imports (updated to new notification service location) ---
from src.stockreports.services.external.notification_services.orchestrator import NotificationServiceOrchestrator
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.model.signal_type import SignalType
from src.stockreports.services.external.notification_services._internal.channel_type import ChannelType


def test_signal_enablement():
    orchestrator = NotificationServiceOrchestrator()
    notification = AlertNotification(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE",
        signal="SELL",
        alert_price=100.0,
        alert_time=2,
        details=None,
        suggested_price=None,
        suggested_profit_threshold=None
    )
    # Should be enabled by default config
    orchestrator.send_notification(notification)
    # Now test a disabled signal
    notification.signal = "PRICE_UP"
    orchestrator.send_notification(notification)  # Should not send
