# tests/debug/alert/approach/STRONG_CANDLE/debug_executor.py
import sys
import os
import argparse
import pandas as pd
import logging
import importlib

# Add the project root to the Python path for reliable imports
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import necessary components from the main application and debug utilities
from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
from src.stockreports.alert.common.constants import Approach
from tests.debug.common.charts.visibility_chart import VisibilityChartGenerator
from tests.debug.common.utils.debug_utils import save_debug_data

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    """
    Sets up the environment and runs the debug analysis for the STRONG_CANDLE approach.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    
    # Dynamically import the executor AFTER reloading the configuration
    from src.stockreports.alert.approach.STRONG_CANDLE.executor import StrongCandleExecutor

    settings = loader.get_settings()
    settings.MODE = 'DEVELOPMENT' # Use DEVELOPMENT mode for debugging
    
    approach_name = Approach.STRONG_CANDLE

    print(f"--- Starting Debug Analysis for {approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching data for {symbol} from {start_time} to {end_time} ---")
    try:
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        df_for_analysis = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if df_for_analysis is None or df_for_analysis.empty:
            print(f"ERROR: Could not retrieve data for '{symbol}'.")
            return
        
        print("Data successfully fetched.")

        if save_to_file:
            save_debug_data(df_for_analysis, symbol, start_time, end_time, project_root)

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching: {e}")
        return

    # --- 3. Run the Executor ---
    print(f"\n--- Running {approach_name} Executor ---")
    try:
        executor = StrongCandleExecutor(symbol)
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

    # --- 4. Generate Chart (Optional) ---
    if generate_chart and not alerts_df.empty:
        print("\n--- Generating Chart ---")
        try:
            chart_generator = VisibilityChartGenerator(
                df=df_for_analysis,
                alerts_df=alerts_df,
                symbol=symbol,
                approach_name=approach_name,
                start_time=start_time,
                end_time=end_time
            )
            chart_generator.create_chart()
            print("Chart generation complete.")
        except Exception as e:
            print(f"ERROR: An error occurred during chart generation: {e}")

    print(f"\n--- Debug Analysis for {approach_name} on {symbol} Finished ---")


def main():
    parser = argparse.ArgumentParser(description="Debug script for the STRONG_CANDLE approach.")
    parser.add_argument("--symbol", type=str, required=True, help="The stock symbol to analyze.")
    parser.add_argument("--start-time", type=str, required=True, help="Start time in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--end-time", type=str, required=True, help="End time in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--save-to-file", action='store_true', help="Save the fetched data to a JSON file in 'tests/debug/data'.")
    parser.add_argument("--generate-chart", action='store_true', help="Generate and display a chart with the alerts.")
    
    args = parser.parse_args()

    run_debug_analysis(
        symbol=args.symbol,
        start_time_str=args.start_time,
        end_time_str=args.end_time,
        save_to_file=args.save_to_file,
        generate_chart=args.generate_chart
    )

if __name__ == "__main__":
    main()
