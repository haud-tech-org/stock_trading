import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks
import ta

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators, 
    check_advanced_confirmation, 
    can_apply_advanced_confirmation
)
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.regime import prepare_regime_indicators, is_regime_favorable

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

    # --- 3. New: Check for momentum using average price ---
    window['avg_price'] = (window['high'] + window['low'] + window['close']) / 3
    
    is_momentum_confirmed = False
    if is_all_bullish:
        # Uptrend: Consistently increasing average price
        if (window['avg_price'].diff().dropna() >= 0).all():
            is_momentum_confirmed = True
            signal = 'BUY'
    elif is_all_bearish:
        # Downtrend: Consistently decreasing average price
        if (window['avg_price'].diff().dropna() <= 0).all():
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

    # --- 5. New: Peak/Trough Breakout Confirmation ---
    lookback_minutes = config.get("PEAK_BOTTOM_LOOKBACK_PERIOD")
    prominence = config.get("PEAK_TROUGH_PROMINENCE", 1)
    momentum_start_time = window.index[0]
    
    if lookback_minutes is None:
        lookback_df = df_indexed.loc[:momentum_start_time].iloc[:-1]
    else:
        lookback_start_time = momentum_start_time - pd.Timedelta(minutes=lookback_minutes)
        lookback_df = df_indexed.loc[lookback_start_time:momentum_start_time].iloc[:-1]

    if lookback_df.empty:
        return None

    is_breakout_confirmed = False
    if signal == 'BUY':
        # Find all peaks in the lookback period
        peaks, _ = find_peaks(lookback_df['high'], prominence=prominence)
        if peaks.size > 0:
            # Get the last (most recent) peak
            last_peak_index = peaks[-1]
            last_peak_high = lookback_df['high'].iloc[last_peak_index]
            if current_candle['close'] > last_peak_high:
                is_breakout_confirmed = True
    elif signal == 'SELL':
        # Find all troughs (by inverting the price series)
        troughs, _ = find_peaks(-lookback_df['low'], prominence=prominence)
        if troughs.size > 0:
            # Get the last (most recent) trough
            last_trough_index = troughs[-1]
            last_trough_low = lookback_df['low'].iloc[last_trough_index]
            if current_candle['close'] < last_trough_low:
                is_breakout_confirmed = True

    if not is_breakout_confirmed:
        return None

    # --- Volume Confirmation ---
    use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
    use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)

    confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
    confirmation_df = df_indexed.iloc[confirmation_candle_index - window_size + 1 : confirmation_candle_index + 1]

    volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
    volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)

    if not (volume_spike_is_confirmed and volume_is_increasing):
        return None

    # --- Create Alert ---
    # --- 7. Body-to-Range Ratio Confirmation on Alert Candle ---
    body_to_range_min_ratio = config.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
    current_candle_body = abs(current_candle['close'] - current_candle['open'])
    current_candle_range = current_candle['high'] - current_candle['low']

    if current_candle_range > 0:
        body_ratio = current_candle_body / current_candle_range
        if body_ratio < body_to_range_min_ratio:
            return None
    else:
        # If range is 0 (a doji-like candle), it cannot meet the ratio unless the ratio is 0.
        if body_to_range_min_ratio > 0:
            return None

    # --- 8. Original: Check for body dominance over wicks for the entire window ---
    window['body'] = abs(window['close'] - window['open'])
    window['range'] = window['high'] - window['low']
    window['wick'] = window['range'] - window['body']
    
    total_body = window['body'].sum()
    total_wick = window['wick'].sum()

    if total_body <= total_wick:
        return None

    # --- 9. Advanced Confirmation (optional) ---
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

    # Format start_time and momentum_start_time as ISO string with configured timezone

    from src.stockreports.utils.time_utils import to_iso8601_with_tz
    start_time = to_iso8601_with_tz(momentum_start_time)
    momentum_start_time_iso = to_iso8601_with_tz(momentum_start_time)

    alert_data = AlertData(
        approach=Approach.CONSISTENT_MOMENTUM,
        id=alert_id,
        signal=signal,
        alert_price=current_price,
        alert_time=alert_time,
        start_price=momentum_start_price,
        start_time=start_time,
        magnitude=round(abs(current_price - momentum_start_price), 2),
        details=json.dumps({
            "reason": "Consistent Momentum with Breakout",
            "momentum_start_time": momentum_start_time_iso,
            "momentum_window_size": window_size,
            "breakout_lookback_minutes": lookback_minutes,
            "used_advanced_confirmation": use_advanced_confirmation
        })
    )
    return alert_data

def _is_immediate_reversal(candle: pd.Series, original_signal: str, config: dict) -> bool:
    """
    Checks if the given candle is a strong reversal compared to the original signal.
    """
    reversal_ratio = config.get("REVERSAL_CANDLE_BODY_RATIO", 0.6)
    
    candle_range = candle['high'] - candle['low']
    if candle_range == 0:
        return False

    body_size = abs(candle['close'] - candle['open'])
    
    # Check for strong bearish reversal after a BUY signal
    if original_signal == 'BUY' and candle['close'] < candle['open']:
        if (body_size / candle_range) >= reversal_ratio:
            return True
            
    # Check for strong bullish reversal after a SELL signal
    elif original_signal == 'SELL' and candle['close'] > candle['open']:
        if (body_size / candle_range) >= reversal_ratio:
            return True

    return False

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

    # --- Market Regime Filter Calculation ---
    use_regime_filter = config.get("USE_MARKET_REGIME_FILTER", False)
    if use_regime_filter:
        prepare_regime_indicators(df, config)

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
        
        # Determine potential signal direction
        is_bullish_signal = (window['close'] > window['open']).all()
        is_bearish_signal = (window['close'] < window['open']).all()
        
        potential_signal = None
        if is_bullish_signal:
            potential_signal = 'BUY'
        elif is_bearish_signal:
            potential_signal = 'SELL'

        # --- Apply Market Regime Filter before detailed analysis ---
        if use_regime_filter and potential_signal:
            current_candle_for_regime = df_indexed.iloc[i]
            if not is_regime_favorable(current_candle_for_regime, potential_signal, config):
                continue

        alert = _analyze_window(window, df_indexed, df_with_indicators, config, window_size, use_advanced_confirmation)
        
        if alert:
            # --- Realtime Reversal Confirmation ---
            if config.get("USE_REALTIME_REVERSAL_CONFIRMATION", False):
                confirmation_window_size = config.get("REALTIME_REVERSAL_CONFIRMATION_WINDOW", 1)
                
                # Ensure we have enough subsequent candles for the confirmation window
                if i + confirmation_window_size < len(df_indexed):
                    confirmation_window = df_indexed.iloc[i + 1 : i + 1 + confirmation_window_size]
                    
                    # Check for reversal within the confirmation window
                    for _, candle in confirmation_window.iterrows():
                        if _is_immediate_reversal(candle, alert.signal, config):
                            # Found a reversal candle within the window, invalidate the alert
                            alert = None
                            break # No need to check further in this window

        # In development mode, generate all alerts.
        # In deployment mode, only generate alerts that are new enough.
        if alert and (is_development_mode or is_new_alert):
            alerts.append(alert)

    return alerts
