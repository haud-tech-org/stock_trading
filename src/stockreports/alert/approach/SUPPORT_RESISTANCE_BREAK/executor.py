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
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    _is_rsi_not_exhausted,
    is_signal_confirmed
)
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
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
    Orchestrates finding both support breakdown and resistance breakout alerts.
    This function uses a truly unified reverse loop for both deployment and development modes.
    The loop's scan depth is naturally handled by the value of `new_candle_count`.
    """
    alerts = []
    lookback_period = config.get("LOOKBACK_PERIOD", 50)
    confirmation_window_size = config.get("CONFIRMATION_WINDOW", 3)
    consistency_threshold = config.get("CONSISTENCY_THRESHOLD", 2)
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    # BB Squeeze parameters
    use_bb_squeeze = config.get("USE_BB_SQUEEZE_CONFIRMATION", False)
    bb_squeeze_lookback = config.get("BB_SQUEEZE_LOOKBACK", 40)
    bb_squeeze_threshold = config.get("BB_SQUEEZE_THRESHOLD_RATIO", 0.08)

    # Standardized data preparation
    df = prepare_indicators(df)

    # The total lookback needed for one full check.
    required_lookback = lookback_period + 1 + confirmation_window_size
    if len(df) < required_lookback:
        return alerts

    df_indexed = df.reset_index()
    last_alert_break_index = float('inf')

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1

    # The loop's scan depth is naturally optimized by this calculation.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    # 'i' is the index of the final confirmation candle.
    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region for the current mode.
        
        # --- 1. Define Windows ---
        final_confirmation_candle = df_indexed.iloc[i]
        break_candle_index = i - confirmation_window_size
        
        # Cooldown check
        if break_candle_index >= last_alert_break_index - lookback_period:
            continue

        break_candle = df_indexed.iloc[break_candle_index]
        
        lookback_window_end = break_candle_index
        lookback_window_start = max(0, lookback_window_end - lookback_period)
        df_lookback_window = df_indexed.iloc[lookback_window_start:lookback_window_end]

        if df_lookback_window.empty:
            continue

        # --- 2. BB Squeeze Check (if enabled) ---
        if use_bb_squeeze and not is_bb_squeeze(df_lookback_window, bb_squeeze_lookback, bb_squeeze_threshold):
            continue

        # --- 3. Identify Level and Check for Break ---
        highest_peak = df_lookback_window['high'].max()
        lowest_trough = df_lookback_window['low'].min()
        
        level = -1
        level_type = ''
        signal = ''

        # Check for Breakout (BUY)
        if _is_breakout_candle(break_candle, highest_peak):
            level = highest_peak
            level_type = 'resistance'
            signal = 'BUY'
        # Check for Breakdown (SELL)
        elif _is_breakdown_candle(break_candle, lowest_trough):
            level = lowest_trough
            level_type = 'support'
            signal = 'SELL'
        else:
            continue # No break occurred

        # --- 4. Filters on the Break Candle ---
        # Step 1: Check for RSI exhaustion on the break candle.
        candles_for_exhaustion_check = [break_candle]
        if not _is_rsi_not_exhausted(candles_for_exhaustion_check, signal, config):
            continue

        # Step 2: Check for confirmation on the break candle.
        if not is_signal_confirmed(break_candle, signal, config):
            continue
        
        use_volume = config.get("USE_VOLUME_CONFIRMATION", False)
        if use_volume and not (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, break_candle_index)):
            continue

        # --- 5. Confirmation Window Validation ---
        confirmation_df = df_indexed.iloc[break_candle_index + 1 : i + 1]
        
        consistency_count = 0
        for _, conf_candle in confirmation_df.iterrows():
            if level_type == 'resistance' and _is_breakout_candle(conf_candle, level):
                consistency_count += 1
            elif level_type == 'support' and _is_breakdown_candle(conf_candle, level):
                consistency_count += 1
        
        use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
        use_last_candle_max_volume = config.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

        volume_increasing_confirmed = not use_increasing_volume or is_volume_increasing(confirmation_df.reset_index())
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df.reset_index())

        is_confirmed = (
            consistency_count >= consistency_threshold and
            final_confirmation_candle['adx'] > signal_settings.ADX_CONFIRMATION_THRESHOLD and
            volume_increasing_confirmed and
            last_candle_max_volume_confirmed
        )

        # --- 6. Alert Generation ---
        if is_confirmed:
            alert = _create_alert(df_indexed, signal, final_confirmation_candle, break_candle, level, lookback_period)
            alerts.append(alert)
            last_alert_break_index = break_candle_index

            if not is_development_mode:
                return alerts
    
    return alerts[::-1]

def _create_alert(df_indexed, signal, confirmation_candle, break_candle, level, lookback_period):
    """Helper function to create an AlertData object."""
    alert_time = confirmation_candle['time']
    alert_price = confirmation_candle['close']
    
    # For this logic, start_time and start_price are less defined than with touch-based levels.
    # We can set them to the break candle's details.
    start_time = break_candle['time']
    if isinstance(start_time, pd.Timestamp):
        start_time = start_time.isoformat()
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
