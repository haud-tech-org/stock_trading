import pandas as pd
from typing import List, Optional
import logging

from src.stockreports.alert.common.constants import Signal
from src.stockreports.utils.historical_data_manager import get_historical_data
from src.stockreports.alert.common.signal.trend_utils import validate_trend
from src.stockreports.config.settings import IMPACT_SYMBOLS

logger = logging.getLogger(__name__)

def validate_market_trend(
    start_time: pd.Timestamp, 
    end_time: pd.Timestamp, 
    expected_signal: Signal,
    symbols: List[str] = IMPACT_SYMBOLS,
    min_price_change: Optional[float] = None,
    use_monotonic_check: bool = False
) -> bool:
    """
    Validates that all specified symbols exhibit a consistent trend over a given period.

    Args:
        start_time (pd.Timestamp): The start of the time period for data fetching.
        end_time (pd.Timestamp): The end of the time period for data fetching.
        expected_signal (Signal): The trend signal (BUY for uptrend, SELL for downtrend)
                                  that all symbols are expected to follow.
        symbols (List[str]): A list of symbol strings to validate. Defaults to IMPACT_SYMBOLS.
        min_price_change (Optional[float]): If provided, validates that the price change
                                            between the first and last candle meets this minimum.
        use_monotonic_check (bool): If True, uses a strict monotonic trend check for validation. Defaults to False.

    Returns:
        bool: True if all symbols match the expected trend signal, False otherwise.
    """
    # Step 1: Basic input validation
    if not symbols:
        logger.debug(f"[{__name__}] Market trend validation passed (Step 1): No symbols provided to validate.")
        return True # No symbols to validate, so trivially true.

    logger.debug(f"[{__name__}] Starting market trend validation for {len(symbols)} symbols, expecting signal '{expected_signal}'.")

    for symbol in symbols:
        # Step 2: Fetch data for each symbol
        df_symbol = get_historical_data(symbol, start_time=start_time, end_time=end_time)

        if df_symbol is None or df_symbol.empty:
            logger.warning(f"[{__name__}] Market trend validation failed for '{symbol}' (Step 2): Data is empty for the period {start_time} to {end_time}.")
            return False

        # Optional: Validate the magnitude of the price change from start to end
        if min_price_change is not None and min_price_change > 0:
            first_close = df_symbol['close'].iloc[0]
            last_close = df_symbol['close'].iloc[-1]
            price_change = last_close - first_close
            if abs(price_change) < min_price_change:
                logger.debug(f"[{__name__}] Market trend validation for '{symbol}' failed minimum price change requirement. "
                             f"Required: {min_price_change}, Actual: {abs(price_change)}")
                return False

        # Step 3: Validate the trend for the individual symbol
        trend_signal = validate_trend(
            df=df_symbol, 
            min_price_change=min_price_change,
            use_monotonic_check=use_monotonic_check
        )

        # Step 4: Compare symbol's trend with the expected market trend
        if trend_signal != expected_signal:
            logger.debug(f"[{__name__}] Market trend validation failed for '{symbol}' (Step 4). Expected '{expected_signal}', but its trend was '{trend_signal}'.")
            return False
        
        logger.debug(f"[{__name__}] Market trend validation passed for '{symbol}' (Step 4). Its trend '{trend_signal}' matched expected '{expected_signal}'.")
            
    # If all symbols passed the validation
    logger.debug(f"[{__name__}] Market trend validation passed for all {len(symbols)} symbols.")
    return True


