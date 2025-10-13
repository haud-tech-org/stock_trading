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
from src.stockreports.alert.model.models import AlertResult, AlertSummary
from src.stockreports.utils.time_utils import get_market_timezone_str

# --- Settings & Logger ---
settings = loader.get_settings()
TIMEZONE = pytz.timezone(get_market_timezone_str())
logger = logging.getLogger(__name__)


def save_alert_report(result: AlertResult, symbol: str, date_str: str):
    """
    Saves the detailed alerts from an analysis result to a JSON file.

    Args:
        result (AlertResult): The result object from an alert approach.
        symbol (str): The stock symbol being processed.
        date_str (str): The date of the analysis in 'YYYY-MM-DD' format.
    """
    if not result.has_alerts:
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    reports_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), result.approach_name.lower())
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, f"alert_notification_{date_str.replace('-', '')}.json")

    try:
        alerts_to_save = result.alerts.copy()
        
        # Identify all datetime-like columns
        datetime_cols = alerts_to_save.select_dtypes(include=['datetime64[ns]', 'datetimetz']).columns

        # Convert to the configured timezone and then format to string
        for col in datetime_cols:
            if alerts_to_save[col].dt.tz is None:
                alerts_to_save[col] = alerts_to_save[col].dt.tz_localize('UTC')
            
            alerts_to_save[col] = alerts_to_save[col].dt.tz_convert(TIMEZONE).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

        alerts_to_save.to_json(filepath, orient='records', indent=4)
        logger.info(f"Successfully saved report for {result.approach_name} to {filepath}")
    except Exception as e:
        logger.error(f"Failed to save report for {result.approach_name}: {e}")


def update_alert_summary(result: AlertResult, symbol: str, date_str: str):
    """
    Updates a running summary JSON file with the latest alert statistics.

    Args:
        result (AlertResult): The result object from an alert approach.
        symbol (str): The stock symbol being processed.
        date_str (str): The date of the analysis in 'YYYY-MM-DD' format.
    """
    if not result.has_alerts:
        return

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    reports_dir = os.path.join(project_root, "reports", symbol, settings.MODE.lower(), result.approach_name.lower())
    os.makedirs(reports_dir, exist_ok=True)
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
            # Remove any existing summary for the same date before adding the new one
            all_summaries = [s for s in all_summaries if s.get('date') != date_str]
        except (json.JSONDecodeError, IOError):
            all_summaries = []

    all_summaries.append(new_summary.to_dict())
    all_summaries.sort(key=lambda x: x.get('date', ''))
    
    with open(filepath, 'w') as f:
        json.dump(all_summaries, f, indent=4)
    
    logger.info(f"Successfully updated alert summary for {result.approach_name} at {filepath}")
