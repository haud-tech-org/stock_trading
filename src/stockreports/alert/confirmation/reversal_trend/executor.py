from abc import ABC
from typing import Optional
import pandas as pd
import logging

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertData
from src.stockreports.alert.common.constants import Signal
from src.stockreports.alert.common.base_settings import BaseSettings


class ReversalConfirmationExecutor(Executor, ABC):
    def __init__(self, symbol: str, settings: BaseSettings):
        super().__init__(symbol)
        self.settings = settings
        self.logger = logging.getLogger(self.__class__.__name__)

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

        # 1. Validate the core reversal pattern and get the latest candle if successful
        latest_candle = self._validate_short_window_reversal_pattern(forward_window, signal, alert_candle_time)
        if latest_candle is None:
            return None

        # 2. Gap price check
        previous_candle = forward_window.iloc[-2]
        if not self._validate_reversal_gap_price(latest_candle, previous_candle, signal, alert_candle_time, "Short-window Step 5"):
            return None

        # 3. Check for large gaps within the window
        if not self._validate_no_large_gaps_in_window(forward_window, signal, alert_candle_time, "Short-window Step 6"):
            return None

        # If all short-window conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{latest_candle.name}] Confirmed short-window reversal from {signal} to {confirmed_signal}.")
        return latest_candle, confirmed_signal

    def _validate_reversal_gap_price(self, latest_candle: pd.Series, previous_candle: pd.Series, signal: Signal, alert_candle_time, context_message: str) -> bool:
        """
        Checks if the gap between the latest candle and the previous one is valid.
        """
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
            self.logger.debug(f"[{alert_candle_time}] {context_message} FAILED: Gap price condition not met. Gap: {gap:.2f}, Threshold: {self.settings.gap_price}")
            return False
        self.logger.info(f"[{alert_candle_time}] {context_message} PASSED: Gap price condition met.")
        return True

    def _validate_short_window_reversal_pattern(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time) -> Optional[pd.Series]:
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
        if not self._is_strong_reversal_body(latest_candle, signal, alert_candle_time, "Short-window Step 2"):
            return None

        # Define comparison candles
        other_candles_for_comparison = forward_window.iloc[1:-1]

        # Find candles with the same trend as the reversal
        if reversal_is_bullish:
            other_same_trend_candles = other_candles_for_comparison[other_candles_for_comparison['close'] > other_candles_for_comparison['open']]
        else:
            other_same_trend_candles = other_candles_for_comparison[other_candles_for_comparison['close'] < other_candles_for_comparison['open']]

        # Conditional Validation:
        # If there are other same-trend candles, perform a dominance check.
        # Otherwise, perform a volume multiplier check.
        if not other_same_trend_candles.empty:
            # 4. Dominance Check (Mandatory if same-trend candles exist)
            is_dominant = False
            if reversal_is_bullish:
                # For a bullish reversal, the latest candle's low must be higher than the max low of other bullish candles.
                max_low_others = other_same_trend_candles['low'].max()
                is_dominant = latest_candle['low'] > max_low_others
                if not is_dominant:
                    self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: Bullish reversal not dominant. "
                                      f"LatestLow: {latest_candle['low']:.2f}, MaxOtherLow: {max_low_others:.2f}")
            else:  # reversal_is_bearish
                # For a bearish reversal, the latest candle's high must be lower than the min high of other bearish candles.
                min_high_others = other_same_trend_candles['high'].min()
                is_dominant = latest_candle['high'] < min_high_others
                if not is_dominant:
                    self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: Bearish reversal not dominant. "
                                      f"LatestHigh: {latest_candle['high']:.2f}, MinOtherHigh: {min_high_others:.2f}")

            if not is_dominant:
                return None
            self.logger.info(f"[{alert_candle_time}] Short-window Step 4 PASSED: Latest candle is dominant.")
        else:
            # If no other same-trend candles exist, the pattern is not confirmed.
            self.logger.debug(f"[{alert_candle_time}] Short-window Step 4 FAILED: No other same-trend candles found for dominance comparison.")
            return None

        return latest_candle

    def _validate_reversal_volume_pattern(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time) -> bool:
        """
        Identifies max and min volume candles and validates their volume and position.
        Returns True if the pattern is valid or skipped, False if it fails.
        """
        if len(forward_window) < 2:
            self.logger.debug(f"[{alert_candle_time}] Forward window has less than 2 candles, skipping reversal volume pattern validation.")
            return False

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
        if not self._is_strong_reversal_body(latest_candle, signal, alert_candle_time, "Long-window Step 2"):
            return False

        # 3. Gap price check
        previous_candle = forward_window.iloc[-2]
        if not self._validate_reversal_gap_price(latest_candle, previous_candle, signal, alert_candle_time, "Long-window Step 3"):
            return False

        # 4. The latest_candle must fail to make a new high (for SELL reversal) or a new low (for BUY reversal).
        if not self._validate_reversal_structure(forward_window, signal, alert_candle_time):
            return False

        # 5. Check for large gaps within the window
        if not self._validate_no_large_gaps_in_window(forward_window, signal, alert_candle_time, "Long-window Step 5"):
            return False

        # 6. Find the max and min volume candles from the entire forward window.
        # If there are less than 2 candles, a max/min pair cannot exist.
        max_volume_candle = forward_window.loc[forward_window['volume'].idxmax()]
        min_volume_candle = forward_window.loc[forward_window['volume'].idxmin()]

        # Validate that the min volume candle is not the last candle in the window.
        if min_volume_candle.name == latest_candle.name:
            self.logger.debug(f"[{alert_candle_time}] Volume pattern check FAILED: The candle with the minimum volume is the last candle.")
            return False

        # 7. Validate the positional requirement: max volume must be before min volume.
        if not (max_volume_candle.name < min_volume_candle.name):
            self.logger.debug(f"[{alert_candle_time}] Positional check FAILED: Max volume candle at {max_volume_candle.name} does not appear before min volume candle at {min_volume_candle.name}.")
            return False
        self.logger.info(f"[{alert_candle_time}] Positional check PASSED: Max volume candle is before min volume candle.")

        # 8. Perform volume ratio check
        self.logger.info(f"[{alert_candle_time}] Potential reversal found. Max vol: {max_volume_candle.name}, Min vol: {min_volume_candle.name}, Reversal (latest): {latest_candle.name}")

        is_volume_ratio_met = max_volume_candle['volume'] >= min_volume_candle['volume'] * self.settings.reversal_volume_multiplier
        if not is_volume_ratio_met:
            self.logger.debug(f"[{alert_candle_time}] Step 3 FAILED: Volume ratio not met. "
                              f"(MaxVol: {max_volume_candle['volume']}, MinVol: {min_volume_candle['volume']}, "
                              f"Multiplier: {self.settings.reversal_volume_multiplier})")
            return False # A failed ratio is a hard failure of the pattern.
        self.logger.info(f"[{alert_candle_time}] Step 3 PASSED: Volume ratio met.")
        
        return True

    def _validate_no_large_gaps_in_window(self, forward_window: pd.DataFrame, signal: Signal, alert_candle_time, context_message: str) -> bool:
        """
        Checks for significant price gaps between consecutive candles that align with the expected reversal direction.
        - For a BUY signal (expecting a SELL reversal), it looks for downward gaps.
        - For a SELL signal (expecting a BUY reversal), it looks for upward gaps.
        """
        if len(forward_window) < 2:
            return True # Not applicable for single candles or empty windows

        for i in range(len(forward_window) - 1):
            current_candle = forward_window.iloc[i]
            next_candle = forward_window.iloc[i + 1]

            gap = 0
            # For a BUY signal, we are looking for a SELL reversal (gap down).
            if signal == Signal.BUY:
                if next_candle['open'] < current_candle['close']:
                    gap = current_candle['close'] - next_candle['open']
            # For a SELL signal, we are looking for a BUY reversal (gap up).
            elif signal == Signal.SELL:
                if next_candle['open'] > current_candle['close']:
                    gap = next_candle['open'] - current_candle['close']

            if gap > self.settings.adjacent_gap_price:
                self.logger.debug(f"[{alert_candle_time}] {context_message} FAILED: Large gap ({gap:.2f}) detected between consecutive candles, exceeding threshold ({self.settings.adjacent_gap_price}).")
                return False

        self.logger.info(f"[{alert_candle_time}] {context_message} PASSED: No large gaps found in window.")
        return True

    def _validate_price_level_proximity(self, alert_candle: pd.Series, forward_window: pd.DataFrame, signal: Signal, alert_candle_time) -> bool:
        """
        Checks if the alert candle's price is close to the forward window's extreme prices.
        """
        highest_price_fw = max(forward_window['open'].max(), forward_window['close'].max())
        lowest_price_fw = min(forward_window['open'].min(), forward_window['close'].min())
        
        price_to_check = alert_candle['close']
        biggest_diff = max(abs(price_to_check - highest_price_fw), abs(price_to_check - lowest_price_fw))
        is_price_level_close = biggest_diff < self.settings.reversal_price_diff_threshold

        if not is_price_level_close:
            self.logger.debug(f"[{alert_candle_time}] Step 3 FAILED: Price level is not close enough to forward window extremes. "
                              f"(Signal: {signal}, BiggestDiff: {biggest_diff:.2f}, Threshold: {self.settings.reversal_price_diff_threshold})")
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

    def _confirm_long_window_reversal(self, forward_window: pd.DataFrame, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, alert_candle_time) -> Optional[tuple[pd.Series, Signal]]:
        """Analyzes the forward window for a specific multi-candle reversal pattern."""
        
        latest_candle = forward_window.iloc[-1]
        alert_candle = df_indexed.iloc[alert_candle_index]

        # Condition 1: Validate the volume and structure pattern of max vs. min volume candles.
        if not self._validate_reversal_volume_pattern(forward_window, signal, alert_candle_time):
            return None

        # Condition 2: The price level of the alert candle must be close to the forward window's extremes.
        if not self._validate_price_level_proximity(alert_candle, forward_window, signal, alert_candle_time):
            return None

        # All conditions are met
        confirmed_signal = Signal.BUY if signal == Signal.SELL else Signal.SELL
        self.logger.info(f"[{latest_candle.name}] Confirmed reversal from {signal} to {confirmed_signal} based on new logic.")
        return latest_candle, confirmed_signal
        
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
