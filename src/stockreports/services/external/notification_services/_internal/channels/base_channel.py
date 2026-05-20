"""
BaseNotificationChannel - Abstract base class for notification channels.
"""

# --- Python Standard Library ---
import logging
from abc import ABC, abstractmethod

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertNotification, NotificationContext
from src.stockreports.utils.alert_utils import normalize_alert_notification
from src.stockreports.config import loader as config_loader
from src.stockreports.config.secrets_loader import SecretsLoader
from src.stockreports.alert.common.constants import RunMode
from src.stockreports.alert.common.environment import EnvironmentType

logger = logging.getLogger(__name__)


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

    # -------------------------------------------------------------------------
    # Common: run-context footer — shared by all channel implementations
    # -------------------------------------------------------------------------

    @staticmethod
    def _get_run_context_footer() -> NotificationContext:
        """
        Returns a NotificationContext with environment and run-mode info to be
        appended at the bottom of any notification payload.

        Sources:
          - notification_settings._secrets_loader._get_environment_type()
                → deployment environment (EnvironmentType.LOCAL / GCP / DOCKER / KUBERNETES / AZURE)
          - loader.get_settings().DEBUG_REPLAY_START_TIME
                → None  => run_mode = RunMode.LIVE
                   <str> => run_mode = "REPLAY (<timestamp>)"

        All calls are individually guarded — a failure in one source never
        prevents notification delivery.
        """
        environment = EnvironmentType.LOCAL
        run_mode = RunMode.LIVE

        try:
            notification_settings = config_loader.get_notification_settings()
            secrets_loader: SecretsLoader = notification_settings._secrets_loader
            if secrets_loader is not None:
                environment = secrets_loader._get_environment_type()
        except Exception as e:
            logger.debug(f"[BaseNotificationChannel] Could not read environment info: {e}")

        try:
            settings = config_loader.get_settings()
            replay_start = settings.DEBUG_REPLAY_START_TIME
            if replay_start:
                try:
                    replay_date = replay_start.date() if hasattr(replay_start, "date") else str(replay_start).split()[0]
                except Exception:
                    replay_date = str(replay_start).split()[0]
                run_mode = f"{RunMode.REPLAY} ({replay_date})"
            else:
                run_mode = RunMode.LIVE
        except Exception as e:
            logger.debug(f"[BaseNotificationChannel] Could not read run mode: {e}")

        return NotificationContext(
            environment=environment,
            run_mode=run_mode,
        )
