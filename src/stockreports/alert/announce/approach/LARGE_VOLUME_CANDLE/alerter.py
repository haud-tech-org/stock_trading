# --- Standard Library Imports ---
import logging
import uuid

# --- Third-Party Imports ---
import pandas as pd

# --- Project Imports ---
from src.stockreports.alert.announce.announcement_alerter import AnnouncementAlerterBase
from src.stockreports.alert.common.constants import Approach, Status, CandleColumn, Trend, Signal
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.model.signal_type import SignalType
from src.stockreports.alert.alerter import Alerter
from src.stockreports.utils.candle_utils import get_trend_from_candle


class LargeVolumeCandleAlerter(AnnouncementAlerterBase):
    """
    Announcement approach for detecting large volume candles (volume spike).
    Implements the abstract execute method from AnnouncementAlerterBase.
    """
    APPROACH_NAME: str = Approach.LARGE_VOLUME_CANDLE

    def __init__(self, symbol: str):
        self._symbol = symbol
        self.approach_name = Approach.LARGE_VOLUME_CANDLE
        self.approach_settings = Alerter.get_approach_config(self._symbol, self.approach_name)
        logging.info(f"LargeVolumeCandleAlerter initialized for {self._symbol}. Config: {self.approach_settings}")

    def execute(self, master_df: pd.DataFrame) -> AlertResult:
        if master_df is None or len(master_df) < 2:
            logging.warning("Insufficient data for LargeVolumeCandleAlerter.")
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.SUCCESS,
                message="No data to process"
            )
        latest = master_df.iloc[-1]
        nearest = master_df.iloc[-2]
        multiplier = self.approach_settings.get('MULTIPLIER_VOLUME', 2)
        confirmed_alerts = []
        # Validation logic
        actual_multiplier = latest[CandleColumn.VOLUME] / nearest[CandleColumn.VOLUME] if nearest[CandleColumn.VOLUME] != 0 else float('inf')
        if actual_multiplier >= multiplier:
            alert_time = latest.name
            start_time = nearest.name
            if isinstance(alert_time, str):
                alert_time = pd.to_datetime(alert_time)
            if isinstance(start_time, str):
                start_time = pd.to_datetime(start_time)
            trend = get_trend_from_candle(latest)
            signal_type = SignalType.PRICE_UP.name if trend == Trend.UPTREND else (SignalType.PRICE_DOWN.name if trend == Trend.DOWNTREND else "NEUTRAL")
            alert = AlertData(
                approach=self.APPROACH_NAME,
                symbol=self._symbol,
                id=str(uuid.uuid4()),
                signal=signal_type,
                alert_price=latest[CandleColumn.CLOSE] if CandleColumn.CLOSE in latest else None,
                alert_time=alert_time,
                start_price=nearest[CandleColumn.CLOSE] if CandleColumn.CLOSE in nearest else None,
                start_time=start_time,
                trend=trend,
                magnitude=latest[CandleColumn.VOLUME],
                details=(
                    f"Volume spike: "
                    f"latest(volume={latest[CandleColumn.VOLUME]}, time={alert_time}), "
                    f"nearest(volume={nearest[CandleColumn.VOLUME]}, time={start_time}), "
                    f"expected_multiplier={multiplier}, "
                    f"actual_multiplier={actual_multiplier:.2f}"
                )
            )
            confirmed_alerts.append(alert)
            logging.info(f"LargeVolumeCandleAlerter: Alert triggered for {self._symbol}. {alert.details}")
        return AlertResult(
            approach_name=self.APPROACH_NAME,
            confirmed_alerts=confirmed_alerts,
            status=Status.SUCCESS,
            message=f"Found {len(confirmed_alerts)} large volume candle alerts"
        )
