# src/stockreports/alert/price_movement_alerter.py


# --- Standard Library Imports ---
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict

# --- Third-Party Imports ---
import pandas as pd
import pytz

# --- Project Imports ---
from src.stockreports.config.loader import get_price_alert_settings
from src.stockreports.utils.time_utils import TIMEZONE
from src.stockreports.alert.common.constants import Approach, Status
from src.stockreports.model.signal_type import SignalType
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.announce.base import AnnouncementAlerter

logger = logging.getLogger(__name__)

class PriceMovementAlerter(AnnouncementAlerter):
    """
    Announcement approach for detecting price movements against predefined levels.
    Implements the abstract execute method from AnnouncementAlerter.
    """
    APPROACH_NAME: str = Approach.PRICE_MOVEMENT
    _triggered_levels_today: Dict[str, Dict[float, datetime]] = {}

    def __init__(self, symbol: str):
        self._symbol = symbol
        self._settings = get_price_alert_settings()
        self._config = self._settings.PRICE_ALERTS.get(self._symbol, {})
        self._allow_repeated_alerts = self._settings.ALLOW_REPEATED_LEVEL_ALERTS
        self._level_alert_cooldown = self._settings.LEVEL_ALERT_COOLDOWN_MINUTES
        self._ensure_symbol_dict()
        self._remove_expired_levels()
        logger.info(f"PriceMovementAlerter initialized for {self._symbol}. Config found: {bool(self._config)}")

    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        if not self._config:
            logger.warning(f"No price alert configuration found for symbol '{self._symbol}'. Skipping.")
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
        last_two_ticks = master_df.iloc[-2:]
        prev_price = last_two_ticks.iloc[0]['close']
        curr_price = last_two_ticks.iloc[-1]['close']
        curr_time = last_two_ticks.index[-1]
        prev_time = last_two_ticks.index[0]
        if isinstance(curr_time, str):
            curr_time = pd.to_datetime(curr_time)
        if isinstance(prev_time, str):
            prev_time = pd.to_datetime(prev_time)
        confirmed_alerts: List[AlertData] = []
        fixed_levels = self._config.get("fixed_levels")
        if fixed_levels:
            for level in fixed_levels:
                if self._has_straddled(prev_price, curr_price, level):
                    should_trigger = self._allow_repeated_alerts or not self._is_level_in_cooldown(level)
                    if should_trigger:
                        direction = "crossed above" if curr_price > prev_price else "crossed below"
                        message = (f"'{self._symbol}' {direction} fixed price level of {level:.2f}. "
                                   f"Current price: {curr_price:.2f}.")
                        signal_type = SignalType.PRICE_UP.name if curr_price > prev_price else SignalType.PRICE_DOWN.name
                        alert = AlertData(
                            approach=self.APPROACH_NAME,
                            symbol=self._symbol,
                            id=str(uuid.uuid4()),
                            signal=signal_type,
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
                        )
                        confirmed_alerts.append(alert)
                        PriceMovementAlerter._triggered_levels_today[self._symbol][level] = curr_time
                        logger.info(f"Alert triggered for fixed level {level:.2f} for {self._symbol} ({direction})")
        interval = self._config.get("absolute_interval")
        ref_price = self._config.get("reference_price")
        if interval and ref_price is not None:
            prev_level = self._get_interval_level(prev_price, ref_price, interval)
            curr_level = self._get_interval_level(curr_price, ref_price, interval)
            if curr_level != prev_level:
                crossed_boundary = curr_level * interval + ref_price if curr_price > prev_price else prev_level * interval + ref_price
                should_trigger = self._allow_repeated_alerts or not self._is_level_in_cooldown(crossed_boundary)
                if should_trigger:
                    direction = "crossed above" if curr_price > prev_price else "crossed below"
                    message = (f"'{self._symbol}' {direction} an interval price level. "
                               f"New level boundary: {crossed_boundary:.2f}. Current price: {curr_price:.2f}.")
                    signal_type = SignalType.PRICE_UP.name if curr_price > prev_price else SignalType.PRICE_DOWN.name
                    alert = AlertData(
                        approach=self.APPROACH_NAME,
                        symbol=self._symbol,
                        id=str(uuid.uuid4()),
                        signal=signal_type,
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
                    )
                    confirmed_alerts.append(alert)
                    PriceMovementAlerter._triggered_levels_today[self._symbol][crossed_boundary] = curr_time
                    logger.info(f"Alert triggered for interval level {crossed_boundary:.2f} for {self._symbol} ({direction})")
        return AlertResult(
            approach_name=self.APPROACH_NAME,
            confirmed_alerts=confirmed_alerts,
            status=Status.SUCCESS,
            message=f"Found {len(confirmed_alerts)} price movement alerts"
        )

    def _ensure_symbol_dict(self) -> None:
        if self._symbol not in PriceMovementAlerter._triggered_levels_today:
            PriceMovementAlerter._triggered_levels_today[self._symbol] = {}

    def _is_level_in_cooldown(self, level: float) -> bool:
        symbol_levels = PriceMovementAlerter._triggered_levels_today.get(self._symbol, {})
        return level in symbol_levels

    def _remove_expired_levels(self) -> None:
        if self._symbol not in PriceMovementAlerter._triggered_levels_today:
            return
        symbol_levels = PriceMovementAlerter._triggered_levels_today[self._symbol]
        current_time = datetime.now(pytz.utc).astimezone(TIMEZONE)
        cooldown_delta = timedelta(minutes=self._level_alert_cooldown)
        expired_levels = [
            level for level, triggered_time in symbol_levels.items()
            if (current_time - triggered_time) >= cooldown_delta
        ]
        for level in expired_levels:
            del symbol_levels[level]
            logger.debug(f"Level {level:.2f} expired for {self._symbol}")
        if expired_levels:
            logger.info(f"Cleaned up {len(expired_levels)} expired levels for {self._symbol}")

    def _has_straddled(self, price1: float, price2: float, level: float) -> bool:
        return (price1 < level <= price2) or (price1 > level >= price2)

    def _get_interval_level(self, price: float, ref_price: float, interval: float) -> int:
        return int((price - ref_price) / interval)
