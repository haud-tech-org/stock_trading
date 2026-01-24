
import pandas as pd
import logging
import json
from typing import Optional, List
from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from src.stockreports.alert.common.constants import Approach, Mode, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from src.stockreports.utils.log_factory import log
from .settings import VolumeSpikeConfirmationSettings
from src.stockreports.utils.candle_utils import is_green_candle, is_red_candle, get_last_candle
from src.stockreports.utils.candle_utils import get_signal_from_candle
from src.stockreports.utils.window_utils import get_window_size_and_trend
from src.stockreports.utils.candle_utils import find_max_volume_candle, find_min_volume_candle, validate_volume_ratio

class VolumeSpikeConfirmationExecutor(Executor):
    # APPROACH_NAME = Approach.VOLUME_SPIKE_CONFIRMATION

    def __init__(self, symbol: str):
        self.settings = VolumeSpikeConfirmationSettings(symbol)
        approach_name = Approach.VOLUME_SPIKE_CONFIRMATION
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int) -> List[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window

        # --- Standardized loop setup ---
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            is_development_mode,
            df,
            new_candle_count,
            window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            # --- Standardized window context extraction ---
            (
                window_df,
                first_candle,
                potential_alert_candle,
                self.current_window_start_time,
                self.current_window_end_time,
                self.current_step
            ) = self.get_window_context(i, df_indexed, window_size)
            if window_df is None or first_candle is None or potential_alert_candle is None:
                continue

            # Step 1: Trend window extraction
            self.next_step()
            trend_window = self._step1_extract_and_validate_trend_window(window_df)
            if trend_window is None:
                continue

            # Step 2: Volume validation in trend window
            self.next_step()
            volume_validation_result = self._step2_validate_volume_spike(trend_window)
            if volume_validation_result is None:
                continue
            max_vol_candle, min_vol_candle = volume_validation_result

            # Step 3: Cooldown check
            self.next_step()
            if self._is_in_cooldown(potential_alert_candle):
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

            # Step 4: Alert creation
            alert_data = self._create_alert_data(
                first_candle=first_candle,
                alert_candle=potential_alert_candle,
                trend_window=trend_window,
                max_vol_candle=max_vol_candle,
                min_vol_candle=min_vol_candle
            )
            alerts.append(alert_data)
            self.LATEST_ALERT = alert_data
            if not is_development_mode:
                return alerts
        return alerts[::-1]

    def _step1_extract_and_validate_trend_window(self, window_df: pd.DataFrame) -> Optional[pd.DataFrame]:
        self.next_validation()
        trend_window = self._extract_trend_window(window_df)

        if trend_window is None or len(trend_window) < self.settings.min_trend_candle_slices:
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
            return None

        window_size, _ = get_window_size_and_trend(trend_window)
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
            return None
        self.validations.append(Validation(
            name=nameof(self.settings.min_trend_window_size),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Trend window size OK: {len(trend_window)}",
            status=ValidationStatus.PASSED
        ))
        return trend_window

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
        self.next_validation()
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

    def _is_in_cooldown(self, alert_candle) -> bool:
        signal = get_signal_from_candle(alert_candle)
        return not self._step_cooldown_check(
            signal=signal,
            cooldown_window=self.settings.cooldown_period
        )

    def _create_alert_data(self, first_candle, alert_candle, trend_window, max_vol_candle, min_vol_candle) -> AlertData:
        alert_id = str(int(self.current_window_end_time.timestamp()))
        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            approach=self.APPROACH_NAME,
            signal=Signal.BUY if alert_candle['close'] > alert_candle['open'] else Signal.SELL,
            alert_price=alert_candle['close'],
            alert_time=self.current_window_end_time,
            start_price=first_candle['open'],
            start_time=self.current_window_start_time,
            magnitude=abs(alert_candle['close'] - first_candle['open']),
            details=json.dumps({
                "trend_window_size": len(trend_window),
                "max_volume": max_vol_candle['volume'],
                "min_volume": min_vol_candle['volume'],
                "validations": [v.to_json() for v in self.validations]
            })
        )

