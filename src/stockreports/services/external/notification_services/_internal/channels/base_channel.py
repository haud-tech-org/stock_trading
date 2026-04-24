"""
BaseNotificationChannel - Abstract base class for notification channels.
"""

# --- Python Standard Library ---
from abc import ABC, abstractmethod

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertNotification, AlertData
from src.stockreports.utils.alert_utils import normalize_alert_notification

class BaseNotificationChannel(ABC):
    def __init__(self, config: object) -> None:
        self.config = config
        self.validate_config()

    def send(self, notification: object) -> None:
        """
        Normalizes the notification to AlertNotification, then delegates to the derived implementation.
        Accepts either AlertData or AlertNotification.
        """
        normalized = self._normalize_notification(notification)
        self._send(normalized)

    @abstractmethod
    def _send(self, notification: AlertNotification) -> None:
        """
        Derived classes must implement this method, which always receives an AlertNotification.
        """
        pass

    def _normalize_notification(self, notification: object) -> AlertNotification:
        return normalize_alert_notification(notification)

    @abstractmethod
    def validate_config(self) -> None:
        pass
