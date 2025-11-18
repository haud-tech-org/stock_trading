import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks
import ta

# --- Settings Loader ---
from src.stockreports.config import loader
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

# --- Project Imports ---
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.confirmation.confirmation import (
    prepare_indicators,
    is_signal_confirmed,
    _is_rsi_not_exhausted
)
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.magnitude import check_magnitude
from src.stockreports.alert.common.volume import (
    is_volume_spike_confirmed, 
    can_apply_volume_confirmation, 
    is_last_candle_volume_max,
    is_volume_increasing
)
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Signal

logger = logging.getLogger(__name__)

# --- Module-level constant for the approach name ---
APPROACH_NAME = Approach.CONSISTENT_MOMENTUM
CONFIG = signal_settings.APPROACH_CONFIG.get(
    APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
)

def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSISTENT_MOMENTUM approach. It takes a DataFrame and returns an AlertResult.
    """
    try:
        logger.info(f"Running '{APPROACH_NAME}' approach...")
        
        # Prepare all indicators here, before calling the analysis function.
        df = prepare_indicators(df)

        alerts_data = _find_consistent_momentum_alerts(df, new_candle_count)
        logger.info(f"'{APPROACH_NAME}' approach found {len(alerts_data)} alerts.")

        # Convert list of AlertData objects to a DataFrame
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

def _analyze_window(window: pd.DataFrame, df_indexed: pd.DataFrame, window_size: int) -> Optional[AlertData]:
    """
    Analyzes a single window of data to find a consistent momentum alert.
    This function contains the core alert detection logic.
    """
    # --- 2. Basic Momentum Check ---
    is_all_bullish = (window['close'] > window['open']).all()
    is_all_bearish = (window['close'] < window['open']).all()

    if not (is_all_bullish or is_all_bearish):
        return None

    # --- 3. New: Check for momentum using average price ---
    window['avg_price'] = (window['high'] + window['low'] + window['close']) / 3
    
    is_momentum_confirmed = False
    if is_all_bullish:
        # Uptrend: Consistently increasing average price
        if (window['avg_price'].diff().dropna() >= 0).all():
            is_momentum_confirmed = True
            signal = Signal.BUY
    elif is_all_bearish:
        # Downtrend: Consistently decreasing average price
        if (window['avg_price'].diff().dropna() <= 0).all():
            is_momentum_confirmed = True
            signal = Signal.SELL
    
    if not is_momentum_confirmed:
        return None

    # --- 4. New: Strong Close Confirmation ---
    current_candle = window.iloc[-1]
    candle_range = (current_candle['high'] - current_candle['low'])
    if candle_range == 0: return None

    strong_close_min, _ = signal_settings.STRONG_CLOSE_THRESHOLD_RANGE
    is_strong_close = False
    if signal == Signal.BUY and ((current_candle['close'] - current_candle['low']) / candle_range) >= strong_close_min:
        is_strong_close = True
    elif signal == Signal.SELL and ((current_candle['high'] - current_candle['close']) / candle_range) >= strong_close_min:
        is_strong_close = True

    if not is_strong_close:
        return None

    # --- 5. New: Peak/Trough Breakout Confirmation ---
    lookback_minutes = CONFIG.get("PEAK_BOTTOM_LOOKBACK_PERIOD")
    prominence = CONFIG.get("PEAK_TROUGH_PROMINENCE", 1)
    momentum_start_time = window.index[0]
    
    if lookback_minutes is None:
        lookback_df = df_indexed.loc[:momentum_start_time].iloc[:-1]
    else:
        lookback_start_time = momentum_start_time - pd.Timedelta(minutes=lookback_minutes)
        lookback_df = df_indexed.loc[lookback_start_time:momentum_start_time].iloc[:-1]

    if lookback_df.empty:
        return None

    is_breakout_confirmed = False
    if signal == Signal.BUY:
        # Find all peaks in the lookback period
        peaks, _ = find_peaks(lookback_df['high'], prominence=prominence)
        if peaks.size > 0:
            # Get the last (most recent) peak
            last_peak_index = peaks[-1]
            last_peak_high = lookback_df['high'].iloc[last_peak_index]
            if current_candle['close'] > last_peak_high:
                is_breakout_confirmed = True
    elif signal == Signal.SELL:
        # Find all troughs (by inverting the price series)
        troughs, _ = find_peaks(-lookback_df['low'], prominence=prominence)
        if troughs.size > 0:
            # Get the last (most recent) trough
            last_trough_index = troughs[-1]
            last_trough_low = lookback_df['low'].iloc[last_trough_index]
            if current_candle['close'] < last_trough_low:
                is_breakout_confirmed = True

    if not is_breakout_confirmed:
        return None

    # --- Volume Confirmation ---
    use_volume_spike = CONFIG.get("USE_VOLUME_CONFIRMATION", False)
    use_increasing_volume = CONFIG.get("USE_INCREASING_VOLUME_CONFIRMATION", False)
    use_last_candle_max_volume = CONFIG.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)

    confirmation_candle_index = df_indexed.index.get_loc(current_candle.name)
    confirmation_df = df_indexed.iloc[confirmation_candle_index - window_size + 1 : confirmation_candle_index + 1]

    volume_spike_is_confirmed = not use_volume_spike or (can_apply_volume_confirmation(df_indexed) and is_volume_spike_confirmed(df_indexed.reset_index(), confirmation_candle_index))
    volume_is_increasing = not use_increasing_volume or is_volume_increasing(confirmation_df)
    last_candle_max_volume_confirmed = not use_last_candle_max_volume or is_last_candle_volume_max(confirmation_df)

    if not (volume_spike_is_confirmed and volume_is_increasing and last_candle_max_volume_confirmed):
        return None

    # --- Create Alert ---
    # --- 7. Body-to-Range Ratio Confirmation on Alert Candle ---
    body_to_range_min_ratio = CONFIG.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
    current_candle_body = abs(current_candle['close'] - current_candle['open'])
    current_candle_range = current_candle['high'] - current_candle['low']

    if current_candle_range > 0:
        body_ratio = current_candle_body / current_candle_range
        if body_ratio < body_to_range_min_ratio:
            return None
    else:
        # If range is 0 (a doji-like candle), it cannot meet the ratio unless the ratio is 0.
        if body_to_range_min_ratio > 0:
            return None

    # --- 8. Original: Check for body dominance over wicks for the entire window ---
    window['body'] = abs(window['close'] - window['open'])
    window['range'] = window['high'] - window['low']
    window['wick'] = window['range'] - window['body']
    
    total_body = window['body'].sum()
    total_wick = window['wick'].sum()

    if total_body <= total_wick:
        return None

    # --- 9. Indicator Confirmation (optional) ---
    # Per the approved plan, check RSI on the start and end candles of the momentum window.
    start_candle = window.iloc[0]
    end_candle = window.iloc[-1]
    candles_for_rsi_check = [start_candle, end_candle]
    
    # Step 1: Check for RSI exhaustion on the start and end candles.
    if not _is_rsi_not_exhausted(candles_for_rsi_check, signal, CONFIG):
        return None

    # Step 2: Check for confirmation on the final candle of the window.
    if not is_signal_confirmed(end_candle, signal, CONFIG):
        return None

    # --- If all checks pass, create an AlertData object ---
    start_candle = window.iloc[0]
    
    alert_time = current_candle.name
    momentum_start_time = start_candle.name
    current_price = current_candle['close']
    momentum_start_price = start_candle['open']

    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

    # Format start_time and momentum_start_time as ISO string with configured timezone

    from src.stockreports.utils.time_utils import to_iso8601_with_tz
    start_time = to_iso8601_with_tz(momentum_start_time)
    momentum_start_time_iso = to_iso8601_with_tz(momentum_start_time)

    alert_data = AlertData(
        approach=APPROACH_NAME,
        id=alert_id,
        signal=signal,
        alert_price=current_price,
        alert_time=alert_time,
        start_price=momentum_start_price,
        start_time=start_time,
        magnitude=round(abs(current_price - momentum_start_price), 2),
        details=json.dumps({
            "reason": "Consistent Momentum with Breakout",
            "momentum_start_time": momentum_start_time_iso,
            "momentum_window_size": window_size,
            "breakout_lookback_minutes": lookback_minutes
        })
    )
    return alert_data

def _is_immediate_reversal(candle: pd.Series, original_signal: Signal) -> bool:
    """
    Checks if the given candle is a strong reversal compared to the original signal.
    """
    reversal_ratio = CONFIG.get("REVERSAL_CANDLE_BODY_RATIO", 0.6)
    
    candle_range = candle['high'] - candle['low']
    if candle_range == 0:
        return False

    body_size = abs(candle['close'] - candle['open'])
    
    # Check for strong bearish reversal after a BUY signal
    if original_signal == Signal.BUY and candle['close'] < candle['open']:
        if (body_size / candle_range) >= reversal_ratio:
            return True
            
    # Check for strong bullish reversal after a SELL signal
    elif original_signal == Signal.SELL and candle['close'] > candle['open']:
        if (body_size / candle_range) >= reversal_ratio:
            return True

    return False

def _find_consistent_momentum_alerts(df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    """
    Finds alerts based on a consistent momentum pattern using a unified reverse loop.
    This function is optimized for both DEPLOYMENT (latest alert) and DEVELOPMENT (all alerts) modes.
    """
    alerts = []
    window_size = CONFIG.get("CONFIRMATION_WINDOW", 3)
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    if window_size < 2:
        logger.error(f"{APPROACH_NAME}: 'CONFIRMATION_WINDOW' must be at least 2. Aborting.")
        return alerts

    # The lookback for peak/trough analysis is handled within _analyze_window.
    # The required lookback for the loop is simply the window_size.
    required_lookback = window_size
    
    can_run_analysis = can_apply_analysis(df, APPROACH_NAME, required_rows=required_lookback)
    if not can_run_analysis:
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

        window = df_indexed.iloc[i - window_size + 1 : i + 1].copy()
        
        # All logic, including indicator checks, is now self-contained in _analyze_window.
        alert = _analyze_window(window, df_indexed, window_size)
        
        if alert:
            # Handle look-forward confirmation for reversal
            if CONFIG.get("USE_REALTIME_REVERSAL_CONFIRMATION", False):
                confirmation_window_size = CONFIG.get("REALTIME_REVERSAL_CONFIRMATION_WINDOW", 1)
                # Ensure we don't look past the end of the dataframe
                if i + confirmation_window_size < len(df_indexed):
                    confirmation_window = df_indexed.iloc[i + 1 : i + 1 + confirmation_window_size]
                    is_reversal = False
                    for _, candle in confirmation_window.iterrows():
                        if _is_immediate_reversal(candle, alert.signal):
                            is_reversal = True
                            break
                    if is_reversal:
                        alert = None # Invalidate the alert
            
            if alert:
                alerts.append(alert)
                # In DEPLOYMENT mode, exit immediately after finding the first (latest) alert.
                if not is_development_mode:
                    return alerts

    # In DEVELOPMENT mode, the loop completes. Return all found alerts in chronological order.
    return alerts[::-1]
