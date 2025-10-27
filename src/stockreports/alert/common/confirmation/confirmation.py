import pandas as pd
# import pandas_ta as ta # No longer needed, will implement indicators manually

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
    # The Ichimoku spans are shifted forward, so their total lookback requirement
    # is the span's calculation period plus the shift period.
    kijun_period = getattr(signal_settings, 'KIJUN_PERIOD', 26)
    senkou_b_period = getattr(signal_settings, 'ICHI_SENKOU_B_PERIOD', 52)
    ichimoku_total_lookback = kijun_period + senkou_b_period

    return max(
        ichimoku_total_lookback,
        getattr(signal_settings, 'MA_LONG_PERIOD', 50),
        getattr(signal_settings, 'RSI_PERIOD', 14),
        getattr(signal_settings, 'MACD_SLOW_PERIOD', 26),
        getattr(signal_settings, 'ADX_PERIOD', 14) * 2 # ADX needs more data to stabilize, 2x period is a safe rule of thumb
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

# --- Manual Indicator Implementations ---

def _calculate_rsi(close: pd.Series, length: int) -> pd.Series:
    """Calculates Relative Strength Index (RSI) manually."""
    delta = close.diff()
    gain = delta.where(delta > 0, 0).fillna(0)
    loss = -delta.where(delta < 0, 0).fillna(0)

    avg_gain = gain.ewm(com=length - 1, min_periods=length).mean()
    avg_loss = loss.ewm(com=length - 1, min_periods=length).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def _calculate_macd(close: pd.Series, fast: int, slow: int, signal: int) -> pd.DataFrame:
    """Calculates Moving Average Convergence Divergence (MACD) manually."""
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line
    
    return pd.DataFrame({
        f'MACD_{fast}_{slow}_{signal}': macd_line,
        f'MACDs_{fast}_{slow}_{signal}': signal_line,
        f'MACDh_{fast}_{slow}_{signal}': macd_hist
    })

def _calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, length: int) -> pd.DataFrame:
    """Calculates the Average Directional Index (ADX) manually."""
    plus_dm = high.diff()
    minus_dm = low.diff()
    
    plus_dm[plus_dm < 0] = 0
    minus_dm[minus_dm > 0] = 0
    
    tr1 = pd.DataFrame(high - low)
    tr2 = pd.DataFrame(abs(high - close.shift(1)))
    tr3 = pd.DataFrame(abs(low - close.shift(1)))
    frames = [tr1, tr2, tr3]
    tr = pd.concat(frames, axis=1, join='inner').max(axis=1)
    atr = tr.ewm(com=length, min_periods=length).mean()
    
    plus_di = 100 * (plus_dm.ewm(com=length, min_periods=length).mean() / atr)
    minus_di = 100 * (abs(minus_dm.ewm(com=length, min_periods=length).mean()) / atr)
    
    dx = (abs(plus_di - minus_di) / abs(plus_di + minus_di)) * 100
    adx = dx.ewm(com=length, min_periods=length).mean()
    
    return pd.DataFrame({f'ADX_{length}': adx})

def prepare_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares the DataFrame by adding various technical indicators.
    """
    # --- Moving Averages ---
    df['ma_short'] = df['close'].rolling(window=signal_settings.MA_SHORT_PERIOD).mean()
    df['ma_long'] = df['close'].rolling(window=signal_settings.MA_LONG_PERIOD).mean()

    # --- Ichimoku Cloud ---
    high_tenkan = df['high'].rolling(window=signal_settings.TENKAN_PERIOD).max()
    low_tenkan = df['low'].rolling(window=signal_settings.TENKAN_PERIOD).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

    high_kijun = df['high'].rolling(window=signal_settings.KIJUN_PERIOD).max()
    low_kijun = df['low'].rolling(window=signal_settings.KIJUN_PERIOD).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2

    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(signal_settings.KIJUN_PERIOD)
    
    high_senkou_b = df['high'].rolling(window=signal_settings.ICHI_SENKOU_B_PERIOD).max()
    low_senkou_b = df['low'].rolling(window=signal_settings.ICHI_SENKOU_B_PERIOD).min()
    df['senkou_span_b'] = ((high_senkou_b + low_senkou_b) / 2).shift(signal_settings.KIJUN_PERIOD)

    # --- RSI (Manual) ---
    df['rsi'] = _calculate_rsi(df['close'], length=getattr(signal_settings, 'RSI_PERIOD', 14))

    # --- MACD (Manual) ---
    fast = getattr(signal_settings, 'MACD_FAST_PERIOD', 12)
    slow = getattr(signal_settings, 'MACD_SLOW_PERIOD', 26)
    signal = getattr(signal_settings, 'MACD_SIGNAL_PERIOD', 9)
    macd = _calculate_macd(df['close'], fast=fast, slow=slow, signal=signal)
    if macd is not None and not macd.empty:
        df['macd'] = macd[f'MACD_{fast}_{slow}_{signal}']
        df['macdsignal'] = macd[f'MACDs_{fast}_{slow}_{signal}']
        df['macdhist'] = macd[f'MACDh_{fast}_{slow}_{signal}']

    # --- ADX (Manual) ---
    adx_period = getattr(signal_settings, 'ADX_PERIOD', 14)
    adx = _calculate_adx(df['high'], df['low'], df['close'], length=adx_period)
    if adx is not None and not adx.empty:
        df['adx'] = adx[f'ADX_{adx_period}']

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
        current_candle['rsi'] > signal_settings.RSI_BULLISH_THRESHOLD and
        # MACD is showing bullish momentum (MACD line is above signal line)
        current_candle['macd'] > current_candle['macdsignal'] and
        # Trend is strong enough to be actionable
        current_candle['adx'] > signal_settings.ADX_CONFIRMATION_THRESHOLD
    )
    if is_bullish_confirmed:
        return 'BUY'

    # --- Bearish Confirmation ---
    is_bearish_confirmed = (
        # Price is below the long-term moving average
        current_candle['close'] < current_candle['ma_long'] and
        # RSI is in a bearish regime
        current_candle['rsi'] < signal_settings.RSI_BEARISH_THRESHOLD and
        # MACD is showing bearish momentum
        current_candle['macd'] < current_candle['macdsignal'] and
        # Trend is strong enough
        current_candle['adx'] > signal_settings.ADX_CONFIRMATION_THRESHOLD
    )
    if is_bearish_confirmed:
        return 'SELL'

    return 'NEUTRAL'
