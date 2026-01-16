"""
A command-line tool for debugging the CONSISTENT_MOMENTUM alert logic by calling the main executor.

Usage:
    # Ensure your PYTHONPATH is set to the project root
    export PYTHONPATH=$(pwd)
    python3 tests/debug/alert/approach/CONSISTENT_MOMENTUM/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS] \\
        --save-to-file \\
        --generate-chart

Example:
    python3 tests/debug/alert/approach/CONSISTENT_MOMENTUM/debug_executor.py \\
        --symbol "VN30F1M" \\
        --start-time "2025-09-15 10:00:00" \\
        --end-time "2025-09-15 11:00:00" \\
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
from tests.debug.common.charts.visibility_chart import VisibilityChartGenerator
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
    from src.stockreports.alert.approach.CONSISTENT_MOMENTUM.executor import ConsistentMomentumExecutor

    settings = loader.get_settings()
    # Set the mode for your test. DEPLOYMENT is common for testing live scenarios.
    settings.MODE = 'DEPLOYMENT' 
    
    approach_name = Approach.CONSISTENT_MOMENTUM

    print(f"--- Starting Debug Analysis for {approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data for the Analysis Window ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\\n--- Fetching data for main symbol from {start_time} to {end_time} ---")
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

    # --- 3. Run the Executor ---
    print("\\n--- Running Executor ---")
    try:
        executor = ConsistentMomentumExecutor(symbol=symbol)
        # The `new_candle_count` is set to the length of the DataFrame in debug mode
        # to simulate a full historical run over the given window.
        alert_result = executor.run(df_for_analysis, new_candle_count=len(df_for_analysis))

        if alert_result.alerts.empty:
            print("Executor finished: No alerts were generated.")
        else:
            print("Executor finished: Alerts were generated.")
            # Pretty-print the alerts DataFrame
            print(alert_result.alerts.to_string())

    except Exception as e:
        print(f"ERROR: An error occurred during executor run: {e}")
        logging.exception("Executor run failed.")
        return

    # --- 4. Generate Visibility Chart (if requested and alerts were found) ---
    if generate_chart and not alert_result.alerts.empty:
        print("\\n--- Generating Visibility Chart ---")
        try:
            # For debugging, we often focus on the first alert found.
            first_alert = alert_result.alerts.iloc[0]
            
            chart_generator = VisibilityChartGenerator(
                df=df_for_analysis,
                alert_data=first_alert.to_dict(),
                approach_name=str(approach_name),
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                project_root=project_root
            )
            chart_generator.generate_chart()
            print("Chart generation complete.")

        except Exception as e:
            print(f"ERROR: An error occurred during chart generation: {e}")
            logging.exception("Chart generation failed.")

    print("\\n--- Debug Analysis Complete ---")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=f"Debug script for the {Approach.CONSISTENT_MOMENTUM} approach.")
    parser.add_argument('--symbol', type=str, required=True, help='The stock symbol to analyze (e.g., "VN30F1M").')
    parser.add_argument('--start-time', type=str, required=True, help='Start time for analysis in "YYYY-MM-DD HH:MM:SS" format.')
    parser.add_argument('--end-time', type=str, required=True, help='End time for analysis in "YYYY-MM-DD HH:MM:SS" format.')
    parser.add_argument('--save-to-file', action='store_true', help='If set, saves the fetched data and alert results to a JSON file in the debug output directory.')
    parser.add_argument('--generate-chart', action='store_true', help='If set, generates and displays a visibility chart for the first alert found.')

    args = parser.parse_args()

    run_debug_analysis(
        symbol=args.symbol,
        start_time_str=args.start_time,
        end_time_str=args.end_time,
        save_to_file=args.save_to_file,
        generate_chart=args.generate_chart
    )
