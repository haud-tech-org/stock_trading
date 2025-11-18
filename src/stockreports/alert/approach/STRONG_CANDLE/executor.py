# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()
validation_settings = loader.get_validation_settings()

# --- Project Imports ---
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    _is_rsi_not_exhausted,
    is_signal_confirmed
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.common.regime import has_divergence
from src.stockreports.alert.common.constants import Signal

# --- Module-level constant for the approach name ---
APPROACH_NAME = Approach.STRONG_CANDLE
CONFIG = signal_settings.APPROACH_CONFIG.get(
    APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
)

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the Strong Candle approach. It identifies candles with
    a strong close and a small tail, indicating decisive momentum.
    """
    try:
        logging.info(f"Running '{APPROACH_NAME}' approach...")
        
        alerts_data = _find_strong_candle_alerts(df, new_candle_count)
        logging.info(f"'{APPROACH_NAME}' approach found {len(alerts_data)} alerts.")

        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=alerts_df
        )
    except Exception as e:
        logging.error(f"An error occurred during '{APPROACH_NAME}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

def _find_strong_candle_alerts(df: pd.DataFrame, new_candle_count=0) -> list[AlertData]:
    """
    Finds alerts based on a state machine pattern, using a unified reverse loop.
    This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
    """
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    confirmation_window = CONFIG.get("CONFIRMATION_WINDOW", 4)
    # Total lookback needed: 1 for momentum, 1 for confirmation, plus the window to find the strong candle.
    required_lookback = confirmation_window + 2

    # All indicators must be prepared first.
    df = prepare_indicators(df)
    
    can_run_analysis = can_apply_analysis(df, APPROACH_NAME, required_rows=required_lookback)
    if not can_run_analysis:
        return alerts
    
    df_indexed = df.reset_index()

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1

    # The loop's scan depth is naturally handled by the value of `new_candle_count`.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    for i in range(loop_end, loop_start, -1):
        # Stop searching if we are past the active region for the current mode.
        if i < active_region_start:
            break

        momentum_candle = df_indexed.iloc[i]
        confirmation_candle = df_indexed.iloc[i-1]

        # --- Inverted State 1: Check for Momentum ---
        # Check if the current candle 'i' confirms the direction of the previous one.
        is_bullish_momentum = momentum_candle['close'] > confirmation_candle['close']
        is_bearish_momentum = momentum_candle['close'] < confirmation_candle['close']
        
        if not (is_bullish_momentum or is_bearish_momentum):
            continue
        
        potential_signal = Signal.BUY if is_bullish_momentum else Signal.SELL

        # --- Inverted State 2: Check for Advanced Confirmation ---
        # Check if the confirmation candle 'i-1' had the correct advanced signal.
        if not is_signal_confirmed(confirmation_candle, potential_signal, CONFIG):
            continue

        # --- Inverted State 3: Find the initial Strong Candle in the lookback window ---
        strong_candle_found = False
        strong_candle = None
        
        # Search for the strong candle in the window *before* the confirmation candle.
        search_window_start = max(0, i - 1 - confirmation_window)
        for j in range(i - 2, search_window_start - 1, -1):
            candidate_strong_candle = df_indexed.iloc[j]
            
            if pd.isna(candidate_strong_candle['body_size']):
                continue

            is_strong_bullish = (
                potential_signal == Signal.BUY and
                candidate_strong_candle['close'] > candidate_strong_candle['open'] and
                candidate_strong_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and
                candidate_strong_candle['upper_wick'] < candidate_strong_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )
            is_strong_bearish = (
                potential_signal == Signal.SELL and
                candidate_strong_candle['close'] < candidate_strong_candle['open'] and
                candidate_strong_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and
                candidate_strong_candle['lower_wick'] < candidate_strong_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )

            if is_strong_bullish or is_strong_bearish:
                strong_candle = candidate_strong_candle
                strong_candle_found = True
                break # Found the first valid strong candle, no need to look further back

        if not strong_candle_found:
            continue

        # --- All parts of the pattern found, now check final filters ---
        start_price = strong_candle['low'] if potential_signal == Signal.BUY else strong_candle['high']
        is_sufficient, magnitude = check_magnitude(momentum_candle['close'], start_price, CONFIG.get("MIN_ALERT_MAGNITUDE", 0))
        if not is_sufficient:
            continue

        # --- Final RSI exhaustion check on the candle before the strong candle ---
        # This validates the initiation of the move, not the conclusion.
        strong_candle_index = strong_candle.name
        if strong_candle_index > 0:
            candle_before_strong = df_indexed.iloc[strong_candle_index - 1]
            candles_for_exhaustion_check = [candle_before_strong]
            
            if not _is_rsi_not_exhausted(candles_for_exhaustion_check, potential_signal, CONFIG):
                continue

        # --- Volume Confirmation (Optional) ---
        volume_window_df = df_indexed.iloc[strong_candle.name : i + 1]
        use_volume_spike = CONFIG.get("USE_VOLUME_CONFIRMATION", False)
        use_increasing_volume = CONFIG.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
        use_last_candle_max_volume = CONFIG.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(volume_window_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(volume_window_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            continue

        # --- Alert Generation ---
        alert_time = momentum_candle['time']
        start_time = strong_candle['time']
        if isinstance(start_time, pd.Timestamp):
            start_time = start_time.isoformat()
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = {
            "strong_candle_time": strong_candle['time'].isoformat(),
            "confirmation_candle_time": confirmation_candle['time'].isoformat(),
            "momentum_candle_time": alert_time.isoformat(),
            "strong_candle_body": round(strong_candle['body_size'], 2)
        }

        alert_data = AlertData(
            approach=APPROACH_NAME,
            id=alert_id,
            signal=potential_signal,
            alert_price=momentum_candle['close'],
            alert_time=alert_time,
            start_price=start_price,
            start_time=start_time,
            magnitude=magnitude,
            details=json.dumps(details)
        )
        alerts.append(alert_data)

        if not is_development_mode:
            return alerts
            
    return alerts[::-1]
