"""
Utilities for saving and managing alert reports and summaries.
"""
import os
import json
import logging
import pandas as pd
from typing import Dict, Any
import pytz

from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertSummary, ProfitabilityReport
from src.stockreports.utils.time_utils import get_market_timezone_str

# --- Settings & Logger ---
settings = loader.get_settings()
TIMEZONE = pytz.timezone(get_market_timezone_str())
logger = logging.getLogger(__name__)


def _save_json_report(data: Any, filepath: str, logger_instance: logging.Logger):
    """
    A generic utility to save data to a JSON file. It creates the directory if it doesn't exist.

    Args:
        data (Any): The data to save (can be a list, dict, or pandas DataFrame).
        filepath (str): The full path to the file.
        logger_instance (logging.Logger): The logger to use for output.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w') as f:
            if isinstance(data, pd.DataFrame):
                data.to_json(f, orient='records', indent=4)
            else:
                json.dump(data, f, indent=4)
        logger_instance.info(f"Successfully saved report to {filepath}")
    except Exception as e:
        logger_instance.error(f"Failed to save report to {filepath}: {e}")


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

    # In deployment mode, read existing alerts and append new ones
    if settings.MODE.lower() == 'deployment' and os.path.exists(filepath):
        try:
            existing_alerts_df = pd.read_json(filepath, orient='records')
            if not existing_alerts_df.empty:
                # Ensure timezone consistency before combining
                new_alerts_df['alert_time'] = pd.to_datetime(new_alerts_df['alert_time']).dt.tz_convert(TIMEZONE)
                existing_alerts_df['alert_time'] = pd.to_datetime(existing_alerts_df['alert_time']).dt.tz_convert(TIMEZONE)
                
                combined_df = pd.concat([existing_alerts_df, new_alerts_df]).drop_duplicates(subset=['id'], keep='last')
                new_alerts_df = combined_df
        except (ValueError, KeyError, json.JSONDecodeError) as e:
            logger.error(f"Could not read or merge existing alert report {filepath}. Overwriting. Error: {e}")

    # --- Save the final DataFrame ---
    alerts_to_save = new_alerts_df
    datetime_cols = alerts_to_save.select_dtypes(include=['datetime64[ns]', 'datetimetz']).columns
    for col in datetime_cols:
        if alerts_to_save[col].dt.tz is None:
            alerts_to_save[col] = alerts_to_save[col].dt.tz_localize('UTC')
        alerts_to_save[col] = alerts_to_save[col].dt.tz_convert(TIMEZONE).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    _save_json_report(alerts_to_save, filepath, logger)


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
    
    _save_json_report(all_summaries, filepath, logger)


def save_profitability_report(summary_data: ProfitabilityReport, symbol: str, date_str: str, logger_instance: logging.Logger):
    """
    Saves the profitability simulation summary to a JSON file.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    report_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), "profitability")
    
    filename = f"profitability_summary_{date_str.replace('-', '')}.json"
    filepath = os.path.join(report_dir, filename)
    
    _save_json_report(summary_data.to_dict(), filepath, logger_instance)
