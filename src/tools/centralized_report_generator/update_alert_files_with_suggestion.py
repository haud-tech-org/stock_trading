"""
Maintenance script to backfill or update suggested entry prices in alert files.

Purpose:
This script is a standalone tool for maintaining data integrity in historical
alert files. It scans the entire 'reports' directory for alert notification
JSON files within a specified date range. For each alert found, it calculates
and populates the 'performance_suggested_price' and/or 'structural_suggested_price'
fields.

This is essential for:
- Backfilling suggested prices on older alert files that were generated before
  this logic existed.
- Updating suggested prices across all files after making changes to the
  price suggestion algorithms.
- Ensuring data consistency for analysis and reporting.

The script recursively searches through all subdirectories, making it compatible
with the new scenario-based report structure (e.g., reports/.../profit_3.0_loss_3.0/).

Usage Examples:

1. Simplified - Update all price types for a single day:
   python3 -m src.tools.centralized_report_generator.update_alert_files_with_suggestion \\
       --from-date 2026-01-08 \\
       --suggestion-type all

2. Full Arguments - Update only the performance-based price for a date range:
   python3 -m src.tools.centralized_report_generator.update_alert_files_with_suggestion \\
       --from-date 2026-01-05 \\
       --to-date 2026-01-08 \\
       --suggestion-type performance
"""
import argparse
import json
import os
from datetime import datetime
import pandas as pd
import logging
import sys
from typing import Optional
import importlib

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.stockreports.utils.alert_utils import calculate_suggested_prices, _apply_price_offset
from src.stockreports.utils.time_utils import get_market_timezone
from src.stockreports.utils.report_utils import find_all_alert_files, get_reports_directory_name
# Import settings for fallback calculation
from src.stockreports.config import price_alert_settings


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

        # Get min/max offsets for clamping
        max_offset = getattr(price_alert_settings, 'MAX_PRICE_ADJUSTMENT_OFFSET')
        min_offset = getattr(price_alert_settings, 'MIN_PRICE_ADJUSTMENT_OFFSET')

        if approach_perf and 'avg_worst_loss_price' in approach_perf:
            # Ensure adjustment is always positive, _apply_price_offset handles direction
            adjustment = abs(approach_perf['avg_worst_loss_price'])
            
            # Use the centralized offset function
            fallback_price = _apply_price_offset(alert_price, adjustment, signal, min_offset, max_offset)
            
            logging.info(f"Calculated performance price for '{approach}' using FALLBACK logic: {fallback_price}")
            return fallback_price
        else:
            logging.warning(f"No 'avg_worst_loss_price' config found for approach '{approach}' in fallback.")
            return None
    except Exception as e:
        logging.error(f"Error during fallback performance price calculation: {e}", exc_info=True)
        return None


def update_alerts_with_suggested_prices(from_date_str: str, to_date_str: str, suggestion_type: Optional[str] = None):
    """
    Scans alert notification files and updates them with suggested prices.

    This function finds all `alert_notification_*.json` files within the given
    date range and calculates suggested prices for each alert inside. The behavior
    is controlled by the `suggestion_type` parameter. If `suggestion_type` is not
    provided, the function will exit without making changes.

    Args:
        from_date_str (str): The start date in 'YYYY-MM-DD' format.
        to_date_str (str): The end date in 'YYYY-MM-DD' format.
        suggestion_type (Optional[str]): The type of price to update.
            Can be 'performance', 'structural', or 'all'. If None, no action is taken.
    """
    if not suggestion_type:
        logging.info("No --suggestion-type provided. Exiting without updating any prices.")
        return

    reports_dir_name = get_reports_directory_name()
    reports_dir = os.path.join(project_root, reports_dir_name)
    logging.info(f"Scanning for alert files in {reports_dir} from {from_date_str} to {to_date_str}")

    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    # Use the centralized utility function to find all relevant alert files
    filtered_files = find_all_alert_files(reports_dir, from_date, to_date)

    if not filtered_files:
        logging.warning("No alert files found in the specified date range across any report directories.")
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
                alert_time_str = alert['alert_time']
                # Parse the timestamp. If it's naive, localize it to the market timezone.
                # If it's aware, it will be handled correctly, then converted to UTC.
                alert_time = pd.to_datetime(alert_time_str)
                if alert_time.tzinfo is None:
                    market_tz = get_market_timezone()
                    alert_time = alert_time.tz_localize(market_tz)
                
                signal = alert.get('signal')
                approach = alert.get('approach')
                symbol = alert.get('symbol')

                if not signal:
                    logging.warning(f"Skipping alert due to missing 'signal': {alert}")
                    continue

                perf_price, struct_price = None, None
                # Calculate prices once, then use the results conditionally.
                if suggestion_type in ['performance', 'structural', 'all']:
                    perf_price, struct_price = calculate_suggested_prices(signal, alert_time, approach, symbol)

                # Fallback logic should only run if performance price was requested and failed.
                if suggestion_type in ['performance', 'all']:
                    if perf_price is None:
                        alert_price = alert.get('alert_price')
                        logging.warning(f"Primary performance price calculation failed for alert at {alert_time}. Attempting fallback.")
                        perf_price = _calculate_performance_fallback(signal, approach, alert_price)

                # Update the alert object if the prices are not None
                price_updated = False
                if suggestion_type in ['performance', 'all'] and perf_price is not None:
                    alert['performance_suggested_price'] = perf_price
                    price_updated = True
                
                if suggestion_type in ['structural', 'all']:
                    if struct_price is not None:
                        alert['structural_suggested_price'] = struct_price
                        price_updated = True
                    elif perf_price is not None:
                        logging.info(f"Structural price calculation failed. Using performance price ({perf_price}) as fallback.")
                        alert['structural_suggested_price'] = perf_price
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
        description="A maintenance tool to scan all report files and backfill/update suggested entry prices for alerts.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--from-date",
        type=str,
        required=True,
        help="The start date for the scan in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--to-date",
        type=str,
        help="The end date for the scan in YYYY-MM-DD format. If omitted, defaults to the same as --from-date."
    )
    parser.add_argument(
        "--suggestion-type",
        type=str,
        choices=['performance', 'structural', 'all'],
        required=True,
        help="Specify which suggested price to calculate and update:\n"
             "  'performance': Update 'performance_suggested_price' only.\n"
             "  'structural':  Update 'structural_suggested_price' only.\n"
             "  'all':         Update both fields."
    )

    args = parser.parse_args()

    # If to_date is not provided, default it to from_date for a single-day scan
    to_date_str = args.to_date if args.to_date else args.from_date

    update_alerts_with_suggested_prices(
        from_date_str=args.from_date,
        to_date_str=to_date_str,
        suggestion_type=args.suggestion_type
    )
