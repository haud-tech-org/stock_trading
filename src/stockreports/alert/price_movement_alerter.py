# src/stockreports/alert/price_movement_alerter.py

import pandas as pd
import json
import uuid
import math
import logging
import pytz
from typing import List, Dict
from datetime import datetime, timedelta
from ..config.loader import get_price_alert_settings
from ..utils.time_utils import TIMEZONE
from .common.constants import Approach, Signal, Status
from .model.models import AlertResult, AlertData

# Get a logger for this module
logger = logging.getLogger(__name__)

class PriceMovementAlerter:
    """
    A detector for price movements against predefined levels.
    Self-contained tracking of triggered levels with time-based expiration.
    Returns standardized AlertResult with confirmed_alerts containing AlertData objects.
    """
    
    APPROACH_NAME: str = Approach.PRICE_MOVEMENT
    
    # Class-level state: persists across all instances and service lifecycle
    triggered_levels_today: Dict[float, datetime] = {}

    def __init__(self, symbol: str):
        """
        Initializes the PriceMovementAlerter.

        Args:
            symbol (str): The stock symbol to check.
        """
        self.symbol = symbol
        self.settings = get_price_alert_settings()
        self.config = self.settings.PRICE_ALERTS.get(self.symbol, {})
        self.allow_repeated_alerts = self.settings.ALLOW_REPEATED_LEVEL_ALERTS
        self.level_alert_cooldown = self.settings.LEVEL_ALERT_COOLDOWN_MINUTES
        
        # Clean up expired levels on initialization
        self._remove_expired_levels()
        
        logger.info(f"PriceMovementAlerter initialized for {self.symbol}. Config found: {bool(self.config)}")

    def _remove_expired_levels(self) -> None:
        """
        Removes all expired level entries from triggered_levels_today dictionary.
        Expired entries are those older than level_alert_cooldown.
        """
        # Get current time in market timezone (timezone-aware)
        current_time = datetime.now(pytz.utc).astimezone(TIMEZONE)
        expired_levels = []
        cooldown_delta = timedelta(minutes=self.level_alert_cooldown)
        
        for level, triggered_time in PriceMovementAlerter.triggered_levels_today.items():
            time_elapsed = current_time - triggered_time
            if time_elapsed >= cooldown_delta:
                expired_levels.append(level)
                logger.debug(f"Level {level:.2f} expired (elapsed: {time_elapsed})")
        
        for level in expired_levels:
            del PriceMovementAlerter.triggered_levels_today[level]
        
        if expired_levels:
            logger.info(f"Cleaned up {len(expired_levels)} expired levels for {self.symbol}")

    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        """
        Checks for price level crossings and returns standardized AlertResult.

        Args:
            master_df (pd.DataFrame): All data received so far today.

        Returns:
            AlertResult: Standardized alert result with confirmed_alerts containing
                        AlertData objects for each price movement detected.
        """
        if not self.config:
            logger.warning(f"No price alert configuration found for symbol '{self.symbol}'. Skipping.")
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.SUCCESS,
                message="No price alert configuration found"
            )
        
        if master_df.empty:
            logger.warning("master_df is empty. Skipping price movement check.")
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.SUCCESS,
                message="No data to process"
            )

        if len(master_df) < 2:
            logger.warning("Not enough data points (< 2) to check for price movement. Skipping.")
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.SUCCESS,
                message="Insufficient data points"
            )

        # Use the last two entries of the master_df to represent the most recent price movement
        last_two_ticks = master_df.iloc[-2:]
        prev_price = last_two_ticks.iloc[0]['close']
        curr_price = last_two_ticks.iloc[-1]['close']
        curr_time = last_two_ticks.iloc[-1]['time']
        prev_time = last_two_ticks.iloc[0]['time']

        # Convert to datetime if string
        if isinstance(curr_time, str):
            curr_time = pd.to_datetime(curr_time)
        if isinstance(prev_time, str):
            prev_time = pd.to_datetime(prev_time)

        confirmed_alerts: List[AlertData] = []

        # 1. Check for fixed level alerts
        fixed_levels = self.config.get("fixed_levels")
        if fixed_levels:
            for level in fixed_levels:
                if self._has_straddled(prev_price, curr_price, level):
                    # Allow alert if: repeated allowed OR level not in tracking
                    should_trigger = self.allow_repeated_alerts or level not in PriceMovementAlerter.triggered_levels_today
                    
                    if should_trigger:
                        direction = "crossed above" if curr_price > prev_price else "crossed below"
                        message = (f"'{self.symbol}' {direction} fixed price level of {level:.2f}. "
                                   f"Current price: {curr_price:.2f}.")
                        
                        # Create AlertData object for this alert
                        alert = AlertData(
                            approach=self.APPROACH_NAME,
                            id=str(uuid.uuid4()),
                            signal=Signal.NEUTRAL,  # Price movements are neutral signals
                            alert_price=curr_price,
                            alert_time=curr_time,
                            start_price=prev_price,
                            start_time=prev_time,
                            magnitude=abs(curr_price - prev_price),
                            details=json.dumps({
                                'message': message,
                                'level': level,
                                'direction': direction
                            })
                            # No suggested prices for price movement alerts
                        )
                        confirmed_alerts.append(alert)
                        PriceMovementAlerter.triggered_levels_today[level] = curr_time
                        logger.info(f"Alert triggered for fixed level {level:.2f} ({direction})")

        # 2. Check for absolute interval alerts
        interval = self.config.get("absolute_interval")
        ref_price = self.config.get("reference_price")

        if interval and ref_price is not None:
            prev_level = self._get_interval_level(prev_price, ref_price, interval)
            curr_level = self._get_interval_level(curr_price, ref_price, interval)

            if curr_level != prev_level:
                # Determine the actual boundary that was crossed
                # When moving UP: use curr_level boundary
                # When moving DOWN: use prev_level boundary
                crossed_boundary = curr_level * interval + ref_price if curr_price > prev_price else prev_level * interval + ref_price
                
                # Allow alert if: repeated allowed OR level not in tracking
                should_trigger = self.allow_repeated_alerts or crossed_boundary not in PriceMovementAlerter.triggered_levels_today
                
                if should_trigger:
                    direction = "crossed above" if curr_price > prev_price else "crossed below"
                    message = (f"'{self.symbol}' {direction} an interval price level. "
                               f"New level boundary: {crossed_boundary:.2f}. Current price: {curr_price:.2f}.")
                    
                    # Create AlertData object for this alert
                    alert = AlertData(
                        approach=self.APPROACH_NAME,
                        id=str(uuid.uuid4()),
                        signal=Signal.NEUTRAL,  # Price movements are neutral signals
                        alert_price=curr_price,
                        alert_time=curr_time,
                        start_price=prev_price,
                        start_time=prev_time,
                        magnitude=abs(curr_price - prev_price),
                        details=json.dumps({
                            'message': message,
                            'boundary': crossed_boundary,
                            'interval': interval,
                            'direction': direction
                        })
                        # No suggested prices for price movement alerts
                    )
                    confirmed_alerts.append(alert)
                    PriceMovementAlerter.triggered_levels_today[crossed_boundary] = curr_time
                    logger.info(f"Alert triggered for interval level {crossed_boundary:.2f} ({direction})")

        return AlertResult(
            approach_name=self.APPROACH_NAME,
            confirmed_alerts=confirmed_alerts,
            status=Status.SUCCESS,
            message=f"Found {len(confirmed_alerts)} price movement alerts"
        )

    def _has_straddled(self, price1: float, price2: float, level: float) -> bool:
        """
        Checks if the price crossed a specific level between two points.
        """
        return (price1 < level <= price2) or (price1 > level >= price2)

    def _get_interval_level(self, price: float, ref_price: float, interval: float) -> int:
        """
        Calculates which interval band a price belongs to using truncation.
        """
        return int((price - ref_price) / interval)
