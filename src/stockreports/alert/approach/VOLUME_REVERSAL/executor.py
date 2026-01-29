import pandas as pd
import logging
import json
from typing import Optional
from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import VolumeReversalSettings
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import window_utils, candle_utils

class VolumeReversalExecutor(Executor):
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VolumeReversalSettings(symbol)
        approach_name = Approach.VOLUME_REVERSAL
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        window_size = self.settings.lookback_window
        if len(df) < window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts

        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, window_size)
            if self.lookback_window_df is None:
                continue

            # Step 1: Trend validation (to get trend window)
            self.next_step()
            trend_result = self._step_trend_validation(self.lookback_window_df)
            if trend_result is None:
                continue
            trend_1, trend_window_df = trend_result

            # Step 2: Volume validation (use trend window)
            self.next_step()
            vol_result = self._step_volume_validation(self.lookback_window_df, trend_window_df)
            if vol_result is None:
                continue
            max_vol_candle, min_vol_candle = vol_result

            # Step 3: Max vol candle close price validation (new step)
            self.next_step()
            if not self._step_max_vol_candle_close_validation(trend_1, max_vol_candle, self.lookback_window_df):
                continue

            # Step 4: Window size validation
            self.next_step()
            window_size_result = self._step_window_size_validation(self.lookback_window_df)
            if window_size_result is None:
                continue
            window_size_val, original_trend = window_size_result

            # Step 5: Cooldown check
            self.next_step()
            reversal_trend = candle_utils.get_reversal_trend(original_trend)
            if not self._step_cooldown_check(
                last_alert=VolumeReversalExecutor.LATEST_ALERT,
                signal=reversal_trend,
                cooldown_window=self.settings.lookback_window
            ):
                continue

            # Step 6: Add details for alert
            details_alert_dict = self._add_details_for_alert(
                max_vol_candle=max_vol_candle,
                min_vol_candle=min_vol_candle,
                original_trend=original_trend,
                trend_window_indices=trend_window_df,
                window_size_val=window_size_val,
                window_trend=original_trend
            )

            # Step 7: Alert creation
            self.next_step()
            reversal_signal = candle_utils.get_signal_from_trend(reversal_trend)
            alert_data = self._create_alert_with_details(
                final_signal=reversal_signal,
                final_trend=reversal_trend,
                final_alert_candle=self.lookback_window_df.iloc[-1],
                final_magnitude=window_size_val,
                details=details_alert_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                VolumeReversalExecutor.LATEST_ALERT = alert_data
            else:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    step=self.current_step,
                    message="Alert creation returned None. Alert not appended.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )

            if not self.is_development_mode and len(self.alerts) >= 1:
                return self.alerts

        return self.alerts[::-1]


    def _step_volume_validation(self, window: pd.DataFrame, trend_window_df: pd.DataFrame) -> Optional[tuple]:
        self.next_validation()
        candle_minus_1 = window.iloc[-2]
        max_vol_candle = window.loc[window['volume'].idxmax()]
        if candle_minus_1.name != max_vol_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="candle_minus_1 does not have max volume in window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        # Use min volume in trend_window_df for comparison
        min_vol_candle = trend_window_df.loc[trend_window_df['volume'].idxmin()]
        v_min = min_vol_candle['volume']
        v_max = max_vol_candle['volume']
        if not (self.settings.max_volume_multiplier * v_min > v_max > self.settings.min_volume_multiplier * v_min):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Volume multiplier check failed: vmax={v_max}, v_min={v_min}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        self.validations.append(Validation(
            name=nameof(self.settings.max_volume_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message="candle_minus_1 has max volume and passes multiplier check.",
            status=ValidationStatus.PASSED
        ))
        return max_vol_candle, min_vol_candle

    def _step_trend_validation(self, window: pd.DataFrame) -> tuple[str, pd.DataFrame]:
        self.next_validation()
        candle_last = window.iloc[-1]
        candle_minus_1 = window.iloc[-2]
        trend_1 = candle_utils.get_trend_from_candle(candle_minus_1)

        # Validation 1: last candle has opposite trend to trend_1
        trend_last = candle_utils.get_trend_from_candle(candle_last)
        if trend_last == trend_1:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Last candle does not have opposite trend to candle_minus_1.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        self.validations.append(Validation(
            name="trend_window_consistent_and_last_opposite",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Trend window (ending at last-1) is consistent, last candle is opposite.",
            status=ValidationStatus.PASSED
        ))
        
        # Build trend window ending at candle_minus_1, going backward until opposite trend is found
        trend_window_indices = [window.index[-2]]
        for idx in range(len(window) - 3, -1, -1):
            c = window.iloc[idx]
            t = candle_utils.get_trend_from_candle(c)
            if t != trend_1:
                break
            trend_window_indices.append(window.index[idx])
        trend_window_indices = trend_window_indices[::-1]  # chronological order
        trend_window_df = window.loc[trend_window_indices]

        self.next_validation()
        # Validation 2: trend_window_df must have at least 2 candles
        if len(trend_window_df) < 2:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Trend window has fewer than 2 candles.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        self.validations.append(Validation(
            name="trend_window_consistent_and_last_opposite",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Trend window (ending at last-1) is consistent, last candle is opposite.",
            status=ValidationStatus.PASSED
        ))

        # Return trend_1 and trend_window_df for downstream use
        return trend_1, trend_window_df

    
    def _step_window_size_validation(self, window: pd.DataFrame):
        self.next_validation()
        window_size_val, trend = window_utils.get_window_size_and_trend_by_close_extremes(window)
        if not (self.settings.max_window_size_threshold > window_size_val > self.settings.min_window_size_threshold):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window size threshold failed: {window_size_val}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None
        self.validations.append(Validation(
            name=nameof(self.settings.max_window_size_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message="Window size threshold passed.",
            status=ValidationStatus.PASSED
        ))
        return window_size_val, trend
    
    def _step_max_vol_candle_close_validation(self, trend: Trend, max_vol_candle: pd.Series, trend_window_df: pd.DataFrame) -> bool:
        """
        Validates that:
    - If trend_1 is UPTREND, max_vol_candle has the highest close price in trend_window_df.
    - If trend_1 is DOWNTREND, max_vol_candle has the lowest close price in trend_window_df.
        Returns True if valid, False otherwise (and logs failure).
        """
        self.next_validation()
        if trend == Trend.UPTREND:
            max_close_idx = trend_window_df['close'].idxmax()
            if max_vol_candle.name != max_close_idx:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="For UPTREND, max_vol_candle does not have the highest close price.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
                return False
        elif trend == Trend.DOWNTREND:
            min_close_idx = trend_window_df['close'].idxmin()
            if max_vol_candle.name != min_close_idx:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message="For DOWNTREND, max_vol_candle does not have the lowest close price.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
                return False
        # Passed validation
        self.validations.append(Validation(
            name="max_vol_candle_close_validation",
            step=self.current_step,
            validation=self.validation_step,
            message="max_vol_candle close price validation passed.",
            status=ValidationStatus.PASSED
        ))
        return True
