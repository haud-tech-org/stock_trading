"""
A command-line tool for debugging the VOLUME_SPIKE_CONFIRMATION alert logic by calling the main executor.

Usage:
    python3 tests/debug/alert/approach/VOLUME_SPIKE_CONFIRMATION/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS]

Example:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=/path/to/your/stock_trading
    python3 tests/debug/alert/approach/VOLUME_SPIKE_CONFIRMATION/debug_executor.py \\
        --symbol "VN30F1M" \\
        --start-time "2023-09-15 10:00:00" \\
        --end-time "2023-09-15- 11:00:00"
"""
import sys
import os
import argparse
import pandas as pd
import logging
import importlib
from typing import Optional
import json

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
# IMPORTANT: Update the import path to your approach's executor
from src.stockreports.alert.approach.VOLUME_SPIKE_CONFIRMATION.executor import VolumeSpikeConfirmationExecutor
from src.stockreports.alert.common.constants import Approach

# Setup basic logging to see output from the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(symbol, start_time_str, end_time_str, save_to_file):
    """
    Sets up the environment and runs the debug analysis by calling the main executor
    with a DataFrame representing the specified time window.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    settings = loader.get_settings()
    # Set the mode for your test. DEPLOYMENT is common for testing live scenarios.
    settings.MODE = 'DEPLOYMENT' 
    
    approach_name = Approach.VOLUME_SPIKE_CONFIRMATION

    print(f"--- Starting Debug Analysis for {approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data for the Analysis Window ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching data for main symbol from {start_time} to {end_time} ---")
    try:
        # Convert to UTC timestamps for the API call
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())

        # Fetch data for the main symbol. The executor is responsible for fetching its own dependencies.
        df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if df_for_analysis is None or df_for_analysis.empty:
            print(f"ERROR: Could not retrieve data for '{symbol}' in the specified range.")
            return
        
        print("Data successfully fetched for the required window.")

        if save_to_file:
            # Format the filename
            start_str = start_time.strftime('%Y%m%d_%H%M')
            end_str = end_time.strftime('%Y%m%d_%H%M')
            
            # Create a specific directory for debug data if it doesn't exist
            debug_data_dir = os.path.join(project_root, 'tests', 'debug', 'data')
            os.makedirs(debug_data_dir, exist_ok=True)
            
            # Create a copy for file saving to avoid modifying the original df
            df_to_save = df_for_analysis.copy()

            # Reset index to make 'time' a column
            df_to_save.reset_index(inplace=True)

            # Convert 'time' column to the local timezone
            df_to_save['time'] = df_to_save['time'].dt.tz_convert(timezone)

            # --- Save to JSON with local timezone ---
            json_filename = f"debug_data_{symbol}_{start_str}_to_{end_str}_intraday.json"
            json_file_path = os.path.join(debug_data_dir, json_filename)
            
            # Manually format the 'time' column to an ISO string with timezone
            df_to_save['time'] = df_to_save['time'].apply(lambda x: x.isoformat())
            
            df_to_save.to_json(json_file_path, orient='records', indent=4)
            print(f"Data saved to {json_file_path}")

            # --- Save to CSV with local timezone ---
            csv_filename = f"debug_data_{symbol}_{start_str}_to_{end_str}_intraday.csv"
            csv_file_path = os.path.join(debug_data_dir, csv_filename)
            df_to_save.to_csv(csv_file_path, index=False)
            print(f"Data saved to {csv_file_path}")

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
    executor = VolumeSpikeConfirmationExecutor(symbol=symbol)
    alert_result = executor.run(df=df_for_analysis.reset_index(), new_candle_count=new_candle_count)

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
    parser = argparse.ArgumentParser(description="Debug the VOLUME_SPIKE_CONFIRMATION logic by calling the main executor.")
    parser.add_argument("--symbol", required=True, help="The primary symbol to analyze (e.g., 'VN30F1M').")
    parser.add_argument("--start-time", required=True, help="The start of the time range to analyze (e.g., '2023-09-15 10:00:00').")
    parser.add_argument("--end-time", required=True, help="The end of the time range to analyze (e.g., '2023-09-15 11:00:00').")
    parser.add_argument("--save-to-file", action='store_true', help="If set, saves the fetched data to a JSON file.")
    
    args = parser.parse_args()
    
    run_debug_analysis(args.symbol, args.start_time, args.end_time, args.save_to_file)
