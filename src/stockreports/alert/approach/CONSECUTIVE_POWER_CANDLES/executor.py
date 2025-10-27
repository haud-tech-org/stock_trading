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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed

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
    Analyzes a window for 3 consecutive power candles with advanced logic.
    """
    # --- 1. Get config and define pattern structure ---
    candle_count = config.get("CANDLE_COUNT", 3)
    min_body_ratio = config.get("MIN_BODY_TO_RANGE_RATIO", 0.7)
    use_volume = config.get("USE_VOLUME_CONFIRMATION", True)
    min_body_t_minus_2 = config.get("MIN_BODY_SIZE_T_MINUS_2", 3.0)
    min_body_t_minus_1 = config.get("MIN_BODY_SIZE_T_MINUS_1", 3.0)

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
    # Avoid division by zero if range is 0
    window_body_ratio = (window['body'] / window['range']).fillna(0)
    if not all(window_body_ratio >= min_body_ratio):
        return None

    # --- 5. Split into individual candles for specific checks ---
    t_minus_2 = window.iloc[0]
    t_minus_1 = window.iloc[1]
    t = window.iloc[2]

    # --- 6. Check minimum body sizes for T-2 and T-1 ---
    if t_minus_2['body'] < min_body_t_minus_2:
        return None
    if t_minus_1['body'] < min_body_t_minus_1:
        return None

    # --- 7. Check open vs. average body price progression ---
    if is_all_bullish:
        if not (t_minus_1['open'] > t_minus_2['avg_body_price'] and t['open'] > t_minus_1['avg_body_price']):
            return None
    elif is_all_bearish:
        if not (t_minus_1['open'] < t_minus_2['avg_body_price'] and t['open'] < t_minus_1['avg_body_price']):
            return None

    # --- 8. Volume spike confirmation on the last candle (T) ---
    if use_volume:
        last_candle_index = df_indexed.index.get_loc(t.name)
        if not is_volume_spike_confirmed(df_indexed.reset_index(), last_candle_index, use_volume):
            return None

    # --- 9. If all checks pass, create an alert ---
    logging.info(f"[{t.name}] SUCCESS: Consecutive Power Candles Pattern Found! Signal: {signal}")

    alert_id = str(int(t.name.tz_convert('UTC').timestamp()))
    start_time_ts = int(t_minus_2.name.tz_convert('UTC').timestamp())

    alert_data = AlertData(
        approach=Approach.CONSECUTIVE_POWER_CANDLES,
        id=alert_id,
        signal=signal,
        alert_price=t['close'],
        alert_time=t.name,
        start_price=t_minus_2['open'],
        start_time=t_minus_2.name,
        magnitude=round(abs(t['close'] - t_minus_2['open']), 2),
        details=json.dumps({
            "reason": f"{candle_count} consecutive power candles with body/open progression detected.",
            "pattern_start_time": start_time_ts,
            "last_candle_volume": t['volume']
        })
    )
    return alert_data


def _find_power_candle_alerts(df: pd.DataFrame, config: dict, new_candle_count: int = 0) -> list[AlertData]:
    """
    Finds alerts based on the consecutive power candles pattern.
    """
    alerts = []
    window_size = config.get("CANDLE_COUNT", 3)

    if len(df) < window_size:
        logging.warning(f"{Approach.CONSECUTIVE_POWER_CANDLES}: DataFrame has less than {window_size} rows, cannot generate alerts.")
        return alerts

    df_indexed = df.set_index('time')
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    grace_period = window_size

    for i in range(window_size - 1, len(df_indexed)):
        is_new_alert = not is_development_mode and (i >= len(df_indexed) - (new_candle_count + grace_period))
        
        window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
        
        alert = _analyze_window(window, df_indexed, config)
        
        if alert and (is_development_mode or is_new_alert):
            alerts.append(alert)

    return alerts
