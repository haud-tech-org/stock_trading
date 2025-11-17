"""
A command-line tool for step-by-step debugging of the CONSOLIDATION_BREAKOUT alert logic.

This script allows you to isolate a specific time window from a historical data file
and run the full consolidation analysis on it, printing the result of each
individual check (e.g., Clustering, Peaks/Troughs, Alternating Pattern).

This is useful for understanding why an alert was or was not generated for a
specific breakout pattern.

Usage:
    python3 tests/debug/alert/approach/CONSOLIDATION_BREAKOUT/debug_executor.py \\
        --file-path [PATH_TO_CSV] \\
        --start-time [HH:MM:SS] \\
        --breakout-time [HH:MM:SS] \\
        --lookback [INTEGER]

Example:
    python3 tests/debug/alert/approach/CONSOLIDATION_BREAKOUT/debug_executor.py \\
        --file-path src/stockreports/data/41I1FB000/41i1fb000_response_251114_1300_to_1358.csv \\
        --start-time "13:29:00" \\
        --breakout-time "13:54:00" \\
        --lookback 25
"""
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
import json
import argparse
import sys
import os
import importlib
from typing import Optional

# Add the project root to the Python path to resolve module imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', '..'))
sys.path.insert(0, project_root)


# --- Standard Imports ---
from src.stockreports.config import loader
from src.stockreports.config import signal_settings as signal_settings_module
from src.stockreports.alert.common.constants import Signal
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed, can_apply_indicator_confirmation
from src.stockreports.alert.model.models import AlertData
from src.stockreports.alert.approach.CONSOLIDATION_BREAKOUT.executor import _create_alert

