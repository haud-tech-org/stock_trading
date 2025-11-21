# Guide: Generating a Debug Script for a New Alert Approach (Class-Based)

## Purpose

When developing a new alert approach (e.g., `MyNewExecutor`), creating a corresponding debug script is **mandatory**. This script allows you to isolate and run your `Executor` class against a specific time window of data, using the same execution path as the main application.

This helps you:
-   Verify that your `run` method behaves as expected.
-   Pinpoint the exact time an alert is generated or why it fails.
-   Fine-tune parameters and test edge cases without running the entire application.
-   Ensure your logic works correctly in both `DEVELOPMENT` and `DEPLOYMENT` modes.

## Location

Place your new debug script in:
`tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`

## Debug Script Template (Class-Based)

Below is a template for a modern debug script that works with the new class-based executors. It instantiates your executor class and calls its `run` method directly.

```python
"""
A command-line tool for debugging the [YOUR_APPROACH_NAME] alert logic by calling the main executor class.

Usage:
    python3 tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS]

Example:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=/path/to/your/stock_trading
    python3 tests/debug/alert/approach/CONSOLIDATION_BREAKOUT/debug_executor.py \\
        --symbol "VN30F1M" \\
        --start-time "2023-09-15 10:00:00" \\
        --end-time "2023-09-15 11:00:00"
"""
import sys
import os
import argparse
import pandas as pd
import logging
import importlib
from typing import Optional

# 1. Add the project root to the Python path for reliable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 2. Import necessary components from the main application
from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
# IMPORTANT: Update the import path to your approach's executor class
from src.stockreports.alert.approach.CONSOLIDATION_BREAKOUT.executor import ConsolidationBreakoutExecutor

# Setup basic logging to see output from the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(symbol, start_time_str, end_time_str):
    """
    Sets up the environment and runs the debug analysis by calling the main executor
    with a DataFrame representing the specified time window.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    settings = loader.get_settings()
    # Set the mode for your test. DEPLOYMENT is common for testing live scenarios.
    settings.MODE = 'DEPLOYMENT' 

    print(f"--- Starting Debug Analysis for {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data for the Analysis Window ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching data for main symbol from {start_time} to {end_time} ---")
    try:
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())

        # The executor is responsible for fetching its own dependencies (like a ref_symbol).
        df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if df_for_analysis is None or df_for_analysis.empty:
            print(f"ERROR: Could not retrieve data for '{symbol}' in the specified range.")
            return
        
        print("Data successfully fetched for the required window.")

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching: {e}")
        return

    # --- 3. Instantiate and Call the Main Executor ---
    # The executor expects a DataFrame with a 'time' column, not as an index.
    df_for_analysis = df_for_analysis.reset_index()
    
    # In DEPLOYMENT mode, new_candle_count determines the active analysis window.
    new_candle_count = len(df_for_analysis)

    print(f"\n--- Calling main executor with a dataframe of {len(df_for_analysis)} candles ---")
    
    # Instantiate your executor class
    # Pass debug=True to enable verbose logging if your executor supports it.
    executor = ConsolidationBreakoutExecutor(symbol=symbol, debug=True)
    
    # Call the run method
    alert_result = executor.run(df=df_for_analysis, new_candle_count=new_candle_count)

    # --- 4. Report Results ---
    print("\n\n===== OVERALL RESULT =====")
    if alert_result.status == "FAILED":
        print(f"EXECUTOR FAILED: {alert_result.message}")
    elif not alert_result.alerts.empty:
        print("✅✅✅ ALERT(S) FOUND! ✅✅✅")
        
        alerts_df = alert_result.alerts.copy()
        alerts_df['alert_time'] = pd.to_datetime(alerts_df['alert_time']).dt.tz_convert(timezone)

        alerts_in_range = alerts_df[
            (alerts_df['alert_time'] >= start_time) & 
            (alerts_df['alert_time'] <= end_time)
        ]
        if not alerts_in_range.empty:
            print(alerts_in_range.to_string())
        else:
            print("Alerts were found by the executor, but they were outside the specified time range.")
    else:
        print("No alerts were generated by the executor in the provided data.")


if __name__ == "__main__":
    """
    Argument parsing. This section generally does not need to be modified.
    """
    parser = argparse.ArgumentParser(description="Debug the [YOUR_APPROACH_NAME] logic by calling the main executor.")
    parser.add_argument("--symbol", required=True, help="The primary symbol to analyze (e.g., 'VN30F1M').")
    parser.add_argument("--start-time", required=True, help="The start of the time range to analyze (e.g., '2023-09-15 10:00:00').")
    parser.add_argument("--end-time", required=True, help="The end of the time range to analyze (e.g., '2023-09-15 11:00:00').")
    
    args = parser.parse_args()
    
    run_debug_analysis(args.symbol, args.start_time, args.end_time)
```

## How to Adapt the Template

1.  **Save the File**: Save the template to `tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`.
2.  **Update Imports**:
    *   Change `from src.stockreports.alert.approach.CONSOLIDATION_BREAKOUT.executor import ConsolidationBreakoutExecutor` to import *your* new `Executor` subclass.
3.  **Update `run_debug_analysis`**:
    *   In the "Instantiate and Call" section, change `ConsolidationBreakoutExecutor` to your executor's class name.
4.  **Update `__main__`**: Change the `description` in `argparse.ArgumentParser` to match your approach name.
5.  **Run from Terminal**: The execution command remains the same. Run it from the project root with `PYTHONPATH` set.

    ```bash
    export PYTHONPATH=$(pwd)
    python3 tests/debug/alert/approach/YOUR_APPROACH_NAME/debug_executor.py --symbol "TICKER" ...
    ```

## Key Changes from the Old Procedural Style

-   **No More `executor as alias`**: You now import the class directly: `from ... import MyExecutor`.
-   **Instantiation**: You create an instance of your class: `executor = MyExecutor(symbol=symbol)`.
-   **Method Call**: You call the instance's `run` method: `alert_result = executor.run(...)`.
-   **No `settings` import**: The executor class is responsible for loading its own settings, so the debug script no longer needs to import the approach-specific settings file.

This updated guide ensures your debug scripts are aligned with the new, more robust, object-oriented framework.
The case studies from the previous guide are still relevant and apply to this new structure.
