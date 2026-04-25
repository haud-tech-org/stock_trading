"""
LARGE_CANDLE Announce Approach Alerter

Detects candles where the absolute body (|close - open|) is greater than or equal to 500 points.
Implements the AnnouncementAlerter interface for Layer 7 notification delivery.
"""

# --- Standard Library Imports ---
import logging
import uuid
from datetime import datetime
from typing import List

# --- Third-Party Imports ---
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.announce.announcement_alerter import AnnouncementAlerterBase
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Status, CandleColumn, Trend
from src.stockreports.model.signal_type import SignalType
from src.stockreports.alert.alerter import Alerter
from src.stockreports.utils.candle_utils import get_trend_from_candle

logger = logging.getLogger(__name__)

class LargeCandleAlerter(AnnouncementAlerterBase):
    """
    Announcement approach for detecting large candle bodies (>= 500 points).
    Implements the abstract execute method from AnnouncementAlerter.
    """
    APPROACH_NAME: str = Approach.LARGE_CANDLE

    def __init__(self, symbol: str):
        self._symbol = symbol
        self.approach_name = Approach.LARGE_CANDLE
        self.approach_settings = Alerter.get_approach_config(self._symbol, self.approach_name)
        logger.info(f"LargeCandleAlerter initialized for {self._symbol}. Config: {self.approach_settings}")

    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        """
        Detects large candles using high and low prices, following code quality standards.
        Uses CandleColumn enum for column access.
        """
        if master_df.empty or len(master_df) < 1:
            logger.warning("No data to process for large candle detection.")
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.SUCCESS,
                message="No data to process"
            )
        last_row = master_df.iloc[-1]
        high_price = last_row[CandleColumn.HIGH]
        low_price = last_row[CandleColumn.LOW]
        open_price = last_row[CandleColumn.OPEN]
        close_price = last_row[CandleColumn.CLOSE]
        candle_range = high_price - low_price
        threshold = self.approach_settings.get("BODY_THRESHOLD", 500)
        curr_time = last_row.name
        if isinstance(curr_time, str):
            curr_time = pd.to_datetime(curr_time)
        trend = get_trend_from_candle(last_row)
        signal_type = SignalType.PRICE_UP.name if trend == Trend.UPTREND else (SignalType.PRICE_DOWN.name if trend == Trend.DOWNTREND else "NEUTRAL")
        confirmed_alerts: List[AlertData] = []
        if candle_range >= threshold:
            message = (
                f"'{self._symbol}' large candle detected: range = {candle_range:.2f} points (trend: {trend})."
            )
            alert = AlertData(
                approach=self.APPROACH_NAME,
                symbol=self._symbol,
                id=str(uuid.uuid4()),
                signal=signal_type,
                alert_price=close_price,
                alert_time=curr_time,
                start_price=open_price,
                start_time=curr_time,
                magnitude=candle_range,
                details=message
            )
            confirmed_alerts.append(alert)
            logger.info(f"Large candle alert triggered for {self._symbol}: {message}")
        return AlertResult(
            approach_name=self.APPROACH_NAME,
            confirmed_alerts=confirmed_alerts,
            status=Status.SUCCESS,
            message=f"Found {len(confirmed_alerts)} large candle alerts"
        )
