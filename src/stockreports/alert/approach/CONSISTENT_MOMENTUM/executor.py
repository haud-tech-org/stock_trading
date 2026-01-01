import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal, PeakTrough, PriceColumn
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    is_signal_confirmed,
    _is_rsi_not_exhausted
)
from src.stockreports.alert.common.data_utils import can_apply_analysis, find_extreme_point, find_nearest_extreme_point
from src.stockreports.alert.common.volume import (
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation, 
    is_last_candle_volume_max,
    is_volume_increasing
)
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.utils.time_utils import to_iso8601_with_tz
from .settings import ConsistentMomentumSettings


class ConsistentMomentumExecutor(Executor):
    APPROACH_NAME = Approach.CONSISTENT_MOMENTUM
    LATEST_ACCEPTED_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = ConsistentMomentumSettings(symbol)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
        """
        try:
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
            
            df = prepare_indicators(df)

            alerts_data = self._find_consistent_momentum_alerts(df, new_candle_count)
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

    def _analyze_window(self, window: pd.DataFrame, df_indexed: pd.DataFrame, confirmation_window: int) -> Optional[AlertData]:
        """
        Analyzes a single window of data to find a consistent momentum alert.
        """
        is_all_bullish = (window['close'] > window['open']).all()
        is_all_bearish = (window['close'] < window['open']).all()

        if not (is_all_bullish or is_all_bearish):
            return None

        window['avg_price'] = (window['open'] + window['close']) / 2
        
        is_momentum_confirmed = False
        if is_all_bullish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_increasing
            signal = Signal.BUY
        elif is_all_bearish:
            is_momentum_confirmed = window['avg_price'].is_monotonic_decreasing
            signal = Signal.SELL
        
        if not is_momentum_confirmed:
            return None

        current_candle = window.iloc[-1]
        candle_range = (current_candle['high'] - current_candle['low'])
        if candle_range == 0: 
            return None

        # Restore momentum strength check (total body vs total wick)
        window['body'] = abs(window['close'] - window['open'])
        window['range'] = window['high'] - window['low']
        window['wick'] = window['range'] - window['body']

        total_body = window['body'].sum()
        total_wick = window['wick'].sum()

        if total_body <= total_wick:
            return None

        # Restore RSI exhaustion check
        start_candle = window.iloc[0]
        end_candle = window.iloc[-1]
        candles_for_rsi_check = [start_candle, end_candle]

        if not _is_rsi_not_exhausted(candles_for_rsi_check, signal, self.settings):
            return None

        # Restore general signal confirmation (MA, ADX, etc.)
        if not is_signal_confirmed(end_candle, signal, self.settings):
            return None

        # The breakout confirmation logic has been moved to the main loop
        # to allow for forward-window analysis.

        use_volume_spike = self.settings.use_volume_confirmation
        use_increasing_volume = self.settings.use_volume_increasing_confirmation
        use_last_candle_max_volume = self.settings.use_last_candle_max_volume_confirmation

        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        confirmation_df = df_indexed.iloc[confirmation_candle_index - confirmation_window + 1 : confirmation_candle_index + 1]

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            return None

        # --- Alert Confirmation and Generation ---
        # If forward window confirmation is not used, we stop here.
        if not self.settings.use_forward_window_confirmation:
            return None

        # If we proceed, it means forward window confirmation is required.
        confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
        
        # New Middle Confirmation Step
        if not self._confirm_significant_price_change(df_indexed, confirmation_candle_index, signal):
            return None
            
        confirmation_result = self._get_forward_window_confirmation(df_indexed, confirmation_candle_index, signal)
        
        # If the forward window does not confirm a breakout or reversal, no alert is generated.
        if confirmation_result is None:
            return None

        # Unpack the results
        final_candle, confirmed_signal = confirmation_result
        
        # Now that the final_candle is determined, generate the details.
        details = {
            "momentum_start_price": start_candle['open'],
            "momentum_start_time": to_iso8601_with_tz(start_candle.name),
            "momentum_window_size": confirmation_window,
            "reason": "Consistent Momentum with Breakout"
        }
        
        original_signal = signal
        if confirmed_signal != original_signal:
            details["reason"] = "Consistent Momentum with Reversal"
        
        details["breakout_lookback_minutes"] = self.settings.peak_bottom_lookback_period

        # Create the AlertData object with the final, confirmed data.
        alert_id = str(int(final_candle.name.tz_convert('UTC').timestamp()))
        current_price = final_candle['close']
        momentum_start_price = start_candle['open']

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            alert_time=final_candle.name,
            signal=confirmed_signal,
            alert_price=current_price,
            start_price=momentum_start_price,
            start_time=start_candle.name,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps(details)
        )

    def _confirm_reversal_in_forward_window(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> Optional[tuple[pd.Series, Signal]]:
        """
        Analyzes the forward window for a reversal pattern, dispatching to the appropriate
        method based on the window size, with fallback logic.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]
        forward_window_size = self.settings.long_forward_window

        # 1. Define the forward window
        start_index = alert_candle_index
        end_index = min(alert_candle_index + forward_window_size, len(df_indexed))
        forward_window = df_indexed.iloc[start_index:end_index]

        # 2. Dispatch with fallback logic
        if len(forward_window) < self.settings.short_forward_window:
            self.logger.debug(f"[{alert_candle_time}] Window size < {self.settings.short_forward_window}, attempting short-window reversal check first.")
            short_window_result = self._confirm_short_window_reversal(forward_window, signal, alert_candle_time)
            if short_window_result:
                return short_window_result
            self.logger.debug(f"[{alert_candle_time}] Short-window check failed. Attempting fallback to long-window check if applicable.")

        # Fallback for failed short-window checks OR primary path for larger windows.
        # The long-window pattern requires at least 3 candles.
        if len(forward_window) >= 3:
            self.logger.debug(f"[{alert_candle_time}] Checking forward window for long-window reversal.")
            return self._confirm_long_window_reversal(forward_window, df_indexed, alert_candle_index, signal, alert_candle_time)

        # If no conditions are met
        return None

    def _confirm_short_window_reversal(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time) -> Optional[tuple[pd.Series, Signal]]:
        """Handles reversal logic for short forward windows."""
        if len(forward_window) < 2: # Need at least alert candle + 1 more
            return None

        forward_candles_only = forward_window.iloc[1:]
        if forward_candles_only.empty:
            return None
        latest_candle = forward_candles_only.iloc[-1]
        
        # 1. Reversal Trend Check
        is_reversal_trend = False
        reversal_is_bullish = False
        if signal == Signal.BUY and latest_candle['close'] < latest_candle['open']: # Reversal SELL
            is_reversal_trend = True
        elif signal == Signal.SELL and latest_candle['close'] > latest_candle['open']: # Reversal BUY
            is_reversal_trend = True
            reversal_is_bullish = True

        if not is_reversal_trend:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 1 FAILED: No reversal trend.")
            return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 1 PASSED: Reversal trend confirmed.")

        # 2. Latest candle must have largest body and volume among same-trend candles
        if reversal_is_bullish:
            same_trend_candles = forward_candles_only[forward_candles_only['close'] > forward_candles_only['open']]
        else:
            same_trend_candles = forward_candles_only[forward_candles_only['close'] < forward_candles_only['open']]

        if same_trend_candles.empty:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 2 FAILED: No same-trend candles found for comparison.")
            return None

        latest_candle_body = abs(latest_candle['close'] - latest_candle['open'])
        is_largest_body = latest_candle_body >= same_trend_candles.apply(lambda x: abs(x['close'] - x['open']), axis=1).max()
        is_largest_volume = latest_candle['volume'] >= same_trend_candles['volume'].max()
        
        if not (is_largest_body and is_largest_volume):
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 2 FAILED: Latest candle not dominant among same-trend candles. "
                              f"LargestBody: {is_largest_body}, LargestVol: {is_largest_volume}")
            return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 2 PASSED: Latest candle is dominant among same-trend candles.")

        # 3. Gap price check
        previous_candle = forward_window.iloc[-2]
        gap_is_valid = False
        gap = 0
        if signal == Signal.BUY: # Reversal SELL
            gap = latest_candle['open'] - previous_candle['close']
            if gap <= self.settings.gap_price:
                gap_is_valid = True
        elif signal == Signal.SELL: # Reversal BUY
            gap = previous_candle['close'] - latest_candle['open']
            if gap <= self.settings.gap_price:
                gap_is_valid = True
        
        if not gap_is_valid:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 3 FAILED: Gap price condition not met. Gap: {gap:.2f}, Threshold: {self.settings.gap_price}")
            return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 3 PASSED: Gap price condition met.")

        # 4. Volume multiplier check
        other_candles_in_fw = forward_window.iloc[:-1]
        if not other_candles_in_fw.empty:
            max_volume_others = other_candles_in_fw['volume'].max()
            is_volume_multiplied = (latest_candle['volume'] * self.settings.reversal_volume_multiplier) > max_volume_others
            if not is_volume_multiplied:
                self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: Volume multiplier condition not met. "
                                  f"LatestVol: {latest_candle['volume']}, MaxOtherVol: {max_volume_others}, Multiplier: {self.settings.reversal_volume_multiplier}")
                return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 4 PASSED: Volume multiplier condition met.")

        # 5. Strong body check for the latest candle
        if not self._is_strong_reversal_body(latest_candle, signal, alert_candle_time, "Short-window Step 5"):
            return None

        # If all short-window conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{latest_candle.name}] Confirmed short-window reversal from {signal} to {confirmed_signal}.")
        return latest_candle, confirmed_signal

    def _confirm_long_window_reversal(self, forward_window: pd.DataFrame, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, alert_candle_time) -> Optional[tuple[pd.Series, Signal]]:
        """Analyzes the forward window for a specific multi-candle reversal pattern."""
        
        # 1. Identify key candles based on the new logic, filtering for original trend
        j_candle = forward_window.iloc[-1]

        # Filter for candles that match the original trend to find the max volume candle
        if signal == Signal.BUY: # Original trend was BUY (bullish candles)
            trend_candles = forward_window[forward_window['close'] > forward_window['open']]
        else: # Original trend was SELL (bearish candles)
            trend_candles = forward_window[forward_window['close'] < forward_window['open']]

        if trend_candles.empty:
            self.logger.debug(f"[{alert_candle_time}] No trend-consistent candles found in forward window to identify max volume candle.")
            return None
            
        max_volume_candle = trend_candles.loc[trend_candles['volume'].idxmax()]
        max_volume_candle_loc = forward_window.index.get_loc(max_volume_candle.name)

        # Define the search window for the minimum volume candle:
        # It must be after the max volume candle and before the final j_candle.
        min_vol_search_start_loc = max_volume_candle_loc + 1
        min_vol_search_end_loc = len(forward_window) - 1

        if min_vol_search_start_loc >= min_vol_search_end_loc:
            self.logger.debug(f"[{alert_candle_time}] No valid window to find min volume candle after max volume and before last candle.")
            return None

        min_vol_search_window = forward_window.iloc[min_vol_search_start_loc:min_vol_search_end_loc]
        
        if min_vol_search_window.empty:
            self.logger.debug(f"[{alert_candle_time}] Search window for min volume candle is empty.")
            return None

        # Filter this search window for trend-consistent candles as well
        if signal == Signal.BUY:
            min_vol_trend_candles = min_vol_search_window[min_vol_search_window['close'] > min_vol_search_window['open']]
        else:
            min_vol_trend_candles = min_vol_search_window[min_vol_search_window['close'] < min_vol_search_window['open']]

        if min_vol_trend_candles.empty:
            self.logger.debug(f"[{alert_candle_time}] No trend-consistent candles found in min-volume search window.")
            return None

        # This is the setup candle, now correctly named and filtered
        min_volume_candle = min_vol_trend_candles.loc[min_vol_trend_candles['volume'].idxmin()]
        min_volume_candle_loc = forward_window.index.get_loc(min_volume_candle.name)

        self.logger.debug(f"[{alert_candle_time}] Potential reversal found. Max vol: {max_volume_candle.name}, Min vol: {min_volume_candle.name}, Reversal (j): {j_candle.name}")

        # 2. Apply all reversal conditions sequentially
        # Condition 0: Max volume candle must be before min volume candle (guaranteed by logic)
        if not (max_volume_candle_loc < min_volume_candle_loc):
            self.logger.debug(f"[{alert_candle_time}] Step 0 FAILED: Max volume candle is not before min volume candle.")
            return None
        self.logger.info(f"[{alert_candle_time}] Step 0 PASSED: Max volume candle is before min volume candle.")

        # Condition 1: Volume of max candle vs. min candle
        is_volume_ratio_met = max_volume_candle['volume'] >= min_volume_candle['volume'] * self.settings.reversal_volume_multiplier
        if not is_volume_ratio_met:
            self.logger.debug(f"[{alert_candle_time}] Step 1 FAILED: Volume ratio not met. "
                              f"(MaxVol: {max_volume_candle['volume']}, MinVol: {min_volume_candle['volume']}, "
                              f"Multiplier: {self.settings.reversal_volume_multiplier})")
            return None
        self.logger.info(f"[{alert_candle_time}] Step 1 PASSED: Volume ratio met.")

        # Condition 2: `j` candle (last candle) must show a strong reversal body
        if not self._is_strong_reversal_body(j_candle, signal, alert_candle_time, "Long-window Step 2"):
            return None

        # Condition 3: The price level of the alert candle must be close to the forward window's extremes.
        alert_candle = df_indexed.iloc[alert_candle_index]
        highest_price_fw = max(forward_window['open'].max(), forward_window['close'].max())
        lowest_price_fw = min(forward_window['open'].min(), forward_window['close'].min())
        
        price_to_check = alert_candle['close']
        biggest_diff = max(abs(price_to_check - highest_price_fw), abs(price_to_check - lowest_price_fw))
        is_price_level_close = biggest_diff < self.settings.reversal_price_diff_threshold

        if not is_price_level_close:
            self.logger.debug(f"[{alert_candle_time}] Step 3 FAILED: Price level is not close enough to forward window extremes. "
                              f"(Signal: {signal}, BiggestDiff: {biggest_diff:.2f}, Threshold: {self.settings.reversal_price_diff_threshold})")
            return None
        self.logger.info(f"[{alert_candle_time}] Step 3 PASSED: Price level is close enough to forward window extremes.")

        # Condition 4: The j_candle must fail to make a new high (for SELL reversal) or a new low (for BUY reversal) in the forward window.
        is_reversal_structure_confirmed = False
        if signal == Signal.SELL: # Original SELL, seeking BUY reversal
            lowest_low_in_window = forward_window['low'].min()
            is_reversal_structure_confirmed = j_candle['low'] > lowest_low_in_window
        elif signal == Signal.BUY: # Original BUY, seeking SELL reversal
            highest_high_in_window = forward_window['high'].max()
            is_reversal_structure_confirmed = j_candle['high'] < highest_high_in_window
        if not is_reversal_structure_confirmed:
            self.logger.debug(f"[{alert_candle_time}] Step 4 FAILED: Reversal structure not confirmed. "
                              f"(Signal: {signal}, j_candle_low: {j_candle['low']:.2f}, j_candle_high: {j_candle['high']:.2f}, "
                              f"FwdLow: {forward_window['low'].min():.2f}, FwdHigh: {forward_window['high'].max():.2f})")
            return None
        self.logger.info(f"[{alert_candle_time}] Step 4 PASSED: Reversal structure confirmed.")

        # All conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{j_candle.name}] Confirmed reversal from {signal} to {confirmed_signal} based on new logic.")
        return j_candle, confirmed_signal
        
    def _is_strong_reversal_body(self, candle: pd.Series, signal: Signal, alert_candle_time: pd.Timestamp, step_name: str) -> bool:
        """
        Checks if a reversal candle has a body that is strong enough relative to its opposing wick.
        """
        body_ratio = 0
        candle_body = abs(candle['close'] - candle['open'])

        if signal == Signal.BUY:  # Checking for SELL reversal (bearish candle)
            # For a bearish reversal, we exclude the lower wick. The range is body + upper wick.
            reversal_check_range = candle['high'] - candle['close']
            if reversal_check_range > 0:
                body_ratio = candle_body / reversal_check_range
        
        elif signal == Signal.SELL:  # Checking for BUY reversal (bullish candle)
            # For a bullish reversal, we exclude the upper wick. The range is body + lower wick.
            reversal_check_range = candle['close'] - candle['low']
            if reversal_check_range > 0:
                body_ratio = candle_body / reversal_check_range

        is_body_strong = body_ratio >= self.settings.reversal_body_ratio_threshold
        if not is_body_strong:
            self.logger.debug(f"[{alert_candle_time}] {step_name} FAILED: Reversal candle body is not strong enough. "
                              f"Ratio: {body_ratio:.2f}, Threshold: {self.settings.reversal_body_ratio_threshold}")
            return False
        
        self.logger.info(f"[{alert_candle_time}] {step_name} PASSED: Reversal candle body is strong enough.")
        return True

    def _get_forward_window_confirmation(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> Optional[tuple[pd.Series, Signal]]:
        """
        Confirms a breakout or reversal by analyzing the backward and forward windows.
        Returns a tuple of (confirmation_candle, confirmed_signal) if confirmed, otherwise None.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]

        # 1. Analyze the backward window to get a breakout price and confirm the breakout
        is_breakout_confirmed = self._confirm_breakout_price(
            df_indexed, 
            alert_candle_index, 
            signal,
            lookback_period=self.settings.peak_bottom_lookback_period,
            prominence=self.settings.peak_trough_prominence
        )
        if not is_breakout_confirmed:
            return None

        # 2. Analyze the forward window for a reversal pattern
        confirmation_result = self._confirm_reversal_in_forward_window(df_indexed, alert_candle_index, signal)
        if confirmation_result is None:
            self.logger.debug(f"[{alert_candle_time}] No confirmation pattern was found in the forward window.")
            return None

        return confirmation_result

    def _confirm_significant_price_change(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal) -> bool:
        """
        Confirms that the alert candle represents a significant price change from the nearest
        peak (for SELL) or trough (for BUY) in the lookback period.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]
        alert_candle = df_indexed.iloc[alert_candle_index]

        # 1. Define the lookback period
        lookback_period = self.settings.peak_bottom_lookback_period
        lookback_start_index = max(0, alert_candle_index - lookback_period)
        lookback_df = df_indexed.iloc[lookback_start_index:alert_candle_index]

        if lookback_df.empty:
            self.logger.debug(f"[{alert_candle_time}] No lookback history available for significant price change check.")
            return True # Bypass if no history

        # 2. Find the nearest peak (for SELL) or trough (for BUY)
        # Note: We look for the opposite of the breakout logic. For a SELL signal, we look for a recent PEAK.
        extreme_type = PeakTrough.PEAK if signal == Signal.SELL else PeakTrough.TROUGH
        price_column = PriceColumn.CLOSE
        
        extreme_point_info = find_nearest_extreme_point(
            lookback_df, 
            price_column, 
            extreme_type, 
            self.settings.peak_trough_prominence
        )

        if extreme_point_info is None:
            self.logger.debug(f"[{alert_candle_time}] No opposing peak/trough found; skipping significant change check.")
            return True

        nearest_extreme_price, _ = extreme_point_info
        
        # 3. Check for significant difference
        price_diff = abs(alert_candle['close'] - nearest_extreme_price)
        
        if price_diff < self.settings.significant_price_change_threshold:
            self.logger.debug(f"[{alert_candle_time}] Price change of {price_diff:.2f} from nearest extreme ({nearest_extreme_price:.2f}) is not significant. Threshold: {self.settings.significant_price_change_threshold}")
            return False

        self.logger.debug(f"[{alert_candle_time}] Significant price change of {price_diff:.2f} confirmed.")
        return True

    def _find_consistent_momentum_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Finds alerts based on a consistent momentum pattern using a unified reverse loop.
        """
        alerts = []
        confirmation_window = self.settings.confirmation_window
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        if confirmation_window < 2:
            self.logger.error(f"{self.APPROACH_NAME}: 'CONFIRMATION_WINDOW' must be at least 2. Aborting.")
            return alerts

        required_lookback = confirmation_window
        
        if not can_apply_analysis(df, self.APPROACH_NAME, required_rows=required_lookback):
            return alerts

        df_indexed = df.set_index('time')

        # The main loop can now run up to the last candle. The forward window logic
        # inside the confirmation function will handle boundaries.
        loop_end = len(df_indexed) - 1
        min_scan_index = required_lookback - 1
        
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In DEPLOYMENT, we must scan back far enough to catch momentum windows
            # that could be confirmed by one of the new candles.
            forward_window = self.settings.long_forward_window if self.settings.use_forward_window_confirmation else 0
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - forward_window)

        for i in range(loop_end, loop_start - 1, -1):
            # Ensure we don't look past the end of the dataframe for the momentum window.
            if i < confirmation_window - 1:
                continue

            window = df_indexed.iloc[i - confirmation_window + 1 : i + 1].copy()

            alert = self._analyze_window(window, df_indexed, confirmation_window)

            if alert:
                # Cooldown Check: Ignore alerts with the same direction within the cooldown period
                if ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT is not None:
                    time_since_last = alert.alert_time - ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.alert_time
                    minutes_since_last = time_since_last.total_seconds() / 60

                    if (minutes_since_last < self.settings.cooldown_period and 
                        alert.signal == ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT.signal):
                        alert = None

                if alert:
                    alerts.append(alert)

                    # Update global state with the accepted alert
                    ConsistentMomentumExecutor.LATEST_ACCEPTED_ALERT = alert

                    if not is_development_mode:
                        return alerts

        return alerts[::-1]
