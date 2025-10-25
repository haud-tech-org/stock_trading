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

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the SUPPORT_RESISTANCE_BREAK approach.
    This approach identifies:
    1. "Support Shelf" and generates a SELL alert on a confirmed breakdown.
    2. "Resistance Ceiling" and generates a BUY alert on a confirmed breakout.
    """
    approach_name = "SUPPORT_RESISTANCE_BREAK"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_break_alerts(df, config, approach_name, new_candle_count)
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

# --- LEVEL IDENTIFICATION ---

def _find_support_shelf(df_window: pd.DataFrame, config: dict) -> Generator[Tuple[float, List[int]], None, None]:
    """Identifies a potential support shelf (floor) based on 'low' prices."""
    price_tolerance = config.get("PRICE_TOLERANCE", 0.0025)
    min_touches = config.get("MIN_TOUCHES", 3)

    if len(df_window) < min_touches:
        return

    sorted_prices = df_window.sort_values(by='low').reset_index()

    for i in range(len(sorted_prices) - min_touches + 1):
        cluster = sorted_prices.iloc[i : i + min_touches]
        min_price = cluster['low'].min()
        max_price = cluster['low'].max()
        
        if (max_price - min_price) / min_price <= price_tolerance:
            level = min_price
            touch_indices = sorted(cluster['index'].tolist())
            yield level, touch_indices

def _find_resistance_ceiling(df_window: pd.DataFrame, config: dict) -> Generator[Tuple[float, List[int]], None, None]:
    """Identifies a potential resistance ceiling based on 'high' prices."""
    price_tolerance = config.get("PRICE_TOLERANCE", 0.0025)
    min_touches = config.get("MIN_TOUCHES", 3)

    if len(df_window) < min_touches:
        return

    sorted_prices = df_window.sort_values(by='high').reset_index()

    for i in range(len(sorted_prices) - min_touches + 1):
        cluster = sorted_prices.iloc[i : i + min_touches]
        min_price = cluster['high'].min()
        max_price = cluster['high'].max()
        
        if (max_price - min_price) / min_price <= price_tolerance:
            level = max_price
            touch_indices = sorted(cluster['index'].tolist())
            yield level, touch_indices

# --- BREAK AND CONFIRMATION CHECKS ---

def _is_breakdown_candle(candle: pd.Series, support_level: float) -> bool:
    """Checks if a candle closes below the support level."""
    return candle['close'] < support_level

def _is_breakout_candle(candle: pd.Series, resistance_level: float) -> bool:
    """Checks if a candle closes above the resistance level."""
    return candle['close'] > resistance_level

def _is_volume_confirmed(df: pd.DataFrame, break_index: int, config: dict) -> bool:
    """Checks if the break is supported by significant volume."""
    if not config.get("USE_VOLUME_CONFIRMATION", False):
        return True

    volume_period = signal_settings.SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD
    volume_multiplier = signal_settings.SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER
    
    if break_index < volume_period:
        return False

    volume_window = df.iloc[max(0, break_index - volume_period):break_index]
    if volume_window.empty:
        return False

    average_volume = volume_window['volume'].mean()
    break_volume = df.iloc[break_index]['volume']
    return break_volume >= average_volume * volume_multiplier

def _is_breakdown_confirmed(candle: pd.Series, support_level: float, config: dict) -> bool:
    """Checks for bearish confirmation (closes below support, weak close)."""
    is_below_support = candle['close'] < support_level
    candle_range = candle['high'] - candle['low']
    if candle_range == 0: return is_below_support
    close_pos = (candle['close'] - candle['low']) / candle_range
    is_weak_close = close_pos <= config.get("CONFIRMATION_CANDLE_BODY_SELL", 0.5)
    return is_below_support and is_weak_close

def _is_breakout_confirmed(candle: pd.Series, resistance_level: float, config: dict) -> bool:
    """Checks for bullish confirmation (closes above resistance, strong close)."""
    is_above_resistance = candle['close'] > resistance_level
    candle_range = candle['high'] - candle['low']
    if candle_range == 0: return is_above_resistance
    close_pos = (candle['close'] - candle['low']) / candle_range
    is_strong_close = close_pos >= config.get("CONFIRMATION_CANDLE_BODY_BUY", 0.5)
    return is_above_resistance and is_strong_close

# --- ALERT ORCHESTRATION ---

def _find_break_alerts(df: pd.DataFrame, config: dict, approach_name: str, new_candle_count: int = 0) -> list[AlertData]:
    """Orchestrates finding both support breakdown and resistance breakout alerts."""
    alerts = []
    lookback_period = config.get("LOOKBACK_PERIOD", 60)
    cooldown_period = config.get("COOLDOWN_PERIOD", 30)
    last_alert_break_index = -np.inf
    
    min_required_len = lookback_period + 2
    if len(df) < min_required_len:
        return alerts

    df_indexed = df.reset_index()

    start_index = 0
    if new_candle_count > 0:
        lookback = lookback_period + cooldown_period + 5 
        start_index = max(0, len(df_indexed) - new_candle_count - lookback)
    
    start_index = max(min_required_len, start_index)

    for i in range(start_index, len(df_indexed)):
        break_index = i - 1
        if break_index <= last_alert_break_index + cooldown_period:
            continue

        confirmation_candle = df_indexed.iloc[i]
        break_candle = df_indexed.iloc[break_index]
        
        window_end = break_index
        window_start = max(0, window_end - lookback_period)
        df_window = df_indexed.iloc[window_start:window_end]

        alert_generated_this_iteration = False

        # --- Check for Support Breakdown (SELL) ---
        if break_candle['close'] < break_candle['open']: # Must be a bearish break candle
            for support_level, touch_indices in _find_support_shelf(df_window, config):
                if (_is_breakdown_candle(break_candle, support_level) and
                    _is_volume_confirmed(df_indexed, break_index, config) and
                    _is_breakdown_confirmed(confirmation_candle, support_level, config)):
                    
                    if (i >= len(df_indexed) - new_candle_count):
                        alert = _create_alert(df_indexed, 'SELL', confirmation_candle, break_candle, support_level, touch_indices, approach_name)
                        alerts.append(alert)
                        logging.info(f"Confirmed Support Breakdown Alert at {alert.alert_time} for price {alert.alert_price:.2f}")
                        last_alert_break_index = break_index
                        alert_generated_this_iteration = True
                        break # Move to next candle
            
        # If a SELL alert was generated, skip the BUY check for this candle
        if alert_generated_this_iteration:
            continue

        # --- Check for Resistance Breakout (BUY) ---
        if break_candle['close'] > break_candle['open']: # Must be a bullish break candle
            for resistance_level, touch_indices in _find_resistance_ceiling(df_window, config):
                if (_is_breakout_candle(break_candle, resistance_level) and
                    _is_volume_confirmed(df_indexed, break_index, config) and
                    _is_breakout_confirmed(confirmation_candle, resistance_level, config)):

                    if (i >= len(df_indexed) - new_candle_count):
                        alert = _create_alert(df_indexed, 'BUY', confirmation_candle, break_candle, resistance_level, touch_indices, approach_name)
                        alerts.append(alert)
                        logging.info(f"Confirmed Resistance Breakout Alert at {alert.alert_time} for price {alert.alert_price:.2f}")
                        last_alert_break_index = break_index
                        break # Move to next candle
    return alerts

def _create_alert(df_indexed, signal, confirmation_candle, break_candle, level, touch_indices, approach_name):
    """Helper function to create an AlertData object."""
    alert_time = confirmation_candle['time']
    alert_price = confirmation_candle['close']
    
    first_touch_candle = df_indexed.loc[touch_indices[0]]
    start_time = first_touch_candle['time']
    start_price = first_touch_candle['low'] if signal == 'SELL' else first_touch_candle['high']
    
    if signal == 'SELL':
        magnitude = ((level - alert_price) / level) * 100 if level > 0 else 0
        level_type = "support_level"
    else: # BUY
        magnitude = ((alert_price - level) / level) * 100 if level > 0 else 0
        level_type = "resistance_level"

    alert_id = f"{signal}-{int(alert_time.tz_convert('UTC').timestamp())}"

    details = {
        level_type: round(level, 2),
        "break_candle_time": break_candle['time'].isoformat(),
        "confirmation_candle_time": confirmation_candle['time'].isoformat(),
        "level_touches": len(touch_indices),
        "touch_times": [df_indexed.loc[idx, 'time'].isoformat() for idx in touch_indices]
    }

    return AlertData(
        approach=approach_name,
        id=alert_id,
        signal=signal,
        alert_price=alert_price,
        alert_time=alert_time,
        start_price=start_price,
        start_time=start_time,
        magnitude=magnitude,
        details=json.dumps(details)
    )
