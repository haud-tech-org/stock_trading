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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.magnitude import check_magnitude

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
    Internal function to find alerts using the Reversal-Confirmation-Magnitude (RCM) approach.
    """
    alerts = []
    
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
    
    peak_trough_prominence = config.get("PEAK_TROUGH_PROMINENCE", 5)
    peaks, _ = find_peaks(df['high'], prominence=peak_trough_prominence)
    troughs, _ = find_peaks(-df['low'], prominence=peak_trough_prominence)
    
    reversal_points = {
        'peak': {idx: True for idx in peaks},
        'trough': {idx: True for idx in troughs}
    }

    trend_state = 'NEUTRAL' # Can be NEUTRAL, CONFIRMING, IN_UPTREND, IN_DOWNTREND
    last_reversal_type = None
    last_reversal_idx = -1
    confirmation_deadline = -1
    
    confirmation_window = config.get("CONFIRMATION_WINDOW", 3)

    # --- 1. Initial Settings ---
    df_indexed = df.reset_index()
    
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    grace_period = confirmation_window
    
    # The loop now iterates over the entire dataframe to find all historical alerts.
    for i in range(1, len(df_indexed)):
        # In deployment mode, check if the alert is recent enough to be notified.
        is_new_alert = not is_development_mode and (i >= len(df_indexed) - (new_candle_count + grace_period))

        current_candle = df_indexed.iloc[i]
        prev_candle = df_indexed.iloc[i-1]

        # --- 2. State Machine Logic ---

        # 1. If we are in a trend, look for an opposing reversal to reset the state
        if trend_state in ['IN_UPTREND', 'IN_DOWNTREND']:
            is_peak = reversal_points['peak'].get(i, False)
            is_trough = reversal_points['trough'].get(i, False)
            if (trend_state == 'IN_UPTREND' and is_peak) or \
               (trend_state == 'IN_DOWNTREND' and is_trough):
                trend_state = 'NEUTRAL' # Reset state

        # 2. If neutral, look for any new reversal to start the confirmation process
        if trend_state == 'NEUTRAL':
            is_peak = reversal_points['peak'].get(i, False)
            is_trough = reversal_points['trough'].get(i, False)
            if is_peak:
                trend_state = 'CONFIRMING'
                last_reversal_type = 'peak'
                last_reversal_idx = i
                confirmation_deadline = i + confirmation_window
            elif is_trough:
                trend_state = 'CONFIRMING'
                last_reversal_type = 'trough'
                last_reversal_idx = i
                confirmation_deadline = i + confirmation_window

        # 3. If confirming, check for signal and magnitude within the window
        elif trend_state == 'CONFIRMING':
            # If we've passed the deadline, go back to neutral
            if i > confirmation_deadline:
                trend_state = 'NEUTRAL'
                continue

            # Determine signal based on confirmation type
            signal = None
            if use_advanced_confirmation:
                adv_signal = check_advanced_confirmation(
                    current_candle, 
                    prev_candle
                )
                if adv_signal == 'BUY' and last_reversal_type == 'trough':
                    signal = 'BUY'
                elif adv_signal == 'SELL' and last_reversal_type == 'peak':
                    signal = 'SELL'
            else: # Simple confirmation
                confirmation_df = df.iloc[last_reversal_idx + 1 : i + 1].copy()
                min_consistency = config.get("CONFIRMATION_MIN_CONSISTENCY", 2)
                if last_reversal_type == 'trough':
                    if (confirmation_df['close'] > confirmation_df['open']).sum() >= min_consistency:
                        signal = 'BUY'
                elif last_reversal_type == 'peak':
                    if (confirmation_df['close'] < confirmation_df['open']).sum() >= min_consistency:
                        signal = 'SELL'

            # If we have a signal, check for magnitude and volume
            if signal:
                reversal_price = df.iloc[last_reversal_idx]['low'] if signal == 'BUY' else df.iloc[last_reversal_idx]['high']
                current_price = current_candle['close']
                
                is_sufficient, magnitude = check_magnitude(current_price, reversal_price, signal_settings)

                # --- 7. Check for volume confirmation ---
                use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
                use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)

                volume_spike_ok = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
                
                # Define the window for checking increasing volume
                volume_check_window = df_indexed.iloc[last_reversal_idx:i+1]
                volume_increasing_ok = not use_increasing_volume or is_volume_increasing(volume_check_window)

                if volume_spike_ok and volume_increasing_ok:
                    # In development mode, generate all alerts.
                    # In deployment mode, only generate alerts that are new enough.
                    if is_sufficient and (is_development_mode or is_new_alert):
                        alert_time = current_candle['time']
                        reversal_time = df.iloc[last_reversal_idx]['time']

                        # Generate a unique ID from the alert time's UTC timestamp
                        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                        # Create the standardized AlertData object
                        alert_data = AlertData(
                            approach=Approach.RCM,
                            id=alert_id,
                            signal=signal,
                            alert_price=current_price,
                            alert_time=alert_time,
                            start_price=reversal_price,
                            start_time=reversal_time,
                            magnitude=magnitude,
                            details=json.dumps({
                                "peak_trough_prominence": peak_trough_prominence,
                                "confirmation_window": confirmation_window,
                                "used_advanced_confirmation": use_advanced_confirmation
                            })
                        )
                        alerts.append(alert_data)
                        
                        # Transition to IN_TREND to prevent more alerts for this move
                        trend_state = 'IN_UPTREND' if signal == 'BUY' else 'IN_DOWNTREND'

    return alerts
