import pandas as pd
import logging
import json
import numpy as np
from typing import Optional

from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.common.regime import prepare_regime_indicators, is_regime_favorable

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSECUTIVE_POWER_CANDLES approach.
    """
    approach_name = Approach.CONSECUTIVE_POWER_CANDLES
    try:
        logging.info(f"Running '{approach_name}' approach...")
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )

        # Prepare indicators here, before calling the analysis function.
        if config.get("USE_MARKET_REGIME_FILTER", False):
            df = prepare_regime_indicators(df, config)

        alerts_data = _find_power_candle_alerts(df, config, new_candle_count)
        logging.info(f"'{approach_name}' approach found {len(alerts_data)} alerts.")

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

def _analyze_window(window: pd.DataFrame, df_indexed: pd.DataFrame, config: dict) -> Optional[AlertData]:
    """
    Analyzes a window for a configurable number of consecutive power candles.
    """
    # --- 1. Get config and validate pattern structure ---
    candle_count = config.get("CANDLE_COUNT", 3)
    min_body_ratio = config.get("MIN_BODY_TO_RANGE_RATIO", 0.7)
    use_volume = config.get("USE_VOLUME_CONFIRMATION", False)
    use_last_candle_max_volume = config.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
    min_pre_candle_body_sizes = config.get("MIN_PRE_CANDLE_BODY_SIZES", [])

    if len(window) != candle_count:
        return None

    # --- 2. Check for consistent direction ---
    is_all_bullish = all(window['close'] > window['open'])
    is_all_bearish = all(window['close'] < window['open'])

    if not (is_all_bullish or is_all_bearish):
        return None

    signal = 'BUY' if is_all_bullish else 'SELL'

    # --- 3. Calculate body, range, and average body price for all candles ---
    window['body'] = abs(window['close'] - window['open'])
    window['range'] = window['high'] - window['low']
    window['avg_body_price'] = (window['open'] + window['close']) / 2

    # --- 4. Apply MIN_BODY_TO_RANGE_RATIO to all candles ---
    window_body_ratio = (window['body'] / window['range']).fillna(0)
    if not all(window_body_ratio >= min_body_ratio):
        return None

    # --- 5. Dynamic validation for pre-candles ---
    pre_candles = window.iloc[:-1]
    
    # Config validation: Ensure the number of body size rules matches the number of pre-candles
    if len(min_pre_candle_body_sizes) != len(pre_candles):
        logging.warning(f"Config mismatch: CANDLE_COUNT is {candle_count}, but MIN_PRE_CANDLE_BODY_SIZES has {len(min_pre_candle_body_sizes)} entries. Skipping.")
        return None

    # Check minimum body sizes for all pre-candles
    for i, min_size in enumerate(min_pre_candle_body_sizes):
        if pre_candles.iloc[i]['body'] < min_size:
            return None

    # --- 6. Dynamic check for open vs. average body price progression ---
    for i in range(1, len(window)):
        current_candle = window.iloc[i]
        prev_candle = window.iloc[i-1]
        
        if is_all_bullish:
            if not (current_candle['open'] > prev_candle['avg_body_price']):
                return None
        elif is_all_bearish:
            if not (current_candle['open'] < prev_candle['avg_body_price']):
                return None

    # --- 7. Volume spike confirmation on the last candle ---
    last_candle = window.iloc[-1]
    if use_volume:
        last_candle_index = df_indexed.index.get_loc(last_candle.name)
        if not (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), last_candle_index)):
            return None

    if use_last_candle_max_volume:
        if not is_last_candle_volume_max(window):
            return None

    # --- 8. If all checks pass, create an alert ---
    logging.info(f"[{last_candle.name}] SUCCESS: Consecutive Power Candles Pattern Found! Signal: {signal}")

    alert_id = str(int(last_candle.name.tz_convert('UTC').timestamp()))
    start_candle = window.iloc[0]

    alert_data = AlertData(
        approach=Approach.CONSECUTIVE_POWER_CANDLES,
        id=alert_id,
        signal=signal,
        alert_price=last_candle['close'],
        alert_time=last_candle.name,
        start_price=start_candle['open'],
        start_time=start_candle.name,
        magnitude=round(abs(last_candle['close'] - start_candle['open']), 2),
        details=json.dumps({
            "reason": f"{candle_count} consecutive power candles with body/open progression detected.",
            "pattern_start_time": int(start_candle.name.tz_convert('UTC').timestamp()),
            "last_candle_volume": last_candle['volume']
        })
    )
    return alert_data


def _find_power_candle_alerts(df: pd.DataFrame, config: dict, new_candle_count: int = 0) -> list[AlertData]:
    """
    Finds alerts based on the consecutive power candles pattern.
    This function uses a truly unified reverse loop for both deployment and development modes.
    The loop's scan depth is naturally handled by the value of `new_candle_count`.
    """
    alerts = []
    window_size = config.get("CANDLE_COUNT", 3)
    use_regime_filter = config.get("USE_MARKET_REGIME_FILTER", False)
    is_development_mode = settings.MODE == Mode.DEVELOPMENT

    if len(df) < window_size:
        logging.warning(f"{Approach.CONSECUTIVE_POWER_CANDLES}: DataFrame has less than {window_size} rows, cannot generate alerts.")
        return alerts

    df_indexed = df.set_index('time')

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = window_size - 1
    
    # The loop's scan depth is naturally optimized by this calculation.
    # In DEV mode, new_candle_count is len(df), so active_region_start is negative, and the loop runs fully.
    # In DEPLOY mode, new_candle_count is small, so the loop breaks early.
    active_region_start = len(df_indexed) - new_candle_count - window_size

    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region for the current mode.

        window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()

        if use_regime_filter:
            is_bullish_signal = all(window['close'] > window['open'])
            is_bearish_signal = all(window['close'] < window['open'])
            potential_signal = 'BUY' if is_bullish_signal else ('SELL' if is_bearish_signal else None)
            
            if potential_signal:
                current_candle_for_regime = df_indexed.iloc[i]
                if not is_regime_favorable(current_candle_for_regime, potential_signal, config):
                    continue
        
        alert = _analyze_window(window, df_indexed, config)
        
        if alert:
            alerts.append(alert)
            # In DEPLOYMENT mode, we exit immediately after finding the first (latest) alert.
            if not is_development_mode:
                return alerts

    # In DEVELOPMENT mode, the loop completes. Return all found alerts in chronological order.
    return alerts[::-1]
