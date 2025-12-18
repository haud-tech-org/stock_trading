# src/stockreports/alert/approach/PROMINENT_PEAK_REVERSAL/executor.py
import logging
import pandas as pd
import json
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertData, AlertResult, ConfirmationResult
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.config import loader

from .confirmation import ProminentPeakReversalConfirmation
from .settings import ProminentPeakReversalSignalSettings


logger = logging.getLogger(__name__)

class ProminentPeakReversalExecutor(Executor):
    """
    Executor for the Prominent Peak Reversal approach.
    """
    APPROACH_NAME = Approach.PROMINENT_PEAK_REVERSAL
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None

    def __init__(self, symbol: str):
        """
        Initializes the executor with the symbol.

        Args:
            symbol (str): The stock symbol.
        """
        super().__init__(symbol)
        self.settings = ProminentPeakReversalSignalSettings(symbol)
        self.confirmation = ProminentPeakReversalConfirmation(self.settings)
        self.global_settings = loader.get_settings()
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Executes the Prominent Peak Reversal logic by checking the latest candles.
        This method uses a unified reverse loop that works for both DEPLOYMENT and DEVELOPMENT modes.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for {self.symbol}...")
            
            alerts_data = self._find_reversal_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _find_reversal_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        """
        Finds alerts using a unified reverse loop for both DEPLOYMENT and DEVELOPMENT modes.
        """
        alerts = []
        is_development_mode = self.global_settings.MODE == Mode.DEVELOPMENT
        
        required_lookback = self.settings.lookback_window
        if len(df) < required_lookback:
            self.logger.warning(f"Not enough data to run analysis. Required: {required_lookback}, have: {len(df)}.")
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        loop_start = required_lookback - 1
        active_region_start = len(df_indexed) - new_candle_count if not is_development_mode else loop_start

        for i in range(loop_end, loop_start - 1, -1):
            if not is_development_mode and i < active_region_start:
                break

            # Cooldown check
            current_time = df_indexed.index[i]
            if ProminentPeakReversalExecutor.LATEST_ALERT_TIMESTAMP is not None:
                time_diff = (current_time - ProminentPeakReversalExecutor.LATEST_ALERT_TIMESTAMP).total_seconds() / 60
                if time_diff < self.settings.cooldown_window:
                    continue

            # Create a view for the confirmation logic
            window_end_index = i + 1
            window_start_index = window_end_index - self.settings.lookback_window
            
            if window_start_index < 0:
                continue

            current_lookback_view = df_indexed.iloc[window_start_index:window_end_index]

            confirmation_result = self.confirmation.confirm(current_lookback_view)

            if confirmation_result:
                last_candle = current_lookback_view.iloc[-1]
                # The first candle of the confirmation window (not the lookback window)
                first_candle = current_lookback_view.iloc[-self.settings.confirmation_window]
                # The peak/trough time is what we call the "reversal_time"
                peak_or_trough_time = confirmation_result.reversal_time
                peak_or_trough_candle = df_indexed.loc[peak_or_trough_time]
                
                alert = self._create_alert(
                    last_candle=last_candle,
                    first_candle=first_candle,
                    peak_or_trough_candle=peak_or_trough_candle,
                    confirmation_result=confirmation_result
                )
                alerts.append(alert)
                
                # Update the latest alert timestamp
                ProminentPeakReversalExecutor.LATEST_ALERT_TIMESTAMP = current_time

                if not is_development_mode:
                    return alerts # Exit after first alert in live mode

        return alerts[::-1] # Reverse to return in chronological order for development

    def _create_alert(self, last_candle: pd.Series, first_candle: pd.Series, peak_or_trough_candle: pd.Series, confirmation_result: ConfirmationResult) -> AlertData:
        """Creates a standardized AlertData object."""
        alert_time = last_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
        magnitude = round(abs(last_candle['close'] - peak_or_trough_candle['close']), 2)

        details = {
            "confirmation_window": self.settings.confirmation_window,
            "peak_prominence": self.settings.peak_prominence,
            "min_reversal_price_diff": self.settings.min_reversal_price_diff,
            "trend": confirmation_result.trend
        }

        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            signal=confirmation_result.signal,
            alert_time=alert_time,
            alert_price=last_candle['close'],
            approach=self.APPROACH_NAME,
            start_time=first_candle.name, # Time of the first candle in the window
            start_price=first_candle['close'], # Price of the first candle in the window
            magnitude=magnitude,
            details=json.dumps(details)
        )
