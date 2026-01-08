"""
This script provides a maintenance utility to update a specific numeric field
in historical alert notification files within a given date range.

It scans the 'reports' directory for alert files (alert_notification_*.json),
filters them by date, and for each alert in the file, it adjusts the
value of a specified numeric field by a pre-configured offset.

The offset is read from the `STRUCTURAL_PRICE_LEVEL_OFFSET` setting in
`src.stockreports.config.price_alert_settings`.

The script will only update the field if it already exists and contains a
numeric value (integer or float). It will skip fields that are null,
non-numeric, or non-existent.

This is useful for backfilling or adjusting calculated price points across
a large number of historical records without manual intervention.
"""
import argparse
import json
import os
import glob
from datetime import datetime
import logging
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.stockreports.config import price_alert_settings
from src.stockreports.utils.alert_utils import adjust_price_by_signal

def update_alert_field(field_name: str, from_date_str: str, to_date_str: str):
    """
    Scans for alert files within a date range and updates a specific numeric field
    for each alert by adding a price level from the configuration.
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
                alerts = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            logging.error(f"Could not read or parse JSON from {file_path}. Skipping.")
            continue

        updated = False
        for alert in alerts:
            if field_name in alert and isinstance(alert[field_name], (int, float)):
                signal = alert.get('signal', '').upper()
                original_price = alert[field_name]
                alert[field_name] = adjust_price_by_signal(original_price, signal)
                
                updated = True
                logging.info(f"Updated '{field_name}' for signal '{signal}' in alert for symbol {alert.get('symbol')} in {file_path}")

        if updated:
            try:
                with open(file_path, 'w') as f:
                    json.dump(alerts, f, indent=4)
                logging.info(f"Successfully updated {file_path}")
            except IOError:
                logging.error(f"Could not write updates to {file_path}.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update a numeric field in alert notifications by adding a configured price level offset.",
        epilog="""
Example usage:
  python3 src/tools/maintenance/update_alert_field.py --field structural_suggested_price --from_date 2025-12-01 --to_date 2025-12-31
""",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--field", type=str, required=True, help="The numeric field to update in the alert notifications (e.g., 'structural_suggested_price').")
    parser.add_argument("--from_date", type=str, required=True, help="Start date for processing alerts (YYYY-MM-DD).")
    parser.add_argument("--to_date", type=str, required=True, help="End date for processing alerts (YYYY-MM-DD).")

    args = parser.parse_args()

    update_alert_field(args.field, args.from_date, args.to_date)
