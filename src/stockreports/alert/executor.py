from abc import ABC, abstractmethod
from typing import Optional, Tuple
import logging
import json
import pandas as pd
import numpy as np
import gc
from src.stockreports.utils.log_factory import log
from varname import nameof
from src.stockreports.utils.conversion_data_utils import make_json_safe
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from src.stockreports.alert.common.constants import Signal, PeakTrough, PriceColumn, LogLevel, Trend, Status
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.utils import candle_utils
from src.stockreports.alert.common.constants import ValidationStatus, Mode  # Add this import
from src.stockreports.utils.alert_utils import is_in_cooldown, calculate_suggested_prices, get_suggested_take_profit
from src.stockreports.alert.analyzer import Analyzer

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
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
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
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )

            # Explicitly trigger garbage collection to free up system resources before returning
            gc.collect()
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=alerts_data,
                status=Status.SUCCESS
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            
            # Explicitly trigger garbage collection to free up system resources before returning in case of exception
            gc.collect()
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                confirmed_alerts=[],
                status=Status.FAILED,
                message=str(e)
            )

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
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
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
            alert.approach,
            symbol=alert.symbol
        )
        suggested_profit_threshold = get_suggested_take_profit(alert.magnitude)
        alert.structural_suggested_price = structural_suggested_price
        alert.performance_suggested_price = performance_suggested_price
        alert.suggested_profit_threshold = suggested_profit_threshold

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
        Common utility for executors: prepares DataFrame and loop boundaries.
        
        The DataFrame maintains 'time' as its index throughout the pipeline.
        This ensures type consistency: time remains as pd.DatetimeIndex with pd.Timestamp elements.
        
        Returns (df, loop_start, loop_end) where df still has 'time' as index.
        """
        loop_end = len(df)
        min_scan_index = lookback_window_size
        if self.is_development_mode:
            loop_start = min_scan_index
        else:
            loop_start = max(min_scan_index, len(df) - new_candle_count)
        return df, loop_start, loop_end
    
    def set_window_context(
        self,
        scan_index: int,
        df_indexed: pd.DataFrame,
        lookback_window_size: int
    ) -> None:
        """
        Sets object-level variables for the lookback window and boundary candles for a given scan index.
        
        The index is pd.DatetimeIndex with pd.Timestamp elements (validated by Coordinator).
        """
        if df_indexed is None or df_indexed.empty:
            return None
        self.lookback_window_df = df_indexed.iloc[scan_index - lookback_window_size : scan_index]
        
        # Extract time values directly from the index (which is pd.DatetimeIndex with Timestamp elements)
        self.current_window_start_time = self.lookback_window_df.index[0]
        self.current_window_end_time = self.lookback_window_df.index[-1]
        
        self.current_step = 0
        self.first_candle = candle_utils.get_first_candle(self.lookback_window_df)
        self.last_candle = candle_utils.get_last_candle(self.lookback_window_df)

        # Reset validations for each alert search iteration to avoid duplication
        self.validations = []

    def update_window_end_time_with_shift(
        self,
        scan_index: int,
        df_indexed: pd.DataFrame,
        shift_offset: int
    ) -> Tuple[bool, Optional[pd.Series]]:
        """
        Orchestration method that updates current_window_end_time to a forward-shifted candle's timestamp.
        
        Delegates the pure calculation logic to Analyzer.get_shifted_candle() and then
        updates the state (current_window_end_time) if successful.
        
        Used by approaches with forward-shifted indicators (e.g., Ichimoku's Senkou Cloud).
        This method allows approaches to align alert timing with shifted technical indicators.
        
        Args:
            scan_index (int): Current scanning index in the dataframe
            df_indexed (pd.DataFrame): Indexed dataframe with all candles
            shift_offset (int): Number of periods to shift forward (e.g., senkou_shift_period)
            
        Returns:
            Tuple[bool, Optional[pd.Series]]: 
                - (True, shifted_candle): If shift was successful or fallback to last candle
                - (False, None): If exception or empty dataframe
            
        Processing Results:
            - success=True, shifted_candle exists: Use shifted_candle for further processing
              (e.g., alert creation, validation, etc.)
            - success=False, shifted_candle is None: Skip processing, failed to retrieve shifted candle
            
        Example:
            ```python
            success, shifted_candle = self.update_window_end_time_with_shift(i, df_indexed, shift_offset)
            if success and shifted_candle is not None:
                # Parse return values and process further steps
                self.current_window_end_time = shifted_candle.name
                alert = self._step_create_alert(shifted_candle, signal)
                # ... continue with validation and other processing
            else:
                # Failed due to exception or empty dataframe - skip this iteration
                continue
            ```
        """
        # Delegate pure calculation to Analyzer
        success, shifted_candle = Analyzer.get_shifted_candle(
            scan_index=scan_index,
            df_indexed=df_indexed,
            shift_offset=shift_offset
        )
        
        # Parse return values and update state if calculation was successful
        if success and shifted_candle is not None:
            # Update orchestration state with shifted candle's timestamp
            self.current_window_end_time = shifted_candle.name
            return True, shifted_candle
        else:
            # Failed to retrieve shifted candle - caller should skip processing
            return False, None


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
        Assumes upstream data (alert_time, start_time) are already validated as pd.Timestamp objects
        by the Coordinator via _ensure_type_compatibility().
        """
        try:
            # Always append validations to details
            details = dict(details)  # Make a copy to avoid mutating caller's dict
            details["validations"] = [v.to_json() for v in self.validations]
            details = make_json_safe(details)

            # Assume coordinator has validated these are pd.Timestamp objects
            alert_time_ts = self.current_window_end_time
            start_time_ts = self.current_window_start_time
            
            # Generate alert_id from alert_time timestamp
            alert_id = str(int(alert_time_ts.timestamp()))
            
            alert = AlertData(
                id=alert_id,
                symbol=self.symbol,
                approach=self.APPROACH_NAME,
                signal=final_signal,
                trend=final_trend,
                alert_price=final_alert_candle['close'] if final_alert_candle is not None else None,
                alert_time=alert_time_ts,
                start_price=self.first_candle['open'],
                start_time=start_time_ts,
                magnitude=final_magnitude,
                details=json.dumps(details)
            )
            self.update_alert_suggestions(alert)

            log(
                logger=self.logger,
                status=ValidationStatus.PASSED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Alert created and appended (alert is not None)",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return alert
        except Exception as e:
            self.logger.error(f"Error in _create_alert_with_details: {e}", exc_info=True)
            raise
