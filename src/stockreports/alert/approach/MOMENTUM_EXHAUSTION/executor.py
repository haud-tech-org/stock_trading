import pandas as pd
import logging
import json
import numpy as np
from typing import Optional

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.volume import is_volume_spike_confirmed, can_apply_volume_confirmation
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators, 
    _is_rsi_not_exhausted,
    is_signal_confirmed
)

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the MOMENTUM_EXHAUSTION approach. It takes a DataFrame and returns an AlertResult.
    """
    approach_name = Approach.MOMENTUM_EXHAUSTION
    try:
        logging.info(f"Running '{approach_name}' approach...")
        
        # Get the config for this specific approach, falling back to default
        config = signal_settings.APPROACH_CONFIG.get(
            approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
        )
        
        alerts_data = _find_momentum_exhaustion_alerts(df, config, new_candle_count)
        logging.info(f"'{approach_name}' approach found {len(alerts_data)} alerts.")

        # Convert list of AlertData objects to a DataFrame
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
    Analyzes a single window of data to find a momentum exhaustion alert.
    This function contains the core alert detection logic based on the visual pattern.
    Pattern: [Momentum Candles] -> [Exhaustion Candles] -> [Reversal Candle]
    """
    # --- 1. Get config and define pattern structure ---
    momentum_count = config.get("MOMENTUM_CANDLE_COUNT", 2)
    exhaustion_count = config.get("EXHAUSTION_CANDLE_COUNT", 2)
    use_volume = config.get("USE_VOLUME_CONFIRMATION", True)
    total_pattern_candles = momentum_count + exhaustion_count

    confirmation_candle = window.iloc[-1]
    reversal_candle = window.iloc[-2]
    exhaustion_candles = window.iloc[-(exhaustion_count + 2):-2]
    momentum_candles = window.iloc[-(total_pattern_candles + 2):-(exhaustion_count + 2)]
    
    # For logging purposes
    window_start_time = window.index[0]
    
    # --- 2. Check for consistent trend direction using the slope of a Simple Moving Average (SMA) ---
    
    # Get the integer location of the start of the current analysis window within the main dataframe
    start_loc = df_indexed.index.get_loc(window.index[0])
    
    # To correctly calculate the SMA for the trend period, we need to include past data.
    # The rolling window size for the SMA is `momentum_count`.
    # So, we need `momentum_count - 1` additional data points before the trend starts.
    required_past_data = momentum_count - 1
    sma_start_loc = max(0, start_loc - required_past_data)
    
    # The data for SMA calculation needs to go up to the end of the trend period
    sma_end_loc = start_loc + momentum_count
    
    # Slice the main dataframe using integer locations to get the data needed for SMA calculation
    sma_data_slice = df_indexed.iloc[sma_start_loc:sma_end_loc]

    # Calculate SMA on this extended slice
    sma = sma_data_slice['close'].rolling(window=momentum_count).mean()

    # The relevant SMA values for our trend start after the initial warmup period.
    # We take the last `momentum_count` values from the calculated SMA series.
    trend_sma = sma.tail(momentum_count)

    if trend_sma.isnull().any() or len(trend_sma) < 2:
        return None

    # Calculate the slope of the SMA using linear regression for a more robust trend detection
    x = range(len(trend_sma))
    y = trend_sma.values
    slope = np.polyfit(x, y, 1)[0]

    # Define a threshold for what is considered a meaningful trend
    slope_threshold = config.get("SMA_SLOPE_THRESHOLD", 0.05) 

    is_bullish_trend = slope > slope_threshold
    is_bearish_trend = slope < -slope_threshold

    if not (is_bullish_trend or is_bearish_trend):
        return None

    signal = None
    if is_bullish_trend and reversal_candle['close'] < reversal_candle['open']:
        # After a bullish trend, we expect a bearish reversal and a bearish confirmation.
        if confirmation_candle['close'] < confirmation_candle['open']:
            signal = 'SELL'
    elif is_bearish_trend and reversal_candle['close'] > reversal_candle['open']:
        # After a bearish trend, we expect a bullish reversal and a bullish confirmation.
        if confirmation_candle['close'] > confirmation_candle['open']:
            signal = 'BUY'
    
    if not signal:
        return None

    # --- 3. Analyze candle bodies for exhaustion pattern ---
    window['body'] = abs(window['close'] - window['open'])
    
    # --- FIX: Check for progressively shrinking candle bodies, not just averages ---
    exhaustion_bodies = window.loc[exhaustion_candles.index, 'body'].tolist()

    # Check if each exhaustion candle body is smaller than the one before it.
    is_shrinking = all(exhaustion_bodies[i] < exhaustion_bodies[i-1] for i in range(1, len(exhaustion_bodies)))

    if not is_shrinking:
        return None
    # --- END FIX ---

    # For logging purposes, calculate the averages that were previously used for the old logic.
    avg_momentum_body = window.loc[momentum_candles.index, 'body'].mean()
    avg_exhaustion_body = window.loc[exhaustion_candles.index, 'body'].mean()

    # --- 4. Analyze volume for confirmation (if enabled) ---
    if use_volume:
        # Volume should fade during exhaustion
        avg_momentum_volume = window.loc[momentum_candles.index, 'volume'].mean()
        avg_exhaustion_volume = window.loc[exhaustion_candles.index, 'volume'].mean()
        if avg_exhaustion_volume >= avg_momentum_volume:
            return None
            
        # Reversal candle should have a volume spike
        reversal_candle_index = df_indexed.index.get_loc(reversal_candle.name)
        if not (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), reversal_candle_index)):
            return None

    # --- 5. If all checks pass, create an AlertData object ---
    logging.info(f"[{reversal_candle.name}] SUCCESS: Momentum Exhaustion Pattern Found! Signal: {signal}")
    start_candle = momentum_candles.iloc[0]
    
    alert_time = confirmation_candle.name
    current_price = confirmation_candle['close']
    start_price = start_candle['open']

    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
    start_time_ts = int(start_candle.name.tz_convert('UTC').timestamp())

    # Format start_time as ISO string with timezone
    start_time = start_candle.name
    if isinstance(start_time, pd.Timestamp):
        start_time = start_time.isoformat()
    alert_data = AlertData(
        approach=Approach.MOMENTUM_EXHAUSTION,
        id=alert_id,
        signal=signal,
        alert_price=current_price,
        alert_time=alert_time,
        start_price=start_price,
        start_time=start_time,
        magnitude=round(abs(current_price - start_price), 2),
        details=json.dumps({
            "reason": "Reversal after momentum exhaustion detected.",
            "pattern_start_time": start_time_ts,
            "avg_momentum_body": round(avg_momentum_body, 2),
            "avg_exhaustion_body": round(avg_exhaustion_body, 2)
        })
    )
    return alert_data


