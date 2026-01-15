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
