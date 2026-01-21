import pandas as pd
from typing import Optional

def find_max_volume_candle(window_df: pd.DataFrame) -> pd.Series:
    """
    Searches for and returns the candle with the maximum volume in a given window.

    Args:
        window_df: A DataFrame representing the window of candles to search.

    Returns:
        The candle (as a Series) with the highest volume.
    """
    max_vol_idx = window_df['volume'].idxmax()
    return window_df.loc[max_vol_idx]

def find_min_volume_candle(window_df: pd.DataFrame) -> pd.Series:
    """
    Searches for and returns the candle with the minimum volume in a given window.

    Args:
        window_df: A DataFrame representing the window of candles to search.

    Returns:
        The candle (as a Series) with the lowest volume.
    """
    min_vol_idx = window_df['volume'].idxmin()
    return window_df.loc[min_vol_idx]

def find_biggest_body_candle(window_df: pd.DataFrame) -> pd.Series:
    """
    Finds the candle with the largest body size (absolute difference between open and close)
    in a given window.

    Args:
        window_df: A DataFrame representing the window of candles to search.

    Returns:
        The candle (as a Series) with the biggest body size.
    """
    body_sizes = (window_df['close'] - window_df['open']).abs()
    biggest_body_idx = body_sizes.idxmax()
    return window_df.loc[biggest_body_idx]

def validate_volume_ratio(large_volume_candle: pd.Series, small_volume_candle: pd.Series, min_volume_multiplier: float) -> tuple[bool, float]:
    """
    Validates if the volume of a larger candle is greater than or equal to a multiplier
    of a smaller candle's volume.

    Args:
        large_volume_candle: The candle expected to have the larger volume.
        small_volume_candle: The candle expected to have the smaller volume.
        min_volume_multiplier: The multiplier to use for the comparison.

    Returns:
        A tuple containing:
        - bool: True if the validation passes, False otherwise.
        - float: The calculated volume ratio.
    """
    if small_volume_candle['volume'] == 0:
        # If the small candle's volume is 0, the ratio is infinite if the large candle's volume is > 0.
        # We can consider the validation passed if the large volume is also 0, otherwise it's infinitely larger.
        # The ratio is effectively infinite, so we can return a large number or handle as a special case.
        # Let's return 0.0 for the ratio to avoid division by zero, and the status will depend on the logic.
        # If large_volume_candle['volume'] is also 0, then ratio is undefined, let's say 1.0 and status is True if min_volume_multiplier <= 1
        # If large_volume_candle['volume'] > 0, ratio is infinite, so status is True.
        if large_volume_candle['volume'] > 0:
            return True, float('inf')
        else:
            return True, 1.0  # Or handle as per specific requirements for 0/0

    ratio = large_volume_candle['volume'] / small_volume_candle['volume']
    status = ratio >= min_volume_multiplier
    return status, ratio

def is_green_candle(candle: pd.Series) -> bool:
    """
    Checks if a candle is green (bullish).

    Args:
        candle: The candle to check.

    Returns:
        True if the close price is greater than the open price, False otherwise.
    """
    return candle['close'] > candle['open']

def is_red_candle(candle: pd.Series) -> bool:
    """
    Checks if a candle is red (bearish).

    Args:
        candle: The candle to check.

    Returns:
        True if the close price is less than the open price, False otherwise.
    """
    return candle['close'] < candle['open']

def is_body_bigger_than_min(candle: pd.Series, min_body_size: float) -> tuple[bool, float]:
    """
    Validates if a candle's body size is bigger than a minimum requirement.

    Args:
        candle: The candle to check.
        min_body_size: The minimum required body size.

    Returns:
        A tuple containing:
        - bool: True if the candle's body size is greater than or equal to the minimum, False otherwise.
        - float: The calculated body size.
    """
    body_size = abs(candle['close'] - candle['open'])
    status = body_size >= min_body_size
    return status, body_size

def is_body_smaller_than_max(candle: pd.Series, max_body_size: float) -> bool:
    """
    Validates if a candle's body size is within a maximum limit.

    Args:
        candle: The candle to check.
        max_body_size: The maximum allowed body size.

    Returns:
        True if the candle's body size is less than or equal to the maximum, False otherwise.
    """
    return abs(candle['close'] - candle['open']) <= max_body_size

def get_first_candle(window_data: pd.DataFrame) -> Optional[pd.Series]:
    """
    Gets the very first candle from the window data.

    Args:
        window_data: The window data.

    Returns:
        The first candle as a Series, or None if the window is empty.
    """
    if not window_data.empty:
        return window_data.iloc[0]
    return None

def get_last_candle(window_data: pd.DataFrame) -> Optional[pd.Series]:
    """
    Gets the very last candle from the window data.

    Args:
        window_data: The window data.

    Returns:
        The last candle as a Series, or None if the window is empty.
    """
    if not window_data.empty:
        return window_data.iloc[-1]
    return None

