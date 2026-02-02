"""
Utilities for saving and managing alert reports and summaries.
"""
import os
import json
import logging
import pandas as pd
from google.cloud import storage
from typing import Dict, Any, Optional
import pytz
import glob
from datetime import datetime

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertSummary, ProfitabilityReport
from src.stockreports.utils.time_utils import get_market_timezone_str
from src.stockreports.utils.file_utils import save_json_report
from src.stockreports.alert.common.constants import Mode

# --- Settings & Logger ---
settings = loader.get_settings()
TIMEZONE = pytz.timezone(get_market_timezone_str())
logger = logging.getLogger(__name__)


def get_report_directory(
    base_dir: str,
    report_type: str,
    mode: str,
    symbol: Optional[str] = None,
    profit_threshold: Optional[float] = None,
    loss_threshold: Optional[float] = None
) -> str:
    """
    Constructs the correct directory path for reports based on the new structure.

    Args:
        base_dir (str): The root 'reports' directory.
        report_type (str): The type of report, e.g., 'consolidated' or a symbol like 'VN30'.
        mode (str): The run mode, 'development' or 'deployment'.
        symbol (Optional[str]): The stock symbol, used for certain report types.
        profit_threshold (Optional[float]): The profit threshold for the scenario.
        loss_threshold (Optional[float]): The loss threshold for the scenario.

    Returns:
        str: The fully constructed directory path.
    """
    # Start with the base path: reports/{report_type}/{mode}
    path_parts = [base_dir, report_type, mode]

    # If thresholds are provided, create the scenario-specific subfolder
    if profit_threshold is not None and loss_threshold is not None:
        scenario_folder = f"profit_{profit_threshold}_loss_{loss_threshold}"
        path_parts.append(scenario_folder)

    # For certain report types that are symbol-specific at this level
    if report_type != 'consolidated':
        if symbol:
            path_parts.insert(2, symbol)  # e.g., reports/VN30/deployment/...
        else:
            # If no symbol is provided for a non-consolidated report,
            # the path intentionally stops at the mode level,
            # allowing callers to iterate through all symbols.
            # e.g., reports/VN30/deployment/
            pass

    return os.path.join(*path_parts)


def get_default_thresholds(
    profit_threshold: Optional[float] = None,
    loss_threshold: Optional[float] = None
) -> tuple[float, float]:
    """
    Ensures valid profit and loss thresholds are returned.

    If the provided thresholds are None, it dynamically imports and returns
    the first values from the validation settings file as defaults.

    Args:
        profit_threshold (Optional[float]): The provided profit threshold.
        loss_threshold (Optional[float]): The provided loss threshold.

    Returns:
        A tuple containing the definite (float, float) profit and loss thresholds.
    """
    # If any threshold is missing, we'll need the defaults from settings.
    if profit_threshold is None or loss_threshold is None:
        from src.stockreports.config.validation_settings import (
            VALIDATION_PRICE_THRESHOLD_PROFIT,
            VALIDATION_PRICE_THRESHOLD_LOSS
        )
        
        if profit_threshold is None:
            logging.info("Profit threshold is missing, loading default from settings.")
            profit_threshold = VALIDATION_PRICE_THRESHOLD_PROFIT[0] if VALIDATION_PRICE_THRESHOLD_PROFIT else 3.0

        if loss_threshold is None:
            logging.info("Loss threshold is missing, loading default from settings.")
            loss_threshold = VALIDATION_PRICE_THRESHOLD_LOSS[0] if VALIDATION_PRICE_THRESHOLD_LOSS else 3.0
    
    return profit_threshold, loss_threshold


