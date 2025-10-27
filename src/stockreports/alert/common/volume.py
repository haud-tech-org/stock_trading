# src/stockreports/alert/common/volume.py
import pandas as pd

from src.stockreports.config import loader
signal_settings = loader.get_signal_settings()

def is_volume_spike_confirmed(df: pd.DataFrame, break_index: int, use_volume_confirmation: bool) -> bool:
    """
    Checks if a specific candle's volume represents a significant spike
    compared to a baseline average.

    The baseline can be a fixed lookback period or the average from the
    start of the trading day, based on global signal settings.

    Args:
        df: The full DataFrame of candle data.
        break_index: The index of the candle to check for a volume spike.
        use_volume_confirmation: A boolean flag to enable or disable the check.

    Returns:
        True if volume confirmation is disabled or if the volume spike
        meets the required criteria. False otherwise.
    """
    if not use_volume_confirmation:
        return True

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
        if break_index < volume_period:
            return False
        volume_window = df.iloc[max(0, break_index - volume_period):break_index]

    if volume_window.empty:
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
