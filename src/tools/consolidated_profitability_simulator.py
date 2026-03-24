import argparse
import json
import os
from datetime import datetime
import pandas as pd
import logging
import glob

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Project Imports ---
# Assuming a project structure where these modules are accessible
# Add project root to path to allow for module imports
import sys
import os
# --- FIX: Remove broken path logic ---
# This will be replaced by running the script as a module.
# project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
# sys.path.insert(0, project_root)
# --- END FIX ---

# --- FIX: Use the correct import from data_utils ---
from src.stockreports.utils.data_utils import fetch_intraday_data, TIMEZONE_STR, SESSIONS
# --- END FIX ---
# --- FIX: Import the correct function, not a class ---
from src.stockreports.alert.common.profitability_simulator import simulate_profitability
from src.stockreports.config import loader
from src.stockreports.config.signal_settings import APPROACH_CONFIG
from src.stockreports.config.validation_settings import VALIDATION_PERIOD_MINUTES, VALIDATION_PRICE_THRESHOLD
from src.stockreports.utils.report_utils import get_reports_directory_name
import pytz

def run_consolidated_simulation(execution_symbol: str, alert_sources: list, date_str: str):
    """
    Runs a profitability simulation using consolidated alerts from multiple sources
    to execute trades on a single target symbol.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    reports_dir_name = get_reports_directory_name()
    reports_dir = os.path.join(project_root, reports_dir_name)
    
    # --- 1. Load and Combine Alerts ---
    all_alerts = []
    date_file_str = date_str.replace('-', '')
    
    for source_symbol in alert_sources:
        # --- FIX: Search recursively within the deployment directory ---
        # The alert files are inside approach-specific subfolders.
        source_dir = os.path.join(reports_dir, source_symbol, "deployment")
        
        # Use glob to find all matching alert files for the date, regardless of the subfolder.
        glob_pattern = os.path.join(source_dir, "**", f"alert_notification_{date_file_str}.json")
        alert_files = glob.glob(glob_pattern, recursive=True)
        
        if not alert_files:
            logging.warning(f"No alert files found for {source_symbol} on {date_str} in {source_dir}. Skipping.")
            continue

        for alert_file_path in alert_files:
            if os.path.exists(alert_file_path):
                try:
                    with open(alert_file_path, 'r') as f:
                        alerts = json.load(f)
                        all_alerts.extend(alerts)
                        logging.info(f"Loaded {len(alerts)} alerts from {alert_file_path}")
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode JSON from {alert_file_path}. Skipping.")
        # --- END FIX ---

    if not all_alerts:
        logging.error("No alerts found for any of the specified sources. Aborting simulation.")
        return

    # --- FIX: Parse alert times before sorting to handle non-standard ISO format ---
    from dateutil import parser as date_parser
    
    parsed_alerts = []
    for alert in all_alerts:
        try:
            # The time from JSON is a string; parse it into a timezone-aware datetime object.
            # dateutil.parser is more flexible than datetime.fromisoformat.
            alert['alert_time'] = date_parser.isoparse(alert['alert_time'])
            parsed_alerts.append(alert)
        except (date_parser.ParserError, TypeError):
            logging.warning(f"Could not parse alert_time '{alert.get('alert_time')}'. Skipping this alert.")
    
    # Sort all alerts chronologically using the new datetime object
    parsed_alerts.sort(key=lambda x: x['alert_time'])
    all_alerts = parsed_alerts
    # --- END FIX ---
    
    logging.info(f"Total of {len(all_alerts)} alerts from all sources will be simulated.")

    # --- 2. Load Price Data for the Execution Symbol ---
    settings = loader.get_settings()
    
    # --- FIX: Implement correct data loading logic ---
    simulation_date = datetime.strptime(date_str, '%Y-%m-%d')
    market_tz = pytz.timezone(TIMEZONE_STR)
    
    all_starts = [times['start'] for times in SESSIONS.values()]
    all_ends = [times['end'] for times in SESSIONS.values()]
    start_time_str = min(all_starts)
    end_time_str = max(all_ends)
    start_h, start_m = map(int, start_time_str.split(':'))
    end_h, end_m = map(int, end_time_str.split(':'))

    from_dt = market_tz.localize(simulation_date.replace(hour=start_h, minute=start_m, second=0))
    to_dt = from_dt.replace(hour=end_h, minute=end_m, second=1)
    from_timestamp = int(from_dt.timestamp())
    to_timestamp = int(to_dt.timestamp())

    raw_data = fetch_intraday_data(execution_symbol, from_timestamp, to_timestamp)

    # --- ENHANCEMENT: Save simulation data if enabled ---
    if settings.SAVE_DEV_API_RESPONSE_TO_FILE and raw_data and raw_data.get('s') == 'ok':
        # Use the existing DATA_DIR setting
        data_path = os.path.join(project_root, settings.DATA_DIR, execution_symbol)
        os.makedirs(data_path, exist_ok=True)
        
        file_date_str = simulation_date.strftime('%y%m%d')
        file_path = os.path.join(data_path, f"{execution_symbol.lower()}_response_{file_date_str}.json")
        
        try:
            with open(file_path, 'w') as f:
                json.dump(raw_data, f, indent=4)
            logging.info(f"Successfully saved simulation source data to {file_path}")
        except IOError as e:
            logging.error(f"Failed to save simulation source data to {file_path}: {e}")
    # --- END ENHANCEMENT ---
    
    price_data_df = pd.DataFrame()
    if raw_data and raw_data.get('s') == 'ok':
        keys = ["t", "o", "h", "l", "c", "v"]
        min_len = min(len(raw_data.get(k, [])) for k in keys)
        if min_len > 0:
            price_data_df = pd.DataFrame({
                "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
                "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
                "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
                "volume": raw_data["v"][:min_len],
            })
            price_data_df['time'] = price_data_df['time'].dt.tz_localize('UTC').dt.tz_convert(market_tz)
            # --- FIX: Set the 'time' column as the index ---
            price_data_df = price_data_df.set_index('time')
            # --- END FIX ---
    # --- END FIX ---

    if price_data_df.empty:
        logging.error(f"Could not load price data for execution symbol '{execution_symbol}' on {date_str}. Aborting.")
        return

    # --- ENHANCEMENT: Add synthetic end-of-day alert to close open positions ---
    if all_alerts and not price_data_df.empty:
        # Determine the final open position from the last chronological alert
        last_real_alert = all_alerts[-1]
        open_position_signal = last_real_alert.get('signal')

        if open_position_signal:
            # Get the last data point for the closing price and time
            last_data_point = price_data_df.iloc[-1]
            closing_price = last_data_point['close']
            closing_time_ts = last_data_point.name # The index is now the timestamp

            # --- FIX: Convert pandas Timestamp to standard datetime ---
            closing_time = closing_time_ts.to_pydatetime()
            # --- END FIX ---

            # Create a synthetic alert to close the position
            synthetic_alert = {
                'alert_time': closing_time,
                'signal': 'SELL' if open_position_signal == 'BUY' else 'BUY',
                'approach': 'EOD_CLOSE',
                'source_symbol': 'SYNTHETIC',
                'suggested_price': closing_price,
                'is_synthetic': True # Flag to identify this alert
            }
            
            all_alerts.append(synthetic_alert)
            logging.info(f"Appended synthetic EOD alert to close '{open_position_signal}' position at {closing_price}.")
    # --- END ENHANCEMENT ---

    # --- 3. Run Simulation ---
    # --- FIX: Call the function directly instead of instantiating a class ---
    summary = simulate_profitability(
        alerts=all_alerts,
        trade_data=price_data_df
    )
    # --- END FIX ---

    # --- 4. Generate and Save Report ---
    output_dir = os.path.join(reports_dir, "consolidated", "deployment")
    os.makedirs(output_dir, exist_ok=True)
    
    # Format date for the filename
    file_date_str = date_str.replace('-', '')
    output_filename = f"simulation_summary_{execution_symbol}_{file_date_str}.json"
    output_path = os.path.join(output_dir, output_filename)

    try:
        # --- FIX: Convert the report object to a dictionary for JSON serialization ---
        with open(output_path, 'w') as f:
            # The function returns a dataclass-like object, convert it to dict
            from dataclasses import asdict
            summary_dict = asdict(summary)
            summary_dict['app_config'] = APPROACH_CONFIG
            validation_config = {
                "VALIDATION_PERIOD_MINUTES": VALIDATION_PERIOD_MINUTES,
                "VALIDATION_PRICE_THRESHOLD": VALIDATION_PRICE_THRESHOLD
            }
            summary_dict['validation_config'] = validation_config
            json.dump(summary_dict, f, indent=4)
        # --- END FIX ---
        logging.info(f"Successfully saved consolidated simulation report to {output_path}")
    except Exception as e:
        logging.error(f"Failed to save report to {output_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a consolidated profitability simulation on a single symbol using alerts from multiple sources."
    )
    parser.add_argument(
        "--execution-symbol",
        type=str,
        required=True,
        help="The symbol to simulate trading on (e.g., '41I1FB000')."
    )
    parser.add_argument(
        "--alert-sources",
        nargs='+',
        required=True,
        help="A list of symbols to use as alert sources (e.g., 'VN30' '41I1FB000')."
    )
    parser.add_argument(
        "--date",
        type=str,
        required=True,
        help="The date to process in YYYY-MM-DD format (e.g., '2025-10-27')."
    )

    args = parser.parse_args()

    run_consolidated_simulation(
        execution_symbol=args.execution_symbol,
        alert_sources=args.alert_sources,
        date_str=args.date
    )
