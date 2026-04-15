# src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py
import pandas as pd
import logging
import json
from typing import Optional, Tuple

from varname import nameof

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel, Trend, CandleColumn
from src.stockreports.alert.model.models import AlertResult, AlertData, Validation
from .settings import ConsistentMomentumSettings
from .analyzer import ConsistentMomentumAnalyzer
from .validator import ConsistentMomentumValidator
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

    def __init__(self, symbol: str, approach: Approach, resolution: int):
        self.settings = ConsistentMomentumSettings(symbol)
        self.analyzer = ConsistentMomentumAnalyzer()
        self.validator = ConsistentMomentumValidator()
        super().__init__(symbol, approach, resolution, self.settings)
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

            # Step 4: Validate that first and last candles have max body momentum
            self.next_step()
            if not self._step_validate_max_body_at_boundaries(confirmation_window_df, signal):
                continue

            # Step 5: Validate volume consistency
            self.next_step()
            if not self._step_validate_volume_consistency(confirmation_window_df):
                continue

            # Step 6: Validate confirmation window price range
            self.next_step()
            if not self._step_validate_confirmation_window_price_range(confirmation_window_df):
                continue

            # Step 7: Validate confirmation window gap between candles
            self.next_step()
            if not self._step_validate_confirmation_window_gap(confirmation_window_df):
                continue

            # Step 8: Validate all candles have same color
            self.next_step()
            if not self._step_validate_color_consistency(confirmation_window_df, signal):
                continue

            # Step 9: Validate open and close price direction
            self.next_step()
            if not self._step_validate_open_close_price_direction(confirmation_window_df, signal):
                continue

            # Step 10: Validate minimum consistent candles
            self.next_step()
            if not self._step_validate_min_consistent_candles(confirmation_window_df):
                continue

            # Step 11: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=ConsistentMomentumExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 12: Alert creation
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
            extreme_idx = lookback_window_df[CandleColumn.OPEN].idxmin()
        else:  # SELL
            extreme_idx = lookback_window_df[CandleColumn.OPEN].idxmax()

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

    def _step_validate_max_body_at_boundaries(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 4: Validate momentum strength at window boundaries with two conditions (OR logic):
        
        Condition 1: The first and last candles are the 1st and 2nd maximum body candles in the confirmation window
        Condition 2: The last candle is the maximum body candle in the confirmation window
        
        This ensures that momentum is strongest at the end (and ideally beginning) of the confirmation window,
        indicating sustained and powerful price movement throughout the period.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_max_body_at_boundaries(
            confirmation_window_df,
            signal
        )
        
        if not is_valid:
            max_pos1, max_pos2, max_body_value = (
                ConsistentMomentumAnalyzer.calculate_max_body_positions(
                    confirmation_window_df
                )
            )
            first_position = 0
            last_position = len(confirmation_window_df) - 1
            condition1 = (
                max_pos1 is not None and max_pos2 is not None and
                first_position in [max_pos1, max_pos2] and
                last_position in [max_pos1, max_pos2]
            )
            condition2 = (
                max_pos1 is not None and
                last_position == max_pos1
            )
            
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Neither condition satisfied. Condition1 (first&last are 1st/2nd max): {condition1}, Condition2 (last is max): {condition2}.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        self.validations.append(Validation(
            step=self.current_step,
            validation=self.validation_step,
            message="Body momentum validation passed.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_volume_consistency(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 5: Validate that volume in the confirmation window is consistent.
        
        The volume ratio must satisfy: max_volume <= min_volume * MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD
        This ensures that volume doesn't spike excessively compared to the minimum, 
        indicating a sustained momentum rather than a brief spike.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_volume_consistency(
            confirmation_window_df,
            self.settings.max_multiplier_difference_volume_threshold
        )
        
        if not is_valid:
            vol_stats = (
                ConsistentMomentumAnalyzer.calculate_volume_stats(
                    confirmation_window_df
                )
            )
            if vol_stats:
                min_vol, max_vol, ratio = vol_stats
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    validation=self.validation_step,
                    message=f"Volume consistency failed: max_volume ({max_vol}) > min_volume ({min_vol}) * threshold ({self.settings.max_multiplier_difference_volume_threshold}). Ratio: {ratio:.2f}",
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
            message="Volume consistency passed.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_confirmation_window_price_range(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 6: Validate that the confirmation window price range is within min and max thresholds.
        
        The price range is calculated as the difference between the highest and lowest close prices
        in the confirmation window. This ensures the confirmation window is neither too narrow 
        (insufficient price movement) nor too wide (excessive volatility).
        """
        self.next_validation()
        
        is_valid = self.validator.validate_price_range(
            confirmation_window_df,
            self.settings.min_confirmation_window_price_threshold,
            self.settings.max_confirmation_window_price_threshold
        )
        
        if not is_valid:
            window_size = (
                ConsistentMomentumAnalyzer.calculate_window_price_range(
                    confirmation_window_df
                )
            )
            if window_size is not None:
                if window_size < self.settings.min_confirmation_window_price_threshold:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"Confirmation window price range {window_size:.2f} is below minimum {self.settings.min_confirmation_window_price_threshold}.",
                        log_level=LogLevel.DEBUG,
                        execution_symbol=self.symbol,
                        start_time=self.current_window_start_time,
                        end_time=self.current_window_end_time,
                        approach=self.APPROACH_NAME
                    )
                elif window_size > self.settings.max_confirmation_window_price_threshold:
                    log(
                        logger=self.logger,
                        status=ValidationStatus.FAILED,
                        name=self.__class__.__name__,
                        alert_time=self.current_window_end_time,
                        step=self.current_step,
                        validation=self.validation_step,
                        message=f"Confirmation window price range {window_size:.2f} exceeds maximum {self.settings.max_confirmation_window_price_threshold}.",
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
            message="Confirmation window price range within thresholds.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_confirmation_window_gap(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 7: Validate that there is no excessive gap between consecutive candles in the confirmation window.
        
        A gap is calculated as the absolute difference between the close price of one candle
        and the open price of the next candle. This ensures there are no significant price jumps
        between consecutive candles (indicating no gaps or slippage).
        
        Formula: gap = |close[i] - open[i+1]| for each consecutive pair
        """
        self.next_validation()
        
        is_valid = self.validator.validate_gaps_between_candles(
            confirmation_window_df,
            self.settings.max_confirmation_gap_threshold
        )
        
        if not is_valid:
            gaps = (
                ConsistentMomentumAnalyzer.calculate_gaps_between_candles(
                    confirmation_window_df
                )
            )
            max_gap = max(gaps) if gaps else 0
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Gap exceeds threshold: max_gap={max_gap:.2f} > {self.settings.max_confirmation_gap_threshold}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time,
                approach=self.APPROACH_NAME
            )
            return False
        
        self.validations.append(Validation(
            name="confirmation_window_gap",
            step=self.current_step,
            validation=self.validation_step,
            message="Confirmation window gaps within threshold.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_color_consistency(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 8: Validate that all candles in the confirmation window have the same color
        matching the signal.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_color_consistency(
            confirmation_window_df,
            signal
        )
        
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Not all candles match {signal} signal color.",
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

    def _step_validate_open_close_price_direction(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 9: Validate that both open and close prices follow the signal direction.
        
        For BUY signal: 
            - Open prices must strictly increase (each candle's open > previous candle's open)
            - Close prices must strictly increase (each candle's close > previous candle's close)
        For SELL signal: 
            - Open prices must strictly decrease (each candle's open < previous candle's open)
            - Close prices must strictly decrease (each candle's close < previous candle's close)
        
        This ensures the price movement is consistent with the signal direction throughout the window.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_open_close_price_direction(
            confirmation_window_df,
            signal
        )
        
        if not is_valid:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message=f"Open and close prices do not follow {signal} direction.",
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
            message=f"Open and close price directions validated for {signal} signal.",
            status=ValidationStatus.PASSED
        ))
        return True

    def _step_validate_min_consistent_candles(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 10: Validate that the confirmation window has at least MIN_CONSISTENT_CANDLES.
        """
        self.next_validation()
        
        is_valid = self.validator.validate_min_consistent_candles(
            confirmation_window_df,
            self.settings.min_consistent_candles
        )
        
        if not is_valid:
            consistent_count = len(confirmation_window_df)
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
            message=f"Consistent candles >= {self.settings.min_consistent_candles}.",
            status=ValidationStatus.PASSED
        ))
        return True
