# src/stockreports/alert/approach/PRICE_GAP/executor.py

import pandas as pd
import logging
import json
from typing import List, Optional

# --- Standard Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode, ValidationStatus, LogLevel
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import PriceGapSettings
from src.stockreports.utils import candle_utils
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.alert.common.signal.market_trend_validation import validate_concurrent_trend
from src.stockreports.utils.log_factory import log

class PriceGapExecutor(Executor):
    APPROACH_NAME = Approach.PRICE_GAP
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = PriceGapSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the PRICE_GAP approach.
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
            
            alerts_data = self._find_price_gap_alerts(df, new_candle_count)
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
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _find_price_gap_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window
        min_gap_size = self.settings.min_gap_size
        cooldown_window = self.settings.cooldown_window

        if len(df) < window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.",
                log_level=LogLevel.WARNING,
                execution_symbol=self.symbol
            )
            return alerts

        df_indexed = df.reset_index()

        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            loop_start_index = min_scan_index
        else:
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        # Reverse loop from the most recent data to the oldest
        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_start_index = i - window_size + 1
            window_df = df_indexed.iloc[window_start_index : i + 1].copy()
            self.current_window_end_time = window_df.iloc[-1]['time']
            self.current_window_start_time = window_df.iloc[0]['time']
            self.current_step = 1
            gap_found_in_window = False

            # Inner loop to find the first significant gap in the window
            for j in range(1, len(window_df)):
                current_candle = window_df.iloc[j]
                previous_candle = window_df.iloc[j - 1]

                # Identify the highest and lowest points of the previous candle's body
                prev_body_high = max(previous_candle['open'], previous_candle['close'])
                prev_body_low = min(previous_candle['open'], previous_candle['close'])

                gap = 0
                is_valid_gap = False

                # Step 1: Check for a valid gap
                if current_candle['open'] > prev_body_high:
                    gap = current_candle['open'] - prev_body_high
                    if gap >= min_gap_size:
                        is_valid_gap = True
                
                elif current_candle['open'] < prev_body_low:
                    gap = current_candle['open'] - prev_body_low
                    if abs(gap) >= min_gap_size:
                        is_valid_gap = True

                if is_valid_gap:
                    gap_found_in_window = True
                    anchor_candle_A = current_candle
                    gap_trend_signal = Signal.BUY if gap > 0 else Signal.SELL

                    # --- Scenario 1: Continuation Alert ---
                    if anchor_candle_A.name == window_df.index[-1]:
                        # Cooldown Check for Continuation
                        self.current_step += 1
                        if is_in_cooldown(
                            new_alert_time=current_candle['time'],
                            new_signal=gap_trend_signal,
                            latest_alert=PriceGapExecutor.LATEST_ALERT,
                            cooldown_window=cooldown_window
                        ):
                            log(
                                logger=self.logger,
                                status=ValidationStatus.FAILED,
                                name=self.__class__.__name__,
                                alert_time=self.current_window_end_time,
                                step=self.current_step,
                                message=f"Continuation alert at {current_candle['time']} is in cooldown.",
                                log_level=LogLevel.DEBUG,
                                execution_symbol=self.symbol,
                                start_time=self.current_window_start_time,
                                end_time=self.current_window_end_time
                            )
                            continue

                        # # Step 3a: Validate the gap candle for the Continuation Alert.
                        # self.current_step += 1
                        # if not validate_concurrent_trend(
                        #     expected_signal=gap_trend_signal,
                        #     alert_time=current_candle['time'],
                        #     symbols=[self.symbol],
                        #     min_body_size=self.settings.min_alert_body_size,
                        #     min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                        #     require_all=True,
                        #     candles_data={self.symbol: current_candle}
                        # ):
                        #     log(
                        #         logger=self.logger,
                        #         status=ValidationStatus.FAILED,
                        #         name=self.__class__.__name__,
                        #         alert_time=self.current_window_end_time,
                        #         step=self.current_step,
                        #         message=f"The gap candle for Continuation Alert at {current_candle['time']} did not meet criteria.",
                        #         log_level=LogLevel.DEBUG,
                        #         execution_symbol=self.symbol,
                        #         start_time=self.current_window_start_time,
                        #         end_time=self.current_window_end_time
                        #     )
                        #     continue

                        # Step 4a: Market Trend Validation for Continuation
                        self.current_step += 1
                        if self.settings.enable_market_trend_validation:
                            if not validate_concurrent_trend(
                                expected_signal=gap_trend_signal,
                                alert_time=current_candle['time'],
                                min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                                require_all=False
                            ):
                                log(
                                    logger=self.logger,
                                    status=ValidationStatus.FAILED,
                                    name=self.__class__.__name__,
                                    alert_time=current_candle['time'],
                                    step=self.current_step,
                                    validation=1,
                                    message="Concurrent market trend validation failed for Continuation alert.",
                                    log_level=LogLevel.DEBUG,
                                    execution_symbol=self.symbol,
                                    start_time=self.current_window_start_time,
                                    end_time=self.current_window_end_time
                                )
                                continue

                        alert_data = self._create_alert_data(
                            signal=gap_trend_signal,
                            alert_candle=anchor_candle_A,
                            previous_candle=previous_candle,
                            gap=gap,
                            alert_type="Continuation"
                        )
                        alerts.append(alert_data)
                        PriceGapExecutor.LATEST_ALERT = alert_data
                        log(
                            logger=self.logger,
                            status=ValidationStatus.PASSED,
                            name=self.__class__.__name__,
                            alert_time=self.current_window_end_time,
                            step=self.current_step,
                            message=f"Price Gap Continuation alert generated for {current_candle['time']}.",
                            log_level=LogLevel.INFO,
                            execution_symbol=self.symbol,
                            start_time=self.current_window_start_time,
                            end_time=self.current_window_end_time
                        )
                        if not is_development_mode: return alerts
                        break # Move to the next outer window

                    # --- Scenario 2: Reversal Alert ---
                    else:
                        reversal_signal = Signal.SELL if gap_trend_signal == Signal.BUY else Signal.BUY
                        
                        # Step 3b: Validate reversal confirmation
                        self.current_step += 1
                        alert_candle = self._validate_reversal_by_volume(
                            window_df=window_df,
                            anchor_candle_A=anchor_candle_A
                        )
                        
                        if alert_candle is None:
                            # Detailed logging is handled within the private method
                            continue

                        # Step 4b: Cooldown Check for reversal
                        self.current_step += 1
                        if is_in_cooldown(
                            new_alert_time=alert_candle['time'],
                            new_signal=reversal_signal,
                            latest_alert=PriceGapExecutor.LATEST_ALERT,
                            cooldown_window=cooldown_window
                        ):
                            log(
                                logger=self.logger,
                                status=ValidationStatus.FAILED,
                                name=self.__class__.__name__,
                                alert_time=self.current_window_end_time,
                                step=self.current_step,
                                message=f"Reversal alert at {alert_candle['time']} is in cooldown.",
                                log_level=LogLevel.DEBUG,
                                execution_symbol=self.symbol,
                                start_time=self.current_window_start_time,
                                end_time=self.current_window_end_time
                            )
                            continue

                        alert_data = self._create_alert_data(
                            signal=reversal_signal,
                            alert_candle=alert_candle,
                            previous_candle=previous_candle,
                            gap=gap,
                            alert_type="Reversal",
                            gap_anchor_candle=anchor_candle_A,
                            reversal_anchor_candle=alert_candle # The alert candle is the reversal anchor
                        )
                        alerts.append(alert_data)
                        PriceGapExecutor.LATEST_ALERT = alert_data
                        log(
                            logger=self.logger,
                            status=ValidationStatus.PASSED,
                            name=self.__class__.__name__,
                            alert_time=self.current_window_end_time,
                            step=self.current_step,
                            message=f"Price Gap Reversal alert generated for {alert_candle['time']}.",
                            log_level=LogLevel.INFO,
                            execution_symbol=self.symbol,
                            start_time=self.current_window_start_time,
                            end_time=self.current_window_end_time
                        )
                        if not is_development_mode: return alerts
                        break # Move to the next outer window
            if not gap_found_in_window:
                log(
                    logger=self.logger,
                    status=ValidationStatus.PASSED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=1,
                    message="No significant price gap found in the window.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol,
                    start_time=self.current_window_start_time,
                    end_time=self.current_window_end_time
                )

        return alerts

    def _validate_reversal_by_volume(self, window_df: pd.DataFrame, anchor_candle_A: pd.Series) -> Optional[pd.Series]:
        """
        Validates a reversal signal based on volume analysis after a price gap.
        """
        # Validation 1: The alert candle must be the last candle in the window.
        alert_candle = candle_utils.get_last_candle(window_df)
        if alert_candle is None or alert_candle.name != window_df.index[-1]:
            # This scenario should not happen if the anchor is not the last candle, but it's a good safeguard.
            return None

        # Validation 2: Define windows
        reversal_window = window_df.loc[anchor_candle_A.name:]
        pre_reversal_window = window_df.loc[:anchor_candle_A.name - 1]

        if pre_reversal_window.empty:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=1,
                message="Pre-reversal window is empty, cannot calculate average volume.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # Validation 3: Calculate average volume of the pre-reversal window
        avg_volume_pre_reversal = pre_reversal_window['volume'].mean()

        # Validation 4: Find max volume candle in the reversal window
        max_volume_candle_in_reversal = candle_utils.find_max_volume_candle(reversal_window)
        if max_volume_candle_in_reversal is None:
            return None

        # Validation 5: Final Volume Confirmation
        # 5a: Max volume candle must be the alert candle (the last candle)
        if max_volume_candle_in_reversal.name != alert_candle.name:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=2,
                message=f"Max volume candle in reversal window is not the alert candle.",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None

        # 5b: Volume of the alert candle must meet the threshold by comparing with the average of the pre-reversal window.
        avg_volume_candle = pd.Series({'volume': avg_volume_pre_reversal})
        is_volume_confirmed, volume_ratio = candle_utils.validate_volume_ratio(
            large_volume_candle=alert_candle,
            small_volume_candle=avg_volume_candle,
            min_volume_multiplier=self.settings.volume_multiplier
        )

        if not is_volume_confirmed:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=3,
                message=f"Alert candle volume confirmation failed. Ratio to average: {volume_ratio:.2f}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                start_time=self.current_window_start_time,
                end_time=self.current_window_end_time
            )
            return None
            
        return alert_candle

    def _create_alert_data(self, signal: Signal, alert_candle: pd.Series, previous_candle: pd.Series, gap: float, alert_type: str, gap_anchor_candle: pd.Series = None, reversal_anchor_candle: pd.Series = None) -> AlertData:
        """
        Creates and populates an AlertData object.
        """
        start_time = previous_candle['time']
        start_price = previous_candle['close']
        magnitude = abs(alert_candle['close'] - start_price)
        alert_time = alert_candle['time']
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = {
            "type": alert_type,
            "initial_gap_size": gap,
        }

        if alert_type == "Continuation":
            details["anchor_candle_time"] = alert_candle['time'].isoformat()
        else: # Reversal
            if gap_anchor_candle is not None:
                details["gap_anchor_time"] = gap_anchor_candle['time'].isoformat()
            if reversal_anchor_candle is not None:
                details["reversal_anchor_time"] = reversal_anchor_candle['time'].isoformat()

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=alert_candle['close'],
            alert_time=alert_time,
            start_price=start_price,
            start_time=start_time.isoformat(),
            magnitude=magnitude,
            details=json.dumps(details)
        )
