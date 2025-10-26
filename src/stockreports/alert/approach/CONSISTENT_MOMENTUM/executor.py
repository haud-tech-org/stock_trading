import pandas as pd
import logging
import json
from typing import Optional

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, check_advanced_confirmation, can_apply_advanced_confirmation

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
    """
    approach_name = Approach.CONSISTENT_MOMENTUM
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Get the config for this specific approach, falling back to default
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_consistent_momentum_alerts(df, config, new_candle_count)
        logging.info(f"'{approach_name}' approach found {len(alerts_data)} alerts.")

        # Convert list of AlertData objects to a DataFrame
        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=approach_name,
            alerts=alerts_df
        )
    except Exception as e:
        logging.error(f"An error occurred during '{approach_name}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=approach_name,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

def _analyze_window(window: pd.DataFrame, df_indexed: pd.DataFrame, df_with_indicators: pd.DataFrame, config: dict, window_size: int, use_advanced_confirmation: bool) -> Optional[AlertData]:
    """
    Analyzes a single window of data to find a consistent momentum alert.
    This function contains the core alert detection logic.
    """
    # --- 2. Basic Momentum Check ---
    is_all_bullish = (window['close'] > window['open']).all()
    is_all_bearish = (window['close'] < window['open']).all()

    if not (is_all_bullish or is_all_bearish):
        return None

    # --- 3. Check for momentum (higher highs/lows or lower highs/lows) ---
    is_momentum_confirmed = False
    if is_all_bullish:
        # Uptrend: Higher highs and higher lows
        if (window['high'].diff().dropna() >= 0).all() and \
           (window['low'].diff().dropna() >= 0).all():
            is_momentum_confirmed = True
            signal = 'BUY'
    elif is_all_bearish:
        # Downtrend: Lower highs and lower lows
        if (window['high'].diff().dropna() <= 0).all() and \
           (window['low'].diff().dropna() <= 0).all():
            is_momentum_confirmed = True
            signal = 'SELL'
    
    if not is_momentum_confirmed:
        return None

    # --- 4. New: Strong Close Confirmation ---
    current_candle = window.iloc[-1]
    candle_range = (current_candle['high'] - current_candle['low'])
    if candle_range == 0: return None

    strong_close_min, _ = signal_settings.STRONG_CLOSE_THRESHOLD_RANGE
    is_strong_close = False
    if signal == 'BUY' and ((current_candle['close'] - current_candle['low']) / candle_range) >= strong_close_min:
        is_strong_close = True
    elif signal == 'SELL' and ((current_candle['high'] - current_candle['close']) / candle_range) >= strong_close_min:
        is_strong_close = True

    if not is_strong_close:
        return None

    # --- 5. New: Peak/Bottom Breakout Confirmation ---
    lookback_minutes = config.get("PEAK_BOTTOM_LOOKBACK_PERIOD", 30)
    momentum_start_time = window.index[0]
    lookback_start_time = momentum_start_time - pd.Timedelta(minutes=lookback_minutes)
    
    # Filter the main indexed dataframe for the lookback period
    lookback_df = df_indexed.loc[lookback_start_time:momentum_start_time].iloc[:-1]

    if lookback_df.empty:
        return None

    is_breakout_confirmed = False
    if signal == 'BUY':
        highest_peak = lookback_df['high'].max()
        if pd.notna(highest_peak) and current_candle['close'] > highest_peak:
            is_breakout_confirmed = True
    elif signal == 'SELL':
        lowest_bottom = lookback_df['low'].min()
        if pd.notna(lowest_bottom) and current_candle['close'] < lowest_bottom:
            is_breakout_confirmed = True
    
    if not is_breakout_confirmed:
        return None

    # --- 6. New: Average Body-to-Range Ratio Confirmation ---
    body_to_range_min_ratio = config.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
    window['body'] = abs(window['close'] - window['open'])
    window['range'] = window['high'] - window['low']
    
    # Avoid division by zero for doji candles
    valid_candles = window[window['range'] > 0]
    if not valid_candles.empty:
        avg_body_to_range_ratio = (valid_candles['body'] / valid_candles['range']).mean()
        if avg_body_to_range_ratio < body_to_range_min_ratio:
            return None

    # --- 7. Original: Check for body dominance over wicks ---
    window['wick'] = window['range'] - window['body']
    
    total_body = window['body'].sum()
    total_wick = window['wick'].sum()

    if total_body <= total_wick:
        return None

    # --- 8. Advanced Confirmation (optional) ---
    if use_advanced_confirmation:
        # Get the specific candles we need from the indicator-rich dataframe
        adv_current_candle = df_with_indicators.loc[current_candle.name]
        
        # Find the previous candle's timestamp to locate it
        # This index is relative to the original df_indexed, not the window
        prev_candle_index = df_indexed.index.get_loc(current_candle.name) - 1
        if prev_candle_index < 0: return None # Not enough history for advanced check
        prev_candle_timestamp = df_indexed.index[prev_candle_index]
        adv_prev_candle = df_with_indicators.loc[prev_candle_timestamp]
        
        adv_signal = check_advanced_confirmation(
            adv_current_candle, 
            adv_prev_candle
        )
        
        # If the advanced signal doesn't match the momentum signal, invalidate it
        if adv_signal != signal:
            return None

    # --- If all checks pass, create an AlertData object ---
    start_candle = window.iloc[0]
    
    alert_time = current_candle.name
    momentum_start_time = start_candle.name
    current_price = current_candle['close']
    momentum_start_price = start_candle['open']

    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
    momentum_start_ts = int(momentum_start_time.tz_convert('UTC').timestamp())

    alert_data = AlertData(
        approach=Approach.CONSISTENT_MOMENTUM,
        id=alert_id,
        signal=signal,
        alert_price=current_price,
        alert_time=alert_time,
        start_price=momentum_start_price,
        start_time=momentum_start_time,
        magnitude=round(abs(current_price - momentum_start_price), 2),
        details=json.dumps({
            "reason": "Consistent Momentum with Breakout",
            "momentum_start_time": momentum_start_ts,
            "momentum_window_size": window_size,
            "breakout_lookback_minutes": lookback_minutes,
            "used_advanced_confirmation": use_advanced_confirmation
        })
    )
    return alert_data

def _find_consistent_momentum_alerts(df: pd.DataFrame, config: dict, new_candle_count: int = 0) -> list[AlertData]:
    """
    Internal function to find alerts based on a consistent momentum pattern.
    This looks for a rolling window of candles that show strong, consistent direction.
    """
    alerts = []
    window_size = config.get("CONFIRMATION_WINDOW", 3)
    
    # Determine if we can use advanced confirmation dynamically.
    use_advanced_confirmation = can_apply_advanced_confirmation(df)

    if use_advanced_confirmation:
        logging.info(f"{Approach.CONSISTENT_MOMENTUM}: Sufficient data available ({len(df)} candles). Advanced confirmation will be used.")
    else:
        logging.warning(
            f"{Approach.CONSISTENT_MOMENTUM}: Insufficient data for advanced confirmation. "
            "Falling back to simple confirmation."
        )

    if window_size < 2:
        logging.error(f"{Approach.CONSISTENT_MOMENTUM}: 'CONFIRMATION_WINDOW' must be at least 2, but got {window_size}. Aborting.")
        return alerts

    if len(df) < window_size:
        logging.warning(f"{Approach.CONSISTENT_MOMENTUM}: DataFrame has less than {window_size} rows, cannot generate alerts.")
        return alerts

    # Set a DatetimeIndex to allow for proper time-based lookups
    df_indexed = df.set_index('time')

    # Prepare indicators once if advanced confirmation is enabled
    df_with_indicators = None
    if use_advanced_confirmation:
        df_with_indicators = df_indexed.copy()
        df_with_indicators = prepare_indicators(df_with_indicators)

    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    grace_period = window_size

    # The loop now iterates over the entire dataframe to find all historical alerts.
    for i in range(window_size - 1, len(df_indexed)):
        # In deployment mode, check if the alert is recent enough to be notified.
        is_new_alert = not is_development_mode and (i >= len(df_indexed) - (new_candle_count + grace_period))

        window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
        
        alert = _analyze_window(window, df_indexed, df_with_indicators, config, window_size, use_advanced_confirmation)
        
        # In development mode, generate all alerts.
        # In deployment mode, only generate alerts that are new enough.
        if alert and (is_development_mode or is_new_alert):
            alerts.append(alert)

    return alerts
