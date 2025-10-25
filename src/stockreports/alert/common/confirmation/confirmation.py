import pandas as pd

from src.stockreports.config.signal_settings import (
    MA_LONG_PERIOD,
    MA_SHORT_PERIOD,
    TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO,
    TENKAN_PERIOD,
    KIJUN_PERIOD,
)

def prepare_indicators(df):
    """Prepares the DataFrame with all potential technical indicators."""
    # --- Indicator Calculations ---
    df['ma_short'] = df['close'].rolling(window=MA_SHORT_PERIOD).mean()
    df['ma_long'] = df['close'].rolling(window=MA_LONG_PERIOD).mean()

    high_tenkan = df['high'].rolling(window=TENKAN_PERIOD).max()
    low_tenkan = df['low'].rolling(window=TENKAN_PERIOD).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

    high_kijun = df['high'].rolling(window=KIJUN_PERIOD).max()
    low_kijun = df['low'].rolling(window=KIJUN_PERIOD).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2

    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df.apply(lambda row: max(row['open'], row['close']), axis=1)
    df['lower_wick'] = df.apply(lambda row: min(row['open'], row['close']), axis=1) - df['low']
    
    return df

def check_advanced_confirmation(candle, prev_candle):
    """
    Checks for a variety of advanced confirmation signals, such as MA Cross,
    Ichimoku Cross, or a Strong Candle, to determine a 'BUY' or 'SELL' signal.
    """
    # Bullish Signals
    ma_cross_up = candle['ma_short'] > candle['ma_long'] and prev_candle['ma_short'] < prev_candle['ma_long']
    ichi_cross_up = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] < prev_candle['kijun_sen']
    strong_bullish_candle = (
        candle['close'] > candle['open'] and
        candle['upper_wick'] < candle['body_size'] * TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
    )
    if ma_cross_up or ichi_cross_up or strong_bullish_candle:
        return 'BUY'

    # Bearish Signals
    ma_cross_down = candle['ma_short'] < candle['ma_long'] and prev_candle['ma_short'] > prev_candle['ma_long']
    ichi_cross_down = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] > prev_candle['kijun_sen']
    strong_bearish_candle = (
        candle['close'] < candle['open'] and
        candle['lower_wick'] < candle['body_size'] * TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
    )
    if ma_cross_down or ichi_cross_down or strong_bearish_candle:
        return 'SELL'
        
    return None
