"""
Maintenance script to backfill or update suggested profit threshold in alert files.

Purpose:
This script is a standalone tool for maintaining data integrity in historical
alert files. It scans the entire 'reports' directory for alert notification
JSON files within a specified date range. For each alert found, it calculates
and populates the 'suggested_profit_threshold' field.

This is essential for:
- Backfilling profit thresholds on older alert files that were generated before
  this logic existed.
- Updating profit thresholds across all files after making changes to the
  threshold calculation algorithms.
- Ensuring data consistency for analysis and reporting.

The script recursively searches through all subdirectories, making it compatible
with the scenario-based report structure (e.g., reports/.../profit_3.0_loss_3.0/).

Usage Examples:

1. Simplified - Update profit threshold for a single day:
   python3 -m src.tools.centralized_report_generator.update_alert_files_with_profit_threshold \\
       --from-date 2026-01-26 \\
       --approach CONSISTENT_MOMENTUM

2. Full Arguments - Update profit threshold for a date range with default value:
   python3 -m src.tools.centralized_report_generator.update_alert_files_with_profit_threshold \\
       --from-date 2026-01-05 \\
       --to-date 2026-01-26 \\
       --default-threshold 3.15

3. Use approach-specific threshold configuration:
   python3 -m src.tools.centralized_report_generator.update_alert_files_with_profit_threshold \\
       --from-date 2026-01-26 \\
       --to-date 2026-02-11 \\
       --use-config
"""
import argparse
import json
import os
import glob
from datetime import datetime, timedelta
import logging
import sys
from typing import Optional

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from src.stockreports.utils.report_utils import find_all_alert_files, get_reports_directory_name
from src.stockreports.config import price_alert_settings
import importlib


def _calculate_profit_threshold_by_approach(approach: str, default_threshold: float = 3.15) -> float:
    """
    Calculates profit threshold based on approach-specific configuration.
    
    This function uses the PROFIT_THRESHOLD_BY_APPROACH configuration dictionary
    from price_alert_settings, which is separate from PERFORMANCE_BY_APPROACH and
    specifically designed for profit threshold calculations.
    
    Args:
        approach (str): The alert approach name (e.g., 'CONSISTENT_MOMENTUM')
        default_threshold (float): Default threshold to use if no config found
        
    Returns:
        float: The calculated profit threshold
    """
    try:
        importlib.reload(price_alert_settings)
        profit_threshold_config = getattr(price_alert_settings, 'PROFIT_THRESHOLD_BY_APPROACH', {})
        threshold = profit_threshold_config.get(approach.upper())

        if threshold is not None:
            # Use the threshold from PROFIT_THRESHOLD_BY_APPROACH configuration
            logging.debug(f"Using approach-specific threshold for '{approach}': {threshold}")
            return threshold
        else:
            logging.debug(f"No approach-specific threshold config found for '{approach}', using default: {default_threshold}")
            return default_threshold
    except Exception as e:
        logging.warning(f"Error during threshold calculation for '{approach}': {e}. Using default: {default_threshold}")
        return default_threshold


def update_alerts_with_profit_threshold(
    from_date_str: str,
    to_date_str: str,
    default_threshold: Optional[float] = None,
    use_config: bool = False,
    approach_filter: Optional[str] = None
):
    """
    Scans alert notification files and updates them with profit threshold.

    This function finds all `alert_notification_*.json` files within the given
    date range and adds/updates the 'suggested_profit_threshold' field for each alert.
    
    The threshold can be:
    - A fixed default value (if default_threshold is provided)
    - Approach-specific from configuration (if use_config is True)
    - Limited to a specific approach (if approach_filter is provided)

    Args:
        from_date_str (str): The start date in 'YYYY-MM-DD' format.
        to_date_str (str): The end date in 'YYYY-MM-DD' format.
        default_threshold (Optional[float]): Fixed threshold value to use. Default: 3.15
        use_config (bool): If True, use approach-specific configuration. Default: False
        approach_filter (Optional[str]): Only process alerts from specific approach.
    """
    # Set default threshold if not provided
    if default_threshold is None:
        default_threshold = 3.15

    reports_dir_name = get_reports_directory_name()
    reports_dir = os.path.join(project_root, reports_dir_name)
    logging.info(f"Scanning for alert files in {reports_dir} from {from_date_str} to {to_date_str}")
    if approach_filter:
        logging.info(f"Filtering for approach: {approach_filter}")
    if use_config:
        logging.info("Using approach-specific configuration for threshold calculation")
    else:
        logging.info(f"Using default threshold: {default_threshold}")

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

    total_alerts_processed = 0
    total_alerts_updated = 0

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
                total_alerts_processed += 1
                
                # Check if we should filter by approach
                approach = alert.get('approach')
                if approach_filter and approach and approach.upper() != approach_filter.upper():
                    logging.debug(f"Skipping alert (approach mismatch): {approach} != {approach_filter}")
                    continue

                # Calculate threshold
                if use_config and approach:
                    threshold = _calculate_profit_threshold_by_approach(approach, default_threshold)
                else:
                    threshold = default_threshold

                # Update the alert object
                old_threshold = alert.get('suggested_profit_threshold')
                alert['suggested_profit_threshold'] = threshold
                
                if old_threshold != threshold:
                    logging.debug(f"Updated profit threshold for alert: {old_threshold} → {threshold}")
                    updated_count += 1
                    total_alerts_updated += 1
                else:
                    logging.debug(f"Alert already has correct threshold: {threshold}")

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

    # Summary
    logging.info(f"\n{'='*60}")
    logging.info(f"SUMMARY")
    logging.info(f"{'='*60}")
    logging.info(f"Total alerts processed: {total_alerts_processed}")
    logging.info(f"Total alerts updated: {total_alerts_updated}")
    logging.info(f"Default threshold used: {default_threshold}")
    logging.info(f"Use config: {use_config}")
    if approach_filter:
        logging.info(f"Approach filter: {approach_filter}")
    logging.info(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="A maintenance tool to scan all report files and backfill/update suggested profit threshold for alerts.",
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
        "--default-threshold",
        type=float,
        default=3.15,
        help="The default profit threshold value to use if not using config. Default: 3.15"
    )
    parser.add_argument(
        "--use-config",
        action='store_true',
        help="If set, use approach-specific configuration from price_alert_settings for threshold calculation."
    )
    parser.add_argument(
        "--approach",
        type=str,
        help="Optional: Filter alerts by specific approach (e.g., CONSISTENT_MOMENTUM)"
    )

    args = parser.parse_args()

    # If to_date is not provided, default it to from_date for a single-day scan
    to_date_str = args.to_date if args.to_date else args.from_date

    update_alerts_with_profit_threshold(
        from_date_str=args.from_date,
        to_date_str=to_date_str,
        default_threshold=args.default_threshold,
        use_config=args.use_config,
        approach_filter=args.approach
    )
