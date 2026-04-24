"""
scheduler.py
Notification microservice: Scheduler/Reminder logic (migrated from legacy unified_scheduler.py)
- Handles scheduling, reminders, and notification timing logic
- Integrates with orchestrator and config-driven architecture
"""



# --- Python Standard Library ---
from datetime import datetime
import logging
from typing import List

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.services.external.notification_services._internal.channels.base_channel import AlertNotification
from src.stockreports.utils.alert_utils import normalize_alert_notification
from src.stockreports.model.signal_type import SignalType
from src.stockreports.alert.common.constants import Approach

logger = logging.getLogger(__name__)

class NotificationSchedulerState:
    def __init__(self, alert: AlertNotification, reminder_delay: float, close_delay: float) -> None:
        self.alert: AlertNotification = alert
        self.order_reminder_status: bool = False
        self.close_position_status: bool = False
        self.reminder_delay: float = reminder_delay
        self.close_delay: float = close_delay


class NotificationScheduler:
    """
    NotificationScheduler - Manages scheduled reminders and close position notifications.
    Migrated and refactored from legacy unified_scheduler.py.
    """

    @staticmethod
    def _get_scheduler_approach():
        """Returns the canonical approach for scheduler-generated notifications."""
        return Approach.SCHEDULER

    def __init__(self, config_loader: object, orchestrator: object = None) -> None:
        self.config_loader = config_loader
        self.orchestrator = orchestrator
        self._state: List[NotificationSchedulerState] = []  # List of alert states
        # Delays are now per-symbol/approach, loaded dynamically
        self.reminder_delay = None
        self.close_delay = None

    def _get_reminder_delays(self, symbol: str, approach: str) -> dict:
        """
        Returns reminder_delays dict for the given symbol/approach from config, or defaults.
        """
        try:
            delays = self.config_loader.data.get("symbols", {}).get(symbol, {}).get("approaches", {}).get(approach, {}).get("reminder_delays", {})
            return {
                "order_delay_minutes": delays.get("order_delay_minutes", 5),
                "close_delay_minutes": delays.get("close_delay_minutes", 10)
            }
        except Exception:
            return {"order_delay_minutes": 5, "close_delay_minutes": 10}

    def append_new_signal(self, notification: object) -> None:
        """
        Update state with the new BUY/SELL alert notification.
        Resets sent status for reminders.
        """
        notification = normalize_alert_notification(notification)
        sig = notification.signal
        symbol = notification.symbol
        approach = notification.approach
        # Accept both enum and string signals
        if isinstance(sig, SignalType):
            is_trade = sig in {SignalType.BUY, SignalType.SELL}
        else:
            norm = str(sig).strip().upper().replace(" ", "_")
            is_trade = norm in {"BUY", "SELL"}
        if is_trade:
            # Load delays for this symbol/approach
            delays = self._get_reminder_delays(symbol, approach)
            reminder_delay = delays["order_delay_minutes"]
            close_delay = delays["close_delay_minutes"]
            # Add new alert state to the list
            self._state.append(NotificationSchedulerState(notification, reminder_delay, close_delay))
        # Ignore non-trade signals

    def check_and_notify(self, current_time: datetime) -> List[AlertNotification]:
        """
        Checks if reminders/close notifications are due for all alerts. Returns a list of notifications to send.
        """
        notifications = []
        # Iterate over all alert states
        for state in self._state[:]:  # Copy to allow removal
            alert = state.alert
            if alert is None:
                continue
            alert_time = alert.alert_time
            logger.debug(f'Scheduler: alert_time={alert_time}, now={current_time}')
            if alert_time is None:
                continue
            time_since_alert = (current_time - alert_time).total_seconds() / 60
            logger.debug(f'Scheduler: time_since_alert={time_since_alert}, reminder_delay={state.reminder_delay}, close_delay={state.close_delay}')
            logger.debug(f'Scheduler: order_reminder_status={state.order_reminder_status}, close_position_status={state.close_position_status}')

            # Order Reminder
            if (state.reminder_delay is not None
                and not state.order_reminder_status
                and time_since_alert >= state.reminder_delay):
                logger.debug('Scheduler: ORDER REMINDER due')
                reminder_notification = self._make_reminder_notification(alert, current_time)
                notifications.append(reminder_notification)
                state.order_reminder_status = True

            # Close Position
            if (state.close_delay is not None
                and not state.close_position_status
                and time_since_alert >= state.close_delay):
                logger.debug('Scheduler: CLOSE POSITION due')
                close_notification = self._make_close_notification(alert, current_time)
                notifications.append(close_notification)
                state.close_position_status = True

            # Remove state if both sent
            if state.order_reminder_status and state.close_position_status:
                logger.debug('Scheduler: Both reminders sent for alert, removing state')
                self._state.remove(state)

        return notifications

    def _make_reminder_notification(self, alert: AlertNotification, now: datetime) -> AlertNotification:
        # Returns a new AlertNotification for order reminder (explicit AlertNotification)
        return AlertNotification(
            symbol=alert.symbol,
            signal=f"ORDER REMINDER ({alert.signal})",
            alert_price=alert.alert_price,
            alert_time=now,
            approach=alert.approach,
            details={
                "original_signal_time": str(alert.alert_time),
                "notification_type": "order_reminder"
            },
            suggested_price=alert.suggested_price
        )

    def _make_close_notification(self, alert: AlertNotification, now: datetime) -> AlertNotification:
        # Returns a new AlertNotification for close position (explicit AlertNotification)
        return AlertNotification(
            symbol=alert.symbol,
            signal=f"CLOSE POSITION ({alert.signal})",
            alert_price=alert.alert_price,
            alert_time=now,
            approach=alert.approach,
            details={
                "original_signal_time": str(alert.alert_time),
                "notification_type": "close_position"
            },
            suggested_price=None
        )


    def get_state(self) -> List[NotificationSchedulerState]:
        """Returns a copy of the current scheduler state list."""
        return list(self._state)

    def reset_state(self) -> None:
        """Resets the scheduler state (clears all alerts)."""
        self._state = []
