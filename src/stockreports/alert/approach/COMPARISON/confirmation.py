import pandas as pd
from typing import Optional
import logging

from .settings import ComparisonSignalSettings
from src.stockreports.alert.common.constants import Signal, Trend
from src.stockreports.alert.model.models import ConfirmationResult

logger = logging.getLogger(__name__)

class ComparisonConfirmation:
    """
    Encapsulates the logic for confirming trading signals by comparing the price
    action of a main symbol against a reference symbol (e.g., a stock vs. an index).
    """
    def __init__(self, settings: ComparisonSignalSettings):
        """
        Initializes the confirmation logic with the specific settings for the comparison.

        Args:
            settings (ComparisonSignalSettings): Configuration object containing the main
                                                 symbol, reference symbol, and MA periods.
        """
        self._settings = settings

    def confirm(self, data: dict[str, pd.DataFrame]) -> Optional[ConfirmationResult]:
        """
        Main entry point to check for a confirmed trend.

        It checks for a synchronized uptrend or downtrend between the two symbols
        and returns the first confirmed signal.

        Args:
            data (dict[str, pd.DataFrame]): A dictionary containing the historical data
                                           for the main symbol and the reference symbol.

        Returns:
            Optional[ConfirmationResult]: A ConfirmationResult object if a signal is
                                          confirmed, otherwise None.
        """
        main_symbol_data = data[self._settings.primary_symbol]
        ref_symbol_data = data[self._settings.referenced_symbol]

        # Check for a confirmed uptrend first.
        uptrend_reversal_time = self._find_price_switch_reversal(main_symbol_data, ref_symbol_data, Signal.BUY)
        if uptrend_reversal_time and self._is_uptrend(main_symbol_data, ref_symbol_data, uptrend_reversal_time):
            return ConfirmationResult(trend=Trend.UPTREND, signal=Signal.BUY, reversal_time=uptrend_reversal_time)
        
        # If no uptrend, check for a confirmed downtrend.
        downtrend_reversal_time = self._find_price_switch_reversal(main_symbol_data, ref_symbol_data, Signal.SELL)
        if downtrend_reversal_time and self._is_downtrend(main_symbol_data, ref_symbol_data, downtrend_reversal_time):
            return ConfirmationResult(trend=Trend.DOWNTREND, signal=Signal.SELL, reversal_time=downtrend_reversal_time)

        # Return empty if no synchronized trend is confirmed.
        return None

    def _is_green(self, candle: pd.Series) -> bool:
        """Helper function to check if a candle is bullish (green)."""
        return candle['close'] > candle['open']

    def _is_red(self, candle: pd.Series) -> bool:
        """Helper function to check if a candle is bearish (red)."""
        return candle['close'] < candle['open']

    def _is_uptrend(self, main_data: pd.DataFrame, ref_data: pd.DataFrame, reversal_time: pd.Timestamp) -> bool:
        """
        Confirms an uptrend by checking for synchronized bullish conditions,
        including a "price-switch" crossover event between the two symbols.
        """
        last_main_candle = main_data.iloc[-1]
        logger.info(f"--- Checking Uptrend for timestamp {last_main_candle.name} ---")

        # 1. Main symbol must end on a green (bullish) candle.
        is_main_green = self._is_green(last_main_candle)
        if not is_main_green:
            logger.info(f"Uptrend FAILED: Main candle is not green.")
            return False
        logger.info("Uptrend PASSED: Main candle is green.")

        # 2. The closing price of main symbol must be above their short-term moving average.
        is_main_above_ma = last_main_candle['close'] > last_main_candle[f'ma_{self._settings.ma_short_period}']
        if not is_main_above_ma:
            logger.info(f"Uptrend FAILED: Main close is not above MA.")
            return False
        logger.info("Uptrend PASSED: Main close is above MA.")
            
        # 3. The current closing price of main symbol must be higher than their
        # respective prices at the time of the crossover. This confirms sustained momentum.
        is_main_higher = last_main_candle['close'] > main_data.loc[reversal_time]['close']
        if not is_main_higher:
            logger.info(f"Uptrend FAILED: Main close is not higher than reversal close.")
            return False
        logger.info("Uptrend PASSED: Main close is higher than reversal close.")

        # 4. The difference between main and ref closing prices must be >= min_price_difference
        last_ref_candle = ref_data.iloc[-1]
        price_diff = last_main_candle['close'] - last_ref_candle['close']
        if price_diff < self._settings.min_price_difference:
            logger.info(f"Uptrend FAILED: Price difference {price_diff} is less than min required {self._settings.min_price_difference}.")
            return False
        logger.info(f"Uptrend PASSED: Price difference {price_diff} >= {self._settings.min_price_difference}.")

        # 4. Confirm divergence conditions are met.
        if not self._is_divergence_confirmed(main_data, ref_data, reversal_time):
            return False

        logger.info(">>> All uptrend conditions PASSED. <<<")
        return True

    def _is_downtrend(self, main_data: pd.DataFrame, ref_data: pd.DataFrame, reversal_time: pd.Timestamp) -> bool:
        """
        Confirms a downtrend by checking for synchronized bearish conditions,
        including a "price-switch" crossover event between the two symbols.
        """
        if self._settings.disable_sell_signal:
            return False
            
        last_main_candle = main_data.iloc[-1]
        logger.info(f"--- Checking Downtrend for timestamp {last_main_candle.name} ---")

        # 1. Main symbol must end on a red (bearish) candle.
        is_main_red = self._is_red(last_main_candle)
        if not is_main_red:
            logger.info(f"Downtrend FAILED: Main candle is not red.")
            return False
        logger.info("Downtrend PASSED: Main candle is red.")

        # 2. The closing price of main symbol must be below their short-term moving average.
        is_main_below_ma = last_main_candle['close'] < last_main_candle[f'ma_{self._settings.ma_short_period}']
        if not is_main_below_ma:
            logger.info(f"Downtrend FAILED: Main close is not below MA.")
            return False
        logger.info("Downtrend PASSED: Main close is below MA.")

        # 3. The current closing price of main symbol must be lower than their
        # respective prices at the time of the crossover. This confirms sustained momentum.
        is_main_lower = last_main_candle['close'] < main_data.loc[reversal_time]['close']
        if not is_main_lower:
            logger.info(f"Downtrend FAILED: Main close is not lower than reversal close.")
            return False
        logger.info("Downtrend PASSED: Main close is lower than reversal close.")

        # 4. The difference between ref and main closing prices must be >= min_price_difference
        last_ref_candle = ref_data.iloc[-1]
        price_diff = last_ref_candle['close'] - last_main_candle['close']
        if price_diff < self._settings.min_price_difference:
            logger.info(f"Downtrend FAILED: Price difference {price_diff} is less than min required {self._settings.min_price_difference}.")
            return False
        logger.info(f"Downtrend PASSED: Price difference {price_diff} >= {self._settings.min_price_difference}.")

        # 4. Confirm divergence conditions are met.
        if not self._is_divergence_confirmed(main_data, ref_data, reversal_time):
            return False

        logger.info(">>> All downtrend conditions PASSED. <<<")
        return True

    def _is_divergence_confirmed(self, main_data: pd.DataFrame, ref_data: pd.DataFrame, reversal_time: pd.Timestamp) -> bool:
        """
        Confirms that the divergence between the main and reference symbols meets
        the configured criteria for both minimum difference and increasing trend.

        Args:
            main_data (pd.DataFrame): Historical data for the main symbol.
            ref_data (pd.DataFrame): Historical data for the reference symbol.
            reversal_time (pd.Timestamp): The timestamp of the crossover event.

        Returns:
            bool: True if divergence conditions are met, False otherwise.
        """
        # Align dataframes to ensure correct element-wise operations
        aligned_main, aligned_ref = main_data.align(ref_data, join='inner', axis=0)

        # 1. Check for minimum price difference at the last candle.
        last_main_close = aligned_main.iloc[-1]['close']
        last_ref_close = aligned_ref.iloc[-1]['close']
        abs_diff = abs(last_main_close - last_ref_close)

        if abs_diff < self._settings.min_price_difference:
            logger.info(f"Divergence FAILED: Absolute difference {abs_diff:.2f} is less than minimum {self._settings.min_price_difference:.2f}")
            return False
        logger.info(f"Divergence PASSED: Absolute difference {abs_diff:.2f} meets minimum.")

        # 2. Check if the absolute difference has been increasing since the reversal.
        if self._settings.use_increasing_difference_confirmation:
            # Calculate the absolute difference series
            diff_series = (aligned_main['close'] - aligned_ref['close']).abs()
            
            # Get the series slice from the reversal point onwards
            diff_since_reversal = diff_series.loc[reversal_time:]
            
            if not diff_since_reversal.is_monotonic_increasing:
                logger.info(f"Divergence FAILED: Absolute difference has not been monotonically increasing since {reversal_time}.")
                return False
            logger.info("Divergence PASSED: Absolute difference is monotonically increasing.")
            
        return True

    def _find_price_switch_reversal(self, main_data: pd.DataFrame, ref_data: pd.DataFrame, signal: str):
        """
        Scans backwards to find a "price-switch" crossover event between the
        main and reference symbols, based on the desired signal direction.

        Args:
            main_data (pd.DataFrame): Historical data for the main symbol.
            ref_data (pd.DataFrame): Historical data for the reference symbol.
            signal (str): The type of signal to look for ("BUY" or "SELL").

        Returns:
            The timestamp of the crossover event (T), or None if not found.
        """
        window_size = self._settings.lookback_window
        main_search = main_data.tail(window_size)
        ref_search = ref_data.tail(window_size)

        for i in range(len(main_search) - 1, 0, -1):
            main_t = main_search.iloc[i]
            ref_t = ref_search.iloc[i]
            main_t_minus_1 = main_search.iloc[i-1]
            ref_t_minus_1 = ref_search.iloc[i-1]

            if signal == Signal.BUY:
                # Uptrend switch: main was below ref, now it's above.
                if main_t_minus_1['close'] < ref_t_minus_1['close'] and main_t['close'] > ref_t['close']:
                    return main_search.index[i]
            elif signal == Signal.SELL:
                # Downtrend switch: main was above ref, now it's below.
                if main_t_minus_1['close'] > ref_t_minus_1['close'] and main_t['close'] < ref_t['close']:
                    return main_search.index[i]
        return None
