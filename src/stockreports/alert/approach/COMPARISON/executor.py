import pandas as pd
import logging
import json
from typing import List, Optional, Tuple

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Mode
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import ComparisonSettings
from src.stockreports.utils.alert_utils import is_in_cooldown
from src.stockreports.utils.historical_data_manager import get_historical_data
from src.stockreports.alert.common.confirmation.reversal import validate_reversal_confirmation
from src.stockreports.alert.common.signal.trend_utils import validate_trend
from src.stockreports.alert.common.signal.market_trend_validation import validate_market_trend

class ComparisonExecutor(Executor):
    APPROACH_NAME = Approach.COMPARISON
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ComparisonSettings(symbol)
        super().__init__(symbol, self.settings)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        # This approach should only run for its configured primary symbol.
        if self.symbol != self.settings.primary_symbol:
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame())

        try:
            self.logger.info(f"[{self.__class__.__name__}] Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")

            alerts_data = self._find_comparison_alerts(df, new_candle_count)
            self.logger.info(f"[{self.__class__.__name__}] '{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"[{self.__class__.__name__}] An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=pd.DataFrame(),
                status="FAILED",
                message=str(e)
            )

    def _find_comparison_alerts(self, df_primary: pd.DataFrame, new_candle_count: int = 0) -> List[AlertData]:
        # --- Data Loading for Reference Symbol ---
        start_time = df_primary['time'].min()
        end_time = df_primary['time'].max()
        df_reference = get_historical_data(self.settings.reference_symbol, start_time=start_time, end_time=end_time)

        if df_reference is None or df_reference.empty:
            self.logger.warning(f"[{self.__class__.__name__}] Reference dataframe for {self.settings.reference_symbol} is empty. Skipping alert finding.")
            return []

        # Reset index to ensure we are working with integer-based indices
        df_primary = df_primary.reset_index()
        df_reference = df_reference.reset_index()

        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        window_size = self.settings.lookback_window

        # Align dataframes by merging on the 'time' column
        df_merged = pd.merge(df_primary, df_reference, on='time', suffixes=('_primary', '_reference'))
        if len(df_merged) < window_size:
            self.logger.warning(f"[{self.__class__.__name__}] Not enough aligned data for {self.APPROACH_NAME}: requires {window_size}, have {len(df_merged)}.")
            return alerts

        df_indexed = df_merged

        loop_end_index = len(df_indexed) - 1
        min_scan_index = window_size - 1

        if is_development_mode:
            loop_start_index = min_scan_index
        else:
            loop_start_index = max(min_scan_index, len(df_indexed) - new_candle_count)

        for i in range(loop_end_index, loop_start_index - 1, -1):
            window_df = df_indexed.iloc[i - window_size + 1 : i + 1]
            alert_time_candidate = window_df.iloc[-1]['time']

            # Step 1: Find the crossover point using the merged data
            anchor_pos, potential_signal = self._find_crossover_point(window_df)
            if anchor_pos is None:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 1 Failed: No crossover point found in window.")
                continue

            # Get the timestamp of the anchor event from its position in the window
            anchor_timestamp = window_df.iloc[anchor_pos]['time']

            # Step 2: Validate reversal on the reference symbol's data
            ref_confirmation_df = df_reference[df_reference['time'] >= anchor_timestamp]
            if len(ref_confirmation_df) < 2:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 2 Failed: Not enough data for reversal validation on reference symbol.")
                continue

            validation_result = validate_reversal_confirmation(
                confirmation_df=ref_confirmation_df,
                reversal_signal=potential_signal,
                min_alert_body_size=self.settings.min_alert_body_size,
                max_distance_close_price=self.settings.max_distance_close_price
            )
            if validation_result is None:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 2 Failed: Reversal confirmation failed on reference symbol.")
                continue
            
            # Extract candle data from the validation result
            alert_candle_ref, anchor_reversal_candle_ref = validation_result
            
            # Extract timestamps from the candles
            anchor_reversal_time = anchor_reversal_candle_ref['time']
            alert_time = alert_candle_ref['time']

            # Step 3: Check the primary trend's magnitude (cheap check first)
            anchor_candle_primary = df_primary[df_primary['time'] == anchor_timestamp].iloc[0]
            alert_candle_primary = df_primary[df_primary['time'] == alert_time].iloc[0]
            primary_trend_magnitude = alert_candle_primary['close'] - anchor_candle_primary['close']
            if abs(primary_trend_magnitude) > self.settings.max_primary_trend_magnitude:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 3 Failed: Primary trend magnitude ({primary_trend_magnitude:.2f}) exceeded max ({self.settings.max_primary_trend_magnitude}).")
                continue

            # Step 4: Define confirmation window and validate trends
            # The window is from the candle AFTER the anchor reversal up to the alert candle
            confirmation_window_primary = df_primary[
                (df_primary['time'] > anchor_reversal_time) & 
                (df_primary['time'] <= alert_time)
            ]
            confirmation_window_ref = df_reference[
                (df_reference['time'] > anchor_reversal_time) & 
                (df_reference['time'] <= alert_time)
            ]

            if confirmation_window_primary.empty or confirmation_window_ref.empty:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 4 Failed: Confirmation window is empty.")
                continue

            primary_trend_signal = validate_trend(
                df=confirmation_window_primary,
                use_monotonic_check=True
            )
            ref_trend_signal = validate_trend(
                df=confirmation_window_ref,
                use_monotonic_check=True
            )

            # Step 5: Determine the final signal based on trend agreement
            final_signal = None
            if (potential_signal == Signal.BUY and 
                primary_trend_signal == Signal.BUY and 
                ref_trend_signal == Signal.BUY and 
                not self.settings.disable_buy_signal):
                final_signal = Signal.BUY
            elif (potential_signal == Signal.SELL and 
                  primary_trend_signal == Signal.SELL and 
                  ref_trend_signal == Signal.SELL and 
                  not self.settings.disable_sell_signal):
                final_signal = Signal.SELL

            if final_signal is None:
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 5 Failed: Trend signals did not agree. Potential: {potential_signal}, Primary: {primary_trend_signal}, Reference: {ref_trend_signal}.")
                continue

            # Step 6: Validate against overall market trend (optional)
            if self.settings.enable_market_trend_validation:
                # Find the timestamp of the candle immediately after the anchor reversal
                anchor_reversal_idx = anchor_reversal_candle_ref.name
                if anchor_reversal_idx + 1 < len(df_reference):
                    market_trend_start_time = df_reference.iloc[anchor_reversal_idx + 1]['time']
                else:
                    self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 6 Failed: No candle found after anchor reversal for market trend validation.")
                    continue # No candles after the reversal to validate, so skip

                if not validate_market_trend(
                    start_time=market_trend_start_time,
                    end_time=alert_time,
                    expected_signal=final_signal,
                    min_price_change=self.settings.min_market_price_change,
                    use_monotonic_check=False
                ):
                    self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 6 Failed: Market trend validation failed.")
                    continue

            # Step 7: Cooldown Check
            if is_in_cooldown(
                new_alert_time=alert_time,
                new_signal=final_signal,
                latest_alert=ComparisonExecutor.LATEST_ALERT,
                cooldown_window=self.settings.cooldown_window
            ):
                self.logger.debug(f"[{self.__class__.__name__}] [{alert_time_candidate}] Step 7 Failed: Alert is in cooldown period.")
                continue
            
            # All checks passed, create the alert
            self.logger.info(f"[{self.__class__.__name__}] [{alert_time_candidate}] All validation steps passed. Creating alert.")
            alert_data = self._create_alert_data(
                alert_candle_primary=alert_candle_primary,
                anchor_candle_primary=anchor_candle_primary,
                signal=final_signal,
                anchor_candle_ref_price=df_reference[df_reference['time'] == anchor_timestamp]['close'].iloc[0]
            )
            alerts.append(alert_data)
            ComparisonExecutor.LATEST_ALERT = alert_data

            if not is_development_mode:
                return alerts
        
        return alerts

    def _find_crossover_point(self, window_df: pd.DataFrame) -> Tuple[Optional[int], Optional[Signal]]:
        """
        Finds the most recent crossover point and the potential signal it implies.
        Searches backwards and returns the relative position and signal of the first flip found.
        """
        if len(window_df) < 2:
            return None, None

        # Iterate backwards from the end of the window.
        for i in range(len(window_df) - 1, 0, -1):
            current_candle = window_df.iloc[i]
            prev_candle = window_df.iloc[i - 1]

            prev_primary_below_ref = prev_candle['close_primary'] < prev_candle['close_reference']
            curr_primary_below_ref = current_candle['close_primary'] < current_candle['close_reference']

            if prev_primary_below_ref != curr_primary_below_ref:
                # Crossover detected. Determine the signal based on the direction of the cross.
                potential_signal = Signal.BUY if not curr_primary_below_ref else Signal.SELL
                self.logger.debug(f"[{self.__class__.__name__}] Crossover found at {current_candle['time']}: Prev Primary < Ref: {prev_primary_below_ref}, Curr Primary < Ref: {curr_primary_below_ref}. Signal: {potential_signal}")
                return i, potential_signal
            else:
                # Log why a crossover did not happen for these two candles
                relation = "below" if curr_primary_below_ref else "above"
                self.logger.debug(
                    f"[{self.__class__.__name__}] No crossover at {current_candle['time']}: Primary remained {relation} reference. "
                    f"Prev: {prev_candle['close_primary']:.2f} vs {prev_candle['close_reference']:.2f}, "
                    f"Curr: {current_candle['close_primary']:.2f} vs {current_candle['close_reference']:.2f}"
                )

        return None, None

    def _create_alert_data(self, alert_candle_primary: pd.Series, anchor_candle_primary: pd.Series, signal: Signal, anchor_candle_ref_price: float) -> AlertData:
        alert_time = alert_candle_primary['time']
        alert_id = str(int(alert_time.timestamp()))
        magnitude = abs(alert_candle_primary['close'] - anchor_candle_primary['close'])
        details = {
            'approach': self.APPROACH_NAME,
            'primary_symbol': self.settings.primary_symbol,
            'reference_symbol': self.settings.reference_symbol,
            'alert_price': alert_candle_primary['close'],
            'alert_time': alert_time.isoformat(),
            'anchor_price_primary': anchor_candle_primary['close'],
            'anchor_price_reference': anchor_candle_ref_price,
            'anchor_time': anchor_candle_primary['time'].isoformat(),
            'magnitude': magnitude,
            'primary_trend_magnitude': alert_candle_primary['close'] - anchor_candle_primary['close'],
        }

        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            approach=self.APPROACH_NAME,
            alert_time=alert_time,
            alert_price=alert_candle_primary['close'],
            start_time=anchor_candle_primary['time'],
            start_price=anchor_candle_primary['close'],
            magnitude=magnitude,
            details=json.dumps(details)
        )
