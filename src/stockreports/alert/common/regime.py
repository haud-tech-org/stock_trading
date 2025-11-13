import pandas as pd
import ta
from scipy.signal import find_peaks

def has_divergence(df: pd.DataFrame, current_index: int, signal: str, config: dict) -> bool:
    """
    Checks for bearish or bullish divergence between price and RSI using peak/trough analysis.
    """
    lookback_period = config.get("DIVERGENCE_LOOKBACK_PERIOD", 30)
    
    if current_index < lookback_period:
        return False

    # Ensure 'rsi' column exists
    if 'rsi' not in df.columns:
        return False

    lookback_slice = df.iloc[current_index - lookback_period : current_index + 1]
    
    price_prominence = config.get("DIVERGENCE_PRICE_PROMINENCE", 0.1)
    rsi_prominence = config.get("DIVERGENCE_RSI_PROMINENCE", 1.0)

    if signal == 'SELL':  # Check for Bearish Divergence
        # Find peaks in high prices and RSI
        price_peaks, _ = find_peaks(lookback_slice['high'], prominence=price_prominence)
        rsi_peaks, _ = find_peaks(lookback_slice['rsi'], prominence=rsi_prominence)

        # We need at least two peaks to compare for divergence
        if len(price_peaks) < 2 or len(rsi_peaks) < 2:
            return False

        # Get the last two price peaks
        last_price_peak_idx = price_peaks[-1]
        prev_price_peak_idx = price_peaks[-2]

        # Check for higher high in price
        if lookback_slice['high'].iloc[last_price_peak_idx] > lookback_slice['high'].iloc[prev_price_peak_idx]:
            # Find corresponding RSI peaks
            corresponding_rsi_peaks = [p for p in rsi_peaks if abs(p - last_price_peak_idx) < 5 or abs(p - prev_price_peak_idx) < 5]
            if len(corresponding_rsi_peaks) < 2:
                return False
            
            last_rsi_peak_val = lookback_slice['rsi'].iloc[corresponding_rsi_peaks[-1]]
            prev_rsi_peak_val = lookback_slice['rsi'].iloc[corresponding_rsi_peaks[-2]]

            # Check for lower high in RSI
            if last_rsi_peak_val < prev_rsi_peak_val:
                return True  # Bearish divergence detected

    elif signal == 'BUY':  # Check for Bullish Divergence
        # Find troughs in low prices and RSI (by inverting the series)
        price_troughs, _ = find_peaks(-lookback_slice['low'], prominence=price_prominence)
        rsi_troughs, _ = find_peaks(-lookback_slice['rsi'], prominence=rsi_prominence)

        if len(price_troughs) < 2 or len(rsi_troughs) < 2:
            return False

        last_price_trough_idx = price_troughs[-1]
        prev_price_trough_idx = price_troughs[-2]

        if lookback_slice['low'].iloc[last_price_trough_idx] < lookback_slice['low'].iloc[prev_price_trough_idx]:
            corresponding_rsi_troughs = [t for t in rsi_troughs if abs(t - last_price_trough_idx) < 5 or abs(t - prev_price_trough_idx) < 5]
            if len(corresponding_rsi_troughs) < 2:
                return False

            last_rsi_trough_val = lookback_slice['rsi'].iloc[corresponding_rsi_troughs[-1]]
            prev_rsi_trough_val = lookback_slice['rsi'].iloc[corresponding_rsi_troughs[-2]]
            
            if last_rsi_trough_val > prev_rsi_trough_val:
                return True  # Bullish divergence detected

    return False
