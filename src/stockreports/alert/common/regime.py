import pandas as pd
import ta

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
    
    return df

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
