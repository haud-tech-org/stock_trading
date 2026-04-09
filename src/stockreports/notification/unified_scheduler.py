# src/stockreports/notification/unified_scheduler.py
"""
Unified Scheduler - Manages both Order Reminder and Close Position notifications.

Checks in order:
1. Order Reminder (shorter delay, e.g., 5 minutes)
2. Close Position (longer delay, e.g., 10 minutes)

By default, close position delay is longer than order reminder delay.

State is stored in a single dictionary for clarity and extensibility.
"""

import logging
from datetime import datetime
from typing import Optional, List

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.alert.common.constants import Signal

# --- Module-level state (Dictionary-based) ---
# Single dictionary tracks the current alert and what's been sent
_scheduled_state = {
    'alert': None,  # Current BUY/SELL alert notification
    'sent': {
        'order_reminder': False,       # Has order reminder been sent?
        'close_position': False        # Has close position been sent?
    }
}

# --- Configuration ---
signal_settings = loader.get_signal_settings()
logger = logging.getLogger(__name__)


def update_latest_signal(notification: AlertNotification) -> None:
    """
    Updates the module-level state with the latest signal alert.
    Resets the sent status for all notification types.
    
    This function is called by the NotificationManager whenever a new BUY/SELL 
    alert is sent. When a new signal replaces the old one, both reminder timers 
    reset and start counting from zero.
    
    Args:
        notification (AlertNotification): The signal notification (BUY/SELL).
    """
    global _scheduled_state
    
    valid_signals = [Signal.BUY, Signal.SELL]
    if notification.signal in valid_signals:
        # Log if replacing a previous signal
        if _scheduled_state['alert'] is not None:
            prev_signal = _scheduled_state['alert'].signal
            logger.info(
                f"Unified Scheduler: Replacing previous {prev_signal} signal "
                f"with new {notification.signal} for {notification.symbol}. "
                f"Timers reset."
            )
        else:
            logger.info(
                f"Unified Scheduler: Updated with {notification.signal} signal "
                f"for {notification.symbol} at {notification.alert_time}."
            )
        
        # Replace with new signal and reset sent flags
        _scheduled_state = {
            'alert': notification,
            'sent': {
                'order_reminder': False,
                'close_position': False
            }
        }
    else:
        logger.debug(
            f"Unified Scheduler: Ignoring non-trade signal '{notification.signal}'"
        )


def check_and_notify(current_time: datetime) -> List[AlertNotification]:
    """
    Checks both scheduled notifications in priority order:
    1. Order Reminder (shorter delay, e.g., 5 minutes)
    2. Close Position (longer delay, e.g., 10 minutes)
    
    This function should be called periodically (e.g., every minute from the 
    monitoring loop). It returns a list of notifications to send, which can be:
    - Empty list: No notifications due yet
    - [order_reminder]: Order reminder due
    - [close_position]: Close position due
    - [order_reminder, close_position]: Both due (if they have same delay or time_since >= both delays)
    
    Automatically resets state when both notifications have been sent, allowing
    a new signal to be tracked.
    
    Args:
        current_time (datetime): Current time (typically from TimeSimulator).
        
    Returns:
        List[AlertNotification]: List of notifications to send (0-2 items).
    """
    global _scheduled_state
    
    notifications = []
    
    # No active alert? Nothing to do
    if _scheduled_state['alert'] is None:
        logger.debug("Unified Scheduler: No active alert")
        return notifications
    
    alert = _scheduled_state['alert']
    time_since_alert = (current_time - alert.alert_time).total_seconds() / 60
    
    logger.debug(
        f"Unified Scheduler: {time_since_alert:.2f} min since {alert.signal} "
        f"for {alert.symbol}. Sent: {_scheduled_state['sent']}"
    )
    
    # --- Check 1: Order Reminder (shorter delay) ---
    reminder_delay = signal_settings.SCHEDULED_REMINDER_ORDER_DELAY_MINUTES
    
    if (reminder_delay is not None 
        and not _scheduled_state['sent']['order_reminder']
        and time_since_alert >= reminder_delay):
        
        logger.info(
            f"Unified Scheduler: Sending ORDER REMINDER for {alert.symbol} "
            f"({time_since_alert:.2f} min >= {reminder_delay} min)"
        )
        
        reminder_notification = AlertNotification(
            symbol=alert.symbol,
            signal=f"ORDER REMINDER ({alert.signal})",
            alert_price=alert.alert_price,
            alert_time=current_time,
            approach="Scheduler",
            details={
                "original_signal_time": alert.alert_time.isoformat(),
                "notification_type": "order_reminder"
            },
            suggested_price=alert.suggested_price
        )
        
        notifications.append(reminder_notification)
        _scheduled_state['sent']['order_reminder'] = True
        logger.debug("Unified Scheduler: Marked order_reminder as sent")
    
    # --- Check 2: Close Position (longer delay) ---
    close_delay = signal_settings.SCHEDULED_REMINDER_CLOSE_DELAY_MINUTES
    
    if (close_delay is not None 
        and not _scheduled_state['sent']['close_position']
        and time_since_alert >= close_delay):
        
        logger.info(
            f"Unified Scheduler: Sending CLOSE POSITION for {alert.symbol} "
            f"({time_since_alert:.2f} min >= {close_delay} min)"
        )
        
        close_notification = AlertNotification(
            symbol=alert.symbol,
            signal=f"CLOSE POSITION ({alert.signal})",
            alert_price=alert.alert_price,
            alert_time=current_time,
            approach="Scheduler",
            details={
                "original_signal_time": alert.alert_time.isoformat(),
                "notification_type": "close_position"
            },
            suggested_price=None  # Not applicable for close signal
        )
        
        notifications.append(close_notification)
        _scheduled_state['sent']['close_position'] = True
        logger.debug("Unified Scheduler: Marked close_position as sent")
    
    # --- Auto-reset when both sent ---
    if all(_scheduled_state['sent'].values()):
        logger.info(
            "Unified Scheduler: Both notifications sent. "
            f"Resetting state for new alert (sent {len(notifications)} notifications)"
        )
        reset_state()
    
    logger.debug(
        f"Unified Scheduler: Returning {len(notifications)} notifications"
    )
    
    return notifications


def get_state() -> dict:
    """
    Returns a copy of the current scheduler state (for debugging/testing).
    
    Returns:
        dict: Current state with 'alert' and 'sent' keys.
    """
    return {
        'alert': _scheduled_state['alert'],
        'sent': _scheduled_state['sent'].copy()
    }


def reset_state() -> None:
    """
    Manually resets the scheduler state (for testing/emergency reset).
    """
    global _scheduled_state
    logger.warning("Unified Scheduler: Manual state reset")
    _scheduled_state = {
        'alert': None,
        'sent': {
            'order_reminder': False,
            'close_position': False
        }
    }