def create_consolidated_candle(candles: pd.DataFrame) -> Optional[pd.Series]:
    """
    Creates a virtual 'consolidated' candle from a DataFrame of multiple candles.

    The consolidated candle has:
    - open/close: The min and max of all open/close prices.
    - high: The highest high.
    - low: The lowest low.
    - volume: The average volume.

    Args:
        candles: A DataFrame of candles to consolidate.

    Returns:
        A pd.Series representing the consolidated candle, or None if input is empty.
    """
    if candles.empty:
        return None

    open_close_prices = pd.concat([candles['open'], candles['close']])
    
    consolidated_open = open_close_prices.min()
    consolidated_close = open_close_prices.max()
    
    consolidated_high = candles['high'].max()
    consolidated_low = candles['low'].min()
    
    # Use sum of volume as requested for data consistency
    consolidated_volume = candles['volume'].sum()

    # The timestamp of the last candle is used for context
    last_time = candles.iloc[-1]['time']

    return pd.Series({
        'time': last_time,
        'open': consolidated_open,
        'high': consolidated_high,
        'low': consolidated_low,
        'close': consolidated_close,
        'volume': consolidated_volume
    })

def is_first_candle_in_window(candle: pd.Series, window_data: pd.DataFrame) -> bool:
    """
    Checks if a given candle is the very first candle in the window.

    Args:
        candle: The candle to check.
        window_data: The window data.

    Returns:
        True if the candle is the first in the window, False otherwise.
    """
    if window_data.empty:
        return False
    first_candle = get_first_candle(window_data)
    return first_candle is not None and candle.name == first_candle.name

def is_last_candle_in_window(candle: pd.Series, window_data: pd.DataFrame) -> bool:
    """
    Checks if a given candle is the very last candle in the window.

    Args:
        candle: The candle to check.
        window_data: The window data.

    Returns:
        True if the candle is the last in the window, False otherwise.
    """
    if window_data.empty:
        return False
    last_candle = get_last_candle(window_data)
    return last_candle is not None and candle.name == last_candle.name

def is_body_ratio_bigger_than_min(candle: pd.Series, min_body_ratio: float) -> tuple[bool, float]:
    """
    Validates if the ratio of a candle's body to its entire range meets a minimum requirement.

    Args:
        candle: The candle to check.
        min_body_ratio: The minimum required ratio (0.0 to 1.0).

    Returns:
        A tuple containing:
        - bool: True if the body ratio is greater than or equal to the minimum, False otherwise.
        - float: The calculated body ratio.
    """
    body_size = abs(candle['close'] - candle['open'])
    entire_range = candle['high'] - candle['low']

    if entire_range == 0:
        ratio = 0.0 if body_size == 0 else float('inf')
        status = ratio >= min_body_ratio
        return status, ratio

    ratio = body_size / entire_range
    status = ratio >= min_body_ratio
    return status, ratio

def is_body_ratio_smaller_than_max(candle: pd.Series, max_body_ratio: float) -> bool:
    """
    Validates if the ratio of a candle's body to its entire range is within a maximum limit.

    Args:
        candle: The candle to check.
        max_body_ratio: The maximum allowed ratio (0.0 to 1.0).

    Returns:
        True if the body ratio is less than or equal to the maximum, False otherwise.
    """
    body_size = abs(candle['close'] - candle['open'])
    entire_range = candle['high'] - candle['low']

    if entire_range == 0:
        return True # If range is 0, ratio is effectively 0, which is <= max_body_ratio

    return (body_size / entire_range) <= max_body_ratio

def is_upper_wick_bigger_than_min(candle: pd.Series, min_size: float) -> bool:
    """
    Validates if a candle's upper wick is bigger than a minimum requirement.

    Args:
        candle: The candle to check.
        min_size: The minimum required size for the upper wick.

    Returns:
        True if the upper wick is greater than or equal to the minimum size, False otherwise.
    """
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    return upper_wick >= min_size

def is_upper_wick_smaller_than_max(candle: pd.Series, max_size: float) -> bool:
    """
    Validates if a candle's upper wick is smaller than a maximum limit.

    Args:
        candle: The candle to check.
        max_size: The maximum allowed size for the upper wick.

    Returns:
        True if the upper wick is less than or equal to the maximum size, False otherwise.
    """
    upper_wick = candle['high'] - max(candle['open'], candle['close'])
    return upper_wick <= max_size

def is_lower_wick_bigger_than_min(candle: pd.Series, min_size: float) -> bool:
    """
    Validates if a candle's lower wick is bigger than a minimum requirement.

    Args:
        candle: The candle to check.
        min_size: The minimum required size for the lower wick.

    Returns:
        True if the lower wick is greater than or equal to the minimum size, False otherwise.
    """
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    return lower_wick >= min_size

def is_lower_wick_smaller_than_max(candle: pd.Series, max_size: float) -> bool:
    """
    Validates if a candle's lower wick is smaller than a maximum limit.

    Args:
        candle: The candle to check.
        max_size: The maximum allowed size for the lower wick.

    Returns:
        True if the lower wick is less than or equal to the maximum size, False otherwise.
    """
    lower_wick = min(candle['open'], candle['close']) - candle['low']
    return lower_wick <= max_size