def _debug_analyze_window(window: pd.DataFrame, config: dict, approach_name: str, lookback: int, can_run_indicator_confirmation: bool) -> Optional[AlertData]:
    """
    A verbose, standalone version of the _analyze_window function for debugging.
    It prints the result of each check.
    """
    print("\n--- Detailed Analysis ---")
    
    # 1. Define windows
    consolidation_window = window.iloc[:lookback]
    breakout_window = window.iloc[lookback:]

    # --- Consolidation Confirmation ---

    # A. Price Clustering Logic
    center_price = consolidation_window['close'].median()
    max_deviation = config.get("MAX_DEVIATION_FROM_CENTER")
    is_clustered = (consolidation_window['close'] >= center_price - max_deviation) & \
                   (consolidation_window['close'] <= center_price + max_deviation)
    
    min_ratio = config.get("MIN_CLUSTERED_CANDLE_RATIO")
    clustered_ratio = is_clustered.mean()
    if clustered_ratio < min_ratio:
        print(f"FAILED: Price Clustering. Ratio {clustered_ratio:.2f} is less than required {min_ratio}.")
        return None
    print(f"PASSED: Price Clustering (Ratio: {clustered_ratio:.2f})")

    # B. Channel Consistency Check
    if config.get("USE_CHANNEL_CONSISTENCY_CHECK", False):
        core_channel_df = consolidation_window[is_clustered]
        core_resistance = core_channel_df['high'].max()
        core_support = core_channel_df['low'].min()
        outliers = (consolidation_window['close'] > core_resistance) | \
                   (consolidation_window['close'] < core_support)
        max_outlier_ratio = config.get("MAX_CHANNEL_OUTLIER_RATIO", 0.1)
        outlier_ratio = outliers.sum() / lookback
        if outlier_ratio > max_outlier_ratio:
            print(f"FAILED: Channel Consistency. Outlier ratio {outlier_ratio:.2f} exceeds max {max_outlier_ratio}.")
            return None
        print(f"PASSED: Channel Consistency (Outlier Ratio: {outlier_ratio:.2f})")

    # C. Balanced Sideways Movement Confirmation
    if config.get("USE_BALANCED_SIDEWAYS_CHECK", False):
        max_slope = config.get("MAX_REGRESSION_SLOPE", 0.05)
        x = np.arange(len(consolidation_window))
        y = consolidation_window['close'].values
        slope, _ = np.polyfit(x, y, 1)
        if abs(slope) > max_slope:
            print(f"FAILED: Balanced Sideways (Slope). Slope {slope:.4f} exceeds max {max_slope}.")
            return None
        print(f"PASSED: Balanced Sideways (Slope: {slope:.4f})")

        max_balance_deviation = config.get("MAX_TIME_BALANCE_DEVIATION_RATIO", 0.3)
        candles_above = (consolidation_window['close'] > center_price).sum()
        candles_below = (consolidation_window['close'] < center_price).sum()
        balance_ratio = abs(candles_above - candles_below) / lookback
        if balance_ratio > max_balance_deviation:
            print(f"FAILED: Balanced Sideways (Time Balance). Ratio {balance_ratio:.2f} exceeds max {max_balance_deviation}.")
            return None
        print(f"PASSED: Balanced Sideways (Time Balance Ratio: {balance_ratio:.2f})")

    # D. Consecutive Trend Check
    if config.get("USE_CONSECUTIVE_TREND_CHECK", False):
        max_consecutive = config.get("MAX_CONSECUTIVE_TREND_CANDLES", 7)
        direction = np.sign(consolidation_window['close'] - consolidation_window['open'])
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
            print(f"FAILED: Consecutive Trend. Longest run ({longest_run}) exceeds max ({max_consecutive}).")
            return None
        print(f"PASSED: Consecutive Trend (Longest Run: {longest_run})")

    # E. Minimum Peaks and Troughs
    min_peaks_troughs = config.get("MIN_PEAKS_TROUGHS", 0)
    if min_peaks_troughs > 0:
        prominence = config.get("PEAK_TROUGH_PROMINENCE", None)
        peak_indices, _ = find_peaks(consolidation_window['high'], prominence=prominence)
        trough_indices, _ = find_peaks(-consolidation_window['low'], prominence=prominence)
        valid_peaks = [p for p in peak_indices if consolidation_window['high'].iloc[p] > center_price]
        valid_troughs = [t for t in trough_indices if consolidation_window['low'].iloc[t] < center_price]
        total_points = len(valid_peaks) + len(valid_troughs)
        if total_points < min_peaks_troughs:
            print(f"FAILED: Minimum Peaks/Troughs. Found {total_points}, require {min_peaks_troughs}.")
            return None
        print(f"PASSED: Minimum Peaks/Troughs (Found: {total_points})")

        if config.get("USE_ALTERNATING_PEAKS_TROUGHS_CHECK", False):
            points = [(i, 'peak') for i in valid_peaks] + [(i, 'trough') for i in valid_troughs]
            points.sort(key=lambda x: x[0])
            if len(points) > 1:
                is_alternating = all(points[i][1] != points[i+1][1] for i in range(len(points) - 1))
                if not is_alternating:
                    print(f"FAILED: Alternating Peaks/Troughs. Pattern is not alternating.")
                    return None
                print("PASSED: Alternating Peaks/Troughs")

    # F. ADX Filter
    if config.get("USE_ADX_FILTER", False):
        adx_threshold = config.get("ADX_THRESHOLD")
        min_non_trending_ratio = config.get("ADX_CONFIRMATION_RATIO", 0.8)
        is_non_trending = consolidation_window['adx'] < adx_threshold
        non_trending_ratio = is_non_trending.mean()
        if non_trending_ratio < min_non_trending_ratio:
            print(f"FAILED: ADX Filter. Non-trending ratio {non_trending_ratio:.2f} is less than required {min_non_trending_ratio}.")
            return None
        print(f"PASSED: ADX Filter (Non-trending Ratio: {non_trending_ratio:.2f})")

    # G. Bollinger Band Width Filter
    if config.get("USE_BB_WIDTH_FILTER", False):
        bb_width_threshold = config.get("BB_WIDTH_THRESHOLD_PERCENT") / 100
        bb_width_percent = consolidation_window['bb_width'] / consolidation_window['bb_middle']
        is_squeezed = bb_width_percent < bb_width_threshold
        min_squeeze_ratio = config.get("BB_SQUEEZE_CONFIRMATION_RATIO", 0.8)
        squeeze_ratio = is_squeezed.mean()
        if squeeze_ratio < min_squeeze_ratio:
            print(f"FAILED: BB Width Filter. Squeeze ratio {squeeze_ratio:.2f} is less than required {min_squeeze_ratio}.")
            return None
        print(f"PASSED: BB Width Filter (Squeeze Ratio: {squeeze_ratio:.2f})")

    # --- Breakout Check ---
    clustered_df = consolidation_window[is_clustered]
    resistance = clustered_df['high'].max()
    support = clustered_df['low'].min()
    breakout_candle = breakout_window.iloc[0]
    
    print(f"\n--- Breakout Check ---")
    print(f"Consolidation Channel: Support={support:.2f}, Resistance={resistance:.2f}")
    print(f"Breakout Candle Close: {breakout_candle['close']:.2f}")

    signal = None
    if breakout_candle['close'] > resistance:
        signal = Signal.BUY
        print("INFO: Breakout detected: BUY")
    elif breakout_candle['close'] < support:
        signal = Signal.SELL
        print("INFO: Breakout detected: SELL")
    else:
        print("FAILED: No breakout.")
        return None

    # --- Post-Signal Confirmation Filters ---
    print("\n--- Post-Signal Filters ---")

    # Last consolidation candle direction
    last_consolidation_candle = consolidation_window.iloc[-1]
    if signal == Signal.BUY and last_consolidation_candle['close'] <= last_consolidation_candle['open']:
        print("FAILED: Last consolidation candle was not bullish for a BUY signal.")
        return None
    elif signal == Signal.SELL and last_consolidation_candle['close'] >= last_consolidation_candle['open']:
        print("FAILED: Last consolidation candle was not bearish for a SELL signal.")
        return None
    print("PASSED: Last consolidation candle direction aligns with signal.")

    # Volume Spike Confirmation
    if config.get("USE_VOLUME_SPIKE_CONFIRMATION", False):
        avg_consolidation_volume = consolidation_window['volume'].mean()
        volume_multiplier = config.get("VOLUME_SPIKE_MULTIPLIER", 1.5)
        breakout_volume_spike = breakout_candle['volume'] >= avg_consolidation_volume * volume_multiplier
        last_candle_volume_spike = last_consolidation_candle['volume'] >= avg_consolidation_volume * volume_multiplier
        if not (breakout_volume_spike or last_candle_volume_spike):
            print(f"FAILED: Volume Spike. BreakoutVol={breakout_candle['volume']:.0f}, LastConsolVol={last_consolidation_candle['volume']:.0f}, AvgVol={avg_consolidation_volume:.0f}")
            return None
        print("PASSED: Volume Spike confirmed.")

    # Indicator Confirmation
    if config.get("USE_CONFIRMATION", False):
        if can_run_indicator_confirmation:
            # Corrected call to use the signal enum object directly
            is_confirmed = is_signal_confirmed(breakout_candle, signal, config)
            if not is_confirmed:
                print("FAILED: General indicator confirmation (is_signal_confirmed).")
                return None
            print("PASSED: General indicator confirmation (is_signal_confirmed).")
        else:
            print("SKIPPED: Indicator confirmation (insufficient data).")

    return _create_alert(window, signal, config, resistance, support, approach_name, lookback, is_clustered, breakout_candle)


