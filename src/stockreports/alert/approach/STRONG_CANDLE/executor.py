# src/stockreports/alert/approach/STRONG_CANDLE/executor.py
import pandas as pd
import logging
import json

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators
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
    Finds alerts based on strong candle patterns.
    """
    alerts = []
    if len(df) < 2:
        return alerts

    df = prepare_indicators(df)
    df.set_index('time', inplace=True)

    for i in range(1, len(df)):
        candle = df.iloc[i]

        if pd.isna(candle['body_size']) or pd.isna(candle['upper_wick']) or pd.isna(candle['lower_wick']):
            continue

        signal = None
        details = {}

        # Strong Bullish Candle
        is_strong_bullish = (
            candle['close'] > candle['open'] and
            candle['upper_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
        )
        if is_strong_bullish:
            signal = 'BUY'
            details = {
                "body_size": round(candle['body_size'], 2),
                "upper_wick": round(candle['upper_wick'], 2),
                "tail_ratio": signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            }

        # Strong Bearish Candle
        is_strong_bearish = (
            candle['close'] < candle['open'] and
            candle['lower_wick'] < candle['body_size'] * signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
        )
        if is_strong_bearish:
            signal = 'SELL'
            details = {
                "body_size": round(candle['body_size'], 2),
                "lower_wick": round(candle['lower_wick'], 2),
                "tail_ratio": signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
            }

        if signal:
            alert_time = candle.name
            alert_price = candle['close']
            
            # For this signal, the "start" is the open of the candle itself
            start_time = alert_time
            start_price = candle['open']
            magnitude = candle['body_size']

            alert_ts = int(alert_time.tz_convert('UTC').timestamp())
            alert_id = f"{alert_ts}_{signal}"

            alert_data = AlertData(
                approach="STRONG_CANDLE",
                id=alert_id,
                signal=signal,
                alert_price=alert_price,
                alert_time=alert_time,
                start_price=start_price,
                start_time=start_time,
                magnitude=magnitude,
                details=json.dumps(details)
            )
            alerts.append(alert_data)
            
    return alerts
