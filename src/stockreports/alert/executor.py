from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import logging

from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Signal, PeakTrough, PriceColumn
from src.stockreports.alert.common.data_utils import find_extreme_point
from src.stockreports.alert.common.base_settings import BaseSettings


class Executor(ABC):
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.logger = logging.getLogger(self.__class__.__name__)

    def _confirm_breakout_price(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, lookback_period: int, prominence: float) -> bool:
        """
        Analyzes the backward window to find a breakout price and confirms if the alert candle breaks it.
        """
        alert_candle_time_for_log = df_indexed.index[alert_candle_index]

        # 1. Define the lookback period
        if lookback_period is None:
            lookback_df = df_indexed.iloc[:alert_candle_index]
        else:
            lookback_start_index = max(0, alert_candle_index - lookback_period)
            lookback_df = df_indexed.iloc[lookback_start_index:alert_candle_index]

        if lookback_df.empty:
            self.logger.debug(f"[{alert_candle_time_for_log}] No lookback history available.")
            return True # Bypass if no history

        # 2. Find the breakout price using the new utility function
        extreme_type = PeakTrough.PEAK if signal == Signal.BUY else PeakTrough.TROUGH
        extreme_point_info = find_extreme_point(lookback_df, PriceColumn.CLOSE, extreme_type, prominence)

        if extreme_point_info is None:
            self.logger.debug(f"[{alert_candle_time_for_log}] No peak/trough found; ignoring breakout confirmation.")
            return True

        breakout_price, _ = extreme_point_info
        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout price set to {breakout_price:.2f} for {signal} signal.")

        # 3. Confirm if the alert candle's price breaks the breakout price
        alert_candle = df_indexed.iloc[alert_candle_index]
        is_price_breakout = False
        if signal == Signal.BUY:
            is_price_breakout = alert_candle['close'] > breakout_price
        elif signal == Signal.SELL:
            is_price_breakout = alert_candle['close'] < breakout_price
        
        if not is_price_breakout:
            self.logger.debug(f"[{alert_candle_time_for_log}] Price breakout not confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
            return False

        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
        return True

    def _confirm_reversal_in_forward_window(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, settings: BaseSettings) -> Optional[tuple[pd.Series, Signal]]:
        """
        Analyzes the forward window for a reversal pattern, dispatching to the appropriate
        method based on the window size, with fallback logic.
        """
        alert_candle_time = df_indexed.index[alert_candle_index]
        forward_window_size = settings.long_forward_window

        # 1. Define the forward window
        start_index = alert_candle_index
        end_index = min(alert_candle_index + forward_window_size, len(df_indexed))
        forward_window = df_indexed.iloc[start_index:end_index]

        # 2. Dispatch with fallback logic
        if len(forward_window) < settings.short_forward_window:
            self.logger.debug(f"[{alert_candle_time}] Window size < {settings.short_forward_window}, attempting short-window reversal check first.")
            short_window_result = self._confirm_short_window_reversal(forward_window, signal, alert_candle_time, settings)
            if short_window_result:
                return short_window_result
            self.logger.debug(f"[{alert_candle_time}] Short-window check failed. Attempting fallback to long-window check if applicable.")

        # Fallback for failed short-window checks OR primary path for larger windows.
        # The long-window pattern requires at least 3 candles.
        if len(forward_window) >= 3:
            self.logger.debug(f"[{alert_candle_time}] Checking forward window for long-window reversal.")
            return self._confirm_long_window_reversal(forward_window, df_indexed, alert_candle_index, signal, alert_candle_time, settings)

        # If no conditions are met
        return None

    def _confirm_short_window_reversal(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time, settings: BaseSettings) -> Optional[tuple[pd.Series, Signal]]:
        """Handles reversal logic for short forward windows."""
        if len(forward_window) < 2: # Need at least alert candle + 1 more
            return None

        # 1. Validate the core reversal pattern and get the latest candle if successful
        latest_candle = self._validate_short_window_reversal_pattern(forward_window, signal, alert_candle_time, settings)
        if latest_candle is None:
            return None

        # 2. Gap price check
        previous_candle = forward_window.iloc[-2]
        if not self._validate_short_window_gap_price(latest_candle, previous_candle, signal, alert_candle_time, settings):
            return None

        # If all short-window conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{latest_candle.name}] Confirmed short-window reversal from {signal} to {confirmed_signal}.")
        return latest_candle, confirmed_signal

    def _validate_short_window_gap_price(self, latest_candle: pd.Series, previous_candle: pd.Series, signal: Signal, alert_candle_time, settings: BaseSettings) -> bool:
        """
        Checks if the gap between the latest candle and the previous one is valid.
        """
        gap_is_valid = False
        gap = 0
        if signal == Signal.BUY: # Reversal SELL
            gap = latest_candle['open'] - previous_candle['close']
            if gap <= settings.gap_price:
                gap_is_valid = True
        elif signal == Signal.SELL: # Reversal BUY
            gap = previous_candle['close'] - latest_candle['open']
            if gap <= settings.gap_price:
                gap_is_valid = True
        
        if not gap_is_valid:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 5 FAILED: Gap price condition not met. Gap: {gap:.2f}, Threshold: {settings.gap_price}")
            return False
        self.logger.info(f"[{alert_candle_time}] Short-window Step 5 PASSED: Gap price condition met.")
        return True

    def _validate_short_window_reversal_pattern(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time, settings: BaseSettings) -> Optional[pd.Series]:
        """
        Validates the entire short-window reversal pattern, including trend, dominance, and volume.
        Returns the latest_candle on success, None on failure.
        """
        forward_candles_only = forward_window.iloc[1:]
        if forward_candles_only.empty:
            return None
        latest_candle = forward_candles_only.iloc[-1]

        # 1. Reversal Trend Check
        reversal_is_bullish = None
        if signal == Signal.BUY and latest_candle['close'] < latest_candle['open']:  # Reversal SELL
            reversal_is_bullish = False
        elif signal == Signal.SELL and latest_candle['close'] > latest_candle['open']:  # Reversal BUY
            reversal_is_bullish = True

        if reversal_is_bullish is None:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 1 FAILED: No reversal trend.")
            return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 1 PASSED: Reversal trend confirmed.")

        # 2. Strong body check for the latest candle
        if not self._is_strong_reversal_body(latest_candle, signal, alert_candle_time, "Short-window Step 2", settings):
            return None

        # 3. Volume multiplier check
        all_other_candles = forward_window.iloc[:-1]
        if not all_other_candles.empty:
            max_volume_others = all_other_candles['volume'].max()
            is_volume_multiplied = (latest_candle['volume'] * settings.reversal_volume_multiplier) > max_volume_others
            if not is_volume_multiplied:
                self.logger.debug(f"[{alert_candle_time}] Short-window Step 3 FAILED: Volume multiplier not met. "
                                  f"LatestVol: {latest_candle['volume']}, MaxOtherVol: {max_volume_others}, Multiplier: {settings.reversal_volume_multiplier}")
                return None
        self.logger.info(f"[{alert_candle_time}] Short-window Step 3 PASSED: Volume multiplier condition met.")

        # 4. Dominance Check (Mandatory): Latest candle must have the largest body and volume 
        # compared to other same-trend candles.
        other_candles_for_comparison = forward_window.iloc[1:-1]

        if other_candles_for_comparison.empty:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: No other candles found for dominance comparison.")
            return None

        if reversal_is_bullish:
            other_same_trend_candles = other_candles_for_comparison[other_candles_for_comparison['close'] > other_candles_for_comparison['open']]
        else:
            other_same_trend_candles = other_candles_for_comparison[other_candles_for_comparison['close'] < other_candles_for_comparison['open']]

        if other_same_trend_candles.empty:
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: No other same-trend candles found for dominance comparison.")
            return None

        latest_candle_body = abs(latest_candle['close'] - latest_candle['open'])
        is_largest_body = latest_candle_body >= other_same_trend_candles.apply(lambda x: abs(x['close'] - x['open']), axis=1).max()
        is_largest_volume = latest_candle['volume'] >= other_same_trend_candles['volume'].max()
        
        if not (is_largest_body and is_largest_volume):
            self.logger.debug(f"[{alert_candle_time}] Short-wndow Step 4 FAILED: Latest candle not dominant. "
                                f"LargestBody: {is_largest_body}, LargestVol: {is_largest_volume}")
            return None
        
        self.logger.info(f"[{alert_candle_time}] Short-window Step 4 PASSED: Latest candle is dominant.")

        return latest_candle

    def _validate_reversal_volume_pattern(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time, settings: BaseSettings) -> bool:
        """
        Identifies max and min volume candles and validates their volume and position.
        Returns True if the pattern is valid or skipped, False if it fails.
        """
        latest_candle = forward_window.iloc[-1]
        
        # 1. Reversal Trend Check
        reversal_is_bullish = None
        if signal == Signal.BUY and latest_candle['close'] < latest_candle['open']:  # Reversal SELL
            reversal_is_bullish = False
        elif signal == Signal.SELL and latest_candle['close'] > latest_candle['open']:  # Reversal BUY
            reversal_is_bullish = True

        if reversal_is_bullish is None:
            self.logger.debug(f"[{alert_candle_time}] Long-window Step 1 FAILED: No reversal trend.")
            return False
        self.logger.info(f"[{alert_candle_time}] Long-window Step 1 PASSED: Reversal trend confirmed.")

        # 2. Strong body check for the latest candle
        if not self._is_strong_reversal_body(latest_candle, signal, alert_candle_time, "Long-window Step 2", settings):
            return False

        # 3. The latest_candle must fail to make a new high (for SELL reversal) or a new low (for BUY reversal).
        if not self._validate_reversal_structure(forward_window, signal, alert_candle_time):
            return False

        # 4. Find all trend-consistent candles in the forward window
        if signal == Signal.BUY:
            trend_candles = forward_window[forward_window['close'] > forward_window['open']]
        else:
            trend_candles = forward_window[forward_window['close'] < forward_window['open']]

        # If there are less than 2 trend candles, a max/min pair cannot exist.
        if len(trend_candles) < 2:
            self.logger.debug(f"[{alert_candle_time}] Not enough trend-consistent candles ({len(trend_candles)}) to find a volume pattern.")
            # This is not a failure, just an optional pattern that wasn't found.
            # We can proceed to the other checks.
            return True
            
        # 5. Find the max and min volume candles from the trend-consistent set
        max_volume_candle = trend_candles.loc[trend_candles['volume'].idxmax()]
        min_volume_candle = trend_candles.loc[trend_candles['volume'].idxmin()]

        # 6. Validate the positional requirement: max volume must be before min volume.
        if not (max_volume_candle.name < min_volume_candle.name):
            self.logger.debug(f"[{alert_candle_time}] Positional check FAILED: Max volume candle at {max_volume_candle.name} does not appear before min volume candle at {min_volume_candle.name}.")
            # This is not a failure of the overall reversal, but this specific volume pattern is not met.
            # We can skip the volume ratio check and proceed.
            return True
        self.logger.info(f"[{alert_candle_time}] Positional check PASSED: Max volume candle is before min volume candle.")

        # 7. Perform volume ratio check
        self.logger.info(f"[{alert_candle_time}] Potential reversal found. Max vol: {max_volume_candle.name}, Min vol: {min_volume_candle.name}, Reversal (latest): {latest_candle.name}")

        is_volume_ratio_met = max_volume_candle['volume'] >= min_volume_candle['volume'] * settings.reversal_volume_multiplier
        if not is_volume_ratio_met:
            self.logger.debug(f"[{alert_candle_time}] Step 3 FAILED: Volume ratio not met. "
                              f"(MaxVol: {max_volume_candle['volume']}, MinVol: {min_volume_candle['volume']}, "
                              f"Multiplier: {settings.reversal_volume_multiplier})")
            return False # A failed ratio is a hard failure of the pattern.
        self.logger.info(f"[{alert_candle_time}] Step 3 PASSED: Volume ratio met.")
        
        return True

    def _validate_price_level_proximity(self, alert_candle: pd.Series, forward_window: pd.DataFrame, signal: Signal, alert_candle_time, settings: BaseSettings) -> bool:
        """
        Checks if the alert candle's price is close to the forward window's extreme prices.
        """
        highest_price_fw = max(forward_window['open'].max(), forward_window['close'].max())
        lowest_price_fw = min(forward_window['open'].min(), forward_window['close'].min())
        
        price_to_check = alert_candle['close']
        biggest_diff = max(abs(price_to_check - highest_price_fw), abs(price_to_check - lowest_price_fw))
        is_price_level_close = biggest_diff < settings.reversal_price_diff_threshold

        if not is_price_level_close:
            self.logger.debug(f"[{alert_candle_time}] Step 3 FAILED: Price level is not close enough to forward window extremes. "
                              f"(Signal: {signal}, BiggestDiff: {biggest_diff:.2f}, Threshold: {settings.reversal_price_diff_threshold})")
            return False
        self.logger.info(f"[{alert_candle_time}] Step 3 PASSED: Price level is close enough to forward window extremes.")
        return True

    def _validate_reversal_structure(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time) -> bool:
        """
        Confirms the reversal structure by checking if the final candle fails to make a new high/low.
        """
        latest_candle = forward_window.iloc[-1]
        is_reversal_structure_confirmed = False
        if signal == Signal.SELL: # Original SELL, seeking BUY reversal
            lowest_low_in_window = forward_window['low'].min()
            is_reversal_structure_confirmed = latest_candle['low'] > lowest_low_in_window
        elif signal == Signal.BUY: # Original BUY, seeking SELL reversal
            highest_high_in_window = forward_window['high'].max()
            is_reversal_structure_confirmed = latest_candle['high'] < highest_high_in_window
            
        if not is_reversal_structure_confirmed:
            self.logger.debug(f"[{alert_candle_time}] Step 4 FAILED: Reversal structure not confirmed. "
                              f"(Signal: {signal}, latest_candle_low: {latest_candle['low']:.2f}, latest_candle_high: {latest_candle['high']:.2f}, "
                              f"FwdLow: {forward_window['low'].min():.2f}, FwdHigh: {forward_window['high'].max():.2f})")
            return False
        self.logger.info(f"[{alert_candle_time}] Step 4 PASSED: Reversal structure confirmed.")
        return True

    def _confirm_long_window_reversal(self, forward_window: pd.DataFrame, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, alert_candle_time, settings: BaseSettings) -> Optional[tuple[pd.Series, Signal]]:
        """Analyzes the forward window for a specific multi-candle reversal pattern."""
        
        latest_candle = forward_window.iloc[-1]
        alert_candle = df_indexed.iloc[alert_candle_index]

        # Condition 1: Validate the volume and structure pattern of max vs. min volume candles.
        if not self._validate_reversal_volume_pattern(forward_window, signal, alert_candle_time, settings):
            return None

        # Condition 2: The price level of the alert candle must be close to the forward window's extremes.
        if not self._validate_price_level_proximity(alert_candle, forward_window, signal, alert_candle_time, settings):
            return None

        # All conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{latest_candle.name}] Confirmed reversal from {signal} to {confirmed_signal} based on new logic.")
        return latest_candle, confirmed_signal
        
    def _is_strong_reversal_body(self, candle: pd.Series, signal: Signal, alert_candle_time: pd.Timestamp, step_name: str, settings: BaseSettings) -> bool:
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

        is_body_strong = body_ratio >= settings.reversal_body_ratio_threshold
        if not is_body_strong:
            self.logger.debug(f"[{alert_candle_time}] {step_name} FAILED: Reversal candle body is not strong enough. "
                              f"Ratio: {body_ratio:.2f}, Threshold: {settings.reversal_body_ratio_threshold}")
            return False
        
        self.logger.info(f"[{alert_candle_time}] {step_name} PASSED: Reversal candle body is strong enough.")
        return True

    @abstractmethod
    def run(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        pass

    def is_in_cooldown(
        self,
        latest_alert_timestamp: Optional[pd.Timestamp],
        current_time: pd.Timestamp,
        cooldown_period: int
    ) -> bool:
        """
        Checks if the approach is in a cooldown period based on a timestamp.
        Returns True if in cooldown, False otherwise.
        """
        if latest_alert_timestamp is None:
            return False

        last_alert_time = latest_alert_timestamp.tz_convert(None)
        current_time_naive = current_time.tz_convert(None)
        time_since_last_alert = (current_time_naive - last_alert_time).total_seconds() / 60

        return time_since_last_alert < cooldown_period
