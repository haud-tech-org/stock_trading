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
from src.stockreports.utils import candle_utils


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

            # Step 4: Validate all candles have same color
            self.next_step()
            if not self._step_validate_color_consistency(confirmation_window_df, signal):
                continue

            # Step 5: Validate minimum consistent candles
            self.next_step()
            if not self._step_validate_min_consistent_candles(confirmation_window_df):
                continue

            # Step 6: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=ConsistentMomentumExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue

            # Step 7: Alert creation
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
        For BUY signal: find candle with minimum open price
        For SELL signal: find candle with maximum open price
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

        if signal == Signal.BUY:
            anchor_idx = lookback_window_df['open'].idxmin()
        else:  # SELL
            anchor_idx = lookback_window_df['open'].idxmax()

        # Convert back to positional index within the window
        position_idx = lookback_window_df.index.get_loc(anchor_idx)
        return position_idx

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

    def _step_validate_color_consistency(self, confirmation_window_df: pd.DataFrame, signal: Signal) -> bool:
        """
        Step 4: Validate that all candles in the confirmation window have the same color
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

    def _step_validate_min_consistent_candles(self, confirmation_window_df: pd.DataFrame) -> bool:
        """
        Step 5: Validate that the confirmation window has at least MIN_CONSISTENT_CANDLES.
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
