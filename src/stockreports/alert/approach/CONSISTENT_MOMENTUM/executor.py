# src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py
import pandas as pd
import logging
import json
from typing import Optional, Tuple

from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import ConsistentMomentumSettings
from src.stockreports.utils.log_factory import log
from src.stockreports.utils import candle_utils, window_utils


class ConsistentMomentumExecutor(Executor):
    """
    Executor for the Consistent Momentum approach.
    Detects alerts by identifying consistent color candles with an anchor point,
    where the last candle's color determines the signal and the anchor is the
    candle with the minimum open (for BUY) or maximum open (for SELL).
    """
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ConsistentMomentumSettings(symbol)
        approach_name = Approach.CONSISTENT_MOMENTUM
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Main alert-finding function for Consistent Momentum approach.
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

            # Step 1: Determine signal from last candle color
            self.next_step()
            signal = self._step_determine_signal_from_color(self.last_candle)
            if signal is None:
                continue

            # Step 2: Find anchor candle based on signal
            self.next_step()
            anchor_idx = self._step_find_anchor_candle(self.lookback_window_df, signal)
            if anchor_idx is None:
                continue

            # Step 3: Extract confirmation window (from anchor to last candle)
            self.next_step()
            confirmation_window_df = self._step_extract_confirmation_window(self.lookback_window_df, anchor_idx)
            if confirmation_window_df is None or len(confirmation_window_df) == 0:
                continue

            # Step 4: Validate volume consistency
            self.next_step()
            if not self._step_validate_volume_consistency(confirmation_window_df):
                continue

            # Step 5: Validate confirmation window price range
            self.next_step()
            if not self._step_validate_confirmation_window_price_range(confirmation_window_df):
                continue

            # Step 6: Validate all candles have same color
            self.next_step()
            if not self._step_validate_color_consistency(confirmation_window_df, signal):
                continue

            # Step 7: Validate open price direction
            self.next_step()
            if not self._step_validate_open_price_direction(confirmation_window_df, signal):
                continue

            # Step 8: Validate minimum consistent candles
            self.next_step()
            if not self._step_validate_min_consistent_candles(confirmation_window_df):
                continue

            # Step 9: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=ConsistentMomentumExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 10: Alert creation
            self.next_step()
            details_dict = self._add_details_for_alert(
                anchor_candle_index=anchor_idx,
                consistency_candle_count=len(confirmation_window_df),
                signal=signal
            )

            alert_data = self._create_alert_with_details(
                final_signal=signal,
                final_trend=Trend.UPTREND if signal == Signal.BUY else Trend.DOWNTREND,
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.magnitude_threshold,
                details=details_dict
            )

            if alert_data is not None:
                self.alerts.append(alert_data)
                ConsistentMomentumExecutor.LATEST_ALERT = alert_data

                if not self.is_development_mode:
                    return self.alerts

        return self.alerts

    def _step_determine_signal_from_color(self, last_candle: pd.Series) -> Optional[Signal]:
        """
        Step 1: Determine the signal from the last candle's color.
        Green candle => BUY signal
        Red candle => SELL signal
        Returns Signal or None if neither.
        """
        if candle_utils.is_green_candle(last_candle):
            return Signal.BUY
        elif candle_utils.is_red_candle(last_candle):
            return Signal.SELL
        
        log(
            logger=self.logger,
            status=ValidationStatus.FAILED,
            name=self.__class__.__name__,
            alert_time=self.current_window_end_time,
            step=self.current_step,
            message=f"Last candle is neither clearly green nor red.",
            log_level=LogLevel.DEBUG,
            execution_symbol=self.symbol,
            start_time=self.current_window_start_time,
            end_time=self.current_window_end_time,
            approach=self.APPROACH_NAME
        )
        return None

    def _step_find_anchor_candle(self, lookback_window_df: pd.DataFrame, signal: Signal) -> Optional[int]:
        """
        Step 2: Find the anchor candle.
        The anchor candle must:
        1. Have the color compatible with the signal (green for BUY, red for SELL)
        2. Be at or after the candle with min open (BUY) or max open (SELL)
        
        Search forward from the extreme position to find the first matching color candle.
        Returns the index within the window, or None if not found.
        """
        if len(lookback_window_df) == 0:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message="Lookback window is empty.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        # Find the index of min open (BUY) or max open (SELL)
        if signal == Signal.BUY:
            extreme_idx = lookback_window_df['open'].idxmin()
        else:  # SELL
            extreme_idx = lookback_window_df['open'].idxmax()

        # Convert to positional index within the window
        extreme_position = lookback_window_df.index.get_loc(extreme_idx)
        
        # Find the anchor candle: iterate forward from extreme position
        # looking for the first candle with the correct color (green for BUY, red for SELL)
        for pos in range(extreme_position, len(lookback_window_df)):
            candle = lookback_window_df.iloc[pos]
            
            if signal == Signal.BUY:
                if candle_utils.is_green_candle(candle):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.PASSED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        message=f"Anchor candle found at position {pos} (green, at or after min open position {extreme_position}).",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return pos
            else:  # SELL
                if candle_utils.is_red_candle(candle):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.PASSED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        message=f"Anchor candle found at position {pos} (red, at or after max open position {extreme_position}).",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return pos
        
        # No compatible color candle found from extreme position onwards
        log(
            logger=self.logger,
            status=ValidationStatus.FAILED,
            name=self.__class__.__name__,
            alert_time=self.current_window_end_time,
            step=self.current_step,
            message=f"No anchor candle with compatible color found. Signal: {signal}, extreme position: {extreme_position}.",
            log_level=LogLevel.DEBUG,
            execution_symbol=self.symbol,
            start_time=self.current_window_start_time,
            end_time=self.current_window_end_time,
            approach=self.APPROACH_NAME
        )
        return None

    def _step_extract_confirmation_window(self, lookback_window_df: pd.DataFrame, anchor_idx: int) -> Optional[pd.DataFrame]:
        """
        Step 3: Extract the confirmation window from anchor candle to the last candle.
        """
        if anchor_idx < 0 or anchor_idx >= len(lookback_window_df):
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                message=f"Invalid anchor index {anchor_idx} for window of size {len(lookback_window_df)}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return None

        # Extract from anchor to end (inclusive)
        confirmation_window = lookback_window_df.iloc[anchor_idx:]
        return confirmation_window

    def _step_validate_volume_consistency(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 4: Validate that volume in the confirmation window is consistent.
        
        The volume ratio must satisfy: max_volume <= min_volume * MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD
        This ensures that volume doesn't spike excessively compared to the minimum, 
        indicating a sustained momentum rather than a brief spike.
        """
        self.next_validation()
        
        if len(confirmation_window_df) == 0:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Confirmation window is empty.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        max_volume = confirmation_window_df['volume'].max()
        min_volume = confirmation_window_df['volume'].min()
        threshold = self.settings.max_multiplier_difference_volume_threshold
        
        # Validate: max_volume <= min_volume * threshold
        if max_volume > min_volume * threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Volume consistency failed: max_volume ({max_volume}) > min_volume ({min_volume}) * threshold ({threshold}). Ratio: {max_volume / min_volume if min_volume > 0 else 0:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        self.validations.append(Validation(
            name=nameof(self.settings.max_multiplier_difference_volume_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Volume consistency passed: max_volume ({max_volume}) <= min_volume ({min_volume}) * threshold ({threshold}). Ratio: {max_volume / min_volume if min_volume > 0 else 0:.2f}",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_confirmation_window_price_range(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 5: Validate that the confirmation window price range is within min and max thresholds.
        
        The price range is calculated as the difference between the highest and lowest close prices
        in the confirmation window. This ensures the confirmation window is neither too narrow 
        (insufficient price movement) nor too wide (excessive volatility).
        """
        self.next_validation()
        
        if len(confirmation_window_df) == 0:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Confirmation window is empty.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        # Calculate price range using close extremes
        window_size_val, window_trend = window_utils.get_window_size_and_trend_by_close_extremes(confirmation_window_df)
        
        if window_size_val is None:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Could not calculate confirmation window price range.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        # Validate minimum threshold
        self.next_validation()
        if window_size_val < self.settings.min_confirmation_window_price_threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Confirmation window price range {window_size_val:.2f} is below minimum {self.settings.min_confirmation_window_price_threshold}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        self.validations.append(Validation(
            name=nameof(self.settings.min_confirmation_window_price_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Confirmation window price range {window_size_val:.2f} >= {self.settings.min_confirmation_window_price_threshold}.",
            status=ValidationStatus.PASSED
        ))
        
        # Validate maximum threshold
        self.next_validation()
        if window_size_val > self.settings.max_confirmation_window_price_threshold:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Confirmation window price range {window_size_val:.2f} exceeds maximum {self.settings.max_confirmation_window_price_threshold}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        self.validations.append(Validation(
            name=nameof(self.settings.max_confirmation_window_price_threshold),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Confirmation window price range {window_size_val:.2f} <= {self.settings.max_confirmation_window_price_threshold}.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_color_consistency(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 6: Validate that all candles in the confirmation window have the same color
        matching the signal.
        """
        self.next_validation()
        
        for _, candle in confirmation_window_df.iterrows():
            if signal == Signal.BUY:
                if not candle_utils.is_green_candle(candle):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"Candle at {candle['time']} is not green in BUY confirmation window.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return False
            else:  # SELL
                if not candle_utils.is_red_candle(candle):
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"Candle at {candle['time']} is not red in SELL confirmation window.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return False

        self.validations.append(Validation(
            name="color_consistency",
            step=self.current_step,
            validation=self.validation_step,
            message=f"All candles in confirmation window are consistent with {signal} signal.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_open_price_direction(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 7: Validate that open prices follow the signal direction.
        
        For BUY signal: open prices must always increase (each candle's open >= previous candle's open)
        For SELL signal: open prices must always decrease (each candle's open <= previous candle's open)
        
        This ensures the price movement is consistent with the signal direction throughout the window.
        """
        self.next_validation()
        
        if len(confirmation_window_df) < 2:
            # Only one candle, no direction to validate
            self.validations.append(Validation(
                name="open_price_direction",
                step=self.current_step,
                validation=self.validation_step,
                message=f"Only one candle in confirmation window, direction validation skipped.",
                status=ValidationStatus.PASSED
            ))
            return True
        
        opens = confirmation_window_df['open'].values
        
        if signal == Signal.BUY:
            # For BUY: check that opens are strictly increasing (open[i] > open[i-1])
            for i in range(1, len(opens)):
                if opens[i] <= opens[i-1]:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"BUY open price direction failed: open[{i}]={opens[i]:.2f} <= open[{i-1}]={opens[i-1]:.2f}",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return False
        else:  # SELL
            # For SELL: check that opens are strictly decreasing (open[i] < open[i-1])
            for i in range(1, len(opens)):
                if opens[i] >= opens[i-1]:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"SELL open price direction failed: open[{i}]={opens[i]:.2f} >= open[{i-1}]={opens[i-1]:.2f}",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                    return False
        
        self.validations.append(Validation(
            name="open_price_direction",
            step=self.current_step,
            validation=self.validation_step,
            message=f"Open price direction validated: {'increasing' if signal == Signal.BUY else 'decreasing'} for {signal} signal. Opens: {[f'{o:.2f}' for o in opens]}",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_min_consistent_candles(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 8: Validate that the confirmation window has at least MIN_CONSISTENT_CANDLES.
        """
        self.next_validation()
        consistent_count = len(confirmation_window_df)

        if consistent_count < self.settings.min_consistent_candles:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Consistent candles {consistent_count} is below minimum {self.settings.min_consistent_candles}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False

        self.validations.append(Validation(
            name=nameof(self.settings.min_consistent_candles),
            step=self.current_step,
            validation=self.validation_step,
            message=f"Consistent candles {consistent_count} >= {self.settings.min_consistent_candles}.",
            status=ValidationStatus.PASSED
        ))
        return True
