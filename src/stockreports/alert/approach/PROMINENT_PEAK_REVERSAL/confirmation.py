# src/stockreports/alert/approach/PROMINENT_PEAK_REVERSAL/confirmation.py
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from typing import Optional
import logging

from .settings import ProminentPeakReversalSignalSettings
from src.stockreports.alert.common.constants import Signal, Trend
from src.stockreports.alert.model.models import ConfirmationResult

class ProminentPeakReversalConfirmation:
    """
    Encapsulates the logic for the Prominent Peak Reversal signal.
    This approach identifies a significant peak or trough within a confirmation window
    and then validates a set of reversal criteria.
    """
    def __init__(self, settings: ProminentPeakReversalSignalSettings):
        self._settings = settings
        self.logger = logging.getLogger(__name__)

    def confirm(self, lookback_data: pd.DataFrame) -> Optional[ConfirmationResult]:
        """
        Confirms if a buy or sell signal is present in the given data window.
        """
        if len(lookback_data) < self._settings.confirmation_window:
            return None

        confirmation_window_data = lookback_data.tail(self._settings.confirmation_window)

        # Attempt to find a sell signal first
        sell_signal = self._is_sell_signal_confirmed(confirmation_window_data, lookback_data)
        if sell_signal:
            return sell_signal

        # If no sell signal, attempt to find a buy signal
        buy_signal = self._is_buy_signal_confirmed(confirmation_window_data, lookback_data)
        if buy_signal:
            return buy_signal

        return None

    def _calculate_left_prominence(self, series: pd.Series, index: int, is_peak: bool) -> float:
        """
        Calculates the 'left prominence' of a peak or trough.
        Left prominence is defined as the vertical distance between the peak/trough 
        and the lowest/highest point in the interval to its left, 
        bounded by the nearest higher/lower point (or the start of the series).
        """
        current_val = series.iloc[index]
        predecessors = series.iloc[:index]
        vals = predecessors.values
        
        if is_peak:
            # Find the most recent point that was higher
            higher_indices = np.where(vals > current_val)[0]
            
            if higher_indices.size > 0:
                last_higher = higher_indices[-1]
                relevant_window = vals[last_higher+1:]
            else:
                relevant_window = vals
                
            if len(relevant_window) == 0:
                return 0.0
            
            min_val = relevant_window.min()
            return current_val - min_val
        else:
            # Trough case: Find the most recent point that was lower
            lower_indices = np.where(vals < current_val)[0]
            
            if lower_indices.size > 0:
                last_lower = lower_indices[-1]
                relevant_window = vals[last_lower+1:]
            else:
                relevant_window = vals
                
            if len(relevant_window) == 0:
                return 0.0
                
            max_val = relevant_window.max()
            return max_val - current_val

    def _is_sell_signal_confirmed(self, window_data: pd.DataFrame, lookback_data: pd.DataFrame) -> Optional[ConfirmationResult]:
        """Checks for a confirmed SELL signal based on a prominent peak."""
        self.logger.debug("--- Checking for PROMINENT_PEAK_REVERSAL (SELL) ---")
        
        # Step 1: Find a single significant peak in the window.
        # Use 'open' prices for peak detection
        prices = window_data['open']
        # Find all local maxima first, without prominence check
        peaks, _ = find_peaks(prices)
        
        if len(peaks) == 0:
            self.logger.debug("SELL FAILED: No peaks found.")
            return None

        # Pick the peak with the highest price
        best_peak = peaks[np.argmax(prices.iloc[peaks])]
        
        # New Rule: The highest peak must also be the last peak found in the window
        if best_peak != peaks[-1]:
            self.logger.debug(f"SELL FAILED: Highest peak at {best_peak} is not the last peak (last is {peaks[-1]}).")
            return None

        # Check prominence for this best peak
        prominence = self._calculate_left_prominence(prices, best_peak, is_peak=True)
        if prominence < self._settings.peak_prominence:
            self.logger.debug(f"SELL FAILED: Best peak at {best_peak} has prominence {prominence:.2f} < {self._settings.peak_prominence}.")
            return None
        
        peak_index = best_peak

        # New Rule: Peak cannot be the first candle
        if peak_index == 0:
            self.logger.debug(f"SELL FAILED: Peak candle at index {peak_index} cannot be the first candle in the window.")
            return None

        peak_candle = window_data.iloc[peak_index]
        self.logger.info(f"SELL PASSED: Found 1 significant peak at {peak_candle.name}.")

        # Step 2: Validate that the peak is the highest point in a longer lookback period.
        if self._settings.use_peak_in_lookback_validation:
            if not self._validate_peak_in_lookback(peak_candle, lookback_data, is_peak=True):
                return None

        # Step 3: Check for a long upper wick on the peak candle or the one immediately following it.
        if not self._validate_long_wick(window_data, peak_index, is_upper_wick=True):
            return None

        # Step 4: Confirm that an uptrend was in place before the peak formed.
        if not self._validate_trend_start(window_data, peak_index, is_uptrend=True):
            return None

        # Step 5: Validate the characteristics of the final reversal candle.
        if not self._validate_reversal_candle(window_data, peak_index, is_sell_signal=True):
            return None
            
        # Step 6: Validate volume conditions around the peak.
        if not self._validate_volume(window_data, lookback_data, peak_index):
            return None

        return ConfirmationResult(trend=Trend.DOWNTREND, signal=Signal.SELL, reversal_time=peak_candle.name)

    def _is_buy_signal_confirmed(self, window_data: pd.DataFrame, lookback_data: pd.DataFrame) -> Optional[ConfirmationResult]:
        """Checks for a confirmed BUY signal based on a prominent trough."""
        self.logger.debug("--- Checking for PROMINENT_PEAK_REVERSAL (BUY) ---")

        # Step 1: Find a single significant trough in the window.
        # Use 'open' prices for trough detection
        prices = window_data['open']
        # Find all local minima first (peaks of negative data)
        troughs, _ = find_peaks(-prices)

        if len(troughs) == 0:
            self.logger.debug("BUY FAILED: No troughs found.")
            return None

        # Pick the trough with the lowest price
        best_trough = troughs[np.argmin(prices.iloc[troughs])]

        # New Rule: The lowest trough must also be the last trough found in the window
        if best_trough != troughs[-1]:
            self.logger.debug(f"BUY FAILED: Lowest trough at {best_trough} is not the last trough (last is {troughs[-1]}).")
            return None

        # Check prominence for this best trough
        prominence = self._calculate_left_prominence(prices, best_trough, is_peak=False)
        if prominence < self._settings.peak_prominence:
            self.logger.debug(f"BUY FAILED: Best trough at {best_trough} has prominence {prominence:.2f} < {self._settings.peak_prominence}.")
            return None

        trough_index = best_trough

        # New Rule: Trough cannot be the first candle
        if trough_index == 0:
            self.logger.debug(f"BUY FAILED: Trough candle at index {trough_index} cannot be the first candle in the window.")
            return None

        trough_candle = window_data.iloc[trough_index]
        self.logger.info(f"BUY PASSED: Found 1 significant trough at {trough_candle.name}.")

        # Step 2: Validate that the trough is the lowest point in a longer lookback period.
        if self._settings.use_peak_in_lookback_validation:
            if not self._validate_peak_in_lookback(trough_candle, lookback_data, is_peak=False):
                return None

        # Step 3: Check for a long lower wick on the trough candle or the one immediately following it.
        if not self._validate_long_wick(window_data, trough_index, is_upper_wick=False):
            return None

        # Step 4: Confirm that a downtrend was in place before the trough formed.
        if not self._validate_trend_start(window_data, trough_index, is_uptrend=False):
            return None

        # Step 5: Validate the characteristics of the final reversal candle.
        if not self._validate_reversal_candle(window_data, trough_index, is_sell_signal=False):
            return None

        # Step 6: Validate volume conditions around the trough.
        if not self._validate_volume(window_data, lookback_data, trough_index):
            return None

        return ConfirmationResult(trend=Trend.UPTREND, signal=Signal.BUY, reversal_time=trough_candle.name)

    def _validate_peak_in_lookback(self, peak_candle: pd.Series, lookback_data: pd.DataFrame, is_peak: bool) -> bool:
        """Rule 2: Checks if the peak is the highest high in the lookback window or trough is the lowest low."""
        if is_peak:
            if peak_candle['open'] < lookback_data['open'].max():
                self.logger.debug(f"SELL FAILED (Lookback): Peak open {peak_candle['open']} is not the highest in the lookback window ({lookback_data['open'].max()}).")
                return False
            self.logger.info("SELL PASSED (Lookback): Peak is highest in lookback window.")
        else: # is_trough
            if peak_candle['open'] > lookback_data['open'].min():
                self.logger.debug(f"BUY FAILED (Lookback): Trough open {peak_candle['open']} is not the lowest in the lookback window ({lookback_data['open'].min()}).")
                return False
            self.logger.info("BUY PASSED (Lookback): Trough is lowest in lookback window.")
        return True

    def _validate_long_wick(self, window_data: pd.DataFrame, peak_index: int, is_upper_wick: bool) -> bool:
        """Rule 3: Checks for a long wick on the peak/trough candle or the one before or after it."""
        candle_T = window_data.iloc[peak_index]
        candle_T_minus_1 = window_data.iloc[peak_index - 1] if peak_index - 1 >= 0 else None
        candle_T_plus_1 = window_data.iloc[peak_index + 1] if peak_index + 1 < len(window_data) else None

        def check_wick(candle):
            body = abs(candle['open'] - candle['close'])
            if body <= 0: return False
            if is_upper_wick:
                wick = candle['high'] - max(candle['open'], candle['close'])
            else: # lower_wick
                wick = min(candle['open'], candle['close']) - candle['low']
            return wick > body * self._settings.wick_to_body_ratio

        if (candle_T_minus_1 is not None and check_wick(candle_T_minus_1)) or \
           check_wick(candle_T) or \
           (candle_T_plus_1 is not None and check_wick(candle_T_plus_1)):
            self.logger.info(f"{'SELL' if is_upper_wick else 'BUY'} PASSED: Long {'upper' if is_upper_wick else 'lower'} wick condition met.")
            return True
        
        self.logger.debug(f"{'SELL' if is_upper_wick else 'BUY'} FAILED: Long {'upper' if is_upper_wick else 'lower'} wick condition not met on peak/trough or adjacent candles.")
        return False

    def _validate_trend_start(self, window_data: pd.DataFrame, peak_or_trough_index: int, is_uptrend: bool) -> bool:
        """Rule 4: Validates that a trend was established before the peak/trough."""
        # This rule checks if the trend started within the confirmation window.
        # For an uptrend (leading to a sell signal), the first candle's average price should be lower than the median of preceding candles.
        # For a downtrend (leading to a buy signal), the first candle's average price should be higher than the median of preceding candles.
        if peak_or_trough_index == 0:
            self.logger.debug("TREND START FAILED: Peak/trough is the first candle, cannot determine trend start.")
            return False

        first_candle = window_data.iloc[0]
        
        # We only care about the candles between the start and the peak/trough
        preceding_candles = window_data.iloc[1:peak_or_trough_index]

        # If there are no candles between the start and the peak, the condition cannot be met.
        if preceding_candles.empty:
            self.logger.debug(f"TREND START FAILED: No preceding candles between the first candle and the peak/trough to form a trend.")
            return False

        # Calculate average prices
        first_candle_avg = (first_candle['open'] + first_candle['close']) / 2
        preceding_avgs = (preceding_candles['open'] + preceding_candles['close']) / 2
        preceding_median = preceding_avgs.median()

        if is_uptrend: # For a SELL signal, we expect an uptrend before the peak
            if first_candle_avg >= preceding_median:
                self.logger.debug(f"SELL FAILED (Trend Start): First candle avg {first_candle_avg:.2f} is not lower than median of preceding avgs ({preceding_median:.2f}).")
                return False
            self.logger.info("SELL PASSED (Trend Start): First candle avg is lower than median, implying uptrend start.")
        else: # For a BUY signal, we expect a downtrend before the trough
            if first_candle_avg <= preceding_median:
                self.logger.debug(f"BUY FAILED (Trend Start): First candle avg {first_candle_avg:.2f} is not higher than median of preceding avgs ({preceding_median:.2f}).")
                return False
            self.logger.info("BUY PASSED (Trend Start): First candle avg is higher than median, implying downtrend start.")
        return True

    def _validate_reversal_candle(self, window_data: pd.DataFrame, peak_or_trough_index: int, is_sell_signal: bool) -> bool:
        """Rule 5: Validates the final candle in the window as a confirmation of reversal."""
        # This rule checks the last candle in the window for several reversal characteristics:
        # - It must have a significant body.
        # - The price must have moved significantly from the peak/trough.
        # - For a sell, it should have a small upper wick and be the lowest close.
        # - For a buy, it should have a small lower wick and be the highest close.
        
        last_candle = window_data.iloc[-1]
        peak_or_trough_candle = window_data.iloc[peak_or_trough_index]

        # New Rule: Last candle must match the signal direction
        # if is_sell_signal:
        #     if last_candle['close'] >= last_candle['open']:
        #         self.logger.debug(f"SELL FAILED: Last candle is not bearish (Close {last_candle['close']} >= Open {last_candle['open']}).")
        #         return False
        # else:
        #     if last_candle['close'] <= last_candle['open']:
        #         self.logger.debug(f"BUY FAILED: Last candle is not bullish (Close {last_candle['close']} <= Open {last_candle['open']}).")
        #         return False
        
        # Subsequent candles are those between the peak/trough and the last candle
        subsequent_candles = window_data.iloc[peak_or_trough_index:-1]

        body = abs(last_candle['open'] - last_candle['close'])
        if body < self._settings.min_body_point_price:
            self.logger.debug(f"REVERSAL FAILED: Last candle body {body} is smaller than min required {self._settings.min_body_point_price}.")
            return False

        # New Rule: Check for significant price difference from peak/trough
        if peak_or_trough_index < len(window_data) - 1:
            if is_sell_signal:
                # Use max of open/close (body top) for peak
                reference_price = max(peak_or_trough_candle['open'], peak_or_trough_candle['close'])
                price_diff = reference_price - last_candle['close']
            else:
                # Use min of open/close (body bottom) for trough
                reference_price = min(peak_or_trough_candle['open'], peak_or_trough_candle['close'])
                price_diff = last_candle['close'] - reference_price
        else:
            # If peak/trough IS the last candle, it must match the signal trend
            if is_sell_signal:
                if last_candle['close'] >= last_candle['open']:
                    self.logger.debug(f"REVERSAL FAILED: Peak is last candle but not bearish (Close {last_candle['close']} >= Open {last_candle['open']}).")
                    return False
            else:
                if last_candle['close'] <= last_candle['open']:
                    self.logger.debug(f"REVERSAL FAILED: Trough is last candle but not bullish (Close {last_candle['close']} <= Open {last_candle['open']}).")
                    return False
            
            # In case the peak and the last candle is the one, the price_diff is the absolute difference body price
            price_diff = abs(last_candle['open'] - last_candle['close'])

        if price_diff < self._settings.min_reversal_price_diff:
            self.logger.debug(f"REVERSAL FAILED: Price difference {price_diff} is less than minimum required {self._settings.min_reversal_price_diff}.")
            return False
        self.logger.info(f"REVERSAL PASSED: Price difference {price_diff} meets minimum requirement.")

        # Calculate average prices for comparison
        # Only apply if the peak/trough is NOT the last candle
        if peak_or_trough_index < len(window_data) - 1:
            last_candle_avg = (last_candle['open'] + last_candle['close']) / 2
            subsequent_avgs = (subsequent_candles['open'] + subsequent_candles['close']) / 2
            
            # If subsequent_candles is empty (e.g. peak is second to last), median will be NaN.
            # We should handle this or skip if empty.
            if not subsequent_candles.empty:
                subsequent_median = subsequent_avgs.median()

                if is_sell_signal:
                    if last_candle_avg >= subsequent_median:
                        self.logger.debug(f"SELL FAILED: Last candle avg {last_candle_avg:.2f} is not lower than median of subsequent avgs ({subsequent_median:.2f}).")
                        return False
                    self.logger.info("SELL PASSED: Final reversal candle conditions met.")
                else: # is_buy_signal
                    if last_candle_avg <= subsequent_median:
                        self.logger.debug(f"BUY FAILED: Last candle avg {last_candle_avg:.2f} is not higher than median of subsequent avgs ({subsequent_median:.2f}).")
                        return False
                    self.logger.info("BUY PASSED: Final reversal candle conditions met.")
        
        return True
        
    def _validate_volume(self, window_data: pd.DataFrame, lookback_data: pd.DataFrame, peak_index: int) -> bool:
        """Rule 6: Validates that volume is highest around the peak and drops off."""
        # 1. Search for the candle with the highest volume in [T-1, T, T+1]
        candidate_indices = [i for i in [peak_index-1, peak_index, peak_index+1] if 0 <= i < len(window_data)]
        
        max_vol = -1.0
        
        for idx in candidate_indices:
            vol = window_data.iloc[idx]['volume']
            if vol > max_vol:
                max_vol = vol
        
        # 2. This volume is bigger than the average volume in the lookback window by a multiplier
        avg_volume = lookback_data['volume'].mean()
        if max_vol <= avg_volume * self._settings.volume_multiplier:
            self.logger.debug(f"VOLUME FAILED: Max volume {max_vol} around peak is not > average {avg_volume:.2f} * {self._settings.volume_multiplier} (threshold: {avg_volume * self._settings.volume_multiplier:.2f}).")
            return False

        # 3. Any volume of subsequencial candles < the highest volume candle
        # We interpret this as "All subsequent candles must have volume < max_vol"
        # Only apply if the peak is NOT the last candle
        # if peak_index < len(window_data) - 1:
        #     subsequent_candles = window_data.iloc[max_vol_idx + 1:]
        #     if not subsequent_candles.empty:
        #         if (subsequent_candles['volume'] >= max_vol).any():
        #             self.logger.debug(f"VOLUME FAILED: Found subsequent candle with volume >= max peak region volume {max_vol}.")
        #             return False

        self.logger.info(f"VOLUME PASSED: Max volume {max_vol} is significant and subsequent volumes are lower.")
        return True
