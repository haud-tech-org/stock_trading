"""
A command-line tool for debugging the VOLUME_SPIKE_CONFIRMATION alert logic by calling the main executor.

Usage:
    python3 tests/debug/alert/approach/VOLUME_SPIKE_CONFIRMATION/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS] \\
        --save-to-file \\
        --generate-chart

Example:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=$(pwd)
    python3 tests/debug/alert/approach/VOLUME_SPIKE_CONFIRMATION/debug_executor.py \\
        --symbol "VN30F1M" \\
        --start-time "2023-09-15 10:00:00" \\
        --end-time "2023-09-15 11:00:00" \\
        --save-to-file --generate-chart
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
from src.stockreports.utils.data_utils import load_live_data
from src.stockreports.alert.common.constants import Approach
from tests.debug.common.charts.visibility_chart import generate_alert_chart
from tests.debug.common.utils.debug_utils import save_debug_data

# Setup basic logging to see output from the main application
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    """
    Sets up the environment and runs the debug analysis by calling the main executor
    with a DataFrame representing the specified time window.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    
    # Dynamically import the executor AFTER reloading the configuration to ensure it sees the changes.
    from src.stockreports.alert.approach.VOLUME_SPIKE_CONFIRMATION.executor import VolumeSpikeConfirmationExecutor

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
    json_file_path = None
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
            # Use the centralized utility to save the data.
            # Note: This function expects Timestamp objects for start/end times.
            json_file_path = save_debug_data(
                df_for_analysis,
                symbol,
                start_time,
                end_time,
                project_root
            )

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching or saving: {e}")
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
    alerts_in_range = pd.DataFrame()
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

    # --- 5. Generate Standardized Alert Chart ---
    if generate_chart and json_file_path and not alerts_in_range.empty:
        print("\n--- Generating standardized alert chart ---")
        chart_output_dir = os.path.join(project_root, 'tests', 'debug', 'charts')
        try:
            # Pass the alert_time of the first alert to the chart function
            alert_time = alerts_in_range.iloc[0]['alert_time'] if not alerts_in_range.empty else None
            generate_alert_chart(
                input_file=json_file_path,
                output_dir=chart_output_dir,
                approach_name=approach_name,
                alerts_df=alerts_in_range,
                alert_time=alert_time
            )
            print(f"Chart saved to directory: {chart_output_dir}")
        except Exception as e:
            print(f"ERROR: An error occurred during chart generation: {e}")
    elif generate_chart:
        print("\n--- Skipping chart generation because no alerts were found in the specified range or --save-to-file was not used. ---")


if __name__ == "__main__":
    """
    Argument parsing. This section generally does not need to be modified.
    """
    parser = argparse.ArgumentParser(description="Debug the VOLUME_SPIKE_CONFIRMATION logic by calling the main executor.")
    parser.add_argument("--symbol", required=True, help="The primary symbol to analyze (e.g., 'VN30F1M').")
    parser.add_argument("--start-time", required=True, help="The start of the time range to analyze (e.g., '2023-09-15 10:00:00').")
    parser.add_argument("--end-time", required=True, help="The end of the time range to analyze (e.g., '2023-09-15 11:00:00').")
    parser.add_argument("--save-to-file", action='store_true', help="If set, saves the fetched data to a JSON file.")
    parser.add_argument("--generate-chart", action='store_true', help="If set, generates a visibility chart for the first found alert.")
    
    args = parser.parse_args()
    
    run_debug_analysis(args.symbol, args.start_time, args.end_time, args.save_to_file, args.generate_chart)
