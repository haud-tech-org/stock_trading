# This file marks this directory as a Python package for test discovery.

# --- Python Standard Library ---
from datetime import datetime, timedelta

# --- Third-Party Libraries ---
import pytest

# --- Project Imports (updated to new notification service location) ---
from src.stockreports.services.external.notification_services.orchestrator import NotificationServiceOrchestrator
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.services.external.notification_services._internal.channel_type import ChannelType


def make_alert(signal="BUY", alert_time=None):
    return AlertNotification(
        symbol="BTC/USDT:USDT",
        approach="REVERSAL_ANCHOR_SIGNAL_CANDLE",
        signal=signal,
        alert_price=50000.0,
        alert_time=alert_time or datetime(2026, 4, 20, 12, 0, 0),
        details=None,
        suggested_price=50500.0,
        suggested_profit_threshold=None
    )

class DummyConfig:
    # Patch for legacy channel config attributes expected by some channel classes
    NTFY_ENABLED = True
    EMAIL_SENDER = 'test@example.com'
    EMAIL_APP_PASSWORD = 'dummy'
    EMAIL_RECEIVERS = ['rcpt@example.com']
    EMAIL_BCC_RECEIVERS = []
    EMAIL_SMTP_SERVER = 'smtp.example.com'
    EMAIL_SMTP_PORT = 587
    NTFY_TOPICS = ['testtopic']
    SCHEDULED_REMINDER_ORDER_DELAY_MINUTES = 2
    SCHEDULED_REMINDER_CLOSE_DELAY_MINUTES = 5
    def __init__(self):
        self.data = {
            'symbols': {
                'BTC/USDT:USDT': {
                    'approaches': {
                        'REVERSAL_ANCHOR_SIGNAL_CANDLE': {
                            'reminder_delays': {
                                'order_delay_minutes': 2,
                                'close_delay_minutes': 5
                            },
                            'channels': {
                                ChannelType.EMAIL.value: {
                                    'enabled': True,
                                    'signals': {
                                        'BUY': {'enabled': True},
                                        'SELL': {'enabled': True},
                                        'CLOSE_POSITION': {'enabled': True},
                                        'ORDER_REMINDER': {'enabled': True}
                                    }
                                },
                                ChannelType.SMS.value: {'enabled': True, 'signals': {'BUY': {'enabled': True}, 'SELL': {'enabled': True}, 'CLOSE_POSITION': {'enabled': True}, 'ORDER_REMINDER': {'enabled': True}}},
                                ChannelType.NTFY.value: {'enabled': True, 'signals': {'BUY': {'enabled': True}, 'SELL': {'enabled': True}, 'CLOSE_POSITION': {'enabled': True}, 'ORDER_REMINDER': {'enabled': True}}}
                            }
                        }
                    }
                }
            }
        }
    def is_signal_enabled(self, symbol, approach, signal):
        # Accept both enum and string signals
        if hasattr(signal, 'value'):
            sig_key = signal.value
        else:
            sig_key = str(signal).strip().upper().replace(" ", "_")
        try:
            channels = self.data['symbols'][symbol]['approaches'][approach]['channels']
            for channel_cfg in channels.values():
                if channel_cfg.get('enabled') and channel_cfg['signals'].get(sig_key, {}).get('enabled'):
                    return True
            return False
        except Exception:
            return False

    def get_enabled_channels(self, symbol, approach, signal):
        if hasattr(signal, 'value'):
            sig_key = signal.value
        else:
            sig_key = str(signal).strip().upper().replace(" ", "_")
        try:
            channels = self.data['symbols'][symbol]['approaches'][approach]['channels']
            return [name for name, cfg in channels.items() if cfg.get('enabled') and cfg['signals'].get(sig_key, {}).get('enabled')]
        except Exception:
            return []

def test_scheduler_integration(monkeypatch):
    orchestrator = NotificationServiceOrchestrator.__new__(NotificationServiceOrchestrator)
    orchestrator.config = DummyConfig()
    from src.stockreports.services.external.notification_services._internal.channel_factory import ChannelFactory
    orchestrator.factory = ChannelFactory(orchestrator.config)
    from src.stockreports.services.external.notification_services._internal.scheduler import NotificationScheduler
    orchestrator.scheduler = NotificationScheduler(orchestrator.config)
    orchestrator.sent_alerts = set()
    sent = []
    class MockChannel:
        def send(self, n):
            sent.append(n.signal)
        def validate_config(self):
            pass
    monkeypatch.setattr(orchestrator.factory, "get_channel", lambda name: MockChannel())
    base_time = datetime(2026, 4, 20, 12, 0, 0)
    alert = make_alert(alert_time=base_time)
    orchestrator.send_notification(alert)
    # Initial trade signal is sent immediately (one per enabled channel)
    print('After initial send:', sent)
    assert sent == ["BUY", "BUY", "BUY"]
    sent.clear()
    # 1 min after alert: nothing due
    orchestrator.process_scheduled_notifications(base_time + timedelta(minutes=1))
    print('After 1 min:', sent)
    assert sent == []
    # 2 min after alert: order reminder due (one per channel)
    orchestrator.process_scheduled_notifications(base_time + timedelta(minutes=2))
    print('After 2 min:', sent)
    assert sorted(sent) == ["ORDER REMINDER (BUY)"] * 3
    sent.clear()
    # 5 min after alert: close position due (one per channel)
    orchestrator.process_scheduled_notifications(base_time + timedelta(minutes=5))
    print('After 5 min:', sent)
    assert sorted(sent) == ["CLOSE POSITION (BUY)"] * 3
    sent.clear()
    # After both sent, state resets, nothing due
    orchestrator.process_scheduled_notifications(base_time + timedelta(minutes=6))
    print('After 6 min:', sent)
    assert sent == []

def test_scheduler_state_exposed():
    orchestrator = NotificationServiceOrchestrator.__new__(NotificationServiceOrchestrator)
    orchestrator.config = DummyConfig()
    from src.stockreports.services.external.notification_services._internal.channel_factory import ChannelFactory
    orchestrator.factory = ChannelFactory(orchestrator.config)
    # Patch factory to always return a mock channel
    class MockChannel:
        def send(self, n):
            pass
        def validate_config(self):
            pass
    orchestrator.factory.get_channel = lambda name: MockChannel()
    from src.stockreports.services.external.notification_services._internal.scheduler import NotificationScheduler
    orchestrator.scheduler = NotificationScheduler(orchestrator.config)
    orchestrator.sent_alerts = set()
    alert = make_alert()
    orchestrator.send_notification(alert)
    state = orchestrator.get_scheduler_state()
    assert state[0].alert is not None
    orchestrator.scheduler.reset_state()
    state = orchestrator.get_scheduler_state()
    assert state == []
