"""
A command-line tool for debugging any alert approach logic (generic version).

This script is designed to be run from the project root. It allows for testing any approach
on a specific symbol and date range, with options to save the data and generate
a chart for visual analysis.

Usage:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=$(pwd)
    python3 tests/debug/alert/approach/debug_executor.py \
        --approach [APPROACH_NAME] \
        --symbol [SYMBOL_TICKER] \
        --start-time [YYYY-MM-DD HH:MM:SS] \
        --end-time [YYYY-MM-DD HH:MM:SS] \
        --save-to-file \
        --generate-chart

Example:
    python3 tests/debug/alert/approach/debug_executor.py \
        --approach VRA \
        --symbol "VN30F1M" \
        --start-time "2026-01-09 09:00:00" \
        --end-time "2026-01-09 10:00:00" \
        --save-to-file --generate-chart
"""
import sys
import os
import argparse
import pandas as pd
import logging
import importlib

# Add the project root to the Python path for reliable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components from the main application and debug utilities
from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
from src.stockreports.alert.common.constants import Approach
from tests.debug.common.charts.visibility_chart import generate_alert_chart
from tests.debug.common.utils.debug_utils import save_debug_data

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(approach, symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    """
    Sets up the environment and runs the debug analysis for the selected approach.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)

    # Dynamically import the executor AFTER reloading the configuration
    # Use the approach argument as-is for the module path (case-sensitive)
    executor_module_path = f"src.stockreports.alert.approach.{approach}.executor"
    try:
        executor_module = importlib.import_module(executor_module_path)
        # Try to get the executor class by convention: e.g., VraExecutor, TrendReversalExecutor
        class_name = f"{''.join([part.capitalize() for part in approach.lower().split('_')])}Executor"
        ExecutorClass = getattr(executor_module, class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        print(f"ERROR: Could not import executor for approach '{approach}'. Error: {e}")
        return

    settings = loader.get_settings()
    settings.MODE = 'DEVELOPMENT' # Use DEVELOPMENT mode for debugging
    approach_name = getattr(Approach, approach.upper(), approach)

    print(f"--- Starting Debug Analysis for {approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching data for {symbol} from {start_time} to {end_time} ---")
    json_file_path = None
    try:
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if df_for_analysis is None or df_for_analysis.empty:
            print(f"ERROR: Could not retrieve data for '{symbol}'.")
            return
        
        print("Data successfully fetched.")

        if save_to_file:
            json_file_path = save_debug_data(df_for_analysis, symbol, start_time, end_time, project_root)

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching: {e}")
        return

    # --- 3. Run the Executor ---
    print(f"\n--- Running {approach_name} Executor ---")
    try:
        executor = ExecutorClass(symbol)
        # In development mode, the executor should process the entire DataFrame
        alert_result = executor.run(df_for_analysis, new_candle_count=len(df_for_analysis))
        alerts_df = alert_result.alerts
        if not alerts_df.empty:
            print(f"\n--- Found {len(alerts_df)} {approach_name} Alerts ---")
            print(alerts_df.to_string())
        else:
            print(f"\n--- No {approach_name} Alerts Found ---")
    except Exception as e:
        print(f"ERROR: An error occurred during {approach_name} execution: {e}")
        logging.error("Executor failed", exc_info=True)
        return

    # --- 4. Generate Chart (Optional, Standardized) ---
    if generate_chart and json_file_path and not alerts_df.empty:
        print("\n--- Generating Chart ---")
        try:
            chart_output_dir = os.path.join(project_root, 'tests', 'debug', 'charts')
            alert_time = alerts_df.iloc[0]['alert_time'] if not alerts_df.empty else None
            generate_alert_chart(
                input_file=json_file_path,
                output_dir=chart_output_dir,
                approach_name=approach_name,
                alerts_df=alerts_df,
                alert_time=alert_time
            )
            print("Chart generation complete.")
        except Exception as e:
            print(f"ERROR: An error occurred during chart generation: {e}")

    print(f"\n--- Debug Analysis for {approach_name} on {symbol} Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generic debug script for any alert approach.")
    parser.add_argument("--approach", type=str, required=True, help="The approach to analyze (e.g., VRA, TREND_REVERSAL, etc.).")
    parser.add_argument("--symbol", type=str, required=True, help="The stock symbol to analyze.")
    parser.add_argument("--start-time", type=str, required=True, help="Start time in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--end-time", type=str, required=True, help="End time in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--save-to-file", action='store_true', help="Save the fetched data to a JSON file in 'tests/debug/data'.")
    parser.add_argument("--generate-chart", action='store_true', help="Generate and display a chart with the alerts.")
    
    args = parser.parse_args()

    run_debug_analysis(
        approach=args.approach,
        symbol=args.symbol,
        start_time_str=args.start_time,
        end_time_str=args.end_time,
        save_to_file=args.save_to_file,
        generate_chart=args.generate_chart
    )
