import pandas as pd
from src.stockreports.config import signal_settings

def prepare_indicators(df):
    """Prepares the DataFrame with all necessary technical indicators."""
    # MA Cross
    df['ma_short'] = df['close'].rolling(window=signal_settings.MA_SHORT_PERIOD).mean()
    df['ma_long'] = df['close'].rolling(window=signal_settings.MA_LONG_PERIOD).mean()
    
    # Ichimoku
    high_9 = df['high'].rolling(window=9).max()
    low_9 = df['low'].rolling(window=9).min()
    df['tenkan_sen'] = (high_9 + low_9) / 2
    high_26 = df['high'].rolling(window=26).max()
    low_26 = df['low'].rolling(window=26).min()
    df['kijun_sen'] = (high_26 + low_26) / 2

    # Strong Candle
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df.apply(lambda row: max(row['open'], row['close']), axis=1)
    df['lower_wick'] = df.apply(lambda row: min(row['open'], row['close']), axis=1) - df['low']
    
    return df

def check_advanced_confirmation(candle, prev_candle):
    """Checks for MA Cross, Ichimoku Cross, or Strong Candle signals."""
    # Bullish Signals
    ma_cross_up = candle['ma_short'] > candle['ma_long'] and prev_candle['ma_short'] < prev_candle['ma_long']
    ichi_cross_up = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] < prev_candle['kijun_sen']
    strong_bullish_candle = (
        candle['close'] > candle['open'] and
        candle['upper_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
    )
    if ma_cross_up or ichi_cross_up or strong_bullish_candle:
        return 'BUY'

    # Bearish Signals
    ma_cross_down = candle['ma_short'] < candle['ma_long'] and prev_candle['ma_short'] > prev_candle['ma_long']
    ichi_cross_down = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] > prev_candle['kijun_sen']
    strong_bearish_candle = (
        candle['close'] < candle['open'] and
        candle['lower_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
    )
    if ma_cross_down or ichi_cross_down or strong_bearish_candle:
        return 'SELL'
        
    return None
