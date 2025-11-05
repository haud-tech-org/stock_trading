import pandas as pd
from scipy.signal import find_peaks
import logging
import json

# --- Settings Loader ---
# Executors still need access to settings for their parameters.
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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.common.regime import prepare_regime_indicators, is_regime_favorable

# --- Constants ---
# This constant is specific to the RCM approach.
# PEAK_TROUGH_PROMINENCE = 5 # This is now configured in signal_settings.py

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the RCM approach. It takes a DataFrame and returns an AlertResult.
    """
    approach_name = Approach.RCM
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Get the config for this specific approach, falling back to default
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        if config.get("USE_MARKET_REGIME_FILTER", False):
            df = prepare_regime_indicators(df, config)

        alerts_data = _find_rcm_alerts(df, config, new_candle_count)
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

def _find_rcm_alerts(df: pd.DataFrame, config: dict, new_candle_count=0) -> list[AlertData]:
    """
    Finds alerts using the Reversal-Confirmation-Magnitude (RCM) approach.
    This function uses a truly unified reverse loop for both deployment and development modes.
    The loop's scan depth is naturally handled by the value of `new_candle_count`.
    """
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    # Dynamically check if advanced confirmation can be used.
    use_advanced_confirmation = can_apply_advanced_confirmation(df)

    if use_advanced_confirmation:
        logging.info(f"{Approach.RCM}: Sufficient data available ({len(df)} candles). Advanced confirmation will be used.")
        df = prepare_indicators(df)
    else:
        logging.warning(
            f"{Approach.RCM}: Insufficient data for advanced confirmation. "
            "Falling back to simple confirmation."
        )
    
    use_regime_filter = config.get("USE_MARKET_REGIME_FILTER", False)
    peak_trough_prominence = config.get("PEAK_TROUGH_PROMINENCE", 5)
    
    # Pre-compute all peaks and troughs once for efficiency
    peaks, _ = find_peaks(df['high'], prominence=peak_trough_prominence)
    troughs, _ = find_peaks(-df['low'], prominence=peak_trough_prominence)
    
    reversal_points = {
        'peak': {idx: True for idx in peaks},
        'trough': {idx: True for idx in troughs}
    }

    confirmation_window = config.get("CONFIRMATION_WINDOW", 3)
    min_consistency = config.get("CONFIRMATION_MIN_CONSISTENCY", 2)
    lookback_period = config.get('PEAK_BOTTOM_LOOKBACK_PERIOD')
    min_magnitude = config.get("MIN_ALERT_MAGNITUDE", 0)
    use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
    use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
    use_last_candle_max_volume = config.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

    # The loop needs enough data for a reversal and confirmation window.
    required_lookback = confirmation_window + 1
    if len(df) < required_lookback:
        return alerts

    df_indexed = df.reset_index()

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1

    # The loop's scan depth is naturally optimized by this calculation.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    # 'i' is the index of the potential confirmation candle.
    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region for the current mode.

        current_candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]

        # The core logic of RCM is to find a confirmation *after* a reversal.
        # So, in our reverse loop, we look for a reversal point *before* the current candle 'i'.
        # We'll search within the confirmation_window.
        for j in range(1, confirmation_window + 1):
            reversal_idx = i - j
            if reversal_idx < 0:
                break

            reversal_candle = df_indexed.iloc[reversal_idx]
            is_peak = reversal_points['peak'].get(reversal_idx, False)
            is_trough = reversal_points['trough'].get(reversal_idx, False)

            if not (is_peak or is_trough):
                continue

            # --- Found a potential reversal, now check the confirmation window ---
            confirmation_df = df.iloc[reversal_idx + 1 : i + 1].copy()
            
            signal = None
            if is_trough: # Look for BUY signal
                adv_signal = check_advanced_confirmation(current_candle, prev_candle) if use_advanced_confirmation else 'BUY'
                if adv_signal == 'BUY' and (confirmation_df['close'] > confirmation_df['open']).sum() >= min_consistency:
                    signal = 'BUY'
            elif is_peak: # Look for SELL signal
                adv_signal = check_advanced_confirmation(current_candle, prev_candle) if use_advanced_confirmation else 'SELL'
                if adv_signal == 'SELL' and (confirmation_df['close'] < confirmation_df['open']).sum() >= min_consistency:
                    signal = 'SELL'

            if not signal:
                continue

            # --- Signal Confirmed, now check filters and magnitude ---
            if use_regime_filter and not is_regime_favorable(current_candle, signal, config):
                continue

            # Peak/Bottom Breakout Confirmation
            if lookback_period is not None:
                lookback_start_idx = max(0, reversal_idx - lookback_period)
                lookback_df = df_indexed.iloc[lookback_start_idx:reversal_idx]
                if not lookback_df.empty:
                    if signal == 'BUY' and current_candle['close'] <= lookback_df['high'].max():
                        continue
                    if signal == 'SELL' and current_candle['close'] >= lookback_df['low'].min():
                        continue
            
            # Magnitude Check
            reversal_price = reversal_candle['low'] if signal == 'BUY' else reversal_candle['high']
            is_sufficient, magnitude = check_magnitude(current_candle['close'], reversal_price, min_magnitude)
            if not is_sufficient:
                continue

            # Volume Confirmation
            volume_spike_ok = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
            volume_increasing_ok = not use_increasing_volume or is_volume_increasing(confirmation_df)
            last_candle_max_volume_ok = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)
            if not (volume_spike_ok and volume_increasing_ok and last_candle_max_volume_ok):
                continue

            # --- All checks passed, create alert ---
            alert_time = current_candle['time']
            reversal_time = reversal_candle['time']
            if isinstance(reversal_time, pd.Timestamp):
                reversal_time = reversal_time.isoformat()
            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

            alert_data = AlertData(
                approach=Approach.RCM,
                id=alert_id,
                signal=signal,
                alert_price=current_candle['close'],
                alert_time=alert_time,
                start_price=reversal_price,
                start_time=reversal_time,
                magnitude=magnitude,
                details=json.dumps({
                    "peak_trough_prominence": peak_trough_prominence,
                    "confirmation_window": confirmation_window,
                    "used_advanced_confirmation": use_advanced_confirmation,
                    "peak_bottom_lookback_period": lookback_period
                })
            )
            alerts.append(alert_data)

            # In DEPLOYMENT mode, exit after finding the first valid alert.
            if not is_development_mode:
                return alerts
            
            # Break the inner loop since we found an alert for this confirmation candle 'i'
            break 
    
    # In DEVELOPMENT mode, return all found alerts in chronological order.
    return alerts[::-1]
