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
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, is_volume_increasing, can_apply_volume_confirmation

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
    Finds alerts based on a state machine:
    1. STRONG_CANDLE: A candle with a large body and small wick.
    2. CONFIRMATION: An advanced signal (e.g., from RSI/MACD) in the same direction.
    3. MOMENTUM: The next candle continues in the same direction.
    The alert is triggered on the MOMENTUM candle.
    """
    alerts = []
    
    # This approach requires advanced confirmation. Check if we can apply it.
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
    
    # State machine: NEUTRAL -> AWAITING_CONFIRMATION -> AWAITING_MOMENTUM
    trend_state = 'NEUTRAL'
    strong_candle_idx = -1
    confirmation_candle_idx = -1
    signal_direction = None

    df_indexed = df.reset_index()
    
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    # It's the confirmation window + 1 for the final momentum candle.
    grace_period = config.get("CONFIRMATION_WINDOW", 4) + 1

    # The loop now iterates over the entire dataframe to find all historical alerts.
    for i in range(1, len(df_indexed)):
        # In deployment mode, check if the alert is recent enough to be notified.
        is_new_alert = not is_development_mode and (i >= len(df_indexed) - (new_candle_count + grace_period))
        
        current_candle = df_indexed.iloc[i]
        
        if pd.isna(current_candle['body_size']):
            continue

        # --- STATE: NEUTRAL -> AWAITING_CONFIRMATION ---
        # Look for a new strong candle to start the sequence.
        if trend_state == 'NEUTRAL':
            is_strong_bullish = (
                current_candle['close'] > current_candle['open'] and
                current_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and
                current_candle['upper_wick'] < current_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )
            is_strong_bearish = (
                current_candle['close'] < current_candle['open'] and
                current_candle['body_size'] > validation_settings.MIN_EXPECTED_PROFIT_LOSS and
                current_candle['lower_wick'] < current_candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            )

            if is_strong_bullish:
                trend_state = 'AWAITING_CONFIRMATION'
                strong_candle_idx = i
                signal_direction = 'BUY'
            elif is_strong_bearish:
                trend_state = 'AWAITING_CONFIRMATION'
                strong_candle_idx = i
                signal_direction = 'SELL'
            continue

        # --- STATE: AWAITING_CONFIRMATION -> AWAITING_MOMENTUM ---
        # We have a strong candle, now we need an advanced confirmation signal.
        if trend_state == 'AWAITING_CONFIRMATION':
            # Reset if too much time has passed
            if i > strong_candle_idx + config.get("CONFIRMATION_WINDOW", 4):
                trend_state = 'NEUTRAL'
                continue

            adv_signal = check_advanced_confirmation(current_candle, df_indexed.iloc[i-1])
            
            if adv_signal == signal_direction:
                trend_state = 'AWAITING_MOMENTUM'
                confirmation_candle_idx = i
            continue

        # --- STATE: AWAITING_MOMENTUM -> ALERT or RESET ---
        # We have a strong candle and confirmation. This is the final momentum check.
        if trend_state == 'AWAITING_MOMENTUM':
            # This state must be resolved on the very next candle. If not, reset.
            if i > confirmation_candle_idx + 1:
                trend_state = 'NEUTRAL'
                continue

            momentum_confirmed = False
            if signal_direction == 'BUY' and current_candle['close'] > df_indexed.iloc[i-1]['close']:
                momentum_confirmed = True
            elif signal_direction == 'SELL' and current_candle['close'] < df_indexed.iloc[i-1]['close']:
                momentum_confirmed = True

            if momentum_confirmed:
                strong_candle = df_indexed.iloc[strong_candle_idx]
                start_price = strong_candle['low'] if signal_direction == 'BUY' else strong_candle['high']
                current_price = current_candle['close']
                
                min_magnitude = config.get("MIN_ALERT_MAGNITUDE", 0)
                is_sufficient, magnitude = check_magnitude(current_price, start_price, min_magnitude)

                # Volume Confirmation
                confirmation_start_index = strong_candle_idx
                confirmation_end_index = i + 1
                confirmation_df = df_indexed.iloc[confirmation_start_index:confirmation_end_index]

                use_volume_spike = config.get("USE_VOLUME_CONFIRMATION", False)
                use_increasing_volume = config.get("USE_INCREASING_VOLUME_CONFIRMATION", False)

                volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed, i))
                volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
                
                volume_confirmed = volume_spike_is_confirmed and volume_is_increasing

                # In development mode, generate all alerts.
                # In deployment mode, only generate alerts that are new enough.
                if is_sufficient and volume_confirmed and (is_development_mode or is_new_alert):
                    alert_time = current_candle['time']
                    start_time = strong_candle['time']
                    if isinstance(start_time, pd.Timestamp):
                        start_time = start_time.isoformat()
                    
                    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

                    details = {
                        "strong_candle_time": strong_candle['time'].isoformat(),
                        "confirmation_candle_time": df_indexed.iloc[confirmation_candle_idx]['time'].isoformat(),
                        "momentum_candle_time": alert_time.isoformat(),
                        "strong_candle_body": round(strong_candle['body_size'], 2),
                        "used_advanced_confirmation": True
                    }

                    alert_data = AlertData(
                        approach=Approach.STRONG_CANDLE,
                        id=alert_id,
                        signal=signal_direction,
                        alert_price=current_price,
                        alert_time=alert_time,
                        start_price=start_price,
                        start_time=start_time,
                        magnitude=magnitude,
                        details=json.dumps(details)
                    )
                    alerts.append(alert_data)
            
            # Whether an alert was generated or not, the sequence is complete. Reset.
            trend_state = 'NEUTRAL'
            
    return alerts
