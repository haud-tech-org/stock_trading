# src/stockreports/alert/approach/PRICE_GAP/executor.py

import pandas as pd
import logging
import json
from typing import List, Optional

# --- Standard Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import PriceGapSettings
from src.stockreports.alert.common.confirmation.reversal import validate_reversal_confirmation
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.alert.common.signal.market_trend_validation import validate_concurrent_trend

class PriceGapExecutor(Executor):
    APPROACH_NAME = Approach.PRICE_GAP
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = PriceGapSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the PRICE_GAP approach.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            alerts_data = self._find_price_gap_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

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
            self.logger.warning(f"Not enough data for {self.APPROACH_NAME}: requires {window_size}, have {len(df)}.")
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
            alert_time_candidate = window_df.iloc[-1]['time']
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

                    # Step 2: Cooldown Check for initial gap
                    if is_in_cooldown(
                        new_alert_time=current_candle['time'],
                        new_signal=gap_trend_signal,
                        latest_alert=PriceGapExecutor.LATEST_ALERT,
                        cooldown_window=cooldown_window
                    ):
                        self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 2 Failed: Initial gap at {current_candle['time']} is in cooldown.")
                        continue

                    # --- Scenario 1: Continuation Alert ---
                    if anchor_candle_A.name == window_df.index[-1]:
                        # New Step: Validate the gap candle for the Continuation Alert.
                        # This checks body size, body-to-range ratio, and direction.
                        if not validate_concurrent_trend(
                            expected_signal=gap_trend_signal,
                            alert_time=current_candle['time'],
                            symbols=[self.symbol],
                            min_body_size=self.settings.min_alert_body_size,
                            min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                            require_all=True,
                            candles_data={self.symbol: current_candle}
                        ):
                            self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 1 Failed: The gap candle for Continuation Alert at {current_candle['time']} did not meet criteria.")
                            continue

                        # Step 3a: Market Trend Validation for Continuation
                        if self.settings.enable_market_trend_validation:
                            if not validate_concurrent_trend(
                                expected_signal=gap_trend_signal,
                                alert_time=current_candle['time'],
                                min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                                require_all=False
                            ):
                                self.logger.debug(f"[{self.__class__.__name__}] [{current_candle['time']}] Step 3a Failed: Concurrent market trend validation failed for Continuation alert.")
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
                        if not is_development_mode: return alerts
                        break # Move to the next outer window

                    # --- Scenario 2: Reversal Alert ---
                    else:
                        confirmation_df = window_df.loc[anchor_candle_A.name:].copy()
                        reversal_signal = Signal.SELL if gap_trend_signal == Signal.BUY else Signal.BUY
                        
                        # Step 3b: Validate reversal confirmation
                        validation_result = validate_reversal_confirmation(
                            confirmation_df, 
                            reversal_signal, 
                            self.settings.min_alert_body_size,
                            self.settings.max_distance_close_price
                        )

                        if validation_result:
                            alert_candle, reversal_anchor_candle = validation_result
                            
                            # Step 4: Market Trend Validation for Reversal
                            if self.settings.enable_market_trend_validation:
                                if not validate_concurrent_trend(
                                    expected_signal=reversal_signal,
                                    alert_time=alert_candle['time'],
                                    min_body_to_range_ratio=self.settings.impact_symbols_min_body_to_range_ratio,
                                    require_all=False
                                ):
                                    self.logger.debug(f"[{self.__class__.__name__}] [{alert_candle['time']}] Step 4 Failed: Concurrent market trend validation failed for Reversal alert.")
                                    continue

                            # Step 5: Cooldown Check for Reversal
                            if is_in_cooldown(
                                new_alert_time=alert_candle['time'],
                                new_signal=reversal_signal,
                                latest_alert=PriceGapExecutor.LATEST_ALERT,
                                cooldown_window=cooldown_window
                            ):
                                self.logger.debug(f"[{self.__class__.__name__}] [{alert_candle['time']}] Step 5 Failed: Reversal alert is in cooldown.")
                                continue

                            alert_data = self._create_alert_data(
                                signal=reversal_signal,
                                alert_candle=alert_candle,
                                previous_candle=previous_candle,
                                gap=gap,
                                alert_type="Reversal",
                                gap_anchor_candle=anchor_candle_A,
                                reversal_anchor_candle=reversal_anchor_candle
                            )
                            alerts.append(alert_data)
                            PriceGapExecutor.LATEST_ALERT = alert_data
                            if not is_development_mode: return alerts
                            break # Move to the next outer window
                        else:
                            self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 3b Failed: Reversal confirmation failed after gap at {anchor_candle_A['time']}.")

            if not gap_found_in_window:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 1 Failed: No significant price gap found in the window.")
            
        return alerts

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
            details["gap_anchor_time"] = gap_anchor_candle['time'].isoformat()
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