def _find_momentum_exhaustion_alerts(df: pd.DataFrame, config: dict, new_candle_count: int = 0) -> list[AlertData]:
    """
    Finds alerts based on a momentum exhaustion pattern using a unified reverse loop.
    This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
    """
    alerts = []
    momentum_count = config.get("MOMENTUM_CANDLE_COUNT", 2)
    exhaustion_count = config.get("EXHAUSTION_CANDLE_COUNT", 2)
    required_lookback = momentum_count + exhaustion_count + 2 # +1 for reversal, +1 for confirmation
    
    is_development_mode = settings.MODE == Mode.DEVELOPMENT

    # All indicators must be prepared first.
    df = prepare_indicators(df)
    
    if len(df) < required_lookback:
        logging.warning(f"{Approach.MOMENTUM_EXHAUSTION}: DataFrame has less than {required_lookback} rows, cannot generate alerts.")
        return alerts

    df_indexed = df.set_index('time')

    # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1

    # The loop's scan depth is naturally optimized by this calculation.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region for the current mode.

        window = df_indexed.iloc[i - required_lookback + 1 : i + 1].copy()
        
        alert = _analyze_window(window, df_indexed, config)
        
        if alert:
            confirmation_candle = df_indexed.iloc[i]

            # Step 1: Check for RSI exhaustion on the confirmation candle.
            candles_for_exhaustion_check = [confirmation_candle]
            if not _is_rsi_not_exhausted(candles_for_exhaustion_check, alert.signal, config):
                continue

            # Step 2: Check for confirmation on the confirmation candle.
            if not is_signal_confirmed(confirmation_candle, alert.signal, config):
                continue

            alerts.append(alert)
            # In DEPLOYMENT mode, exit after finding the first valid alert.
            if not is_development_mode:
                return alerts

    # In DEVELOPMENT mode, return all found alerts in chronological order.
    return alerts[::-1]
