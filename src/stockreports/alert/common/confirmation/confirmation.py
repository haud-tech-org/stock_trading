import pandas as pd
# import pandas_ta as ta # No longer needed, will implement indicators manually

# --- Project Imports ---
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

def get_min_data_for_indicator_confirmation() -> int:
    """
    Calculates and returns the minimum number of data points required for
    all indicators used in the indicator confirmation logic.
    
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

def can_apply_indicator_confirmation(df: pd.DataFrame) -> bool:
    """
    Checks if the DataFrame has enough data to apply indicator-based confirmation.
    
    Args:
        df (pd.DataFrame): The input dataframe.
        
    Returns:
        bool: True if indicator confirmation can be applied, False otherwise.
    """
    min_data_required = get_min_data_for_indicator_confirmation()
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
    
    return pd.DataFrame({
        f'adx': adx,
        f'dip': plus_di,
        f'din': minus_di
    })

def prepare_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepares the DataFrame by adding various technical indicators.
    """
    # --- Moving Averages ---
    df['ma_short'] = df['close'].rolling(window=signal_settings.MA_SHORT_PERIOD).mean()
    df['ma_long'] = df['close'].rolling(window=signal_settings.MA_LONG_PERIOD).mean()
    df['ma_long_term'] = df['close'].rolling(window=signal_settings.MA_LONG_TERM_PERIOD).mean()

    # --- Bollinger Bands ---
    bb_period = getattr(signal_settings, 'BBANDS_PERIOD', 20)
    bb_std = getattr(signal_settings, 'BBANDS_STDDEV', 2.0)
    df['bb_middle'] = df['close'].rolling(window=bb_period).mean()
    std_dev = df['close'].rolling(window=bb_period).std()
    df['bb_upper'] = df['bb_middle'] + (std_dev * bb_std)
    df['bb_lower'] = df['bb_middle'] - (std_dev * bb_std)
    df['bb_width'] = df['bb_upper'] - df['bb_lower']

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
    adx_df = _calculate_adx(df['high'], df['low'], df['close'], length=adx_period)
    if adx_df is not None and not adx_df.empty:
        df['adx'] = adx_df['adx']
        df['dip'] = adx_df['dip']
        df['din'] = adx_df['din']

    # --- Candle Properties ---
    df['body_size'] = abs(df['close'] - df['open'])
    df['upper_wick'] = df['high'] - df.apply(lambda row: max(row['open'], row['close']), axis=1)
    df['lower_wick'] = df.apply(lambda row: min(row['open'], row['close']), axis=1) - df['low']
    
    return df

# --- Individual Confirmation Functions ---

def _is_short_term_ma_confirmed(candle: pd.Series, signal: str) -> bool:
    """Checks if the price is on the correct side of the short-term moving average."""
    if signal == 'BUY':
        return candle['close'] > candle['ma_short']
    elif signal == 'SELL':
        return candle['close'] < candle['ma_short']
    return False

def _is_ma_confirmed(candle: pd.Series, signal: str) -> bool:
    """Checks if the price is on the correct side of the long-term moving average."""
    if signal == 'BUY':
        return candle['close'] > candle['ma_long']
    elif signal == 'SELL':
        return candle['close'] < candle['ma_long']
    return False

def _is_rsi_confirmed(candle: pd.Series, signal: str) -> bool:
    """Checks if the RSI is in a bullish or bearish regime."""
    if signal == 'BUY':
        return candle['rsi'] > signal_settings.RSI_BULLISH_THRESHOLD
    elif signal == 'SELL':
        return candle['rsi'] < signal_settings.RSI_BEARISH_THRESHOLD
    return False

def _is_macd_confirmed(candle: pd.Series, signal: str) -> bool:
    """Checks if the MACD indicates momentum in the signal's direction."""
    if signal == 'BUY':
        return candle['macd'] > candle['macdsignal']
    elif signal == 'SELL':
        return candle['macd'] < candle['macdsignal']
    return False

def _is_adx_confirmed(candle: pd.Series) -> bool:
    """Checks if the ADX indicates a strong trend."""
    return candle['adx'] > signal_settings.ADX_CONFIRMATION_THRESHOLD

def _is_long_term_ma_confirmed(candle: pd.Series, signal: str) -> bool:
    """Checks if the price is on the correct side of the long-term moving average."""
    if signal == 'BUY':
        return candle['close'] > candle['ma_long_term']
    elif signal == 'SELL':
        return candle['close'] < candle['ma_long_term']
    return False

def _is_rsi_not_exhausted(candles_to_check: list, signal: str, config: dict) -> bool:
    """
    Checks if RSI is in an exhaustion zone for any of the provided candles.
    Returns False if the signal should be stopped, True otherwise.
    """
    rsi_oversold = config.get("RSI_OVERSOLD_THRESHOLD", 30)
    rsi_overbought = config.get("RSI_OVERBOUGHT_THRESHOLD", 70)

    for candle in candles_to_check:
        if candle is None or 'rsi' not in candle or pd.isna(candle['rsi']):
            continue  # Skip if candle is invalid or has no RSI

        if signal == 'BUY' and candle['rsi'] > rsi_overbought:
            return False  # Exhausted: BUY signal when RSI is overbought
        if signal == 'SELL' and candle['rsi'] < rsi_oversold:
            return False  # Exhausted: SELL signal when RSI is oversold
            
    return True # Signal is not invalidated by RSI exhaustion.

# --- Main Orchestrator Function ---

def is_signal_confirmed(confirmation_candle: pd.Series, signal: str, config: dict) -> bool:
    """
    Orchestrates the state of various indicators on a single candle to determine
    if the given signal is confirmed.
    Returns True if the signal is confirmed, False otherwise.
    """
    # --- Confirmation checks (must all be true) ---
    checks = []
    if config.get("USE_SHORT_TERM_MA_CONFIRMATION", False):
        checks.append(_is_short_term_ma_confirmed(confirmation_candle, signal))

    if config.get("USE_MA_CONFIRMATION", False):
        checks.append(_is_ma_confirmed(confirmation_candle, signal))
    
    if config.get("USE_LONG_TERM_MA_FILTER", False):
        checks.append(_is_long_term_ma_confirmed(confirmation_candle, signal))
        
    if config.get("USE_RSI_CONFIRMATION", False):
        checks.append(_is_rsi_confirmed(confirmation_candle, signal))

    if config.get("USE_MACD_CONFIRMATION", False):
        checks.append(_is_macd_confirmed(confirmation_candle, signal))
    
    # ADX is direction-agnostic, so it's checked for both signals.
    if config.get("USE_ADX_CONFIRMATION", False):
        checks.append(_is_adx_confirmed(confirmation_candle))
    
    # If 'checks' is empty, it means no confirmations were configured,
    # so the check implicitly passes because all([]) returns True.
    return all(checks)
