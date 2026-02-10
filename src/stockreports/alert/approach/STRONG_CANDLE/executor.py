# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json
from typing import Optional, Tuple

from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import StrongCandleSettings
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import candle_utils, window_utils


class StrongCandleExecutor(Executor):
    """
    Executor for the Strong Candle approach.
    Detects alerts by identifying a strong candle with significant body size,
    volume confirmation, and color consistency with the lookback window trend.
    """
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = StrongCandleSettings(symbol)
        approach_name = Approach.STRONG_CANDLE
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Main alert-finding function for Strong Candle approach.
        Orchestrates the reverse loop and step-by-step validation.
        """
        lookback_window_size = self.settings.lookback_window

        if len(df) < lookback_window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {lookback_window_size}, have {len(df)}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts

        # --- Standardized loop setup ---
        # Use base class utility to prepare indexed DataFrame and loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )

        for i in range(loop_end, loop_start - 1, -1):
            # --- Standardized window context extraction ---
            # Use base class utility to extract lookback window, boundary candles, and context variables
            self.set_window_context(i, df_indexed, lookback_window_size)
            if self.lookback_window_df is None or self.last_candle is None:
                continue

            # Step 1: Validate strong candle body size
            self.next_step()
            body_result = self._step_validate_alert_candle_body(self.last_candle)
            if body_result is None:
                continue
            body_size = body_result

            # Step 2: Validate alert candle volume
            self.next_step()
            if not self._step_validate_alert_candle_volume(self.lookback_window_df, self.last_candle):
                continue

            # Step 3: Validate window and candle color consistency
            self.next_step()
            signal, window_trend = self._step_validate_window_color_consistency(self.lookback_window_df, self.last_candle)
            if signal is None or window_trend is None:
                continue

            # Step 4: Validate opposite-color candles' bodies
            self.next_step()
            if not self._step_validate_opposite_color_candles_bodies(self.lookback_window_df, self.last_candle):
                continue

            # Step 5: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=StrongCandleExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 6: Alert creation
            self.next_step()
            details_dict = self._add_details_for_alert(
                body_size=body_size,
                window_trend=window_trend if window_trend else "UNKNOWN",
                strong_candle_time=self.last_candle['time'].isoformat()
            )

            alert_data = self._create_alert_with_details(
                final_signal=signal,
                final_trend=window_trend,
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.magnitude_threshold,
                details=details_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                StrongCandleExecutor.LATEST_ALERT = alert_data

                if not self.is_development_mode:
                    return self.alerts

        return self.alerts

    def _step_validate_alert_candle_body(self, alert_candle: pd.Series) -> Optional[float]:
        """
        Step 1: Validate that the alert candle has a strong body (both ratio and size).
        Returns the body size if validation passes, None otherwise.
        """
        self.next_validation()
        is_thick_body, body_ratio = candle_utils.is_body_ratio_bigger_than_min(alert_candle, self.settings.min_body_ratio)
        if not is_thick_body:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Body ratio {body_ratio:.2f} is below minimum {self.settings.min_body_ratio}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        self.validations.append(Validation(
            name=nameof(self.settings.min_body_ratio),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Body ratio {body_ratio:.2f} is >= {self.settings.min_body_ratio}.",
            status=ValidationStatus.PASSED
        ))

        # Validate body size
        self.next_validation()
        is_min_body_size, body_size = candle_utils.is_body_bigger_than_min(alert_candle, self.settings.min_body_size)
        if not is_min_body_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Body size {body_size:.2f} is below minimum {self.settings.min_body_size}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        self.validations.append(Validation(
            name=nameof(self.settings.min_body_size),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Body size {body_size:.2f} is >= {self.settings.min_body_size}.",
            status=ValidationStatus.PASSED
        ))

        return body_size

    def _step_validate_alert_candle_volume(self, lookback_window_df: pd.DataFrame, alert_candle: pd.Series) -> bool:
        """
        Step 2: Validate that alert candle volume <= max volume in conditional window * MAX_VOLUME_MULTIPLIER.
        The conditional window excludes the last (alert) candle from the lookback window.
        Returns True if valid, False otherwise.
        """
        self.next_validation()
        # Conditional window: exclude the last candle (the alert candle)
        conditional_window_df = lookback_window_df.iloc[:-1]
        max_conditional_volume = conditional_window_df['volume'].max()
        max_allowed_volume = max_conditional_volume * self.settings.max_volume_multiplier

        if alert_candle['volume'] > max_allowed_volume:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Alert candle volume {alert_candle['volume']:.0f} exceeds max conditional window volume {max_conditional_volume:.0f} * {self.settings.max_volume_multiplier}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.max_volume_multiplier),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Alert candle volume {alert_candle['volume']:.0f} <= max conditional window volume {max_conditional_volume:.0f} * {self.settings.max_volume_multiplier}.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_window_color_consistency(self, lookback_window_df: pd.DataFrame, alert_candle: pd.Series) -> Tuple[Optional[Signal], Optional[Trend]]:
        """
        Step 3: Validate that alert candle color is consistent with window trend and that window size is within threshold range.
        Uses close price extremes (min and max) in the full lookback window to determine the window trend and size.
        Validates that window size is between MIN_DIFFERENCE_PRICE_THRESHOLD and MAX_DIFFERENCE_PRICE_THRESHOLD.
        Returns (signal, trend) tuple if valid, (None, None) otherwise.
        """
        self.next_validation()
        # Use the full lookback window to determine trend and size
        window_size_val, window_trend = window_utils.get_window_size_and_trend_by_close_extremes(lookback_window_df)

        if window_trend is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Could not determine window trend by close extremes.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return (None, None)

        # Validate window size is within minimum threshold
        self.next_validation()
        if window_size_val < self.settings.min_window_size_threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window price range {window_size_val:.2f} is below minimum {self.settings.min_window_size_threshold}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return (None, None)

        self.validations.append(Validation(
            name=nameof(self.settings.min_window_size_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Window price range {window_size_val:.2f} >= {self.settings.min_window_size_threshold}.",
            status=ValidationStatus.PASSED
        ))

        # Validate window size is within maximum threshold
        self.next_validation()
        if window_size_val > self.settings.max_window_size_threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window price range {window_size_val:.2f} exceeds maximum {self.settings.max_window_size_threshold}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return (None, None)

        self.validations.append(Validation(
            name=nameof(self.settings.max_window_size_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Window price range {window_size_val:.2f} <= {self.settings.max_window_size_threshold}.",
            status=ValidationStatus.PASSED
        ))

        # Determine if candle color matches trend
        self.next_validation()
        is_consistent = False
        signal = None

        if window_trend == Trend.UPTREND:
            is_green = candle_utils.is_green_candle(alert_candle)
            if is_green:
                is_consistent = True
                signal = Signal.BUY
        elif window_trend == Trend.DOWNTREND:
            is_red = candle_utils.is_red_candle(alert_candle)
            if is_red:
                is_consistent = True
                signal = Signal.SELL

        if not is_consistent:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
            message=f"Alert candle color not consistent with {window_trend} trend.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return (None, None)

        self.validations.append(Validation(
            name="candle_trend_consistency",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Alert candle color is consistent with {window_trend} trend.",
            status=ValidationStatus.PASSED
        ))

        return (signal, window_trend)

    def _step_validate_window_price_range(self, lookback_window_df: pd.DataFrame) -> bool:
        """
        Step 4: Validate that the conditional window (excluding alert candle) price range
        is within the MAX_WINDOW_SIZE_THRESHOLD.
        Returns True if valid, False otherwise.
        """
        self.next_validation()
        conditional_window_df = lookback_window_df.iloc[:-1]
        window_size_val, window_trend = window_utils.get_window_size_and_trend(conditional_window_df)

        if window_size_val is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Could not calculate window price range.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False

        if window_size_val > self.settings.max_window_size_threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Window price range {window_size_val:.2f} exceeds threshold {self.settings.max_window_size_threshold}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.max_window_size_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Window price range {window_size_val:.2f} <= {self.settings.max_window_size_threshold}.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_opposite_color_candles_bodies(self, lookback_window_df: pd.DataFrame, alert_candle: pd.Series) -> bool:
        """
        Step 4: Validate that all candles in the conditional window (excluding alert candle) 
        that have opposite color against the alert candle have body sizes <= MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE.
        Candles with the same color as the alert candle are filtered out.
        Returns True if valid, False otherwise.
        """
        self.next_validation()
        conditional_window_df = lookback_window_df.iloc[:-1]

        # Determine alert candle color
        alert_is_green = candle_utils.is_green_candle(alert_candle)

        # Filter candles with opposite color against alert candle (exclude same color candles)
        opposite_color_candles = []
        for _, row in conditional_window_df.iterrows():
            is_green = candle_utils.is_green_candle(row)
            # Keep only candles with opposite color to alert candle
            if is_green != alert_is_green:
                opposite_color_candles.append(row)

        # Validate body sizes of opposite-color candles
        if len(opposite_color_candles) > 0:
            all_small_bodies = all(
                candle_utils.is_body_smaller_than_max(row, self.settings.max_opposite_color_candle_body_size)
                for row in opposite_color_candles
            )

            if not all_small_bodies:
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Not all opposite-color candles have body size <= {self.settings.max_opposite_color_candle_body_size}.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time,
                    approach=self.APPROACH_NAME
                )
                return False

        self.validations.append(Validation(
            name=nameof(self.settings.max_opposite_color_candle_body_size),
            step=self.current_step,
            validation=self.validation_step,
            message=f"All opposite-color candles have body size <= {self.settings.max_opposite_color_candle_body_size} ({len(opposite_color_candles)} candles checked).",
            status=ValidationStatus.PASSED
        ))
        return True
