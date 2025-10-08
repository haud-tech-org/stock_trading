import pandas as pd
from scipy.signal import find_peaks
import logging
import json

# --- Settings Loader ---
# Executors still need access to settings for their parameters.
from src.stockreports.config import loader
settings, signal_settings = loader.load_config()

# --- Project Imports ---
from src.stockreports.alert.common.confirmation import prepare_indicators, check_advanced_confirmation
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.models import AlertResult, AlertData

# --- Constants ---
# This constant is specific to the RCM approach.
# PEAK_TROUGH_PROMINENCE = 5 # This is now configured in signal_settings.py

def run_analysis(df: pd.DataFrame) -> AlertResult:
    """
    Entry point for the RCM approach. It takes a DataFrame and returns an AlertResult.
    """
    approach_name = "RCM"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Get the config for this specific approach, falling back to default
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_rcm_alerts(df, config)
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

def _find_rcm_alerts(df: pd.DataFrame, config: dict) -> list[AlertData]:
    """
    Internal function to find alerts using the Reversal-Confirmation-Magnitude (RCM) approach.
    """
    alerts = []
    if len(df) < 30: 
        logging.warning("RCM: Input DataFrame has less than 30 rows, cannot generate alerts.")
        return alerts

    df = prepare_indicators(df)
    
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
    
    confirmation_window = config.get("CONFIRMATION_WINDOW", 4)
    use_advanced_confirmation = config.get("USE_ADVANCED_CONFIRMATION", False)

    for i in range(1, len(df)):
        current_candle = df.iloc[i]
        prev_candle = df.iloc[i-1]

        # --- State Machine ---

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
                adv_signal = check_advanced_confirmation(current_candle, prev_candle)
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

            # If we have a signal, check for magnitude
            if signal:
                reversal_price = df.iloc[last_reversal_idx]['low'] if signal == 'BUY' else df.iloc[last_reversal_idx]['high']
                current_price = current_candle['close']
                
                is_sufficient, magnitude = check_magnitude(current_price, reversal_price, signal_settings)

                if is_sufficient:
                    alert_time = current_candle['time']
                    reversal_time = df.iloc[last_reversal_idx]['time']

                    # Generate a unique ID from UTC timestamps
                    alert_ts = int(alert_time.tz_convert('UTC').timestamp())
                    reversal_ts = int(reversal_time.tz_convert('UTC').timestamp())
                    alert_id = f"{reversal_ts}_{alert_ts}"

                    # Create the standardized AlertData object
                    alert_data = AlertData(
                        approach="RCM",
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
