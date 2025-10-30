# src/stockreports/alert/common/volume.py
import pandas as pd

from src.stockreports.config import loader
signal_settings = loader.get_signal_settings()

def can_apply_volume_confirmation(df: pd.DataFrame) -> bool:
    """
    Checks if the DataFrame has enough data to apply volume confirmation.
    If a fixed lookback period is set, ensures the DataFrame is at least that large.
    
    Args:
        df (pd.DataFrame): The input dataframe.
        
    Returns:
        bool: True if volume confirmation can be applied, False otherwise.
    """
    volume_period = signal_settings.SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD
    if volume_period is not None:
        return len(df) >= volume_period
    # If period is None, we calculate from start of day, so any data is fine.
    return True

def is_volume_spike_confirmed(df: pd.DataFrame, break_index: int) -> bool:
    """
    Checks if a specific candle's volume represents a significant spike
    compared to a baseline average.

    The baseline can be a fixed lookback period or the average from the
    start of the trading day, based on global signal settings.

    Args:
        df: The full DataFrame of candle data.
        break_index: The index of the candle to check for a volume spike.

    Returns:
        True if the volume spike meets the required criteria. False otherwise.
    """
    volume_period = signal_settings.SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD
    volume_multiplier = signal_settings.SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER
    
    break_candle = df.iloc[break_index]
    break_candle_time = break_candle['time']

    if volume_period is None:
        # New logic: Calculate average from the start of the day up to the break candle.
        start_of_day = break_candle_time.normalize()
        
        # Filter for candles from the start of the day until just before the break candle.
        volume_window = df[
            (df['time'] >= start_of_day) & 
            (df['time'] < break_candle_time)
        ]
    else:
        # Original logic: Use a fixed lookback period.
        # This check is now primarily handled by can_apply_volume_confirmation,
        # but kept as a safeguard.
        if break_index < volume_period:
            return False
        volume_window = df.iloc[max(0, break_index - volume_period):break_index]

    if volume_window.empty or volume_window['volume'].mean() == 0:
        return False

    average_volume = volume_window['volume'].mean()
    break_volume = break_candle['volume']
    
    return break_volume >= average_volume * volume_multiplier

def is_volume_increasing(df: pd.DataFrame) -> bool:
    """
    Checks if the volume is monotonically increasing throughout the given window.

    Args:
        df: The DataFrame window to check.

    Returns:
        True if the volume is strictly increasing, False otherwise.
    """
    return df['volume'].is_monotonic_increasing
