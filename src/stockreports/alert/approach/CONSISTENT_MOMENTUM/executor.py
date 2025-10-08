import pandas as pd
import logging
import json

# --- Settings Loader ---
from src.stockreports.config import loader
settings, signal_settings = loader.load_config()

# --- Project Imports ---
from src.stockreports.alert.models import AlertResult, AlertData
from src.stockreports.alert.common.confirmation import prepare_indicators, check_advanced_confirmation

def run_analysis(df: pd.DataFrame) -> AlertResult:
    """
    Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
    """
    approach_name = "CONSISTENT_MOMENTUM"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Get the config for this specific approach, falling back to default
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_consistent_momentum_alerts(df, config)
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

def _find_consistent_momentum_alerts(df: pd.DataFrame, config: dict) -> list[AlertData]:
    """
    Internal function to find alerts based on a consistent momentum pattern.
    This looks for a rolling window of candles that show strong, consistent direction.
    """
    alerts = []
    window_size = config.get("CONFIRMATION_WINDOW", 4)
    use_advanced_confirmation = config.get("USE_ADVANCED_CONFIRMATION", False)

    if len(df) < window_size:
        logging.warning(f"CONSISTENT_MOMENTUM: DataFrame has less than {window_size} rows, cannot generate alerts.")
        return alerts

    # Set a DatetimeIndex to allow for proper time-based lookups
    df_indexed = df.set_index(pd.to_datetime(df['time'], unit='s'))

    # Prepare indicators once if advanced confirmation is enabled
    df_with_indicators = None
    if use_advanced_confirmation:
        # The minimum required length for indicators should be checked.
        # For example, Ichimoku's Kijun-sen needs 26 periods.
        if len(df_indexed) < 26:
            logging.warning("DataFrame too short for advanced confirmation indicators. Skipping.")
            use_advanced_confirmation = False # Disable it for this run
        else:
            df_with_indicators = prepare_indicators(df_indexed.copy())

    # Use a standard loop for clarity and to avoid dtype issues
    # Start from index 1 if we need a previous candle for advanced confirmation
    start_index = 1 if use_advanced_confirmation else 0
    for i in range(start_index, len(df_indexed) - window_size + 1):
        window = df_indexed.iloc[i : i + window_size].copy()

        # --- 1. Check for same direction ---
        is_all_bullish = (window['close'] > window['open']).all()
        is_all_bearish = (window['close'] < window['open']).all()

        if not (is_all_bullish or is_all_bearish):
            continue

        # --- 2. Check for momentum (higher highs/lows or lower highs/lows) ---
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
            continue

        # --- 3. New: Strong Close Confirmation ---
        current_candle = window.iloc[-1]
        candle_range = (current_candle['high'] - current_candle['low'])
        if candle_range == 0: continue

        strong_close_min, _ = signal_settings.STRONG_CLOSE_THRESHOLD_RANGE
        is_strong_close = False
        if signal == 'BUY' and ((current_candle['close'] - current_candle['low']) / candle_range) >= strong_close_min:
            is_strong_close = True
        elif signal == 'SELL' and ((current_candle['high'] - current_candle['close']) / candle_range) >= strong_close_min:
            is_strong_close = True

        if not is_strong_close:
            continue

        # --- 4. New: Peak/Bottom Breakout Confirmation ---
        lookback_minutes = config.get("PEAK_BOTTOM_LOOKBACK_PERIOD", 30)
        momentum_start_time = window.index[0]
        lookback_start_time = momentum_start_time - pd.Timedelta(minutes=lookback_minutes)
        
        # Filter the main indexed dataframe for the lookback period
        lookback_df = df_indexed.loc[lookback_start_time:momentum_start_time].iloc[:-1]

        if lookback_df.empty:
            continue

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
            continue

        # --- 5. Original: Check for body dominance over wicks ---
        window['body'] = abs(window['close'] - window['open'])
        window['wick'] = window['high'] - window['low'] - window['body']
        
        total_body = window['body'].sum()
        total_wick = window['wick'].sum()

        if total_body <= total_wick:
            continue

        # --- 6. Advanced Confirmation (optional) ---
        if use_advanced_confirmation:
            # Get the specific candles we need from the indicator-rich dataframe
            adv_current_candle = df_with_indicators.loc[current_candle.name]
            
            # Find the previous candle's timestamp to locate it
            # This index is relative to the original df_indexed, not the window
            prev_candle_index = df_indexed.index.get_loc(current_candle.name) - 1
            prev_candle_timestamp = df_indexed.index[prev_candle_index]
            adv_prev_candle = df_with_indicators.loc[prev_candle_timestamp]
            
            adv_signal = check_advanced_confirmation(adv_current_candle, adv_prev_candle)
            
            # If the advanced signal doesn't match the momentum signal, invalidate it
            if adv_signal != signal:
                continue

        # --- If all checks pass, create an AlertData object ---
        start_candle = window.iloc[0]
        
        # Convert timestamps from DatetimeIndex back to integer for AlertData
        alert_time = int(current_candle.name.timestamp())
        momentum_start_time_int = int(start_candle.name.timestamp())
        current_price = current_candle['close']
        momentum_start_price = start_candle['open']

        alert_data = AlertData(
            approach="CONSISTENT_MOMENTUM",
            id=f"{momentum_start_time_int}_{alert_time}",
            signal=signal,
            alert_price=current_price,
            alert_time=current_candle.name,
            start_price=momentum_start_price,
            start_time=start_candle.name,
            magnitude=round(abs(current_price - momentum_start_price), 2),
            details=json.dumps({
                "reason": "Consistent Momentum with Breakout",
                "momentum_start_time": momentum_start_time_int,
                "momentum_window_size": window_size,
                "breakout_lookback_minutes": lookback_minutes
            })
        )
        alerts.append(alert_data)

    return alerts
