import argparse
import json
import os
import glob
from datetime import datetime, timedelta
import pandas as pd
import logging
import sys
from typing import Optional

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.stockreports.utils.alert_utils import calculate_suggested_prices
from src.stockreports.utils.time_utils import get_market_timezone
from dateutil import parser as date_parser
# Import settings for fallback calculation
from src.stockreports.config import price_alert_settings
import importlib


def _calculate_performance_fallback(signal: str, approach: str, alert_price: float) -> Optional[float]:
    """
    Calculates performance-based suggested price using the alert_price as a fallback.
    This is used when market data is unavailable.
    """
    if not all([signal, approach, alert_price is not None]):
        logging.warning("Fallback calculation skipped due to missing signal, approach, or alert_price.")
        return None

    try:
        importlib.reload(price_alert_settings)
        performance_config = getattr(price_alert_settings, 'PERFORMANCE_BY_APPROACH', {})
        approach_perf = performance_config.get(approach.upper())

        if approach_perf and 'avg_worst_loss_price' in approach_perf:
            adjustment = approach_perf['avg_worst_loss_price']
            
            if signal.upper() == 'BUY':
                fallback_price = round(alert_price - adjustment, 1)
            elif signal.upper() == 'SELL':
                fallback_price = round(alert_price + adjustment, 1)
            else:
                return None
            
            logging.info(f"Calculated performance price for '{approach}' using FALLBACK logic: {fallback_price}")
            return fallback_price
        else:
            logging.warning(f"No 'avg_worst_loss_price' config found for approach '{approach}' in fallback.")
            return None
    except Exception as e:
        logging.error(f"Error during fallback performance price calculation: {e}", exc_info=True)
        return None


def update_alerts_with_suggested_prices(from_date_str: str, to_date_str: str, override: bool = False):
    """
    Scans for alert files within a date range and updates each alert
    with performance and structural suggested prices.
    """
    reports_dir = os.path.join(project_root, "reports")
    logging.info(f"Scanning for alert files in {reports_dir} from {from_date_str} to {to_date_str}")

    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    # Find all alert files recursively
    glob_pattern = os.path.join(reports_dir, "**", "alert_notification_*.json")
    all_files = glob.glob(glob_pattern, recursive=True)

    # Filter files by date
    filtered_files = []
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            date_part_str = filename.replace('alert_notification_', '').replace('.json', '')
            file_date = datetime.strptime(date_part_str, '%Y%m%d').date()
            if from_date <= file_date <= to_date:
                filtered_files.append(file_path)
        except (ValueError, IndexError):
            logging.warning(f"Could not parse date from filename: {filename}. Skipping.")
            continue

    if not filtered_files:
        logging.warning("No alert files found in the specified date range.")
        return

    logging.info(f"Found {len(filtered_files)} alert files to process.")

    for file_path in filtered_files:
        try:
            with open(file_path, 'r') as f:
                content = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Could not read or parse {file_path}: {e}. Skipping.")
            continue

        # The alerts might be under a key (e.g., 'alerts') or be the root object
        alerts = []
        if isinstance(content, dict) and 'alerts' in content and isinstance(content['alerts'], list):
            alerts = content['alerts']
        elif isinstance(content, list):
            alerts = content
        else:
            logging.warning(f"Alerts in {file_path} are not in a recognized list format. Skipping file.")
            continue
        
        if not alerts:
            logging.info(f"No alerts found inside {file_path}. Skipping.")
            continue

        logging.info(f"Processing {len(alerts)} alerts in {file_path}...")
        
        updated_count = 0
        for alert in alerts:
            try:
                # Check if we should skip this alert based on the override flag
                if not override and alert.get('performance_suggested_price') is not None:
                    continue

                alert_time_str = alert['alert_time']
                # Parse the timestamp. If it's naive, localize it to the market timezone.
                # If it's aware, it will be handled correctly, then converted to UTC.
                alert_time = pd.to_datetime(alert_time_str)
                if alert_time.tzinfo is None:
                    market_tz = get_market_timezone()
                    alert_time = alert_time.tz_localize(market_tz)
                
                signal = alert.get('signal')
                approach = alert.get('approach')

                if not signal:
                    logging.warning(f"Skipping alert due to missing 'signal': {alert}")
                    continue

                # Calculate the suggested prices using the localized market timestamp
                perf_price, struct_price = calculate_suggested_prices(signal, alert_time, approach)

                # If performance price could not be calculated (e.g., due to missing data),
                # try the fallback method using the alert_price.
                if perf_price is None:
                    alert_price = alert.get('alert_price')
                    logging.warning(f"Primary performance price calculation failed for alert at {alert_time}. Attempting fallback.")
                    perf_price = _calculate_performance_fallback(signal, approach, alert_price)

                # Update the alert object if the prices are not None
                price_updated = False
                if perf_price is not None:
                    alert['performance_suggested_price'] = perf_price
                    price_updated = True
                
                if struct_price is not None:
                    alert['structural_suggested_price'] = struct_price
                    price_updated = True

                if price_updated:
                    updated_count += 1

            except Exception as e:
                logging.error(f"Failed to process an alert in {file_path}: {alert}. Error: {e}", exc_info=True)

        # Write the updated content back to the file
        try:
            # Determine if the original content was a dict or a list
            if isinstance(content, dict) and 'alerts' in content:
                content['alerts'] = alerts
                output_content = content
            else:
                output_content = alerts

            with open(file_path, 'w') as f:
                json.dump(output_content, f, indent=4, default=str)
            logging.info(f"Successfully updated {updated_count} alerts in {file_path}.")

        except IOError as e:
            logging.error(f"Failed to write updated file {file_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update existing alert notification files with performance and structural suggested prices."
    )
    parser.add_argument(
        "--from-date",
        type=str,
        required=True,
        help="The start date for updating alerts in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--to-date",
        type=str,
        required=True,
        help="The end date for updating alerts in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--override",
        action='store_true',
        help="If set, override existing suggested prices. Otherwise, only update if they are missing."
    )

    args = parser.parse_args()

    update_alerts_with_suggested_prices(
        from_date_str=args.from_date,
        to_date_str=args.to_date,
        override=args.override
    )
