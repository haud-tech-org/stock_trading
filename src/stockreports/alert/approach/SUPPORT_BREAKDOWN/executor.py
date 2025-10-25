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
    Entry point for the SUPPORT_BREAKDOWN approach.
    This approach identifies a "support shelf" and generates a SELL alert
    when the price breaks below it and shows immediate confirmation of weakness.
    """
    approach_name = "SUPPORT_BREAKDOWN"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_support_breakdown_alerts(df, config, approach_name, new_candle_count)
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

def _find_support_shelf(df_window: pd.DataFrame, config: dict) -> Generator[Tuple[float, List[int]], None, None]:
    """
    Phase 1: Identify a potential support shelf within a given window.
    This function is a generator, yielding all found support shelves.
    """
    price_tolerance = config.get("PRICE_TOLERANCE", 0.0025) # 0.25%
    min_touches = config.get("MIN_TOUCHES", 3)

    if len(df_window) < min_touches:
        return None

    # Sort by low price to group potential touches
    sorted_lows = df_window.sort_values(by='low').reset_index()

    for i in range(len(sorted_lows) - min_touches + 1):
        cluster = sorted_lows.iloc[i : i + min_touches]
        
        min_low_in_cluster = cluster['low'].min()
        max_low_in_cluster = cluster['low'].max()
        
        if (max_low_in_cluster - min_low_in_cluster) / min_low_in_cluster <= price_tolerance:
            support_level = min_low_in_cluster
            touch_indices = sorted(cluster['index'].tolist())
            logging.info(f"Found potential support shelf at {support_level:.2f} with {len(touch_indices)} touches at indices: {touch_indices}")
            yield support_level, touch_indices
            
    return None

def _is_breakdown_candle(candle: pd.Series, support_level: float) -> bool:
    """
    Phase 2: Check if a candle represents a clear breakdown below support.
    A breakdown is defined as the candle's close being below the support level.
    """
    return candle['close'] < support_level

def _is_volume_confirmed(df: pd.DataFrame, breakdown_index: int, config: dict) -> bool:
    """
    Phase 3: Check if the breakdown is supported by significant volume.
    """
    if not config.get("USE_VOLUME_CONFIRMATION", False):
        return True # Skip if not enabled

    volume_period = signal_settings.SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD
    volume_multiplier = signal_settings.SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER
    
    # Ensure we have enough data for the lookback
    if breakdown_index < volume_period:
        logging.warning(f"Not enough data for volume confirmation at index {breakdown_index}. Need {volume_period} periods.")
        return False

    # Define the window for calculating average volume, which is *before* the breakdown candle
    volume_window_start = breakdown_index - volume_period
    volume_window = df.iloc[volume_window_start:breakdown_index]
    
    if volume_window.empty:
        return False

    average_volume = volume_window['volume'].mean()
    breakdown_volume = df.iloc[breakdown_index]['volume']

    is_confirmed = breakdown_volume >= average_volume * volume_multiplier
    
    if is_confirmed:
        logging.info(f"Volume confirmed at index {breakdown_index}: Breakdown Volume ({breakdown_volume:.0f}) >= Avg Volume ({average_volume:.0f}) * {volume_multiplier}")
    else:
        logging.info(f"Volume NOT confirmed at index {breakdown_index}: Breakdown Volume ({breakdown_volume:.0f}) < Avg Volume ({average_volume:.0f}) * {volume_multiplier}")

    return is_confirmed

def _is_breakdown_confirmed(confirmation_candle: pd.Series, support_level: float, config: dict) -> bool:
    """
    Phase 4: Check for bearish confirmation on the next candle.
    Confirmation requires the candle to close below the support level and in the lower part of its own range.
    """
    is_below_support = confirmation_candle['close'] < support_level
    
    candle_range = confirmation_candle['high'] - confirmation_candle['low']
    if candle_range == 0:
        # For doji-like candles, just confirm if the close is below support
        return is_below_support

    close_position_in_range = (confirmation_candle['close'] - confirmation_candle['low']) / candle_range
    
    # The close must be in the lower part of the candle's range
    is_weak_close = close_position_in_range <= config.get("CONFIRMATION_CANDLE_BODY", 0.5)

    return is_below_support and is_weak_close

def _find_support_breakdown_alerts(df: pd.DataFrame, config: dict, approach_name: str, new_candle_count: int = 0) -> list[AlertData]:
    """
    Orchestrates the phases of finding a support breakdown alert.
    This version avoids lookahead bias by generating the alert on the confirmation candle.
    """
    alerts = []
    lookback_period = config.get("LOOKBACK_PERIOD", 60)
    cooldown_period = config.get("COOLDOWN_PERIOD", 30)
    last_alert_breakdown_index = -np.inf
    
    min_required_len = lookback_period + 2
    if len(df) < min_required_len:
        logging.warning(f"SUPPORT_BREAKDOWN: DataFrame has less than {min_required_len} rows, cannot generate alerts.")
        return alerts

    df_indexed = df.reset_index()

    # --- Main Analysis Loop ---
    # Use the same "warm-up" logic as other stateful executors (RCM, STRONG_CANDLE)
    start_index = 0
    if new_candle_count > 0:
        # Look back enough to establish state for the cooldown period
        lookback = lookback_period + cooldown_period + 5 
        start_index = max(0, len(df_indexed) - new_candle_count - lookback)
    
    # Start loop from a point where we have enough data for a full lookback
    start_index = max(min_required_len, start_index)

    for i in range(start_index, len(df_indexed)):
        # In this new logic, 'i' is the index of the CONFIRMATION candle.
        # The breakdown candle is at 'i - 1'.
        
        is_new_candle = (i >= len(df_indexed) - new_candle_count)
        breakdown_index = i - 1

        # --- 1. Cooldown Check ---
        if breakdown_index <= last_alert_breakdown_index + cooldown_period:
            continue

        confirmation_candle = df_indexed.iloc[i]
        breakdown_candle = df_indexed.iloc[breakdown_index]

        # --- 2. Basic Signal Check ---
        # The breakdown candle must be bearish.
        if breakdown_candle['close'] >= breakdown_candle['open']:
            continue
        
        # --- 3. Define Lookback Window for Shelf ---
        window_end = breakdown_index
        window_start = max(0, window_end - lookback_period)
        df_window = df_indexed.iloc[window_start:window_end]
        
        # --- 4. Find Support Shelf and Check for Breakdown ---
        shelf_generator = _find_support_shelf(df_window, config)
        
        for support_level, touch_indices in shelf_generator:
            # --- 5. Breakdown Confirmation ---
            if not _is_breakdown_candle(breakdown_candle, support_level):
                continue

            # --- 6. Volume Confirmation ---
            if not _is_volume_confirmed(df_indexed, breakdown_index, config):
                continue

            # --- 7. Bearish Confirmation (on the current candle 'i') ---
            if not _is_breakdown_confirmed(confirmation_candle, support_level, config):
                continue

            # --- 8. Alert Generation (if all checks pass) ---
            # Only generate alerts for new candles
            if is_new_candle:
                alert_time = confirmation_candle['time']
                alert_price = confirmation_candle['close']
                
                first_touch_candle = df_indexed.loc[touch_indices[0]]
                start_time = first_touch_candle['time']
                start_price = first_touch_candle['low']
                
                magnitude = ((support_level - alert_price) / support_level) * 100 if support_level > 0 else 0
                alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                details = {
                    "support_level": round(support_level, 2),
                    "breakdown_candle_time": breakdown_candle['time'].isoformat(),
                    "confirmation_candle_time": confirmation_candle['time'].isoformat(),
                    "support_touches": len(touch_indices),
                    "touch_times": [df_indexed.loc[idx, 'time'].isoformat() for idx in touch_indices]
                }

                alert = AlertData(
                    approach=approach_name,
                    id=alert_id,
                    signal='SELL',
                    alert_price=alert_price,
                    alert_time=alert_time,
                    start_price=start_price,
                    start_time=start_time,
                    magnitude=magnitude,
                    details=json.dumps(details)
                )
                alerts.append(alert)
                
                logging.info(f"Confirmed Support Breakdown Alert generated at {alert_time} for price {alert_price:.2f}")
                
                # Update last alert index and break from shelf loop since we found our alert
                last_alert_breakdown_index = breakdown_index
                break
            
    return alerts
