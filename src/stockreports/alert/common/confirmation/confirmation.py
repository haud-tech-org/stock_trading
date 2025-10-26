import pandas as pd
import pandas_ta as ta

# --- Project Imports ---
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

def get_min_data_required_for_advanced_confirmation() -> int:
    """
    Calculates and returns the minimum number of data points required for
    all indicators used in the advanced confirmation logic.
    
    Returns:
        int: The maximum lookback period required among all indicators.
    """
    return max(
        getattr(signal_settings, 'TENKAN_SEN_PERIOD', 9),
        getattr(signal_settings, 'KIJUN_SEN_PERIOD', 26),
        getattr(signal_settings, 'SENKOU_SPAN_B_PERIOD', 52),
        getattr(signal_settings, 'MA_LONG_PERIOD', 50),
        getattr(signal_settings, 'RSI_PERIOD', 14),
        getattr(signal_settings, 'MACD_SLOW_PERIOD', 26),
        getattr(signal_settings, 'ADX_PERIOD', 14)
    )

def can_apply_advanced_confirmation(df: pd.DataFrame) -> bool:
    """
    Checks if the DataFrame has enough data to apply advanced confirmation.
    
    Args:
        df (pd.DataFrame): The input dataframe.
        
    Returns:
        bool: True if advanced confirmation can be applied, False otherwise.
    """
    min_data_required = get_min_data_required_for_advanced_confirmation()
    return len(df) >= min_data_required

def prepare_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares the DataFrame by adding various technical indicators.
    """
    # --- Moving Averages ---
    df['ma_short'] = df['close'].rolling(window=signal_settings.MA_SHORT_PERIOD).mean()
    df['ma_long'] = df['close'].rolling(window=signal_settings.MA_LONG_PERIOD).mean()

    # --- Ichimoku Cloud ---
    high_tenkan = df['high'].rolling(window=signal_settings.TENKAN_SEN_PERIOD).max()
    low_tenkan = df['low'].rolling(window=signal_settings.TENKAN_SEN_PERIOD).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

    high_kijun = df['high'].rolling(window=signal_settings.KIJUN_SEN_PERIOD).max()
    low_kijun = df['low'].rolling(window=signal_settings.KIJUN_SEN_PERIOD).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2

    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(signal_settings.KIJUN_SEN_PERIOD)
    
    high_senkou_b = df['high'].rolling(window=signal_settings.SENKOU_SPAN_B_PERIOD).max()
    low_senkou_b = df['low'].rolling(window=signal_settings.SENKOU_SPAN_B_PERIOD).min()
    df['senkou_span_b'] = ((high_senkou_b + low_senkou_b) / 2).shift(signal_settings.KIJUN_SEN_PERIOD)

    # --- RSI ---
    df['rsi'] = ta.rsi(df['close'], length=signal_settings.RSI_PERIOD)

    # --- MACD ---
    macd = ta.macd(df['close'], fast=signal_settings.MACD_FAST_PERIOD, slow=signal_settings.MACD_SLOW_PERIOD, signal=signal_settings.MACD_SIGNAL_PERIOD)
    if macd is not None and not macd.empty:
        df['macd'] = macd[f'MACD_{signal_settings.MACD_FAST_PERIOD}_{signal_settings.MACD_SLOW_PERIOD}_{signal_settings.MACD_SIGNAL_PERIOD}']
        df['macdsignal'] = macd[f'MACDs_{signal_settings.MACD_FAST_PERIOD}_{signal_settings.MACD_SLOW_PERIOD}_{signal_settings.MACD_SIGNAL_PERIOD}']
        df['macdhist'] = macd[f'MACDh_{signal_settings.MACD_FAST_PERIOD}_{signal_settings.MACD_SLOW_PERIOD}_{signal_settings.MACD_SIGNAL_PERIOD}']

    # --- ADX ---
    adx = ta.adx(df['high'], df['low'], df['close'], length=signal_settings.ADX_PERIOD)
    if adx is not None and not adx.empty:
        df['adx'] = adx[f'ADX_{signal_settings.ADX_PERIOD}']

    # --- Candle Properties ---
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df.apply(lambda row: max(row['open'], row['close']), axis=1)
    df['lower_wick'] = df.apply(lambda row: min(row['open'], row['close']), axis=1) - df['low']
    
    return df

def check_advanced_confirmation(current_candle: pd.Series, prev_candle: pd.Series) -> str:
    """
    Checks for advanced confirmation signals (e.g., RSI, MACD, ADX) to validate a primary signal.
    """
    # --- Bullish Confirmation ---
    is_bullish_confirmed = (
        # Price is above the long-term moving average
        current_candle['close'] > current_candle['ma_long'] and
        # RSI is in a bullish regime
        current_candle['rsi'] > 50 and
        # MACD is showing bullish momentum (MACD line is above signal line)
        current_candle['macd'] > current_candle['macdsignal'] and
        # Trend is strong enough to be actionable
        current_candle['adx'] > 25
    )
    if is_bullish_confirmed:
        return 'BUY'

    # --- Bearish Confirmation ---
    is_bearish_confirmed = (
        # Price is below the long-term moving average
        current_candle['close'] < current_candle['ma_long'] and
        # RSI is in a bearish regime
        current_candle['rsi'] < 50 and
        # MACD is showing bearish momentum
        current_candle['macd'] < current_candle['macdsignal'] and
        # Trend is strong enough
        current_candle['adx'] > 25
    )
    if is_bearish_confirmed:
        return 'SELL'

    return 'NEUTRAL'
