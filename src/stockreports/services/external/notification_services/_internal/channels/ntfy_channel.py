"""
NtfyNotificationChannel - Ntfy (web push) notification channel implementation.
"""




# --- Python Standard Library ---
import logging
from typing import Optional, List

# --- Third-Party Libraries ---
import requests

# --- Project Imports ---
from .base_channel import BaseNotificationChannel
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.config import loader as config_loader

logger = logging.getLogger(__name__)


class NtfyNotificationChannel(BaseNotificationChannel):
    def __init__(self, config: Optional[object] = None) -> None:
        self._config: Optional[object] = config

    def _get_settings(self) -> object:
        if self._config is not None:
            return self._config
        return config_loader.get_notification_settings()

    def _send(self, notification: AlertNotification) -> bool:
        """
        Send a ntfy push notification for the given AlertNotification.
        """
        notification_settings = self._get_settings()
        if not notification_settings.NTFY_ENABLED:
            logger.info("Ntfy notifications are disabled in settings.")
            return False
        topics: List[str] = notification_settings.NTFY_TOPICS or []
        if not topics:
            logger.warning("Ntfy is enabled but no topics are configured in notification_settings. Skipping.")
            return False
        profit_thresh: str = ""
        if notification.suggested_profit_threshold is not None:
            profit_thresh = f" | Profit Threshold: {notification.suggested_profit_threshold:.2f}"
        suggested_price_str: str = f"{notification.suggested_price:.2f}" if notification.suggested_price is not None else "N/A"
        alert_price_str: str = f"{notification.alert_price:.2f}" if notification.alert_price is not None else "N/A"
        title: str = f"{notification.signal} - {notification.symbol} - Suggest: {suggested_price_str}{profit_thresh} - at signal price {alert_price_str} ({notification.approach})"
        alert_time_str: str = "N/A"
        if notification.alert_time is not None:
            try:
                alert_time_str = notification.alert_time.strftime('%H:%M:%S')
            except Exception:
                alert_time_str = str(notification.alert_time)
        message: str = f"Time: {alert_time_str}"
        for topic in topics:
            try:
                requests.post(
                    f"https://ntfy.sh/{topic}",
                    data=message.encode('utf-8'),
                    headers={"Title": title}
                )
                logger.info(f"Successfully sent ntfy push notification to topic '{topic}' for {notification.approach} signal.")
            except Exception as e:
                logger.error(f"Failed to send ntfy push notification to topic '{topic}': {e}")
        return True

    def validate_config(self) -> None:
        notification_settings = self._get_settings()
        if notification_settings.NTFY_ENABLED and not notification_settings.NTFY_TOPICS:
            raise ValueError("NtfyNotificationChannel: NTFY_TOPICS must be set in notification_settings.py or environment if NTFY is enabled.")
