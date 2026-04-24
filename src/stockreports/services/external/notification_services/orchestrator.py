"""
NotificationServiceOrchestrator - Public API for notification microservice.

Handles config-driven notification dispatch, deduplication, and channel orchestration.
"""

# --- Python Standard Library ---
from __future__ import annotations
import logging
import copy
from typing import Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from ._internal.channel_factory import ChannelFactory
from ._internal.config.loader import NotificationConfigLoader
from ._internal.scheduler import NotificationScheduler
from src.stockreports.model.signal_type import SignalType
from src.stockreports.alert.model.models import AlertData, AlertNotification
from src.stockreports.utils.alert_utils import normalize_alert_notification
from src.stockreports.services.external.notification_services._internal.scheduler import NotificationScheduler



class NotificationServiceOrchestrator:
    _instance: Optional[NotificationServiceOrchestrator] = None

    def __init__(self, config_path: Optional[str] = None) -> None:
        self.logger = logging.getLogger(__name__)
        self.config = NotificationConfigLoader.load(config_path)
        self.factory = ChannelFactory(self.config)
        self.sent_alerts = set()  # For deduplication
        self.scheduler = NotificationScheduler(self.config)

    @classmethod
    def get_instance(cls, config_path: Optional[str] = None) -> NotificationServiceOrchestrator:
        if cls._instance is None:
            cls._instance = cls(config_path)
        return cls._instance

    def send_notification(self, notification: object) -> None:
        # Always normalize to AlertNotification for downstream logic
        notification = normalize_alert_notification(notification)
        symbol = notification.symbol
        approach = notification.approach
        # Accept both SignalType and string for notification.signal
        if isinstance(notification.signal, SignalType):
            signal = notification.signal
        else:
            signal = SignalType.from_str(notification.signal)
        if not signal:
            self.logger.warning(f"Unknown signal: {notification.signal}")
            return
        # Check config for symbol/approach/channel/signal enablement
        if not self.config.is_signal_enabled(symbol, approach, signal):
            self.logger.info(f"Signal {signal} for {symbol}/{approach} is not enabled in config.")
            return
        # Deduplication key uses only normalized, immutable values
        alert_time_key = str(notification.alert_time) if notification.alert_time is not None else None
        alert_key = (symbol, approach, signal, alert_time_key)
        if alert_key in self.sent_alerts:
            self.logger.info(f"Duplicate alert: {alert_key}, skipping.")
            return
        # Send via all enabled channels
        for channel in self.config.get_enabled_channels(symbol, approach, signal):
            channel_instance = self.factory.get_channel(channel)
            if channel_instance:
                channel_instance.send(notification)
        self.sent_alerts.add(alert_key)
        # If this is a trade signal, update scheduler
        if signal in {SignalType.BUY, SignalType.SELL}:
            self.scheduler.append_new_signal(notification)

    def process_scheduled_notifications(self, now: object) -> None:
        """
        Checks for due reminders/close notifications and sends them via enabled channels.
        Ensures approach is set to SCHEDULER on a copy of each notification before sending.
        """
        due_notifications = self.scheduler.check_and_notify(now)
        for notification in due_notifications:
            symbol = notification.symbol
            raw_signal = notification.signal
            approach = notification.approach

            # Robustly map reminder/close signals to config signal names
            if raw_signal.startswith('ORDER REMINDER'):
                config_signal = 'ORDER_REMINDER'
            elif raw_signal.startswith('CLOSE POSITION'):
                config_signal = 'CLOSE_POSITION'
            else:
                config_signal = raw_signal
            # Try to get SignalType, fallback to string
            signal = SignalType.from_str(config_signal) or config_signal
            if not signal:
                continue
            for channel in self.config.get_enabled_channels(symbol, approach, signal):
                channel_instance = self.factory.get_channel(channel)
                if channel_instance:
                    notification_copy = copy.copy(notification)
                    notification_copy.approach = NotificationScheduler._get_scheduler_approach()
                    channel_instance.send(notification_copy)

    def validate_config(self) -> None:
        """Advanced config/schema validation stub (extend as needed)."""
        # Example: check required keys, types, etc.
        # For now, just check config is loaded
        if not self.config:
            raise ValueError("Notification config failed to load.")
        # Add more validation as needed

    def get_scheduler_state(self) -> dict:
        """Expose scheduler state for inspection/testing."""
        return self.scheduler.get_state()
