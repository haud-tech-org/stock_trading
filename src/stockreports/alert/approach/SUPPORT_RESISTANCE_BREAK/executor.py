import pandas as pd
import numpy as np
import logging
import json
from typing import List, Optional, Tuple, Generator

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing
from src.stockreports.alert.common.volatility import is_bb_squeeze

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the SUPPORT_RESISTANCE_BREAK approach.
    This approach identifies:
    1. "Support Shelf" and generates a SELL alert on a confirmed breakdown.
    2. "Resistance Ceiling" and generates a BUY alert on a confirmed breakout.
    """
    approach_name = Approach.SUPPORT_RESISTANCE_BREAK
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Ensure all necessary indicators are present on the DataFrame
        df = prepare_indicators(df.copy())

        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_break_alerts(df, config, new_candle_count)
        logging.info(f"'{approach_name}' approach found {len(alerts_data)} alerts.")

        if not alerts_data:
            return AlertResult(approach_name=approach_name, alerts=pd.DataFrame())

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

# --- BREAK AND CONFIRMATION CHECKS ---

def _is_breakdown_candle(candle: pd.Series, support_level: float) -> bool:
    """Checks if a candle closes below the support level."""
    return candle['close'] < support_level

def _is_breakout_candle(candle: pd.Series, resistance_level: float) -> bool:
    """Checks if a candle closes above the resistance level."""
    return candle['close'] > resistance_level

def _find_break_alerts(df: pd.DataFrame, config: dict, new_candle_count: int = 0) -> list[AlertData]:
    """
    Orchestrates finding both support breakdown and resistance breakout alerts
    by iterating through the dataframe and checking for valid patterns based on
    highest peaks and lowest troughs in a lookback period.
    """
    alerts = []
    lookback_period = config.get("LOOKBACK_PERIOD", 50)
    confirmation_window = config.get("CONFIRMATION_WINDOW", 3)
    consistency_threshold = config.get("CONSISTENCY_THRESHOLD", 2)
    
    # BB Squeeze parameters
    use_bb_squeeze = config.get("USE_BB_SQUEEZE_CONFIRMATION", False)
    bb_squeeze_lookback = config.get("BB_SQUEEZE_LOOKBACK", 40)
    bb_squeeze_threshold = config.get("BB_SQUEEZE_THRESHOLD_RATIO", 0.08)

    last_alert_break_index = -np.inf
    
    # Define the grace period for considering an alert "new".
    grace_period = confirmation_window

    # We need at least the lookback window + break candle + confirmation window.
    min_required_len = lookback_period + 1 + confirmation_window
    if len(df) < min_required_len:
        return alerts

    df_indexed = df.reset_index()

    # State machine: NEUTRAL -> AWAITING_CONFIRMATION
    state = 'NEUTRAL'
    break_candle_index = -1
    level = -1
    level_type = ''

    # Iterate through each candle that could be a 'break_candle'.
    # We subtract confirmation_window to ensure there's room for confirmation.
    for i in range(lookback_period, len(df_indexed) - confirmation_window):
        
        # --- STATE: NEUTRAL -> AWAITING_CONFIRMATION ---
        if state == 'NEUTRAL':
            # Enforce a cooldown period after an alert to prevent spam.
            # For simplicity, we can use a fixed number of candles as cooldown.
            if i <= last_alert_break_index + lookback_period:
                continue

            current_candle = df_indexed.iloc[i]
            window_end = i
            window_start = max(0, window_end - lookback_period)
            df_window = df_indexed.iloc[window_start:window_end]

            if df_window.empty:
                continue

            # --- Bollinger Band Squeeze Check ---
            # Before checking for a breakout, verify if we are in a squeeze state.
            # The window passed to the squeeze check should end at the candle *before* the breakout.
            if use_bb_squeeze and not is_bb_squeeze(df_window, bb_squeeze_lookback, bb_squeeze_threshold):
                continue

            highest_peak = df_window['high'].max()
            lowest_trough = df_window['low'].min()

            # Check for Breakout (BUY)
            if _is_breakout_candle(current_candle, highest_peak):
                if is_volume_spike_confirmed(df_indexed, i, config.get("USE_VOLUME_CONFIRMATION", False)):
                    state = 'AWAITING_CONFIRMATION'
                    break_candle_index = i
                    level = highest_peak
                    level_type = 'resistance'
            
            # If a breakout is found, continue to the next candle to start confirmation phase
            if state == 'AWAITING_CONFIRMATION':
                continue

            # Check for Breakdown (SELL)
            if _is_breakdown_candle(current_candle, lowest_trough):
                if is_volume_spike_confirmed(df_indexed, i, config.get("USE_VOLUME_CONFIRMATION", False)):
                    state = 'AWAITING_CONFIRMATION'
                    break_candle_index = i
                    level = lowest_trough
                    level_type = 'support'
        
        # --- STATE: AWAITING_CONFIRMATION -> ALERT or RESET ---
        if state == 'AWAITING_CONFIRMATION':
            confirmation_start = break_candle_index + 1
            confirmation_end = confirmation_start + confirmation_window
            
            # Ensure we don't go out of bounds
            if confirmation_end > len(df_indexed):
                state = 'NEUTRAL'
                continue

            confirmation_df = df_indexed.iloc[confirmation_start:confirmation_end]

            consistency_count = 0
            for _, confirmation_candle in confirmation_df.iterrows():
                if level_type == 'resistance' and _is_breakout_candle(confirmation_candle, level):
                    consistency_count += 1
                elif level_type == 'support' and _is_breakdown_candle(confirmation_candle, level):
                    consistency_count += 1

            final_confirmation_candle = df_indexed.iloc[confirmation_end - 1]
            
            use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
            volume_confirmed = not use_increasing_volume or is_volume_increasing(confirmation_df.reset_index())

            is_confirmed = (
                consistency_count >= consistency_threshold and
                final_confirmation_candle['adx'] > signal_settings.ADX_CONFIRMATION_THRESHOLD and
                volume_confirmed
            )

            if is_confirmed:
                is_development_mode = settings.MODE == Mode.DEVELOPMENT
                is_new_alert = not is_development_mode and (break_candle_index >= len(df_indexed) - (new_candle_count + grace_period))

                if is_development_mode or is_new_alert:
                    signal = 'BUY' if level_type == 'resistance' else 'SELL'
                    break_candle = df_indexed.iloc[break_candle_index]
                    
                    alert = _create_alert(df_indexed, signal, final_confirmation_candle, break_candle, level, lookback_period)
                    
                    if level_type == 'resistance':
                        logging.info(f"Confirmed Resistance Breakout Alert at {alert.alert_time} for price {alert.alert_price:.2f}")
                    else:
                        logging.info(f"Confirmed Support Breakdown Alert at {alert.alert_time} for price {alert.alert_price:.2f}")
                        
                    alerts.append(alert)
                    last_alert_break_index = break_candle_index
            
            # Reset state regardless of outcome
            state = 'NEUTRAL'
            
    return alerts

def _create_alert(df_indexed, signal, confirmation_candle, break_candle, level, lookback_period):
    """Helper function to create an AlertData object."""
    alert_time = confirmation_candle['time']
    alert_price = confirmation_candle['close']
    
    # For this logic, start_time and start_price are less defined than with touch-based levels.
    # We can set them to the break candle's details.
    start_time = break_candle['time']
    start_price = break_candle['close']
    
    if signal == 'SELL':
        magnitude = ((level - alert_price) / level) * 100 if level > 0 else 0
        level_type = "lowest_trough"
    else: # BUY
        magnitude = ((alert_price - level) / level) * 100 if level > 0 else 0
        level_type = "highest_peak"

    alert_id = f"{signal}-{int(alert_time.tz_convert('UTC').timestamp())}"

    details = {
        level_type: round(level, 2),
        "break_candle_time": break_candle['time'].isoformat(),
        "confirmation_candle_time": confirmation_candle['time'].isoformat(),
        "lookback_period": lookback_period
    }

    return AlertData(
        approach=Approach.SUPPORT_RESISTANCE_BREAK,
        id=alert_id,
        signal=signal,
        alert_price=alert_price,
        alert_time=alert_time,
        start_price=start_price,
        start_time=start_time,
        magnitude=magnitude,
        details=json.dumps(details)
    )
