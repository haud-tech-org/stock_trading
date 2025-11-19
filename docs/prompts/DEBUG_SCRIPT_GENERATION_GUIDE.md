# Guide: Generating a Debug Script for a New Alert Approach

## Purpose

When developing a new alert approach (e.g., `MY_NEW_PATTERN`), creating a corresponding debug script is **mandatory** for testing and validation. This script allows you to isolate and run your approach's core logic against a specific, narrow time window of data, using the same execution path as the main application.

This helps you:
-   Verify that your main executor function (`run_analysis`) behaves as expected.
-   Pinpoint the exact time an alert is generated or why it fails.
-   Fine-tune parameters and test edge cases with specific data slices without running the entire application.
-   Ensure your logic works correctly in both `DEVELOPMENT` and `DEPLOYMENT` modes.

This guide provides a template and instructions for creating a modern, effective debug script.

## Location

Place your new debug script in:
`tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`

Replace `[YOUR_APPROACH_NAME]` with the name of your new approach in all caps (e.g., `COMPARISON`).

## Debug Script Template

Below is a template based on the `COMPARISON` debug executor. This template calls the main executor directly, ensuring perfect logical consistency. You should only need to change the import path and the approach name.

```python
"""
A command-line tool for debugging the [YOUR_APPROACH_NAME] alert logic by calling the main executor.

Usage:
    python3 tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS]

Example:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=/path/to/your/stock_trading
    python3 tests/debug/alert/approach/COMPARISON/debug_executor.py \\
        --symbol "41I1FB000" \\
        --start-time "2025-11-19 10:00:00" \\
        --end-time "2025-11-19 11:00:00"
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
# IMPORTANT: Choose the correct data loader based on your testing mode.
# Use load_live_data for DEPLOYMENT mode testing (fetches from API).
# Use load_data_for_development and historical_data_manager for DEVELOPMENT mode.
from src.stockreports.utils.data_utils import load_live_data
# IMPORTANT: Update the import path to your approach's executor and settings
from src.stockreports.alert.approach.COMPARISON import executor as comparison_executor
from src.stockreports.alert.approach.COMPARISON.settings import ComparisonSignalSettings
import src.stockreports.alert.approach.COMPARISON.settings as signal_settings_module

# Setup basic logging to see output from the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(symbol, start_time_str, end_time_str):
    """
    Sets up the environment and runs the debug analysis by calling the main executor
    with a DataFrame representing the specified time window.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(signal_settings_module)
    importlib.reload(loader)
    settings = loader.get_settings()
    # Set the mode for your test. DEPLOYMENT is common for testing live scenarios.
    settings.MODE = 'DEPLOYMENT' 
    
    # Load approach-specific settings to get dependent symbols or parameters
    approach_settings = ComparisonSignalSettings(symbol)
    ref_symbol = approach_settings.referenced_symbol # Example for an approach with a reference symbol

    print(f"--- Starting Debug Analysis for {approach_settings.approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")
    print(f"Referenced Symbol: {ref_symbol}")

    # --- 2. Fetch Data for the Analysis Window ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching data for main symbol from {start_time} to {end_time} ---")
    try:
        # Convert to UTC timestamps for the API call
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())

        # Fetch data for the main symbol. The executor is responsible for fetching its own dependencies (like ref_symbol).
        df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if df_for_analysis is None or df_for_analysis.empty:
            print(f"ERROR: Could not retrieve data for '{symbol}' in the specified range.")
            return
        
        print("Data successfully fetched for the required window.")

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching: {e}")
        return

    # --- 3. Prepare and Call the Main Executor ---
    # The executor expects specific column names and format
    df_for_analysis.columns = [col.lower() for col in df_for_analysis.columns]
    df_for_analysis['symbol'] = symbol
    
    # In DEPLOYMENT mode, new_candle_count determines the active analysis window.
    new_candle_count = len(df_for_analysis)

    print(f"\n--- Calling main executor with a dataframe of {len(df_for_analysis)} candles ---")
    # Call the run_analysis function from YOUR approach's executor
    alert_result = comparison_executor.run_analysis(df=df_for_analysis.reset_index(), new_candle_count=new_candle_count)

    # --- 4. Report Results ---
    print("\n\n===== OVERALL RESULT =====")
    if alert_result.status == "FAILED":
        print(f"EXECUTOR FAILED: {alert_result.message}")
    elif not alert_result.alerts.empty:
        print("✅✅✅ ALERT(S) FOUND! ✅✅✅")
        
        alerts_df = alert_result.alerts.copy()
        # Convert alert_time to datetime objects for correct filtering
        alerts_df['alert_time'] = pd.to_datetime(alerts_df['alert_time']).dt.tz_convert(timezone)

        # Filter alerts to only show those within our precise start/end time window
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
    parser.add_argument("--symbol", required=True, help="The primary symbol to analyze (e.g., '41I1FB000').")
    parser.add_argument("--start-time", required=True, help="The start of the time range to analyze (e.g., '2025-11-19 10:00:00').")
    parser.add_argument("--end-time", required=True, help="The end of the time range to analyze (e.g., '2025-11-19 11:00:00').")
    
    args = parser.parse_args()
    
    run_debug_analysis(args.symbol, args.start_time, args.end_time)
```

