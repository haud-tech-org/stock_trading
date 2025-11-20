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
        last_ref_candle = ref_data.iloc[-1]
        logger.info(f"--- Checking Uptrend for timestamp {last_main_candle.name} ---")

        # 1. Both symbols must end on a green (bullish) candle.
        is_main_green = self._is_green(last_main_candle)
        is_ref_green = self._is_green(last_ref_candle)
        if not (is_main_green and is_ref_green):
            logger.info(f"Uptrend FAILED: Candles are not both green. Main green: {is_main_green}, Ref green: {is_ref_green}")
            return False
        logger.info("Uptrend PASSED: Both candles are green.")

        # 2. The closing price of both symbols must be above their short-term moving average.
        is_main_above_ma = last_main_candle['close'] > last_main_candle[f'ma_{self._settings.ma_short_period}']
        is_ref_above_ma = last_ref_candle['close'] > last_ref_candle[f'ma_{self._settings.ma_short_period}']
        if not (is_main_above_ma and is_ref_above_ma):
            logger.info(f"Uptrend FAILED: Close is not above MA. Main above MA: {is_main_above_ma}, Ref above MA: {is_ref_above_ma}")
            return False
        logger.info("Uptrend PASSED: Both closes are above their MA.")
            
        # 3. The current closing price of both symbols must be higher than their
        # respective prices at the time of the crossover. This confirms sustained momentum.
        is_main_higher = last_main_candle['close'] > main_data.loc[reversal_time]['close']
        is_ref_higher = last_ref_candle['close'] > ref_data.loc[reversal_time]['close']
        if not (is_main_higher and is_ref_higher):
            logger.info(f"Uptrend FAILED: Close is not higher than reversal close. Main higher: {is_main_higher}, Ref higher: {is_ref_higher}")
            return False
        logger.info("Uptrend PASSED: Both closes are higher than their reversal closes.")

        logger.info(">>> All uptrend conditions PASSED. <<<")
        return True

    def _is_downtrend(self, main_data: pd.DataFrame, ref_data: pd.DataFrame, reversal_time: pd.Timestamp) -> bool:
        """
        Confirms a downtrend by checking for synchronized bearish conditions,
        including a "price-switch" crossover event between the two symbols.
        """
        last_main_candle = main_data.iloc[-1]
        last_ref_candle = ref_data.iloc[-1]
        logger.info(f"--- Checking Downtrend for timestamp {last_main_candle.name} ---")

        # 1. Both symbols must end on a red (bearish) candle.
        is_main_red = self._is_red(last_main_candle)
        is_ref_red = self._is_red(last_ref_candle)
        if not (is_main_red and is_ref_red):
            logger.info(f"Downtrend FAILED: Candles are not both red. Main red: {is_main_red}, Ref red: {is_ref_red}")
            return False
        logger.info("Downtrend PASSED: Both candles are red.")

        # 2. The closing price of both symbols must be below their short-term moving average.
        is_main_below_ma = last_main_candle['close'] < last_main_candle[f'ma_{self._settings.ma_short_period}']
        is_ref_below_ma = last_ref_candle['close'] < last_ref_candle[f'ma_{self._settings.ma_short_period}']
        if not (is_main_below_ma and is_ref_below_ma):
            logger.info(f"Downtrend FAILED: Close is not below MA. Main below MA: {is_main_below_ma}, Ref below MA: {is_ref_below_ma}")
            return False
        logger.info("Downtrend PASSED: Both closes are below their MA.")

        # 3. The current closing price of both symbols must be lower than their
        # respective prices at the time of the crossover. This confirms sustained momentum.
        is_main_lower = last_main_candle['close'] < main_data.loc[reversal_time]['close']
        is_ref_lower = last_ref_candle['close'] < ref_data.loc[reversal_time]['close']
        if not (is_main_lower and is_ref_lower):
            logger.info(f"Downtrend FAILED: Close is not lower than reversal close. Main lower: {is_main_lower}, Ref lower: {is_ref_lower}")
            return False
        logger.info("Downtrend PASSED: Both closes are lower than their reversal closes.")

        logger.info(">>> All downtrend conditions PASSED. <<<")
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
