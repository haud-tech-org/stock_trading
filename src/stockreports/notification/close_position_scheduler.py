# src/stockreports/notification/close_position_scheduler.py
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertNotification
from src.stockreports.alert.common.constants import Signal

# --- Module-level state ---
# Stores the latest signal alert that is pending a "close" notification.
_latest_signal_alert: Optional[AlertNotification] = None

# --- Configuration ---
signal_settings = loader.get_signal_settings()
notification_settings = loader.get_notification_settings()
logger = logging.getLogger(__name__)

def update_latest_signal(notification: AlertNotification):
    """
    Updates the module-level state with the latest signal alert.
    This function is called by the NotificationManager whenever a new alert is sent.
    """
    global _latest_signal_alert
    
    # We only care about BUY/SELL signals for closing positions
    valid_signals = [Signal.BUY, Signal.SELL]
    if notification.signal in valid_signals:
        logger.info(f"Close position scheduler updated with new signal: {notification.signal} for {notification.symbol} at {notification.alert_time}.")
        _latest_signal_alert = notification
    else:
        logger.debug(f"Scheduler: Ignoring non-trade signal '{notification.signal}' for close position scheduler.")

def check_and_notify(current_time: datetime) -> Optional[AlertNotification]:
    """
    Checks if the time since the last alert has exceeded the configured delay
    and sends a "Close Position" notification if it has.
    
    Args:
        current_time (datetime): The current time from the TimeSimulator.
        
    Returns:
        Optional[AlertNotification]: A notification object if the timer has expired, otherwise None.
    """
    global _latest_signal_alert
    
    logger.debug("Scheduler: Checking for expired timers.")
    
    delay_minutes = signal_settings.CLOSE_POSITION_DELAY_MINUTES
    
    # Do nothing if the feature is disabled or no signal is pending
    if delay_minutes is None or _latest_signal_alert is None:
        logger.debug("Scheduler: Inactive (disabled or no pending signal).")
        return None

    time_since_alert = (current_time - _latest_signal_alert.alert_time).total_seconds() / 60
    logger.debug(f"Scheduler: Time since last alert: {time_since_alert:.2f} minutes. Required: {delay_minutes} minutes.")
    
    if time_since_alert >= delay_minutes:
        logger.info(f"Scheduler: Timer of {delay_minutes} minutes expired for signal at {_latest_signal_alert.alert_time}. Preparing 'Close Position' notification.")
        
        # Create a new notification object for the close signal
        close_notification = AlertNotification(
            symbol=_latest_signal_alert.symbol,
            signal=f"CLOSE POSITION ({_latest_signal_alert.signal})",
            alert_price=_latest_signal_alert.alert_price, # Or fetch current price if needed
            alert_time=current_time,
            approach="Scheduler",
            details={"original_signal_time": _latest_signal_alert.alert_time.isoformat()},
            suggested_price=None # Not applicable for a close signal
        )
        
        # Reset the latest signal to prevent re-sending
        _latest_signal_alert = None

        return close_notification
        
    logger.debug("Scheduler: Timer has not expired yet.")
    return None
