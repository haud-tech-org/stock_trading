import pandas as pd
import logging
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader
from src.stockreports.config.signal_settings import APPROACH_CONFIG
from typing import Optional, Tuple
from scipy.signal import find_peaks
from .constants import PeakTrough, PriceColumn

signal_settings = loader.get_signal_settings()


def get_min_data_for_indicator_confirmation(approach_name: str) -> int:
    """
    Calculates and returns the minimum number of data points required for
    the specific confirmation indicators enabled for a given approach.

    Args:
        approach_name (str): The name of the approach (e.g., 'CONSOLIDATION_BREAKOUT').

    Returns:
        int: The maximum lookback period required among all enabled indicators for the approach.
    """
    config = APPROACH_CONFIG.get(approach_name, APPROACH_CONFIG["default"])
    required_periods = [1]  # Default to 1 to avoid errors with max() on an empty list

    # --- Ichimoku Cloud ---
    # Only calculate Ichimoku requirements if the approach explicitly uses it.
    if config.get("USE_ICHIMOKU_CONFIRMATION", False) or approach_name == Approach.ICHIMOKU:
        kijun_period = getattr(signal_settings, 'KIJUN_PERIOD', 26)
        senkou_b_period = getattr(signal_settings, 'ICHI_SENKOU_B_PERIOD', 52)
        # The total lookback is the calculation period of the longest span (Senkou B)
        # plus the amount it's shifted forward (Kijun period).
        ichimoku_total_lookback = senkou_b_period + kijun_period
        required_periods.append(ichimoku_total_lookback)

    # --- Standard Indicator Checks ---
    if config.get("USE_SHORT_TERM_MA_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MA_SHORT_PERIOD', 5))

    if config.get("USE_MA_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MA_LONG_PERIOD', 10))

    if config.get("USE_LONG_TERM_MA_FILTER", False):
        required_periods.append(getattr(signal_settings, 'MA_LONG_TERM_PERIOD', 50))

    if config.get("USE_RSI_CONFIRMATION", False) or config.get("USE_RSI_EXHAUSTION_FILTER", False):
        required_periods.append(getattr(signal_settings, 'RSI_PERIOD', 14))

    if config.get("USE_MACD_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MACD_SLOW_PERIOD', 26))

    if config.get("USE_ADX_CONFIRMATION", False) or config.get("USE_ADX_FILTER", False):
        # ADX needs more data to stabilize; 2x the period is a safe rule of thumb.
        required_periods.append(getattr(signal_settings, 'ADX_PERIOD', 14) * 2)
    
    if config.get("USE_BB_WIDTH_FILTER", False):
        required_periods.append(getattr(signal_settings, 'BBANDS_PERIOD', 20))

    return max(required_periods)


def can_apply_analysis(df: pd.DataFrame, approach_name: str, required_rows: int = 0) -> bool:
    """
    Checks if the dataframe has enough data to apply the analysis for a given approach.
    It considers both the requirements for technical indicators and any specific
    row count needed by the calling logic (e.g., a pattern window size).
    """
    # 1. Check for indicator confirmation data requirements
    min_indicator_len = get_min_data_for_indicator_confirmation(approach_name)

    # 2. Determine the overall minimum required length
    # This will be the larger of the indicator requirement or the specific row requirement
    min_len = max(min_indicator_len, required_rows)

    if len(df) < min_len:
        symbol = df.iloc[0]['symbol'] if 'symbol' in df.columns and not df.empty else 'N/A'
        logging.warning(
            f"Skipping '{approach_name}' for {symbol}: requires {min_len} candles, "
            f"but only {len(df)} are available. (Indicator requirement: {min_indicator_len}, "
            f"Pattern requirement: {required_rows})"
        )
        return False
    return True


def find_extreme_point(
    df: pd.DataFrame,
    price_column: PriceColumn,
    extreme_type: PeakTrough,
    prominence: float
) -> Optional[Tuple[float, pd.Timestamp]]:
    """
    Finds the most extreme peak or trough in a given DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to search. Must have a datetime index.
        price_column (PriceColumn): The enum member for the column to analyze (e.g., PriceColumn.CLOSE).
        extreme_type (PeakTrough): The enum member for the type of extreme point (PeakTrough.PEAK or PeakTrough.TROUGH).
        prominence (float): The prominence required for a peak/trough to be detected.

    Returns:
        Optional[Tuple[float, pd.Timestamp]]: A tuple of (price, timestamp) of the most extreme point, or None if not found.
    """
    if df.empty or price_column not in df.columns:
        return None

    points, _ = find_peaks(df[price_column] if extreme_type == PeakTrough.PEAK else -df[price_column], prominence=prominence)

    if points.size == 0:
        return None

    if extreme_type == PeakTrough.PEAK:
        # Find the index of the maximum value among the detected peaks
        extreme_point_index = df.iloc[points][price_column].idxmax()
    else: # TROUGH
        # Find the index of the minimum value among the detected troughs
        extreme_point_index = df.iloc[points][price_column].idxmin()

    extreme_price = df.loc[extreme_point_index, price_column]
    
    # The index of a DataFrame slice is a pd.Timestamp
    return extreme_price, extreme_point_index


def find_nearest_extreme_point(
    df: pd.DataFrame,
    price_column: PriceColumn,
    extreme_type: PeakTrough,
    prominence: float
) -> Optional[Tuple[float, pd.Timestamp]]:
    """
    Finds the nearest (most recent) peak or trough in a given DataFrame.

    Args:
        df (pd.DataFrame): The DataFrame to search. Must have a datetime index.
        price_column (str): The column to search ('high', 'low', 'close').
        extreme_type (str): 'peak' or 'trough'.
        prominence (float): The prominence required for a peak/trough to be detected.

    Returns:
        Optional[Tuple[float, pd.Timestamp]]: A tuple of (price, timestamp) of the nearest point, or None if not found.
    """
    if df.empty or price_column not in df.columns:
        return None

    series = df[price_column]
    
    if extreme_type == PeakTrough.PEAK:
        points, _ = find_peaks(series, prominence=prominence)
    elif extreme_type == PeakTrough.TROUGH:
        points, _ = find_peaks(-series, prominence=prominence)
    else:
        return None

    if points.size == 0:
        return None

    # The nearest point is the one with the largest index (most recent)
    nearest_point_iloc = points[-1]
    nearest_point_index = series.index[nearest_point_iloc]
    nearest_price = series.loc[nearest_point_index]
    
    return nearest_price, nearest_point_index
