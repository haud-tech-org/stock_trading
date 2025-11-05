import pandas as pd
import ta
from scipy.signal import find_peaks

def prepare_regime_indicators(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """
    Calculates and adds market regime indicators (MA, ADX) to the DataFrame.
    This function modifies the DataFrame in place.
    """
    ma_period = config.get("REGIME_MA_PERIOD", 50)
    adx_period = config.get("REGIME_ADX_PERIOD", 14)
    
    # Ensure there is enough data to calculate the indicators
    if len(df) < ma_period or len(df) < adx_period:
        # Not enough data, return the original DataFrame without indicators
        return df

    # Calculate indicators only if they don't already exist
    if f'regime_ma' not in df.columns:
        df[f'regime_ma'] = ta.trend.sma_indicator(df['close'], window=ma_period)
    
    if 'adx' not in df.columns:
        adx_indicator = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=adx_period)
        df['adx'] = adx_indicator.adx()

    # --- Refactored: Calculate RSI once if needed for any filter ---
    if config.get("USE_RSI_EXHAUSTION_FILTER", False) or config.get("USE_DIVERGENCE_FILTER", False):
        # Prioritize divergence-specific period, then general RSI period, then default.
        rsi_period = config.get("DIVERGENCE_RSI_PERIOD", config.get("RSI_PERIOD", 14))
        if len(df) >= rsi_period and 'rsi' not in df.columns:
            df['rsi'] = ta.momentum.rsi(df['close'], window=rsi_period)

    # --- New: Calculate MACD if needed ---
    if config.get("USE_MACD_CONFIRMATION_FILTER", False):
        macd_fast = config.get("MACD_FAST_PERIOD", 12)
        macd_slow = config.get("MACD_SLOW_PERIOD", 26)
        macd_signal = config.get("MACD_SIGNAL_PERIOD", 9)
        
        # Ensure there is enough data
        if len(df) >= macd_slow and 'macd_line' not in df.columns:
            macd = ta.trend.MACD(close=df['close'], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
            df['macd_line'] = macd.macd()
            df['macd_signal_line'] = macd.macd_signal()

    return df

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

def is_regime_favorable(candle: pd.Series, signal: str, config: dict) -> bool:
    """
    Checks if the market regime is favorable for a given signal direction.
    
    Args:
        candle (pd.Series): The current candle being evaluated (must include regime indicators).
        signal (str): The potential signal direction ('BUY' or 'SELL').
        config (dict): The configuration for the specific approach.

    Returns:
        bool: True if the regime is favorable, False otherwise.
    """
    use_ma_filter = config.get("USE_MA_REGIME_FILTER", True)
    use_adx_filter = config.get("USE_ADX_REGIME_FILTER", True)
    adx_threshold = config.get("REGIME_ADX_THRESHOLD", 20)

    # --- New: RSI Exhaustion Filter ---
    use_rsi_filter = config.get("USE_RSI_EXHAUSTION_FILTER", False)
    if use_rsi_filter:
        rsi_oversold = config.get("RSI_OVERSOLD_THRESHOLD", 30)
        rsi_overbought = config.get("RSI_OVERBOUGHT_THRESHOLD", 70)
        
        if 'rsi' in candle and not pd.isna(candle['rsi']):
            # For a SELL signal, if RSI is overbought, the uptrend is likely exhausted. Do not sell.
            if signal == 'SELL' and candle['rsi'] > rsi_overbought:
                return False
            
            # For a BUY signal, if RSI is oversold, the downtrend is likely exhausted. Do not buy.
            if signal == 'BUY' and candle['rsi'] < rsi_oversold:
                return False

    # --- New: MACD Confirmation Filter ---
    use_macd_filter = config.get("USE_MACD_CONFIRMATION_FILTER", False)
    if use_macd_filter:
        if 'macd_line' in candle and 'macd_signal_line' in candle and \
           not pd.isna(candle['macd_line']) and not pd.isna(candle['macd_signal_line']):
            
            # For a BUY signal, MACD line must be above the signal line.
            if signal == 'BUY' and candle['macd_line'] < candle['macd_signal_line']:
                return False
            
            # For a SELL signal, MACD line must be below the signal line.
            if signal == 'SELL' and candle['macd_line'] > candle['macd_signal_line']:
                return False

    # ADX check: must be trending
    if use_adx_filter:
        if pd.isna(candle['adx']) or candle['adx'] < adx_threshold:
            return False # Market is not trending enough

    # MA check: must be on the right side of the long-term trend
    if use_ma_filter:
        if pd.isna(candle['regime_ma']):
            return False # MA is not available yet

        # For a BUY signal, price must be above the regime MA
        if signal == 'BUY' and candle['close'] < candle['regime_ma']:
            return False
        
        # For a SELL signal, price must be below the regime MA
        elif signal == 'SELL' and candle['close'] > candle['regime_ma']:
            return False
            
    return True