def find_all_alert_files(
    base_reports_dir: str,
    from_date: datetime.date,
    to_date: datetime.date
) -> list[str]:
    """
    Recursively finds all 'alert_notification_*.json' files within a date range,
    searching through all subdirectories.

    Args:
        base_reports_dir (str): The root 'reports' directory to start the scan from.
        from_date (datetime.date): The start date for filtering.
        to_date (datetime.date): The end date for filtering.

    Returns:
        A list of absolute file paths to the alert files.
    """
    logging.info(f"Scanning for all alert files in {base_reports_dir} from {from_date} to {to_date}")
    
    # Use a recursive glob to find all potential files
    glob_pattern = os.path.join(base_reports_dir, "**", "alert_notification_*.json")
    all_files = glob.glob(glob_pattern, recursive=True)

    filtered_files = []
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            # Handles both 'alert_notification_YYYY-MM-DD.json' and 'alert_notification_YYYYMMDD.json'
            date_part_str = filename.replace('alert_notification_', '').replace('.json', '')
            
            file_date = None
            try:
                # First, try parsing 'YYYY-MM-DD' format
                file_date = datetime.strptime(date_part_str, '%Y-%m-%d').date()
            except ValueError:
                # If that fails, try parsing 'YYYYMMDD' format
                file_date = datetime.strptime(date_part_str, '%Y%m%d').date()

            if from_date <= file_date <= to_date:
                filtered_files.append(file_path)
        except (ValueError, IndexError):
            logging.warning(f"Could not parse date from filename: {filename}. Skipping.")
            continue
            
    logging.info(f"Found {len(filtered_files)} alert files in the specified date range.")
    return filtered_files


