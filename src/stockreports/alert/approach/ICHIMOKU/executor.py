# src/stockreports/alert/approach/ICHIMOKU/executor.py
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
    Entry point for the Ichimoku approach. It identifies strong Ichimoku signals
    based on multiple conditions including Kumo, Chikou, and Kijun-sen distance.
    """
    approach_name = "ICHIMOKU"
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_ichimoku_alerts(df, config)
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

def _find_ichimoku_alerts(df: pd.DataFrame, config: dict) -> list[AlertData]:
    """
    Finds alerts based on a comprehensive Ichimoku Cloud analysis.
    This is based on the logic from `tests/manual/validate_alerts.py`.
    """
    alerts = []
    # Need at least 52 periods for Senkou Span B and 26 for Chikou lag.
    if len(df) < 52 + 26: 
        logging.warning(f"Ichimoku: DataFrame has less than {52+26} rows, cannot generate alerts.")
        return alerts

    df.set_index('time', inplace=True)
    # Use the common indicator preparation function
    df = prepare_indicators(df)
    
    # --- Add Ichimoku-specific indicators not in the common function ---
    # Senkou Span A: (Tenkan-sen + Kijun-sen) / 2
    df['senkou_span_a'] = (df['tenkan_sen'] + df['kijun_sen']) / 2
    
    # Senkou Span B: (52-period high + 52-period low) / 2
    high_52 = df['high'].rolling(window=signal_settings.ICHI_SENKOU_B_PERIOD).max()
    low_52 = df['low'].rolling(window=signal_settings.ICHI_SENKOU_B_PERIOD).min()
    df['senkou_span_b'] = (high_52 + low_52) / 2
    
    # Chikou Span (Lagging Span) is handled in the loop by comparing current close to past close.

    # --- Iterate and find signals ---
    # Start from a point where all data is available (52 for Senkou B, 26 for Chikou lag)
    start_index = max(signal_settings.ICHI_SENKOU_B_PERIOD, signal_settings.ICHI_CHIKOU_LAG)
    for i in range(start_index, len(df)):
        candle = df.iloc[i]
        prev_candle = df.iloc[i-1]

        # --- Condition Checks ---
        
        # 1. Tenkan/Kijun Cross
        is_bullish_cross = candle['tenkan_sen'] > candle['kijun_sen'] and prev_candle['tenkan_sen'] <= prev_candle['kijun_sen']
        is_bearish_cross = candle['tenkan_sen'] < candle['kijun_sen'] and prev_candle['tenkan_sen'] >= prev_candle['kijun_sen']

        # 2. Kumo (Cloud) Confirmation
        # The Kumo for the current price is composed of the Senkou spans from 26 periods ago.
        kumo_a = df['senkou_span_a'].iloc[i - signal_settings.ICHI_CHIKOU_LAG]
        kumo_b = df['senkou_span_b'].iloc[i - signal_settings.ICHI_CHIKOU_LAG]
        price_above_kumo = candle['close'] > max(kumo_a, kumo_b)
        price_below_kumo = candle['close'] < min(kumo_a, kumo_b)

        # 3. Chikou Span Confirmation
        # The current close price (acting as Chikou) must be above/below the close from 26 periods ago.
        chikou_confirms_bullish = candle['close'] > df['close'].iloc[i - signal_settings.ICHI_CHIKOU_LAG]
        chikou_confirms_bearish = candle['close'] < df['close'].iloc[i - signal_settings.ICHI_CHIKOU_LAG]

        # 4. Kijun-sen Distance Filter
        kijun_dist_min, kijun_dist_max = signal_settings.ICHI_MAX_KIJUN_DISTANCE_PCT_RANGE
        kijun_distance_pct = (abs(candle['close'] - candle['kijun_sen']) / candle['kijun_sen']) * 100
        kijun_distance_ok = kijun_dist_min <= kijun_distance_pct <= kijun_dist_max

        # --- Signal Aggregation ---
        signal = None
        if is_bullish_cross and price_above_kumo and chikou_confirms_bullish and kijun_distance_ok:
            signal = 'BUY'
        elif is_bearish_cross and price_below_kumo and chikou_confirms_bearish and kijun_distance_ok:
            signal = 'SELL'

        if signal:
            alert_time = candle.name # Use the index (timestamp)
            alert_price = candle['close']
            
            start_time = prev_candle.name
            start_price = prev_candle['close']
            magnitude = abs(alert_price - start_price)

            alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

            details = {
                "tenkan_sen": round(candle['tenkan_sen'], 2),
                "kijun_sen": round(candle['kijun_sen'], 2),
                "price_kumo_relation": "Above" if price_above_kumo else ("Below" if price_below_kumo else "Inside"),
                "chikou_confirmation": "Yes",
                "kijun_distance_pct": round(kijun_distance_pct, 2)
            }

            alert_data = AlertData(
                approach="ICHIMOKU",
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
