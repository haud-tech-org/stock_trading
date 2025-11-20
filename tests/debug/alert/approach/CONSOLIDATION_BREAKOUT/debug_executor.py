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
from src.stockreports.alert.approach.CONSOLIDATION_BREAKOUT.executor import ConsolidationBreakoutExecutor


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
        # We need to provide the executor with a dataframe that includes the consolidation window
        # and the breakout candle. The executor logic will handle slicing.
        # The main executor receives a dataframe and `new_candle_count`.
        # For this debug script, we can simulate this by passing the whole dataframe up to the breakout time.
        analysis_df = df.loc[:end_time].copy()
        if analysis_df.empty:
            raise KeyError("The breakout time is not in the dataframe or is the first entry.")
            
    except KeyError:
        print(f"ERROR: Could not find start or end time in the data.")
        return

    if len(analysis_df) < lookback + 1:
        print(f"ERROR: Insufficient data for analysis. Need at least {lookback + 1} candles, found {len(analysis_df)}.")
        return

    print(f"\n--- Window Information ---")
    print(f"Analyzing data up to {analysis_df.index[-1]}")
    
    # --- Execute Main Analysis Logic ---
    print("\n--- Running Main Executor Logic ---")
    # The executor is designed to be stateful for a given symbol, but for debugging,
    # we can instantiate it directly. The symbol is not strictly required for this approach
    # if we provide the data directly, but we pass a dummy one for compatibility.
    executor = ConsolidationBreakoutExecutor(symbol="DEBUG_SYMBOL", debug=True)
    
    # We simulate the main loop by passing the dataframe and setting new_candle_count to 1,
    # which tells the executor to analyze the very last candle as the potential breakout.
    alert_result = executor.run(df=analysis_df.reset_index(), new_candle_count=1)

    # --- Final Verdict ---
    print("\n--- FINAL VERDICT ---")
    if alert_result and not alert_result.alerts.empty:
        print(f"PASSED: An alert would be generated.")
        alert_data = alert_result.alerts.iloc[0]
        print(f"  - Signal: {alert_data['signal']}")
        print(f"  - Alert Price: {alert_data['alert_price']}")
        print(f"  - Details: {alert_data['details']}")
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
