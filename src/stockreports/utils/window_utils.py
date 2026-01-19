import pandas as pd
from scipy.signal import find_peaks
from typing import Optional, List, Tuple
from src.stockreports.alert.common.constants import Trend
from src.stockreports.utils.candle_utils import get_first_candle, get_last_candle

def get_window_by_trend(window_data: pd.DataFrame, expected_trend: Trend) -> pd.DataFrame:
    """
    Filters a window of candles to find those matching a specific trend.

    Args:
        window_data: The DataFrame containing the candle data.
        expected_trend: The trend to filter by (Trend.UPTREND or Trend.DOWNTREND).

    Returns:
        A new DataFrame containing only the candles that match the expected trend.
    """
    if expected_trend == Trend.UPTREND:
        return window_data[window_data['close'] > window_data['open']]
    elif expected_trend == Trend.DOWNTREND:
        return window_data[window_data['close'] < window_data['open']]
    
    return pd.DataFrame()

def get_trend(window_data: pd.DataFrame) -> Optional[Trend]:
    """
    Determines the overall trend of a window based on its first and last candles.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        Trend.UPTREND if the last close is higher than the first open,
        Trend.DOWNTREND if not. Returns None for empty or single-candle windows.
    """
    first_candle = get_first_candle(window_data)
    last_candle = get_last_candle(window_data)

    if first_candle is None or last_candle is None or first_candle.name == last_candle.name:
        return None

    if last_candle['close'] > first_candle['open']:
        return Trend.UPTREND
    else:
        return Trend.DOWNTREND

def get_highest_peak(window_data: pd.DataFrame) -> Optional[Tuple[pd.Series, float]]:
    """
    Finds the highest peak in the window data based on the 'high' prices.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        A tuple containing the highest peak candle (pd.Series) and its prominence (float),
        or None if no peaks are found.
    """
    peaks_indices, properties = find_peaks(window_data['high'], prominence=1)
    
    if len(peaks_indices) == 0:
        return None

    # Get all peak candles and their prominences
    all_peaks = window_data.iloc[peaks_indices]
    all_prominences = properties['prominences']

    # Find the index of the peak with the maximum 'high' value
    highest_peak_idx_in_all_peaks = all_peaks['high'].idxmax()
    
    # Get the candle
    peak_candle = all_peaks.loc[highest_peak_idx_in_all_peaks]
    
    # Find the original index to get the correct prominence
    original_peak_index = all_peaks.index.get_loc(highest_peak_idx_in_all_peaks)
    prominence = all_prominences[original_peak_index]
    
    return peak_candle, prominence

def get_lowest_trough(window_data: pd.DataFrame) -> Optional[Tuple[pd.Series, float]]:
    """
    Finds the lowest trough in the window data based on the 'low' prices.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        A tuple containing the lowest trough candle (pd.Series) and its prominence (float),
        or None if no troughs are found.
    """
    # Find troughs by finding peaks in the inverted 'low' series
    troughs_indices, properties = find_peaks(-window_data['low'], prominence=1)
    
    if len(troughs_indices) == 0:
        return None

    # Get all trough candles and their prominences
    all_troughs = window_data.iloc[troughs_indices]
    all_prominences = properties['prominences']

    # Find the index of the trough with the minimum 'low' value
    lowest_trough_idx_in_all_troughs = all_troughs['low'].idxmin()

    # Get the candle
    trough_candle = all_troughs.loc[lowest_trough_idx_in_all_troughs]

    # Find the original index to get the correct prominence
    original_trough_index = all_troughs.index.get_loc(lowest_trough_idx_in_all_troughs)
    prominence = all_prominences[original_trough_index]
    
    return trough_candle, prominence

def get_list_of_peaks(window_data: pd.DataFrame) -> List[Tuple[pd.Series, float]]:
    """
    Finds all peaks in the window data based on the 'high' prices.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        A list of tuples, where each tuple contains a peak candle (pd.Series) 
        and its prominence (float). Returns an empty list if no peaks are found.
    """
    peaks_indices, properties = find_peaks(window_data['high'], prominence=1)
    
    if len(peaks_indices) == 0:
        return []

    result = []
    for i, peak_idx in enumerate(peaks_indices):
        peak_candle = window_data.iloc[peak_idx]
        prominence = properties['prominences'][i]
        result.append((peak_candle, prominence))
        
    return result

def get_list_of_troughs(window_data: pd.DataFrame) -> List[Tuple[pd.Series, float]]:
    """
    Finds all troughs in the window data based on the 'low' prices.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        A list of tuples, where each tuple contains a trough candle (pd.Series) 
        and its prominence (float). Returns an empty list if no troughs are found.
    """
    troughs_indices, properties = find_peaks(-window_data['low'], prominence=1)
    
    if len(troughs_indices) == 0:
        return []

    result = []
    for i, trough_idx in enumerate(troughs_indices):
        trough_candle = window_data.iloc[trough_idx]
        prominence = properties['prominences'][i]
        result.append((trough_candle, prominence))
        
    return result

def get_window_size_and_trend(window_data: pd.DataFrame) -> Tuple[float, Optional[Trend]]:
    """
    Calculates the absolute size and trend of a window.

    The size is determined by the difference between the close price of the last candle
    and the open price of the first candle.

    Args:
        window_data: The DataFrame containing the candle data.

    Returns:
        A tuple containing the calculated size (float) and the trend (Trend object or None).
        Returns (0, None) if the window has fewer than two candles.
    """
    first_candle = get_first_candle(window_data)
    last_candle = get_last_candle(window_data)

    if first_candle is None or last_candle is None or first_candle.name == last_candle.name:
        return 0, None

    size = last_candle['close'] - first_candle['open']
    
    trend = None
    if size > 0:
        trend = Trend.UPTREND
    elif size < 0:
        trend = Trend.DOWNTREND
        
    return size, trend
