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
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, check_advanced_confirmation
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.model.models import AlertResult, AlertData

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the Strong Candle approach. It identifies candles with
    a strong close and a small tail, indicating decisive momentum.
    """
    approach_name = "STRONG_CANDLE"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
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
    Finds alerts based on strong candle patterns, but with added confirmation and
    magnitude checks inspired by the RCM approach.
    """
    alerts = []
    if len(df) < 2:
        return alerts

    df = prepare_indicators(df)
    
    trend_state = 'NEUTRAL'  # NEUTRAL, CONFIRMING
    last_strong_candle_idx = -1
    last_strong_candle_type = None # 'bullish' or 'bearish'
    confirmation_deadline = -1

    confirmation_window = config.get("CONFIRMATION_WINDOW", 4)
    use_advanced_confirmation = config.get("USE_ADVANCED_CONFIRMATION", True) # Default to True for this approach

    # --- 1. Initial Settings ---
    df_indexed = df.reset_index()
    
    # Determine the starting point for the loop.
    start_index = 0
    # In deployment mode, we need to look back further than just the new candles
    # to correctly establish the state of the state machine.
    # The lookback should be at least the size of the confirmation window.
    if new_candle_count > 0:
        lookback = confirmation_window + 5 # Add a small buffer
        start_index = max(0, len(df_indexed) - new_candle_count - lookback)

    for i in range(start_index, len(df_indexed)):
        # The check for new candles is now simplified as new_candle_count is always > 0
        is_new_candle = (i >= len(df_indexed) - new_candle_count)

        current_candle = df_indexed.iloc[i]
        
        # --- 2. Basic Signal Check ---
        if pd.isna(current_candle['body_size']) or pd.isna(current_candle['upper_wick']) or pd.isna(current_candle['lower_wick']):
            continue

        # 1. Look for a new strong candle to start the process if we are neutral
        if trend_state == 'NEUTRAL':
            is_strong_bullish = (
                current_candle['close'] > current_candle['open'] and
                current_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and # ENHANCEMENT: Pre-filter by body size
                current_candle['upper_wick'] < current_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )
            is_strong_bearish = (
                current_candle['close'] < current_candle['open'] and
                current_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and # ENHANCEMENT: Pre-filter by body size
                current_candle['lower_wick'] < current_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )

            if is_strong_bullish:
                trend_state = 'CONFIRMING'
                last_strong_candle_idx = i
                last_strong_candle_type = 'bullish'
                confirmation_deadline = i + confirmation_window
            elif is_strong_bearish:
                trend_state = 'CONFIRMING'
                last_strong_candle_idx = i
                last_strong_candle_type = 'bearish'
                confirmation_deadline = i + confirmation_window
        
        # 2. If we are confirming, look for a signal within the window
        elif trend_state == 'CONFIRMING':
            if i > confirmation_deadline:
                trend_state = 'NEUTRAL'
                continue

            signal = None
            adv_signal = check_advanced_confirmation(
                current_candle, 
                df_indexed.iloc[i-1]
            )
            
            if adv_signal == 'BUY' and last_strong_candle_type == 'bullish':
                signal = 'BUY'
            elif adv_signal == 'SELL' and last_strong_candle_type == 'bearish':
                signal = 'SELL'

            if signal:
                # --- ENHANCEMENT: Add momentum confirmation from the next candle ---
                # This check requires looking ahead, which can be problematic.
                # Ensure we don't go out of bounds.
                if i + 1 >= len(df_indexed):
                    continue

                momentum_confirmed = False
                if signal == 'BUY' and df_indexed.iloc[i+1]['close'] > current_candle['close']:
                    momentum_confirmed = True
                elif signal == 'SELL' and df_indexed.iloc[i+1]['close'] < current_candle['close']:
                    momentum_confirmed = True

                if momentum_confirmed:
                    start_price = df_indexed.iloc[last_strong_candle_idx]['low'] if signal == 'BUY' else df_indexed.iloc[last_strong_candle_idx]['high']
                    current_price = current_candle['close']
                    
                    is_sufficient, magnitude = check_magnitude(current_price, start_price, signal_settings)

                    if is_sufficient and is_new_candle: # Only create alert for new candles
                        alert_time = current_candle['time']
                        start_time = df_indexed.iloc[last_strong_candle_idx]['time']
                        
                        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                        details = {
                            "strong_candle_body": round(df_indexed.iloc[last_strong_candle_idx]['body_size'], 2),
                            "confirmation_window": confirmation_window,
                            "used_advanced_confirmation": use_advanced_confirmation,
                            "momentum_confirmed": True
                        }

                        alert_data = AlertData(
                            approach="STRONG_CANDLE",
                            id=alert_id,
                            signal=signal,
                            alert_price=current_price,
                            alert_time=alert_time,
                            start_price=start_price,
                            start_time=start_time,
                            magnitude=magnitude,
                            details=json.dumps(details)
                        )
                        alerts.append(alert_data)
                        
                        # Reset to neutral after a successful alert to find the next one
                        trend_state = 'NEUTRAL'
            
    return alerts
