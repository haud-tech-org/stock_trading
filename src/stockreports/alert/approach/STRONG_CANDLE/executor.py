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
    check_advanced_confirmation, 
    can_apply_advanced_confirmation,
    get_min_data_required_for_advanced_confirmation
)
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation, is_last_candle_volume_max
from src.stockreports.alert.common.regime import is_regime_favorable, prepare_regime_indicators

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the Strong Candle approach. It identifies candles with
    a strong close and a small tail, indicating decisive momentum.
    """
    approach_name = Approach.STRONG_CANDLE
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        df = prepare_regime_indicators(df, config)
        
        alerts_data = _find_strong_candle_alerts(df, config, new_candle_count)
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

def _find_strong_candle_alerts(df: pd.DataFrame, config: dict, new_candle_count=0) -> list[AlertData]:
    """
    Finds alerts based on a state machine pattern, using a unified reverse loop.
    This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
    """
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    # This approach requires advanced confirmation.
    if not can_apply_advanced_confirmation(df):
        min_data_required = get_min_data_required_for_advanced_confirmation()
        logging.warning(
            f"{Approach.STRONG_CANDLE}: Insufficient data for advanced confirmation "
            f"(have {len(df)}, need {min_data_required}). "
            "Cannot generate alerts for this approach."
        )
        return alerts

    logging.info(f"{Approach.STRONG_CANDLE}: Sufficient data available ({len(df)} candles). Advanced confirmation will be used.")
    df = prepare_indicators(df)
    
    confirmation_window = config.get("CONFIRMATION_WINDOW", 4)
    # Total lookback needed: 1 for momentum, 1 for confirmation, plus the window to find the strong candle.
    required_lookback = confirmation_window + 2
    
    if len(df) < required_lookback:
        return alerts

    df_indexed = df.reset_index()

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1

    # The loop's scan depth is naturally optimized by this calculation.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    # 'i' is the index of the final momentum candle (the alert candle).
    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region for the current mode.

        momentum_candle = df_indexed.iloc[i]
        confirmation_candle = df_indexed.iloc[i-1]

        # --- Inverted State 1: Check for Momentum ---
        # Check if the current candle 'i' confirms the direction of the previous one.
        is_bullish_momentum = momentum_candle['close'] > confirmation_candle['close']
        is_bearish_momentum = momentum_candle['close'] < confirmation_candle['close']
        
        if not (is_bullish_momentum or is_bearish_momentum):
            continue
        
        potential_signal = 'BUY' if is_bullish_momentum else 'SELL'

        # --- Inverted State 2: Check for Advanced Confirmation ---
        # Check if the confirmation candle 'i-1' had the correct advanced signal.
        adv_signal = check_advanced_confirmation(confirmation_candle, df_indexed.iloc[i-2])
        if adv_signal != potential_signal:
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
                potential_signal == 'BUY' and
                candidate_strong_candle['close'] > candidate_strong_candle['open'] and
                candidate_strong_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and
                candidate_strong_candle['upper_wick'] < candidate_strong_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )
            is_strong_bearish = (
                potential_signal == 'SELL' and
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
        start_price = strong_candle['low'] if potential_signal == 'BUY' else strong_candle['high']
        is_sufficient, magnitude = check_magnitude(momentum_candle['close'], start_price, config.get("MIN_ALERT_MAGNITUDE", 0))
        if not is_sufficient:
            continue

        # Volume Confirmation
        volume_window_df = df_indexed.iloc[strong_candle.name : i + 1]
        use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
        use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
        use_last_candle_max_volume = config.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

        volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
        volume_is_increasing = not use_increasing_volume or is_volume_increasing(volume_window_df)
        last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(volume_window_df)

        if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
            continue

        # Regime Filter
        use_regime_filter = config.get("USE_MARKET_REGIME_FILTER", False)
        if use_regime_filter and not is_regime_favorable(momentum_candle, potential_signal, config):
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
            "strong_candle_body": round(strong_candle['body_size'], 2),
            "used_advanced_confirmation": True,
            "used_regime_filter": use_regime_filter
        }

        alert_data = AlertData(
            approach=Approach.STRONG_CANDLE,
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
