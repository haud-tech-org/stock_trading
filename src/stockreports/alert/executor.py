from abc import ABC, abstractmethod
from typing import Optional, Tuple
import logging
import json
import pandas as pd

import numpy as np

from src.stockreports.utils.log_factory import log
from varname import nameof
from src.stockreports.utils.conversion_data_utils import make_json_safe

from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from src.stockreports.alert.common.constants import Signal, PeakTrough, PriceColumn, LogLevel, Trend
from src.stockreports.alert.common.data_utils import find_extreme_point
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.utils import candle_utils
from src.stockreports.alert.common.constants import ValidationStatus, Mode  # Add this import
from src.stockreports.utils.alert_utils import is_in_cooldown, calculate_suggested_prices, get_suggested_take_profit

class Executor(ABC):

    def __init__(self, symbol: str, approach: str, settings: Optional[BaseSettings] = None):
        self.symbol = symbol
        self.APPROACH_NAME = approach
        self.settings = settings

        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize context variables
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.first_candle: Optional[pd.Series] = None
        self.last_candle: Optional[pd.Series] = None
        self.lookback_window_df: Optional[pd.DataFrame] = None
        self.current_step: int = 0
        self.validation_step: int = 0
        self.validations: list = []
        self.alerts: list[AlertData] = []
        self.is_development_mode = self.settings.MODE == Mode.DEVELOPMENT

    def _add_details_for_alert(self, **kwargs) -> dict:
        """
        Common method to build alert details dictionary dynamically from keyword arguments.
        Subclasses can override for custom logic.
        """
        return kwargs
    
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
                alerts=alerts_df,
                confirmed_alerts=alerts_data
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame(), status="FAILED", message=str(e))

    def _step_cooldown_check(self, last_alert: AlertData, signal: Signal, cooldown_window) -> bool:
        self.next_validation()
        if is_in_cooldown(
            new_alert_time=self.current_window_end_time,
            new_signal=signal,
            latest_alert=last_alert,
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

    def update_alert_suggestions(self, alert: AlertData) -> None:
        """
        Updates the given alert in-place with structural_suggested_price, performance_suggested_price, and suggested_profit_threshold.
        """
        performance_suggested_price, structural_suggested_price = calculate_suggested_prices(
            alert.signal,
            alert.alert_time,
            alert.approach
        )
        suggested_profit_threshold = get_suggested_take_profit(alert.magnitude)
        alert.structural_suggested_price = structural_suggested_price
        alert.performance_suggested_price = performance_suggested_price
        alert.suggested_profit_threshold = suggested_profit_threshold

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
        if self.is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count)
        return df_indexed, loop_start, loop_end
    
    def set_window_context(
        self,
        scan_index: int,
        df_indexed: pd.DataFrame,
        lookback_window_size: int
    ) -> None:
        """
        Sets object-level variables for the lookback window and boundary candles for a given scan index.
        """
        if df_indexed is None or df_indexed.empty:
            return None
        self.lookback_window_df = df_indexed.iloc[scan_index - lookback_window_size : scan_index]
        self.current_window_start_time = self.lookback_window_df.iloc[0]['time']
        self.current_window_end_time = self.lookback_window_df.iloc[-1]['time']
        self.current_step = 0
        self.first_candle = candle_utils.get_first_candle(self.lookback_window_df)
        self.last_candle = candle_utils.get_last_candle(self.lookback_window_df)

        # Reset validations for each alert search iteration to avoid duplication
        self.validations = []

    def _create_alert_with_details(
        self,
        final_signal: Signal,
        final_trend: Trend,
        details: dict,
        final_alert_candle: Optional[pd.Series],
        final_magnitude: Optional[float] = None
    ) -> AlertData:
        """
        Common alert creation method: appends validations to details and creates AlertData.
        If any error occurs, logs the exception and re-raises it.
        """
        try:
            # Always append validations to details
            details = dict(details)  # Make a copy to avoid mutating caller's dict
            details["validations"] = [v.to_json() for v in self.validations]
            details = make_json_safe(details)

            alert_id = str(int(self.current_window_end_time.timestamp()))
            alert = AlertData(
                id=alert_id,
                symbol=self.symbol,
                approach=self.APPROACH_NAME,
                signal=final_signal,
                trend=final_trend,
                alert_price=final_alert_candle['close'] if final_alert_candle is not None else None,
                alert_time=self.current_window_end_time,
                start_price=self.first_candle['open'],
                start_time=self.current_window_start_time,
                magnitude=final_magnitude,
                details=json.dumps(details)
            )
            self.update_alert_suggestions(alert)
            return alert
        except Exception as e:
            self.logger.error(f"Error in _create_alert_with_details: {e}", exc_info=True)
            raise
