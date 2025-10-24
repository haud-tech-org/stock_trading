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

def run_analysis(df: pd.DataFrame) -> AlertResult:
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
        
        alerts_data = _find_strong_candle_alerts(df, config)
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

def _find_strong_candle_alerts(df: pd.DataFrame, config: dict) -> list[AlertData]:
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

    for i in range(1, len(df) -1): # Stop one candle earlier to allow for momentum check
        candle = df.iloc[i]
        prev_candle = df.iloc[i-1]
        next_candle = df.iloc[i+1] # Look at the next candle for momentum

        if pd.isna(candle['body_size']) or pd.isna(candle['upper_wick']) or pd.isna(candle['lower_wick']):
            continue

        # 1. Look for a new strong candle to start the process if we are neutral
        if trend_state == 'NEUTRAL':
            is_strong_bullish = (
                candle['close'] > candle['open'] and
                candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and # ENHANCEMENT: Pre-filter by body size
                candle['upper_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )
            is_strong_bearish = (
                candle['close'] < candle['open'] and
                candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and # ENHANCEMENT: Pre-filter by body size
                candle['lower_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
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
            adv_signal = check_advanced_confirmation(candle, prev_candle)
            
            if adv_signal == 'BUY' and last_strong_candle_type == 'bullish':
                signal = 'BUY'
            elif adv_signal == 'SELL' and last_strong_candle_type == 'bearish':
                signal = 'SELL'

            if signal:
                # --- ENHANCEMENT: Add momentum confirmation from the next candle ---
                momentum_confirmed = False
                if signal == 'BUY' and next_candle['close'] > candle['close']:
                    momentum_confirmed = True
                elif signal == 'SELL' and next_candle['close'] < candle['close']:
                    momentum_confirmed = True

                if momentum_confirmed:
                    start_price = df.iloc[last_strong_candle_idx]['low'] if signal == 'BUY' else df.iloc[last_strong_candle_idx]['high']
                    current_price = candle['close']
                    
                    is_sufficient, magnitude = check_magnitude(current_price, start_price, signal_settings)

                    if is_sufficient:
                        alert_time = candle['time']
                        start_time = df.iloc[last_strong_candle_idx]['time']
                        
                        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                        details = {
                            "strong_candle_body": round(df.iloc[last_strong_candle_idx]['body_size'], 2),
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