def validate_concurrent_trend(
    expected_signal: Signal,
    alert_time: pd.Timestamp,
    symbols: List[str] = IMPACT_SYMBOLS,
    min_body_size: Optional[float] = None,
    min_body_to_range_ratio: Optional[float] = None,
    require_all: bool = True,
    candles_data: Optional[dict] = None
) -> bool:
    """
    Validates that all or at least one of the specified symbols have a candle of a specific direction at a given time.

    Args:
        expected_signal (Signal): The expected signal (BUY for green candle, SELL for red candle).
        alert_time (pd.Timestamp): The specific timestamp of the candle to validate.
        symbols (List[str]): A list of symbol strings to validate. Defaults to IMPACT_SYMBOLS.
        min_body_size (Optional[float]): If provided, validates that the candle's body size
                                         meets this minimum requirement.
        min_body_to_range_ratio (Optional[float]): If provided, validates that the candle's body
                                                   is at least this ratio of the total candle range (high-low).
        require_all (bool): If True, all symbols must pass validation. If False, at least one must pass.
        candles_data (Optional[dict]): A dictionary where keys are symbol strings and values are the candle's data
                                       (as a dict or pd.Series) at the alert_time. If provided, this data is
                                       used instead of fetching from the database.

    Returns:
        bool: True if the validation condition is met, False otherwise.
    """
    if not symbols:
        logger.debug(f"[{__name__}] Concurrent trend validation passed: No symbols provided.")
        return True

    logger.debug(f"[{__name__}] Starting concurrent trend validation for {len(symbols)} symbols at {alert_time}, expecting signal '{expected_signal}'. Require all: {require_all}.")

    passed_symbols_count = 0
    for symbol in symbols:
        candle = None
        # If pre-fetched candle data is available for the symbol, use it
        if candles_data and symbol in candles_data:
            candle = candles_data[symbol]
            logger.debug(f"[{__name__}] Using pre-fetched candle data for '{symbol}'.")
        else:
            # Add a buffer to the time range to ensure data is captured
            buffer = pd.Timedelta(minutes=1)
            start_buffer = alert_time - buffer
            end_buffer = alert_time + buffer

            # Fetch data within the buffered time window
            df_symbol_buffered = get_historical_data(symbol, start_time=start_buffer, end_time=end_buffer)

            if df_symbol_buffered is None or df_symbol_buffered.empty:
                logger.warning(f"[{__name__}] Concurrent trend validation: No data for '{symbol}' around {alert_time}.")
                if require_all:
                    return False # If all are required, this is a failure.
                continue # Otherwise, just skip to the next symbol.

            # --- FIX: Ensure 'time' column is the index ---
            if 'time' in df_symbol_buffered.columns and not isinstance(df_symbol_buffered.index, pd.DatetimeIndex):
                df_symbol_buffered = df_symbol_buffered.set_index('time')
            # --- End FIX ---

            # Find the specific candle at the exact alert_time
            candle_series = df_symbol_buffered[df_symbol_buffered.index == alert_time]
            if candle_series.empty:
                logger.warning(f"[{__name__}] Concurrent trend validation: Could not find candle for '{symbol}' at exact time {alert_time}.")
                if require_all:
                    return False
                continue
            
            candle = candle_series.iloc[0]
        
        # Determine the candle's signal
        is_green = candle['close'] > candle['open']
        is_red = candle['close'] < candle['open']
        
        actual_signal = Signal.BUY if is_green else (Signal.SELL if is_red else None)

        # Check if the signal matches the expected signal
        if actual_signal != expected_signal:
            logger.debug(f"[{__name__}] Concurrent trend validation for '{symbol}' failed. Expected '{expected_signal}', but its signal was '{actual_signal}'.")
            if require_all:
                return False
            continue

        # Optional: Validate the body size of the candle
        if min_body_size is not None and min_body_size > 0:
            body_size = abs(candle['close'] - candle['open'])
            if body_size < min_body_size:
                logger.debug(f"[{__name__}] Concurrent trend validation for '{symbol}' failed minimum body size. "
                             f"Required: {min_body_size}, Actual: {body_size}")
                if require_all:
                    return False
                continue

        # Optional: Validate the body to range ratio
        if min_body_to_range_ratio is not None and min_body_to_range_ratio > 0:
            body_size = abs(candle['close'] - candle['open'])
            range_size = candle['high'] - candle['low']
            
            if range_size > 0:
                body_ratio = body_size / range_size
                if body_ratio < min_body_to_range_ratio:
                    logger.debug(f"[{__name__}] Concurrent trend validation for '{symbol}' failed minimum body-to-range ratio. "
                                 f"Required: {min_body_to_range_ratio}, Actual: {body_ratio:.2f}")
                    if require_all:
                        return False
                    continue
            elif min_body_to_range_ratio > 0: # If range is 0 (a doji), it can't meet any positive ratio requirement.
                logger.debug(f"[{__name__}] Concurrent trend validation for '{symbol}' failed body-to-range ratio. "
                             f"Candle has zero range, but a ratio of {min_body_to_range_ratio} was required.")
                if require_all:
                    return False
                continue
        
        logger.debug(f"[{__name__}] Concurrent trend validation passed for '{symbol}'. Its signal '{actual_signal}' matched expected '{expected_signal}'.")
        
        # If we don't require all and we found one, we can exit early.
        if not require_all:
            logger.debug(f"[{__name__}] Concurrent trend validation passed: at least one symbol '{symbol}' met the criteria.")
            return True
        
        passed_symbols_count += 1

    if require_all:
        logger.debug(f"[{__name__}] Concurrent trend validation passed for all {passed_symbols_count} symbols.")
        return True
    else:
        # If we are here and `require_all` is false, it means no symbols passed the validation.
        logger.debug(f"[{__name__}] Concurrent trend validation failed: No symbols met the required criteria.")
        return False
