# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/executor.py

import pandas as pd
import logging
import json
from typing import Optional
from scipy.signal import find_peaks
import numpy as np

# --- Standard Imports ---
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed
from src.stockreports.alert.common.data_utils import can_apply_analysis

# --- Settings Loader ---
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()
logger = logging.getLogger(__name__)

# --- Module-level constant for the approach name ---
APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT
CONFIG = signal_settings.APPROACH_CONFIG.get(
    APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
)

# 1. MAIN ENTRY POINT
def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSOLIDATION_BREAKOUT approach.
    """
    try:
        logger.info(f"Running '{APPROACH_NAME}' approach...")
        
        alerts_data = _find_consolidation_breakout_alerts(df, new_candle_count)
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

# 2. PRIMARY FINDER FUNCTION
def _find_consolidation_breakout_alerts(df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
    """
    Finds alerts by iterating through a range of lookback periods.
    """
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT

    lookback_values = CONFIG.get("CONSOLIDATION_LOOKBACK", [50])
    if not isinstance(lookback_values, list):
        lookback_values = [lookback_values]

    min_lookback, max_lookback = min(lookback_values), max(lookback_values)
    required_lookback = max_lookback + CONFIG.get("BREAKOUT_CONFIRMATION_CANDLES", 1)

    # --- Pre-analysis validation ---
    df = prepare_indicators(df)
    can_run_analysis = can_apply_analysis(df, APPROACH_NAME, required_rows=required_lookback)
    if not can_run_analysis:
        return alerts

    df_indexed = df.set_index('time')

    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1
    
    active_region_start = len(df_indexed) - new_candle_count if not is_development_mode else loop_start

    for i in range(loop_end, loop_start - 1, -1):
        if not is_development_mode and i < active_region_start:
            break

        for lookback in range(min_lookback, max_lookback + 1):
            current_required_lookback = lookback + CONFIG.get("BREAKOUT_CONFIRMATION_CANDLES", 1)
            if i < current_required_lookback - 1:
                continue

            window = df_indexed.iloc[i - current_required_lookback + 1 : i + 1].copy()
            
            # Pass the specific lookback being tested to the analysis function
            alert = _analyze_window(window, lookback)
            
            if alert:
                alerts.append(alert)
                if not is_development_mode:
                    return alerts
                # If an alert is found for one lookback, we can stop checking other lookbacks for this candle
                break 

    return alerts[::-1]

# 3. CORE ANALYSIS FUNCTION
def _analyze_window(window: pd.DataFrame, lookback: int) -> Optional[AlertData]:
    """
    Analyzes a single window of data to find a consolidation breakout pattern for a specific lookback.
    """
    # 1. Define windows
    consolidation_window = window.iloc[:lookback]
    breakout_window = window.iloc[lookback:]

    # --- Consolidation Confirmation ---

    # A. Price Clustering Logic: The primary method for identifying consolidation.
    # It checks if a significant number of candles are tightly packed around a central price.
    center_price = consolidation_window['close'].median()
    max_deviation = CONFIG.get("MAX_DEVIATION_FROM_CENTER")
    is_clustered = (consolidation_window['close'] >= center_price - max_deviation) & \
                   (consolidation_window['close'] <= center_price + max_deviation)
    
    # Condition 1: The first and last candles of the window MUST be part of the cluster.
    # This ensures the consolidation is well-defined at its boundaries.
    # if not is_clustered.iloc[0] or not is_clustered.iloc[-1]:
    #     return None
        
    # Condition 2: A minimum percentage of candles in the window must be clustered.
    # This confirms that the price has been stable and not just randomly touching the center.
    min_ratio = CONFIG.get("MIN_CLUSTERED_CANDLE_RATIO")
    if is_clustered.mean() < min_ratio:
        return None

    # --- New: Channel Consistency Check (Corrected Logic) ---
    # This ensures the price respects the consolidation channel and is not too erratic.
    if CONFIG.get("USE_CHANNEL_CONSISTENCY_CHECK", False):
        # Define the channel based on the HIGHS and LOWS of the CLUSTERED candles only.
        core_channel_df = consolidation_window[is_clustered]
        core_resistance = core_channel_df['high'].max()
        core_support = core_channel_df['low'].min()
        
        # Count candles from the ENTIRE window that CLOSE outside this core channel.
        outliers = (consolidation_window['close'] > core_resistance) | \
                   (consolidation_window['close'] < core_support)
        
        max_outlier_ratio = CONFIG.get("MAX_CHANNEL_OUTLIER_RATIO", 0.1)
        
        if outliers.sum() / lookback > max_outlier_ratio:
            return None

    # --- New: Balanced Sideways Movement Confirmation ---
    if CONFIG.get("USE_BALANCED_SIDEWAYS_CHECK", False):
        # Condition A: Ensure the overall trend of the window is flat using linear regression.
        # A slope near zero indicates a sideways trend.
        max_slope = CONFIG.get("MAX_REGRESSION_SLOPE", 0.05)
        x = np.arange(len(consolidation_window))
        y = consolidation_window['close'].values
        slope, _ = np.polyfit(x, y, 1)
        if abs(slope) > max_slope:
            return None

        # Condition B: Ensure the price is balanced around the median.
        # This prevents identifying a slow, grinding trend as consolidation.
        max_balance_deviation = CONFIG.get("MAX_TIME_BALANCE_DEVIATION_RATIO", 0.3)
        candles_above = (consolidation_window['close'] > center_price).sum()
        candles_below = (consolidation_window['close'] < center_price).sum()
        balance_ratio = abs(candles_above - candles_below) / lookback
        if balance_ratio > max_balance_deviation:
            return None

    # --- New: Consecutive Trend Check ---
    # This prevents identifying a slow, drifting trend as a consolidation.
    if CONFIG.get("USE_CONSECUTIVE_TREND_CHECK", False):
        max_consecutive = CONFIG.get("MAX_CONSECUTIVE_TREND_CANDLES", 7)
        
        # Determine direction: 1 for up, -1 for down, 0 for neutral
        direction = np.sign(consolidation_window['close'] - consolidation_window['open'])
        
        # Find the longest run of consecutive non-zero values
        longest_run = 0
        current_run = 0
        for i in range(1, len(direction)):
            if direction.iloc[i] != 0 and direction.iloc[i] == direction.iloc[i-1]:
                current_run += 1
            else:
                longest_run = max(longest_run, current_run)
                current_run = 1 if direction.iloc[i] != 0 else 0
        longest_run = max(longest_run, current_run)

        if longest_run > max_consecutive:
            return None

    # E. New Condition: Minimum Peaks and Troughs
    # This confirms volatility and sideways movement by finding local highs and lows.
    min_peaks_troughs = CONFIG.get("MIN_PEAKS_TROUGHS", 0)
    if min_peaks_troughs > 0:
        prominence = CONFIG.get("PEAK_TROUGH_PROMINENCE", None)
        # Find peaks in the 'high' prices and troughs in the 'low' prices
        peak_indices, _ = find_peaks(consolidation_window['high'], prominence=prominence)
        trough_indices, _ = find_peaks(-consolidation_window['low'], prominence=prominence)

        # Filter peaks to be above the median and troughs to be below the median
        valid_peaks = [p for p in peak_indices if consolidation_window['high'].iloc[p] > center_price]
        valid_troughs = [t for t in trough_indices if consolidation_window['low'].iloc[t] < center_price]
        
        if len(valid_peaks) + len(valid_troughs) < min_peaks_troughs:
            return None

        # --- New: Alternating Peaks and Troughs Check ---
        if CONFIG.get("USE_ALTERNATING_PEAKS_TROUGHS_CHECK", False):
            # Combine peaks and troughs with their types and sort by index (time)
            points = [(i, 'peak') for i in valid_peaks] + [(i, 'trough') for i in valid_troughs]
            points.sort(key=lambda x: x[0])

            # If there's more than one point, check if they alternate
            if len(points) > 1:
                is_alternating = all(points[i][1] != points[i+1][1] for i in range(len(points) - 1))
                if not is_alternating:
                    return None

    # B. Optional ADX Filter: If enabled, ensures a minimum ratio of candles are non-trending.
    if CONFIG.get("USE_ADX_FILTER", False):
        adx_threshold = CONFIG.get("ADX_THRESHOLD")
        min_non_trending_ratio = CONFIG.get("ADX_CONFIRMATION_RATIO", 0.8)
        
        is_non_trending = consolidation_window['adx'] < adx_threshold
        
        if is_non_trending.mean() < min_non_trending_ratio:
            return None

    # C. Optional Bollinger Band Width Filter: If enabled, confirms low volatility.
    # A "squeeze" (narrow bands) often precedes a significant price move.
    if CONFIG.get("USE_BB_WIDTH_FILTER", False):
        bb_width_threshold = CONFIG.get("BB_WIDTH_THRESHOLD_PERCENT") / 100
        bb_width_percent = consolidation_window['bb_width'] / consolidation_window['bb_middle']
        is_squeezed = bb_width_percent < bb_width_threshold
        
        # Check if the ratio of squeezed candles meets the minimum requirement
        min_squeeze_ratio = CONFIG.get("BB_SQUEEZE_CONFIRMATION_RATIO", 0.8)
        if is_squeezed.mean() < min_squeeze_ratio:
            return None

    # --- If consolidation is confirmed, check for breakout ---

    # 5. Define Channel based on CLUSTERED candles only.
    # This creates a more accurate channel by ignoring outlier prices.
    clustered_df = consolidation_window[is_clustered]
    resistance = clustered_df['high'].max()
    support = clustered_df['low'].min()

    # 6. Check for Breakout on the confirmation candle(s)
    breakout_candle = breakout_window.iloc[0] # Check the first candle after the window
    
    breakout_up = breakout_candle['close'] > resistance
    breakout_down = breakout_candle['close'] < support

    signal = None
    if breakout_up:
        signal = Signal.BUY
    elif breakout_down:
        signal = Signal.SELL
    else:
        return None # No breakout occurred

    # --- Post-Signal Confirmation Filters ---

    # --- Final Confirmation: Last consolidation candle must align with breakout direction ---
    last_consolidation_candle = consolidation_window.iloc[-1]
    if signal == Signal.BUY and last_consolidation_candle['close'] <= last_consolidation_candle['open']:
        return None # Last candle must be bullish for a buy signal
    elif signal == Signal.SELL and last_consolidation_candle['close'] >= last_consolidation_candle['open']:
        return None # Last candle must be bearish for a sell signal

    # E. Volume Spike Confirmation:
    # This confirms significant market interest. The check passes if either the last
    # candle of the consolidation or the breakout candle itself has a volume spike.
    if CONFIG.get("USE_VOLUME_SPIKE_CONFIRMATION", False):
        avg_consolidation_volume = consolidation_window['volume'].mean()
        volume_multiplier = CONFIG.get("VOLUME_SPIKE_MULTIPLIER", 1.5)
        
        breakout_volume_spike = breakout_candle['volume'] >= avg_consolidation_volume * volume_multiplier
        last_candle_volume_spike = last_consolidation_candle['volume'] >= avg_consolidation_volume * volume_multiplier
        
        if not (breakout_volume_spike or last_candle_volume_spike):
            return None # Volume is not strong enough on either candle to confirm breakout

    # --- Indicator Confirmation (Moved to the end) ---
    if CONFIG.get("USE_CONFIRMATION", False):
        if not is_signal_confirmed(breakout_candle, signal, CONFIG):
            return None

    return _create_alert(window, signal, resistance, support, lookback, is_clustered, breakout_candle)


# 4. HELPER FUNCTION
def _create_alert(window: pd.DataFrame, signal: Signal, resistance: float, support: float, lookback: int, is_clustered: pd.Series, breakout_candle: pd.Series) -> AlertData:
    """
    Creates and returns a standardized AlertData object.
    """
    start_candle = window.iloc[0]
    
    alert_time = breakout_candle.name
    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

    details = {
        "reason": f"Price broke out of a {lookback}-candle consolidation channel.",
        "consolidation_resistance": resistance,
        "consolidation_support": support,
        "breakout_candle_close": breakout_candle['close'],
        "breakout_candle_volume": breakout_candle['volume'],
        "clustered_ratio": round(is_clustered.mean(), 2)
    }

    return AlertData(
        approach=APPROACH_NAME,
        id=alert_id,
        signal=signal,
        alert_price=breakout_candle['close'],
        alert_time=alert_time,
        start_price=start_candle['open'],
        start_time=start_candle.name,
        magnitude=round(abs(breakout_candle['close'] - start_candle['open']), 2),
        details=json.dumps(details)
    )