def get_consolidated_scenario_directory(
    mode: str,
    profit_threshold: float,
    loss_threshold: float
) -> str:
    """
    Constructs the directory path for a specific consolidated report scenario.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    base_reports_dir = os.path.join(project_root, "reports")
    
    return get_report_directory(
        base_dir=base_reports_dir,
        report_type="consolidated",
        mode=mode,
        profit_threshold=profit_threshold,
        loss_threshold=loss_threshold
    )


def save_alert_report(result: AlertResult, symbol: str, date_str: str):
    """
    Saves the detailed alerts from an analysis result to a JSON file.
    In 'deployment' mode, it appends new alerts to the existing file for the day.
    In 'development' mode, it overwrites the file.
    """
    if not result.has_alerts:
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    reports_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), result.approach_name.lower())
    filepath = os.path.join(reports_dir, f"alert_notification_{date_str.replace('-', '')}.json")

    new_alerts_df = result.alerts.copy()

    # Ensure 'details' is a dict, not a string, for each alert
    if 'details' in new_alerts_df.columns:
        def parse_details(val):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return val
            return val
        new_alerts_df['details'] = new_alerts_df['details'].apply(parse_details)

    # In deployment mode, read existing alerts and append new ones
    if settings.MODE.lower() == 'deployment' and os.path.exists(filepath):
        try:
            existing_alerts_df = pd.read_json(filepath, orient='records')
            if not existing_alerts_df.empty:
                # Ensure timezone consistency before combining
                new_alerts_df['alert_time'] = pd.to_datetime(new_alerts_df['alert_time']).dt.tz_convert(TIMEZONE)
                existing_alerts_df['alert_time'] = pd.to_datetime(existing_alerts_df['alert_time']).dt.tz_convert(TIMEZONE)
                combined_df = pd.concat([existing_alerts_df, new_alerts_df])
                new_alerts_df = combined_df
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Could not read or merge existing alert report {filepath}. Overwriting. Error: {e}")


    # Ensure all IDs are strings (do not overwrite with timestamp, just cast to str)
    if 'id' in new_alerts_df.columns:
        new_alerts_df['id'] = new_alerts_df['id'].astype(str)

    # Remove duplicates by 'id', keeping the latest (by alert_time if available)
    if 'alert_time' in new_alerts_df.columns:
        new_alerts_df = new_alerts_df.sort_values('alert_time')
    new_alerts_df = new_alerts_df.drop_duplicates(subset=['id'], keep='last')

    # --- Save the final DataFrame ---
    alerts_to_save = new_alerts_df.copy()
    # Normalize alert_time and start_time to ISO 8601 string with timezone for all rows
    for col in ["alert_time", "start_time"]:
        if col in alerts_to_save.columns:
            # Convert all to datetime, handling int, float, str, or already datetime
            alerts_to_save[col] = pd.to_datetime(alerts_to_save[col], errors='coerce', utc=True)
            alerts_to_save[col] = alerts_to_save[col].dt.tz_convert(TIMEZONE).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    # Also process any other datetime columns for robustness
    datetime_cols = alerts_to_save.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns
    for col in datetime_cols:
        if col not in ["alert_time", "start_time"]:
            alerts_to_save[col] = pd.to_datetime(alerts_to_save[col], errors='coerce', utc=True)
            alerts_to_save[col] = alerts_to_save[col].dt.tz_convert(TIMEZONE).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    save_json_report(alerts_to_save, filepath, logger)

    # --- Upload to GCS (function will check config and mode) ---
    upload_report_to_gcs(filepath, project_root, settings.GCS_REPORT_BUCKET_NAME)

def update_alert_summary(result: AlertResult, symbol: str, date_str: str):
    """
    Updates a running summary JSON file with the latest alert statistics.
    """
    if not result.has_alerts:
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    reports_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), result.approach_name.lower())
    filepath = os.path.join(reports_dir, "alert_summary.json")

    total_alerts = len(result.alerts)
    successful_alerts = len(result.alerts[result.alerts['status'] == 'Success'])
    success_rate = (successful_alerts / total_alerts) * 100 if total_alerts > 0 else 0
    
    successful_df = result.alerts[result.alerts['status'] == 'Success'].copy()
    avg_profit_loss, min_time_to_best, avg_time_to_best, max_time_to_best = None, None, None, None
    min_expected_profit_loss = None

    if not successful_df.empty:
        successful_df['profit_loss'] = pd.to_numeric(successful_df['profit_loss'], errors='coerce')
        successful_df['time_to_best_price'] = pd.to_numeric(successful_df['time_to_best_price'], errors='coerce')
        successful_df.dropna(subset=['profit_loss', 'time_to_best_price'], inplace=True)
        
        if not successful_df.empty:
            avg_profit_loss = successful_df['profit_loss'].mean()
            min_time_to_best = int(successful_df['time_to_best_price'].min())
            avg_time_to_best = int(successful_df['time_to_best_price'].mean())
            max_time_to_best = int(successful_df['time_to_best_price'].max())
            min_expected_profit_loss = successful_df['min_expected_profit_loss'].iloc[0] if 'min_expected_profit_loss' in successful_df.columns else None

    new_summary = AlertSummary(
        approach=result.approach_name, date=date_str, total_alerts=total_alerts,
        successful_alerts=successful_alerts, failed_alerts=total_alerts - successful_alerts,
        success_rate_pct=round(success_rate, 2),
        average_profit_loss=round(avg_profit_loss, 4) if avg_profit_loss is not None else None,
        min_time_to_best_price=min_time_to_best,
        avg_time_to_best_price=avg_time_to_best,
        max_time_to_best_price=max_time_to_best,
        min_expected_profit_loss=min_expected_profit_loss
    )

    all_summaries = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                all_summaries = json.load(f)
            if not isinstance(all_summaries, list):
                all_summaries = []
            all_summaries = [s for s in all_summaries if s.get('date') != date_str]
        except (json.JSONDecodeError, IOError):
            all_summaries = []

    all_summaries.append(new_summary.to_dict())
    all_summaries.sort(key=lambda x: x.get('date', ''))
    
    save_json_report(all_summaries, filepath, logger)


def save_profitability_report(summary_data: ProfitabilityReport, symbol: str, date_str: str, logger_instance: logging.Logger):
    """
    Saves the profitability simulation summary to a JSON file.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    report_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), "profitability")
    
    filename = f"profitability_summary_{date_str.replace('-', '')}.json"
    filepath = os.path.join(report_dir, filename)
    
    save_json_report(summary_data.to_dict(), filepath, logger_instance)


def find_overall_performance_files(root_dir: str) -> list[str]:
    """
    Recursively finds all overall performance JSON files in a directory.
    """
    glob_pattern = os.path.join(root_dir, "**", "*_overall_performance_*.json")
    return glob.glob(glob_pattern, recursive=True)

def upload_report_to_gcs(local_filepath: str, project_root: str, bucket_name: str):
    """
    Uploads a report file to Google Cloud Storage, preserving the directory structure under project_root.
    Any exceptions are caught and logged as errors.
    """
    try:
        # Only upload if enabled and in deployment mode
        if not (settings.ENABLE_GCS_REPORT_STORAGE and settings.MODE.lower() == Mode.DEPLOYMENT.lower()):
            return

        # Compute the relative path for the blob
        rel_path = os.path.relpath(local_filepath, project_root)
        blob_path = rel_path.replace(os.sep, "/")

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        blob.upload_from_filename(local_filepath)
        logger.info(f"Uploaded {local_filepath} to GCS bucket {bucket_name} as {blob_path}")
    except Exception as e:
        logger.error(f"Failed to upload {local_filepath} to GCS bucket {bucket_name}: {e}")


