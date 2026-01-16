"""
A command-line tool for debugging the COMPARISON alert logic.

This script allows for testing the COMPARISON approach on a specific symbol and 
time range, with options to save the data and generate a chart for visual analysis.

Usage:
    python3 tests/debug/alert/approach/COMPARISON/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS] \\
        --save-to-file \\
        --generate-chart

Example:
    python3 tests/debug/alert/approach/COMPARISON/debug_executor.py \\
        --symbol "VN30F1M" \\
        --start-time "2026-01-13 13:30:00" \\
        --end-time "2026-01-13 13:55:00" \\
        --save-to-file --generate-chart
"""
import argparse
import logging
import os
import sys
import pandas as pd
import importlib

# Add project root to path to allow direct imports from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../')))

# Import necessary components from the main application and debug utilities
from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
from src.stockreports.alert.common.constants import Approach, Mode
from tests.debug.common.charts.visibility_chart import VisibilityChartGenerator
from tests.debug.common.utils.debug_utils import save_debug_data

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug(symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    """
    Run the debug script for the COMPARISON approach.
    This function orchestrates the setup, data loading, execution, and reporting.
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    
    # Dynamically import the executor AFTER reloading the configuration
    from src.stockreports.alert.approach.COMPARISON.executor import ComparisonExecutor

    settings = loader.get_settings()
    settings.MODE = Mode.DEPLOYMENT # Use DEPLOYMENT to fetch data for the specified date
    
    approach_name = Approach.COMPARISON

    logging.info(f"--- Starting Debug Analysis for {approach_name} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Fetch Data ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    logging.info(f"Fetching data for {symbol} from {start_time} to {end_time}")
    try:
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        market_data = load_live_data(symbol, from_timestamp=from_timestamp, to_timestamp=to_timestamp)

        if market_data is None or market_data.empty:
            logging.warning(f"No data found for symbol '{symbol}' in the given time range. Exiting.")
            return
        
        logging.info(f"Loaded {len(market_data)} data points.")

        if save_to_file:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../../'))
            save_debug_data(market_data, symbol, start_time, end_time, project_root)

    except Exception as e:
        logging.error(f"An error occurred during data fetching: {e}", exc_info=True)
        return

    # --- 3. Executor Initialization & Execution ---
    logging.info("Executing alert generation...")
    try:
        executor = ComparisonExecutor(symbol)
        # In development mode, the executor processes the entire DataFrame
        alert_result = executor.run(df=market_data, new_candle_count=len(market_data))
        
        alerts_df = alert_result.alerts
        if not alerts_df.empty:
            logging.info(f"Successfully generated {len(alerts_df)} new alerts.")
            print("\n--- Generated Alerts ---")
            print(alerts_df.to_string())
            print("----------------------\n")
        else:
            logging.info("No new alerts were generated.")

    except Exception as e:
        logging.error(f"An error occurred during {approach_name} execution: {e}", exc_info=True)
        return

    # --- 4. Report & Visualize Results ---
    if generate_chart and not alerts_df.empty:
        logging.info("Generating chart...")
        try:
            chart_generator = VisibilityChartGenerator(
                df=market_data,
                alerts_df=alerts_df,
                symbol=symbol,
                approach_name=approach_name,
                start_time=start_time,
                end_time=end_time
            )
            chart_generator.create_chart()
            logging.info("Chart generation complete.")
        except Exception as e:
            logging.error(f"An error occurred during chart generation: {e}", exc_info=True)

    logging.info(f"--- Debug Analysis for {approach_name} on {symbol} Finished ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug script for the COMPARISON alert approach.")
    parser.add_argument("--symbol", type=str, required=True, help="The stock symbol to analyze (e.g., 'VN30F1M').")
    parser.add_argument("--start-time", type=str, required=True, help="The start of the time window in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--end-time", type=str, required=True, help="The end of the time window in 'YYYY-MM-DD HH:MM:SS' format.")
    parser.add_argument("--save-to-file", action="store_true", help="If set, saves the generated alerts to a report file.")
    parser.add_argument("--generate-chart", action="store_true", help="If set, generates and saves a chart with the alerts plotted.")

    args = parser.parse_args()

    run_debug(
        symbol=args.symbol,
        start_time_str=args.start_time,
        end_time_str=args.end_time,
        save_to_file=args.save_to_file,
        generate_chart=args.generate_chart,
    )
