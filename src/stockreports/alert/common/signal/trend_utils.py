import pandas as pd
from typing import Optional
import logging

from src.stockreports.alert.common.constants import Signal

logger = logging.getLogger(__name__)

def validate_trend(
    df: pd.DataFrame, 
    price_type: str = 'close', 
    min_price_change: Optional[float] = None,
    use_monotonic_check: bool = False
) -> Optional[Signal]:
    """
    Validates the trend of a dataframe. Can use a strict monotonic check or a simpler first-to-last price check.

    Args:
        df (pd.DataFrame): The dataframe containing the price data.
        price_type (str): The column name to check for the trend (e.g., 'close', 'high').
        min_price_change (Optional[float]): If provided, validates that the price change
                                            between the first and last candle meets this minimum.
        use_monotonic_check (bool): If True, uses a strict monotonic trend check. 
                                    If False (default), checks the overall direction from the first to the last price.

    Returns:
        Optional[Signal]: Signal.BUY for an uptrend, Signal.SELL for a downtrend, or None if no trend is found.
    """
    # Step 1: Basic DataFrame validation
    if df.empty or len(df) < 2:
        logger.debug(f"[{__name__}] Trend validation failed (Step 1): DataFrame is empty or has fewer than 2 rows.")
        return None

    if price_type not in df.columns:
        logger.error(f"[{__name__}] Trend validation failed (Step 1): Column '{price_type}' not found in the dataframe.")
        raise ValueError(f"Column '{price_type}' not found in the dataframe.")

    series = df[price_type]
    alert_time = df.iloc[-1].get('time', 'N/A') # For logging context

    trend_signal = None
    if use_monotonic_check:
        # Step 2 (Option A): Monotonic trend check
        is_uptrend = series.is_monotonic_increasing
        is_downtrend = series.is_monotonic_decreasing

        if is_uptrend and not is_downtrend:
            trend_signal = Signal.BUY
        elif is_downtrend and not is_uptrend:
            trend_signal = Signal.SELL
        else:
            logger.debug(f"[{__name__}] [{alert_time}] Trend validation failed (Step 2): Trend is not monotonic. Uptrend={is_uptrend}, Downtrend={is_downtrend}.")
            return None
    else:
        # Step 2 (Option B): Overall trend direction check
        first_price = series.iloc[0]
        last_price = series.iloc[-1]

        if last_price > first_price:
            trend_signal = Signal.BUY
        elif last_price < first_price:
            trend_signal = Signal.SELL
        else:
            logger.debug(f"[{__name__}] [{alert_time}] Trend validation failed (Step 2): First price ({first_price:.2f}) and last price ({last_price:.2f}) are equal.")
            return None
        logger.debug(f"[{__name__}] [{alert_time}] Trend validation passed (Step 2): Overall direction check from {first_price:.2f} to {last_price:.2f} determined signal: {trend_signal}.")

    # Step 3: Optional minimum price change validation
    if min_price_change is not None and min_price_change > 0:
        first_close = series.iloc[0]
        last_close = series.iloc[-1]
        price_change = last_close - first_close

        if trend_signal == Signal.BUY:
            if price_change < min_price_change:
                logger.debug(f"[{__name__}] [{alert_time}] Trend validation failed (Step 3): Price change {price_change:.2f} is less than min required {min_price_change:.2f} for BUY.")
                return None
        elif trend_signal == Signal.SELL:
            # For SELL, price_change is negative, so we check if it's greater than the negative minimum.
            if price_change > -min_price_change:
                logger.debug(f"[{__name__}] [{alert_time}] Trend validation failed (Step 3): Price change {price_change:.2f} is greater than min required {-min_price_change:.2f} for SELL.")
                return None
        
        logger.debug(f"[{__name__}] [{alert_time}] Trend validation passed (Step 3): Price change {price_change:.2f} met minimum requirement.")

    logger.debug(f"[{__name__}] [{alert_time}] Trend validation passed. Final Signal: {trend_signal}")
    return trend_signal
