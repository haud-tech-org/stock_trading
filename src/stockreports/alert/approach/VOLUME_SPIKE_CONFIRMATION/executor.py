
import pandas as pd
import logging
import json
import src.stockreports.utils.alert_utils as alert_utils

from typing import Optional, List
from typing import Tuple
from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.utils.log_factory import log
from .settings import VolumeSpikeConfirmationSettings
from src.stockreports.utils.candle_utils import is_green_candle, is_red_candle, get_last_candle
from src.stockreports.utils.candle_utils import get_reversal_trend_signal
from src.stockreports.utils.window_utils import get_window_size_and_trend
from src.stockreports.utils.candle_utils import find_max_volume_candle, find_min_volume_candle, validate_volume_ratio

class VolumeSpikeConfirmationExecutor(Executor):
    # APPROACH_NAME = Approach.VOLUME_SPIKE_CONFIRMATION
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VolumeSpikeConfirmationSettings(symbol)
        approach_name = Approach.VOLUME_SPIKE_CONFIRMATION
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int) -> List[AlertData]:
        window_size = self.settings.lookback_window

        # --- Standardized loop setup ---
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            # --- Standardized window context extraction ---
            self.set_window_context(i, df_indexed, window_size)
            if self.lookback_window_df is None or self.first_candle is None or self.last_candle is None:
                continue

            # Step 1: Trend window extraction
            self.next_step()
            trend_window, window_size_val = self._step1_extract_and_validate_trend_window(self.lookback_window_df)
            if trend_window is None:
                continue

            # Step 2: Volume validation in trend window
            self.next_step()
            volume_validation_result = self._step2_validate_volume_spike(trend_window)
            if volume_validation_result is None:
                continue
            max_vol_candle, min_vol_candle = volume_validation_result


            # Step 3: Reversal process
            reversal_trend, reversal_signal = self._step3_reversal_process(self.last_candle)

            # Step 4: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=VolumeSpikeConfirmationExecutor.LATEST_ALERT,
                signal=reversal_signal,
                cooldown_window=self.settings.cooldown_period
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
                continue
            self.validations.append(Validation(
                name=nameof(self.settings.cooldown_period),
                step=self.current_step,
                validation=self.validation_step,
                message="Alert is not in cooldown period.",
                status=ValidationStatus.PASSED
            ))

            # Step 5: Alert creation
            details_for_alert_dict = self._add_details_for_alert(
                trend_window=trend_window,
                max_vol_candle=max_vol_candle,
                min_vol_candle=min_vol_candle
            )

            alert_data = self._create_alert_with_details(
                final_signal=reversal_signal,
                final_trend=reversal_trend,
                final_alert_candle=self.last_candle,
                final_magnitude=window_size_val,
                details=details_for_alert_dict
            )

            self.alerts.append(alert_data)
            VolumeSpikeConfirmationExecutor.LATEST_ALERT = alert_data
            if not self.is_development_mode:
                return self.alerts
            
        return self.alerts[::-1]

    def _step1_extract_and_validate_trend_window(self, window_df: pd.DataFrame) -> Tuple[Optional[pd.DataFrame], Optional[float]]:
        trend_window = self._extract_trend_window(window_df)

        self.next_validation()
        if trend_window is None or len(trend_window) < self.settings.min_trend_candle_slice:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend window too short: {len(trend_window) if trend_window is not None else 0}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None

        window_size, _ = get_window_size_and_trend(trend_window)

        self.next_validation()
        if window_size < self.settings.min_trend_window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Trend window size {window_size} < min required {self.settings.min_trend_window_size}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None, None
        self.validations.append(Validation(
            name=nameof(self.settings.min_trend_window_size),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Trend window size OK: {len(trend_window)}",
            status=ValidationStatus.PASSED
        ))
        return trend_window, window_size

    def _extract_trend_window(self, window_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Extracts the trend confirmation window: consecutive same-color candles from the end.
        Returns the trend window DataFrame or None if not enough candles.
        """
        if window_df.empty:
            return None
        
        last_candle = get_last_candle(window_df)

        # Determine the trend color of the last candle
        if is_green_candle(last_candle):
            is_trend_candle = is_green_candle
        elif is_red_candle(last_candle):
            is_trend_candle = is_red_candle
        else:
            # If the last candle is neutral (doji), no trend window
            return None

        # Collect indices of consecutive candles matching the trend color, starting from the end
        trend_indices = [window_df.index[-1]]
        for idx in range(len(window_df) - 2, -1, -1):
            candle = window_df.iloc[idx]
            if is_trend_candle(candle):
                trend_indices.append(window_df.index[idx])
            else:
                break

        # Return the DataFrame of the trend window, sorted in ascending order
        trend_indices = sorted(trend_indices)
        return window_df.loc[trend_indices]
    
    def _step2_validate_volume_spike(self, trend_window: pd.DataFrame) -> Optional[tuple[pd.Series, pd.Series]]:
        max_vol_candle = find_max_volume_candle(trend_window)
        min_vol_candle = find_min_volume_candle(trend_window)

        # New validation: min volume candle must be before max volume candle
        min_idx = trend_window.index.get_loc(min_vol_candle.name)
        max_idx = trend_window.index.get_loc(max_vol_candle.name)
        if min_idx >= max_idx:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Min volume candle (idx={min_idx}) does not occur before max volume candle (idx={max_idx}) in trend window.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        
        self.next_validation()
        status, ratio = validate_volume_ratio(max_vol_candle, min_vol_candle, self.settings.trend_volume_multiplier)
        if not status:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Max volume {max_vol_candle['volume']} < min volume {min_vol_candle['volume']} * multiplier {self.settings.trend_volume_multiplier} (ratio: {ratio})",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
        self.validations.append(Validation(
            name=nameof(self.settings.trend_volume_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Volume spike confirmed: {max_vol_candle['volume']} >= {min_vol_candle['volume']} * {self.settings.trend_volume_multiplier} (ratio: {ratio})",
            status=ValidationStatus.PASSED
        ))
        
        return max_vol_candle, min_vol_candle

    def _step3_reversal_process(self, potential_alert_candle):
        """
        Handles the reversal process: uses get_reversal_trend_signal from candle_utils to get reversal_trend and reversal_signal.
        Returns (reversal_trend, reversal_signal) if not None.
        """
        reversal_trend, reversal_signal = get_reversal_trend_signal(potential_alert_candle)
        return reversal_trend, reversal_signal

        

