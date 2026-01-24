from abc import ABC, abstractmethod
from typing import Optional, Tuple
import pandas as pd
import logging
from src.stockreports.utils.log_factory import log
from varname import nameof

from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from src.stockreports.alert.common.constants import Signal, PeakTrough, PriceColumn, LogLevel, Trend
from src.stockreports.alert.common.data_utils import find_extreme_point
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.utils import candle_utils
from src.stockreports.alert.common.constants import ValidationStatus  # Add this import
from src.stockreports.utils.alert_utils import is_in_cooldown

class Executor(ABC):
    def __init__(self, symbol: str, approach: str, settings: Optional[BaseSettings] = None):
        self.symbol = symbol
        self.APPROACH_NAME = approach
        self.settings = settings

        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize context variables
        self.final_signal = Signal.NEUTRAL
        self.final_trend = Trend.NEUTRAL
        self.final_alert_candle = None
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0
        self.validation_step: int = 0
        self.validations: list = []
        self.LATEST_ALERT: Optional[AlertData] = None

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the VOLUME_SPIKE_CONFIRMATION approach (trend window version).
        """
        try:
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )
            alerts_data = self._find_alerts(df, new_candle_count)
            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.",
                log_level=LogLevel.INFO,
                execution_symbol=self.symbol
            )
            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame(), status="FAILED", message=str(e))

    def _step_cooldown_check(self, signal: Signal, cooldown_window) -> bool:
        self.next_validation()
        if is_in_cooldown(
            new_alert_time=self.current_window_end_time,
            new_signal=signal,
            latest_alert=self.LATEST_ALERT,
            cooldown_window=cooldown_window
        ):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert is in cooldown period.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return False
        self.validations.append(Validation(
            name=nameof(cooldown_window),
            step=self.current_step,
            validation=self.validation_step,
            message="Alert is not in cooldown period.",
            status=ValidationStatus.PASSED
        ))
        return True
    
    def set_final_alert_info(
        self,
        signal: Signal,
        trend: Trend,
        alert_candle: Optional[pd.Series]
    ) -> None:
        """
        Set the final signal, trend, and alert candle for this executor instance.

        Args:
            signal (Signal): The final signal (BUY, SELL, or NEUTRAL).
            trend (Trend): The final trend (UPTREND, DOWNTREND, or NEUTRAL).
            alert_candle (Optional[pd.Series]): The final alert candle as a pandas Series, or None.
        """
        self.final_signal = signal
        self.final_trend = trend
        self.final_alert_candle = alert_candle

    def get_final_alert_info(self) -> Tuple[Signal, Trend, Optional[pd.Series]]:
        """
        Get the final signal, trend, and alert candle for this executor instance.
        Returns:
            Tuple[Signal, Trend, Optional[pd.Series]]: (final_signal, final_trend, final_alert_candle)
        """
        return self.final_signal, self.final_trend, self.final_alert_candle
    
    def _confirm_breakout_price(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, lookback_period: int, prominence: float) -> bool:
        """
        Analyzes the backward window to find a breakout price and confirms if the alert candle breaks it.
        """
        alert_candle_time_for_log = df_indexed.index[alert_candle_index]

        # 1. Define the lookback period
        if lookback_period is None:
            lookback_df = df_indexed.iloc[:alert_candle_index]
        else:
            lookback_start_index = max(0, alert_candle_index - lookback_period)
            lookback_df = df_indexed.iloc[lookback_start_index:alert_candle_index]

        if lookback_df.empty:
            self.logger.debug(f"[{alert_candle_time_for_log}] No lookback history available.")
            return True # Bypass if no history

        # 2. Find the breakout price using the new utility function
        extreme_type = PeakTrough.PEAK if signal == Signal.BUY else PeakTrough.TROUGH
        extreme_point_info = find_extreme_point(lookback_df, PriceColumn.CLOSE, extreme_type, prominence)

        if extreme_point_info is None:
            self.logger.debug(f"[{alert_candle_time_for_log}] No peak/trough found; ignoring breakout confirmation.")
            return True

        breakout_price, _ = extreme_point_info
        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout price set to {breakout_price:.2f} for {signal} signal.")

        # 3. Confirm if the alert candle's price breaks the breakout price
        alert_candle = df_indexed.iloc[alert_candle_index]
        is_price_breakout = False
        if signal == Signal.BUY:
            is_price_breakout = alert_candle['close'] > breakout_price
        elif signal == Signal.SELL:
            is_price_breakout = alert_candle['close'] < breakout_price
        
        if not is_price_breakout:
            self.logger.debug(f"[{alert_candle_time_for_log}] Price breakout not confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
            return False

        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
        return True

    @abstractmethod
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        pass

    def is_in_cooldown(
        self,
        latest_alert_timestamp: Optional[pd.Timestamp],
        current_time: pd.Timestamp,
        cooldown_period: int
    ) -> bool:
        """
        Checks if the approach is in a cooldown period based on a timestamp.
        Returns True if in cooldown, False otherwise.
        """
        if latest_alert_timestamp is None:
            return False

        last_alert_time = latest_alert_timestamp.tz_convert(None)
        current_time_naive = current_time.tz_convert(None)
        time_since_last_alert = (current_time_naive - last_alert_time).total_seconds() / 60

        return time_since_last_alert < cooldown_period
    
    def next_step(self):
        """
        Increments the current step and resets validation_step to 1.
        Intended for use in derived classes to track validation/performance steps.
        """
        self.current_step += 1
        self.validation_step = 0

    def next_validation(self):
        """
        Increments the validation_step by 1. Use this to track sub-step validations within a main step.
        """
        self.validation_step += 1

    def get_loop_setup(
        self,
        is_development_mode: bool,
        df: pd.DataFrame,
        new_candle_count: int,
        lookback_window_size: int
    ) -> tuple[pd.DataFrame, int, int]:
        """
        Common utility for executors: prepares indexed DataFrame and loop boundaries.
        Returns (df_indexed, loop_start, loop_end).
        """
        df_indexed = df.reset_index()
        loop_end = len(df_indexed)
        min_scan_index = lookback_window_size
        if is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)
        return df_indexed, loop_start, loop_end
    
    def get_window_context(
        self,
        scan_index: int,
        df_indexed: pd.DataFrame,
        lookback_window_size: int
    ) -> Tuple[
        Optional[pd.DataFrame],
        Optional[pd.Series],
        Optional[pd.Series],
        Optional[pd.Timestamp],
        Optional[pd.Timestamp],
        int
    ]:
        """
        Utility to extract lookback window and boundary candles for a given scan index.
        Returns (lookback_window_df, first_candle, last_candle, current_window_start_time, current_window_end_time, current_step).
        """
        if df_indexed is None or df_indexed.empty:
            return None, None, None, None, None, 0
        lookback_window_df = df_indexed.iloc[scan_index - lookback_window_size : scan_index]
        if lookback_window_df.empty:
            return lookback_window_df, None, None, None, None, 0
        current_window_start_time = lookback_window_df.iloc[0]['time']
        current_window_end_time = lookback_window_df.iloc[-1]['time']
        current_step = 0
        first_candle = candle_utils.get_first_candle(lookback_window_df)
        last_candle = candle_utils.get_last_candle(lookback_window_df)
        return lookback_window_df, first_candle, last_candle, current_window_start_time, current_window_end_time, current_step