## How to Adapt the Template

1.  **Save the File**: Save the template above to `tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`.
2.  **Update Imports**:
    *   Change `from src.stockreports.alert.approach.COMPARISON import executor as comparison_executor` to import from *your* new approach's directory.
    *   Update the `settings` imports to match your approach's specific settings class if you created a custom one.
3.  **Update `run_debug_analysis`**:
    *   If your approach has its own settings class (like `ComparisonSignalSettings`), update the instantiation.
    *   If your approach does not have dependencies like a `ref_symbol`, you can remove that logic.
    *   Ensure the call to `comparison_executor.run_analysis` is updated to use the alias for *your* executor.
4.  **Update `__main__`**: Change the `description` in `argparse.ArgumentParser` to match your approach name.
5.  **Run from Terminal**: From the project root, execute the script. **It is critical to set the `PYTHONPATH`** so that Python can find the `src` directory.

    ```bash
    # Set the PYTHONPATH to the project's root directory
    export PYTHONPATH=$(pwd)

    # Run the debug script
    python3 tests/debug/alert/approach/YOUR_APPROACH_NAME/debug_executor.py \
        --symbol "TICKER" \
        --start-time "YYYY-MM-DD HH:MM:SS" \
        --end-time "YYYY-MM-DD HH:MM:SS"
    ```

By following this new guide, you create a debug script that is simpler, more robust, and perfectly mirrors the behavior of the main application, leading to more effective testing.

---

## Case Studies: Common Debugging Scenarios

Based on real-world debugging sessions, here are common issues you might encounter and how to solve them using this script.

### Case Study 1: `ModuleNotFoundError`

-   **Symptom**: The script fails immediately with `ModuleNotFoundError: No module named 'src.stockreports...'`.
-   **Root Cause**: The Python interpreter cannot find the `src` directory because the script is being run from a subdirectory (`tests/debug/...`).
-   **Solution**: Always run the debug script from the project's root directory and set the `PYTHONPATH` environment variable. The template includes the necessary `sys.path.insert(0, project_root)` as a fallback, but setting `PYTHONPATH` is the most reliable method.

    ```bash
    # From the project root
    export PYTHONPATH=$(pwd)
    python3 tests/debug/alert/approach/YOUR_APPROACH_NAME/debug_executor.py ...
    ```

### Case Study 2: `TypeError` on Time Comparison

-   **Symptom**: The script finds an alert but then crashes with `TypeError: '>=' not supported between instances of 'str' and 'Timestamp'`.
-   **Root Cause**: The `alert_result` DataFrame returned by the executor has an `alert_time` column containing string representations of timestamps. The debug script's filtering logic then tries to compare these strings directly with the `start_time` and `end_time` `Timestamp` objects.
-   **Solution**: Before filtering, you **must** convert the `alert_time` column back into proper, timezone-aware datetime objects. The template includes the correct code for this.

    ```python
    # In the "Report Results" section of the debug script
    alerts_df = alert_result.alerts.copy()
    # Convert alert_time to datetime objects and apply the correct timezone
    alerts_df['alert_time'] = pd.to_datetime(alerts_df['alert_time']).dt.tz_convert(timezone)

    # Now the comparison will work correctly
    alerts_in_range = alerts_df[
        (alerts_df['alert_time'] >= start_time) & 
        (alerts_df['alert_time'] <= end_time)
    ]
    ```

### Case Study 3: No Alerts Found and "Insufficient Data" Warnings

-   **Symptom**: The debug script runs but finds no alerts, and the executor's logs show warnings like `Not enough aligned data to run comparison after indicator calculation.`
-   **Root Cause**: The time window specified (`--start-time` to `--end-time`) is too short. While data is fetched for this window, there isn't enough *preceding* data to "warm up" the indicators (e.g., a 5-period moving average needs 5 data points to produce its first value).
-   **Solution**: When calling the data fetching function (`load_live_data` or `get_historical_data`), fetch a larger "warm-up" window of data. A good practice is to start fetching from a duration equal to `lookback_period * 2` before your actual `start_time`. The main executor logic is responsible for handling this, but if you are fetching data manually in the script, you must account for it.

    ```python
    # In the "Fetch Data" section of the debug script
    
    # Calculate a warm-up period
    warm_up_period = pd.Timedelta(minutes=approach_settings.lookback_window * 2)
    fetch_start_time = start_time - warm_up_period

    from_timestamp = int(fetch_start_time.timestamp())
    to_timestamp = int(end_time.timestamp())

    df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)
    ```
    The final report will still filter alerts to your original `start_time` and `end_time`, but the analysis will be more accurate.
