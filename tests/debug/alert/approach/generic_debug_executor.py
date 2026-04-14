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
from src.stockreports.data_services import DataServiceOrchestrator
from src.stockreports.alert.common.constants import Approach
from src.stockreports.coordination import get_coordinator
from src.stockreports.utils.approach_utils import get_approach_executor
from src.stockreports.alert.model.models import AlertResult
from tests.debug.common.charts.visibility_chart import generate_alert_chart
from tests.debug.common.utils.debug_utils import save_debug_data

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def run_debug_analysis(approach, symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    """
    Sets up the environment and runs the debug analysis for the selected approach.
    
    This mirrors the executor initialization used in symbol_alerter._perform_monitoring_session:
    1. Get resolution from resolution_coordinator
    2. Use get_approach_executor(symbol, approach, resolution) to instantiate
    3. Run executor.run(df=data, new_candle_count=len(data))
    """
    # --- 1. Load Configuration & Set Mode ---
    importlib.reload(loader)
    settings = loader.get_settings()
    settings.MODE = 'DEPLOYMENT'  # Use DEPLOYMENT mode to bypass load_data_for_development() bug
    
    # Normalize approach name to uppercase with underscores
    # E.g., "VRA" → "VRA", "reversal-anchor-signal-candle" → "REVERSAL_ANCHOR_SIGNAL_CANDLE"
    approach_normalized = approach.upper().replace('-', '_')
    
    print(f"--- Starting Debug Analysis for {approach_normalized} on {symbol} from {start_time_str} to {end_time_str} (Mode: {settings.MODE}) ---")

    # --- 2. Get Resolution from Coordinator ---
    try:
        resolution_coordinator = get_coordinator()
        resolution = resolution_coordinator.get_resolutions(approach_normalized)
        print(f"Resolution for {approach_normalized}: {resolution} minutes")
    except KeyError as e:
        print(f"ERROR: Cannot get resolution for approach '{approach_normalized}'. Error: {e}")
        return
    except Exception as e:
        print(f"ERROR: An error occurred while getting resolution: {e}")
        return

    # --- 3. Fetch Data ---
    timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']
    start_time = pd.to_datetime(start_time_str).tz_localize(timezone)
    end_time = pd.to_datetime(end_time_str).tz_localize(timezone)

    print(f"\n--- Fetching {resolution}-minute data for {symbol} from {start_time} to {end_time} ---")
    json_file_path = None
    try:
        # ✅ USE CENTRALIZED DATA SERVICES ORCHESTRATOR
        orchestrator = DataServiceOrchestrator()
        
        print(f"DEBUG: Calling orchestrator.fetch_and_process with resolution={resolution}")
        df_for_analysis = orchestrator.fetch_and_process(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            resolution=resolution  # Use approach-specific resolution
        )

        # More explicit type checking to avoid ambiguous DataFrame truth value
        if df_for_analysis is None:
            print(f"ERROR: orchestrator returned None")
            return
        
        if not isinstance(df_for_analysis, pd.DataFrame):
            print(f"ERROR: orchestrator did not return a DataFrame, got {type(df_for_analysis)}")
            return
        
        if len(df_for_analysis) == 0:
            print(f"ERROR: DataFrame is empty")
            return
        
        print(f"Data successfully fetched: {len(df_for_analysis)} rows")

        if save_to_file:
            json_file_path = save_debug_data(df_for_analysis, symbol, start_time, end_time, project_root)

    except Exception as e:
        print(f"ERROR: An error occurred during data fetching: {e}")
        logging.error("Data fetching failed", exc_info=True)
        return

    # --- 4. Initialize Executor (Same as symbol_alerter) ---
    print(f"\n--- Initializing {approach_normalized} Executor ---")
    try:
        executor = get_approach_executor(symbol, approach_normalized, resolution)
        if not executor:
            print(f"ERROR: Could not instantiate executor for '{approach_normalized}'")
            return
        print(f"Executor initialized successfully")
    except Exception as e:
        print(f"ERROR: An error occurred while initializing executor: {e}")
        logging.error("Executor initialization failed", exc_info=True)
        return

    # --- 5. Run the Executor ---
    print(f"\n--- Running {approach_normalized} Executor ---")
    try:
        # In development mode, process the entire DataFrame
        print(f"DEBUG: Calling executor.run with df shape={df_for_analysis.shape}, new_candle_count={len(df_for_analysis)}")
        alert_result: AlertResult = executor.run(df=df_for_analysis.copy(), new_candle_count=len(df_for_analysis))
        
        # Verify AlertResult structure
        if not isinstance(alert_result, AlertResult):
            print(f"ERROR: executor.run() did not return AlertResult, got {type(alert_result)}")
            return
        
        # Use confirmed_alerts (List[AlertData]) instead of deprecated alerts property
        if not hasattr(alert_result, 'confirmed_alerts'):
            print(f"ERROR: AlertResult has no 'confirmed_alerts' attribute")
            return
        
        confirmed_alerts = alert_result.confirmed_alerts
        
        # Use len() instead of .empty to avoid ambiguous truth value
        if len(confirmed_alerts) == 0:
            print(f"\n--- No {approach_normalized} Alerts Found ---")
        else:
            print(f"\n--- Found {len(confirmed_alerts)} {approach_normalized} Alerts ---")
            # Convert AlertData list to DataFrame for display
            alerts_data = [
                {
                    'symbol': alert.symbol,
                    'approach': alert.approach,
                    'alert_time': alert.alert_time,
                    'start_time': alert.start_time,
                    'signal': alert.signal,
                    'alert_price': alert.alert_price,
                    'start_price': alert.start_price,
                    'confidence': getattr(alert, 'confidence', 'N/A'),
                    'details': getattr(alert, 'details', 'N/A')
                }
                for alert in confirmed_alerts
            ]
            alerts_df = pd.DataFrame(alerts_data)
            print(alerts_df.to_string())
    except Exception as e:
        print(f"ERROR: An error occurred during {approach_normalized} execution: {e}")
        logging.error("Executor failed", exc_info=True)
        return

    # --- 6. Generate Chart (Optional, Standardized) ---
    if generate_chart and json_file_path and len(confirmed_alerts) > 0:
        print("\n--- Generating Chart ---")
        try:
            chart_output_dir = os.path.join(project_root, 'tests', 'debug', 'charts')
            alert_time = alerts_df.iloc[0]['alert_time'] if len(alerts_df) > 0 else None
            generate_alert_chart(
                input_file=json_file_path,
                output_dir=chart_output_dir,
                approach_name=approach_normalized,
                alerts_df=alerts_df,
                alert_time=alert_time
            )
            print("Chart generation complete.")
        except Exception as e:
            print(f"ERROR: An error occurred during chart generation: {e}")

    print(f"\n--- Debug Analysis for {approach_normalized} on {symbol} Finished ---")


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
