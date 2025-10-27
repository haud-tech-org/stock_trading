import pandas as pd
import numpy as np

def is_bb_squeeze(df_window: pd.DataFrame, lookback: int, threshold_ratio: float) -> bool:
    """
    Detects a Bollinger Band Squeeze.

    A squeeze is identified when the current Bollinger Band Width is among the narrowest
    over a given lookback period.

    Args:
        df_window (pd.DataFrame): DataFrame window ending at the potential breakout candle. 
                                  Must contain 'bb_upper', 'bb_lower', and 'bb_middle' columns.
        lookback (int): The number of candles to look back to find the narrowest band width.
        threshold_ratio (float): A tolerance ratio. The current width must be less than 
                                 the historical minimum width * (1 + threshold_ratio) to be 
                                 considered a squeeze.

    Returns:
        bool: True if a Bollinger Band Squeeze is detected, False otherwise.
    """
    if not all(col in df_window.columns for col in ['bb_upper', 'bb_lower', 'bb_middle']):
        # If BBs aren't calculated, we can't check for a squeeze.
        # This can be treated as a non-squeeze condition.
        return False

    if len(df_window) < lookback:
        # Not enough data to determine a squeeze
        return False

    # Calculate Bollinger Band Width (BBW)
    df_window['bb_width'] = (df_window['bb_upper'] - df_window['bb_lower']) / df_window['bb_middle']

    # Lookback window for historical context, excluding the current candle
    historical_window = df_window.iloc[-lookback:-1]
    
    if historical_window.empty:
        return False

    # Find the lowest band width in the historical lookback period
    min_bb_width = historical_window['bb_width'].min()

    # Get the band width of the candle just before the potential breakout
    current_bb_width = df_window.iloc[-1]['bb_width']

    # The squeeze condition is met if the current width is near the historical low
    is_squeezing = current_bb_width <= min_bb_width * (1 + threshold_ratio)
    
    return is_squeezing
