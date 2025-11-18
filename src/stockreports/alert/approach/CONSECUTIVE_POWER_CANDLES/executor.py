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
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed, _is_rsi_not_exhausted
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.constants import Signal

logger = logging.getLogger(__name__)

# --- Module-level constant for the approach name ---
APPROACH_NAME = Approach.CONSECUTIVE_POWER_CANDLES
CONFIG = signal_settings.APPROACH_CONFIG.get(
    APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
)

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSECUTIVE_POWER_CANDLES approach.
    """
    try:
        logger.info(f"Running '{APPROACH_NAME}' approach...")

        alerts_data = _find_power_candle_alerts(df, new_candle_count)
        logger.info(f"'{APPROACH_NAME}' approach found {len(alerts_data)} alerts.")

        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=alerts_df
        )
    except Exception as e:
        logger.error(f"An error occurred during '{APPROACH_NAME}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

def _analyze_window(window: pd.DataFrame, df_indexed: pd.DataFrame) -> Optional[AlertData]:
    """
    Analyzes a window for a configurable number of consecutive power candles.
    """
    # --- 1. Get config and validate pattern structure ---
    candle_count = CONFIG.get("CANDLE_COUNT", 3)
    min_body_ratio = CONFIG.get("MIN_BODY_TO_RANGE_RATIO", 0.7)
    use_volume = CONFIG.get("USE_VOLUME_CONFIRMATION", False)
    use_last_candle_max_volume = CONFIG.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
    min_pre_candle_body_sizes = CONFIG.get("MIN_PRE_CANDLE_BODY_SIZES", [])

    if len(window) != candle_count:
        return None

    # --- 2. Check for consistent direction ---
    is_all_bullish = all(window['close'] > window['open'])
    is_all_bearish = all(window['close'] < window['open'])

    if not (is_all_bullish or is_all_bearish):
        return None

    signal = Signal.BUY if is_all_bullish else Signal.SELL

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
        logger.warning(f"Config mismatch: CANDLE_COUNT is {candle_count}, but MIN_PRE_CANDLE_BODY_SIZES has {len(min_pre_candle_body_sizes)} entries. Skipping.")
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

    # --- 8. Validation Step 1: RSI Exhaustion Check ---
    # Use the "setup candle" (before the pattern) to ensure the move isn't starting from an exhausted state.
    first_candle_index = df_indexed.index.get_loc(window.iloc[0].name)
    setup_candle = df_indexed.iloc[first_candle_index - 1] if first_candle_index > 0 else None
    
    if CONFIG.get("USE_RSI_EXHAUSTION_FILTER", False):
        candles_for_exhaustion_check = [setup_candle] if setup_candle is not None else []
        if not _is_rsi_not_exhausted(candles_for_exhaustion_check, signal, CONFIG):
            return None

    # --- 9. Validation Step 2: Signal Confirmation ---
    # Use the "final candle" of the pattern for all standard confirmation checks (MA, MACD, etc.).
    final_candle = window.iloc[-1]
    if not is_signal_confirmed(final_candle, signal, CONFIG):
        return None

    # --- 10. If all checks pass, create an alert ---
    logger.info(f"[{final_candle.name}] SUCCESS: Consecutive Power Candles Pattern Found! Signal: {signal}")

    alert_id = str(int(final_candle.name.tz_convert('UTC').timestamp()))
    start_candle = window.iloc[0]

    alert_data = AlertData(
        approach=APPROACH_NAME,
        id=alert_id,
        signal=signal,
        alert_price=final_candle['close'],
        alert_time=final_candle.name,
        start_price=start_candle['open'],
        start_time=start_candle.name,
        magnitude=round(abs(final_candle['close'] - start_candle['open']), 2),
        details=json.dumps({
            "reason": f"{candle_count} consecutive power candles with body/open progression detected.",
            "pattern_start_time": int(start_candle.name.tz_convert('UTC').timestamp()),
            "last_candle_volume": final_candle['volume']
        })
    )
    return alert_data


def _find_power_candle_alerts(df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    """
    Finds alerts based on the consecutive power candles pattern.
    This function uses a truly unified reverse loop for both deployment and development modes.
    The loop's scan depth is naturally handled by the value of `new_candle_count`.
    """
    alerts = []
    window_size = CONFIG.get("CANDLE_COUNT", 3)
    is_development_mode = settings.MODE == Mode.DEVELOPMENT

    # All indicators must be prepared first.
    df = prepare_indicators(df)

    can_run_analysis = can_apply_analysis(df, APPROACH_NAME, required_rows=window_size)
    if not can_run_analysis:
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
        
        # No need to pre-check signal here, _analyze_window handles it all
        alert = _analyze_window(window, df_indexed)
        
        if alert:
            alerts.append(alert)
            # In DEPLOYMENT mode, we exit immediately after finding the first (latest) alert.
            if not is_development_mode:
                return alerts

    # In DEVELOPMENT mode, the loop completes. Return all found alerts in chronological order.
    return alerts[::-1]
