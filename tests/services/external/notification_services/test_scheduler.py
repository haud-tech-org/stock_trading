"""
Unit tests for NotificationScheduler (migrated scheduler/reminder logic)
"""
import pytest
from datetime import datetime, timedelta
from src.stockreports.services.external.notification_services._internal.scheduler import NotificationScheduler
from src.stockreports.alert.model.models import AlertNotification

class DummyConfigLoader:
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
                                'EMAIL': {'enabled': True, 'signals': {'BUY': {'enabled': True}, 'ORDER_REMINDER': {'enabled': True}, 'CLOSE_POSITION': {'enabled': True}}},
                                'SMS': {'enabled': False, 'signals': {}},
                                'NTFY': {'enabled': False, 'signals': {}}
                            }
                        }
                    }
                }
            }
        }

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

def test_scheduler_order_reminder_and_close():
    scheduler = NotificationScheduler(DummyConfigLoader())
    base_time = datetime(2026, 4, 20, 12, 0, 0)
    alert = make_alert(alert_time=base_time)
    scheduler.append_new_signal(alert)

    # 1 min after alert: nothing due
    notifications = scheduler.check_and_notify(base_time + timedelta(minutes=1))
    assert notifications == []

    # 2 min after alert: order reminder due
    notifications = scheduler.check_and_notify(base_time + timedelta(minutes=2))
    assert len(notifications) == 1
    assert "ORDER REMINDER" in notifications[0].signal

    # 5 min after alert: close position due
    notifications = scheduler.check_and_notify(base_time + timedelta(minutes=5))
    assert len(notifications) == 1