def run_debug_analysis(file_path, start_time_str, breakout_time_str, lookback):
    """
    Runs a step-by-step debug analysis for the CONSOLIDATION_BREAKOUT approach on a given data slice.
    """
    print(f"--- Starting Debug Analysis for Breakout at {breakout_time_str} ---")

    # --- Configuration from signal_settings.py ---
    importlib.reload(signal_settings_module)
    importlib.reload(loader)
    settings = loader.get_settings()
    signal_settings = loader.get_signal_settings()
    config = signal_settings.APPROACH_CONFIG.get(
        "CONSOLIDATION_BREAKOUT", signal_settings.APPROACH_CONFIG.get("default", {})
    )

    print("\n--- Loaded Configuration ---")
    for key, value in config.items():
        if 'THRESHOLD' in key or 'RATIO' in key or 'CHECK' in key or 'MIN_' in key or 'MAX_' in key:
            print(f"   - {key}: {value}")

    # --- Load and Prepare Data ---
    try:
        df = pd.read_csv(file_path)
        df.columns = [col.lower() for col in df.columns]
        time_col = 'time' if 'time' in df.columns else df.columns[0]
        base_date_str = pd.to_datetime(start_time_str).strftime('%Y-%m-%d')
        
        # Combine date and time, then localize to the project's timezone from the settings file
        timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
        df[time_col] = pd.to_datetime(base_date_str + ' ' + df[time_col].astype(str))
        df[time_col] = df[time_col].dt.tz_localize(timezone)

        # Prepare indicators and set index *before* calling the analysis function
        df = prepare_indicators(df)
        df = df.set_index(time_col)

    except Exception as e:
        print(f"ERROR: Could not process data file. {e}")
        return

    # --- Isolate Window ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(breakout_time_str).tz_localize(timezone)
    
    try:
        window = df.loc[start_time:end_time].copy()
    except KeyError:
        print(f"ERROR: Could not find start or end time in the data.")
        return

    if len(window) != lookback + 1:
        print(f"ERROR: Incorrect window size. Expected {lookback + 1}, found {len(window)}.")
        return

    print(f"\n--- Window Information ---")
    print(f"Analyzing window from {window.index[0]} to {window.index[-1]}")
    
    # --- Execute Main Analysis Logic Directly ---
    print("\n--- Running Main Executor Logic ---")
    # Determine if confirmation can run based on the full dataset, mirroring the main executor
    can_run_confirmation = can_apply_indicator_confirmation(df)
    if not can_run_confirmation:
        print("INFO: Cannot run indicator confirmation based on the provided data (insufficient length for all indicators).")
    else:
        print("INFO: Data is sufficient for indicator confirmation.")

    alert = _debug_analyze_window(window, config, "CONSOLIDATION_BREAKOUT", lookback, can_run_confirmation)

    # --- Final Verdict ---
    print("\n--- FINAL VERDICT ---")
    if alert:
        print(f"PASSED: An alert would be generated.")
        print(f"  - Signal: {alert.signal}")
        print(f"  - Alert Price: {alert.alert_price}")
        print(f"  - Details: {alert.details}")
    else:
        print("FAILED: No alert generated. All conditions were not met.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug the CONSOLIDATION_BREAKOUT logic for a specific time window.")
    parser.add_argument("--file-path", required=True, help="Path to the CSV data file.")
    parser.add_argument("--start-time", required=True, help="Start time of the consolidation window (e.g., '2025-11-14 10:23:00').")
    parser.add_argument("--breakout-time", required=True, help="Time of the breakout candle (e.g., '2025-11-14 10:48:00').")
    parser.add_argument("--lookback", type=int, default=25, help="The lookback period for the consolidation window.")
    
    args = parser.parse_args()
    
    run_debug_analysis(args.file_path, args.start_time, args.breakout_time, args.lookback)
