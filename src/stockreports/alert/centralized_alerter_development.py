import json
import os
import pandas as pd
import glob
import logging
import pytz
from tabulate import tabulate
import sys
from datetime import datetime, timedelta
import importlib
from typing import Optional
import time

# --- Path Setup ---
# This is handled by the entry-point script, but kept for robustness
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# --- Settings Loader ---
# This MUST be the first project import to ensure settings are fresh.
from src.stockreports.config import loader

# Other modules should use the getters to access the loaded modules.
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()
notification_settings = loader.get_notification_settings()

# --- Project Imports ---
from src.stockreports.utils.email_utils import send_email
from src.stockreports.utils.sms_utils import send_sms
from src.stockreports.utils.data_utils import fetch_intraday_data
from src.stockreports.alert.models import AlertNotification, AlertResult, AlertData, AlertSummary
from src.stockreports.alert.validation import calculate_alert_performance
from src.stockreports.alert.models import AlertData

# --- Constants & Configuration ---
# The primary timezone is now driven by the market setting
MARKET_CONFIG = settings.TRADING_HOURS.get(settings.MARKET_COUNTRY_CODE, {})
TIMEZONE_STR = MARKET_CONFIG.get("timezone", "UTC")
TIMEZONE = pytz.timezone(TIMEZONE_STR)
DEFAULT_APPROACH = "RCM"

# --- Global State for DEPLOYMENT mode ---
# Keeps track of alerts sent for a specific (approach, timestamp) pair to avoid duplicates in a single run
ALERTS_SENT_IN_SESSION = set()


def _setup_logging():
    """Configures logging to file and console."""
    log_dir = os.path.join(project_root, "logs", settings.MODE.lower())
    os.makedirs(log_dir, exist_ok=True)
    log_file_path = os.path.join(log_dir, "alerter.log")

    # Remove existing handlers to avoid duplication
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level="INFO",
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    logging.info(f"Logging configured. Log file: {log_file_path}")


def _format_email_subject(notification: AlertNotification) -> str:
    """Generates a concise and informative email subject."""
    return (
        f"{notification.signal} Signal for {notification.symbol} "
        f"at {notification.alert_price:.2f} ({notification.approach})"
    )

def _format_sms_body(notification: AlertNotification) -> str:
    """Generates a very concise message body suitable for an SMS."""
    return (
        f"{notification.symbol} Alert\n"
        f"Signal: {notification.signal}\n"
        f"Price: {notification.alert_price:.2f}\n"
        f"Approach: {notification.approach}"
    )

def _send_ntfy_notification(notification: AlertNotification):
    """Sends a push notification using the ntfy.sh service."""
    if not notification_settings.NTFY_ENABLED or not notification_settings.NTFY_TOPIC:
        if notification_settings.NTFY_ENABLED:
            logging.warning("ntfy is enabled, but NTFY_TOPIC is not set. Skipping push notification.")
        return

    try:
        title = f"{notification.signal} for {notification.symbol} ({notification.approach})"
        message = (
            f"Price: {notification.alert_price:.2f}\n"
            f"Time: {notification.alert_time.strftime('%H:%M:%S')}"
        )
        
        # The requests library should already be available from data_utils
        import requests
        
        requests.post(
            f"https://ntfy.sh/{notification_settings.NTFY_TOPIC}",
            data=message.encode('utf-8'),
            headers={"Title": title}
        )
        logging.info(f"Successfully sent ntfy push notification for {notification.approach} signal.")
    except Exception as e:
        logging.error(f"Failed to send ntfy push notification: {e}")

def _format_email_body(notification: AlertNotification) -> str:
    """Generates a clean, readable email body from the notification object."""
    body = (
        f"A new trading signal has been generated for {notification.symbol}.\n\n"
        f"Signal:     {notification.signal}\n"
        f"Price:      {notification.alert_price:.2f}\n"
        f"Time:       {notification.alert_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Approach:   {notification.approach}\n"
    )
    
    if notification.details:
        body += "\n--- Details ---\n"
        for key, value in notification.details.items():
            # Format timestamps nicely if they are present
            if isinstance(value, pd.Timestamp):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            body += f"{key.replace('_', ' ').title()}: {value}\n"
            
    return body

def _load_all_data_from_files():
    """
    Loads and combines all JSON data from the symbol-specific directory into a single, sorted DataFrame.
    """
    data_path = os.path.join(project_root, settings.DATA_DIR, settings.SYMBOL)
    all_files = glob.glob(f"{data_path}/*.json")
    if not all_files:
        logging.warning(f"No JSON data files found in {data_path}")
        return pd.DataFrame()

    all_dfs = []
    for filename in sorted(all_files):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
                keys = ["t", "o", "h", "l", "c", "v"]
                if not all(k in data for k in keys): continue
                min_len = min(len(data[k]) for k in keys)
                if min_len == 0: continue
                df_single = pd.DataFrame({
                    "time": pd.to_datetime(data["t"][:min_len], unit="s"),
                    "open": data["o"][:min_len], "high": data["h"][:min_len],
                    "low": data["l"][:min_len], "close": data["c"][:min_len],
                    "volume": data["v"][:min_len],
                })
                all_dfs.append(df_single)
            except Exception as e:
                logging.error(f"Error processing {filename}: {e}")

    if not all_dfs: return pd.DataFrame()
    df = pd.concat(all_dfs, ignore_index=True)
    df.drop_duplicates(subset=['time'], keep='first', inplace=True)
    df = df.sort_values(by='time').reset_index(drop=True)
    if not df.empty:
        df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(TIMEZONE)
    return df

def _load_live_data(symbol, date_str):
    """Fetches and prepares live intraday data for a specific date."""
    logging.info(f"Fetching live data for {symbol} on {date_str}...")
    raw_data = fetch_intraday_data(symbol, date_str)
    if not raw_data or raw_data.get('s') != 'ok':
        logging.error("Failed to fetch or process live data.")
        return pd.DataFrame()

    keys = ["t", "o", "h", "l", "c", "v"]
    min_len = min(len(raw_data.get(k, [])) for k in keys)
    if min_len == 0:
        logging.warning("No data points in the live response.")
        return pd.DataFrame()

    df = pd.DataFrame({
        "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
        "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
        "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
        "volume": raw_data["v"][:min_len],
    })
    df.drop_duplicates(subset=['time'], keep='first', inplace=True)
    df = df.sort_values(by='time').reset_index(drop=True)
    if not df.empty:
        df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(TIMEZONE)
    return df

def _get_approach_executor(approach_name: str):
    """Dynamically imports and returns the 'run_analysis' function from an executor."""
    try:
        # Corrected module path to find the executor
        module_path = f"src.stockreports.alert.approach.{approach_name.upper()}.executor"
        executor_module = importlib.import_module(module_path)
        return getattr(executor_module, 'run_analysis')
    except (ImportError, AttributeError) as e:
        logging.error(f"Could not load approach '{approach_name}'. Check if the module and function exist. Error: {e}")
        return None

def _process_and_notify_for_approach(result: AlertResult):
    """
    Finds the latest alert from a single approach result and sends one notification.
    """
    if not result.has_alerts:
        logging.info(f"No new alerts generated by the {result.approach_name} approach in this interval.")
        return

    # --- Find the latest alert ---
    latest_alert_row = result.alerts.sort_values(by='alert_time', ascending=False).iloc[0]
    
    # --- Avoid Duplicate Notifications ---
    # Create a unique key for the latest alert
    alert_key = (result.approach_name, latest_alert_row['alert_time'])
    if alert_key in ALERTS_SENT_IN_SESSION:
        logging.info(f"Alert for {result.approach_name} at {latest_alert_row['alert_time']} has already been sent. Skipping.")
        return
    
    logging.info(f"Latest alert from {result.approach_name}: {latest_alert_row['signal']} at {latest_alert_row['alert_price']:.2f}")

    # --- Prepare Notification for the latest alert ---
    details_dict = {}
    if pd.notna(latest_alert_row.get('details')) and isinstance(latest_alert_row.get('details'), str):
        try:
            details_dict = json.loads(latest_alert_row['details'])
        except json.JSONDecodeError:
            logging.warning(f"Could not parse 'details' JSON for alert ID {latest_alert_row.get('id')}")

    notification = AlertNotification(
        symbol=settings.SYMBOL,
        signal=latest_alert_row['signal'],
        alert_price=latest_alert_row['alert_price'],
        alert_time=latest_alert_row['alert_time'],
        approach=latest_alert_row['approach'],
        details=details_dict
    )

    # --- Send Notifications ---
    # 1. Send push notification via ntfy
    _send_ntfy_notification(notification)

    # 2. Send email
    subject = _format_email_subject(notification)
    body = _format_email_body(notification)
    
    if notification_settings.EMAIL_ENABLED and all([notification_settings.EMAIL_SENDER, notification_settings.EMAIL_RECEIVER, notification_settings.EMAIL_APP_PASSWORD]):
        try:
            send_email(subject, body)
            logging.info(f"Successfully sent email for latest {notification.approach} signal at {notification.alert_time}.")
            # Mark this alert as sent to prevent re-sending
            ALERTS_SENT_IN_SESSION.add(alert_key)
        except Exception as e:
            logging.error(f"Failed to send email for {notification.approach} signal: {e}")
    else:
        logging.warning("Email not enabled or credentials not configured. Skipping email.")

    # 3. Send SMS
    sms_body = _format_sms_body(notification)
    send_sms(sms_body)

    # Mark alert as processed for this session regardless of email success, to avoid duplicate pushes
    ALERTS_SENT_IN_SESSION.add(alert_key)


def _save_report_for_approach(result: AlertResult, date_str: str):
    """Saves all alerts from an approach result to a JSON report file."""
    if not result.has_alerts:
        return

    # Ensure the reports directory for the symbol and mode exists
    reports_dir = os.path.join(project_root, "reports", settings.SYMBOL, settings.MODE.lower(), result.approach_name.lower())
    os.makedirs(reports_dir, exist_ok=True)
    
    # Create a filename based on the new convention
    filename = f"alert_notification_{date_str.replace('-', '')}.json"
    filepath = os.path.join(reports_dir, filename)

    try:
        # Convert dataframe to JSON and save
        result.alerts.to_json(filepath, orient='records', indent=4, date_format='iso')
        logging.info(f"Successfully saved report for {result.approach_name} to {filepath}")
    except Exception as e:
        logging.error(f"Failed to save report for {result.approach_name}: {e}")

def _calculate_max_lookback_period() -> int:
    """
    Calculates the maximum lookback period in minutes required by any active alert approach.
    It reads the default from settings and overrides it with larger, approach-specific values if found.
    """
    # Start with a default lookback from settings, falling back to 60 if not specified
    max_lookback = getattr(signal_settings, 'DEFAULT_LOOKBACK_PERIOD', 60)
    if not hasattr(signal_settings, 'DEFAULT_LOOKBACK_PERIOD'):
        logging.warning(f"DEFAULT_LOOKBACK_PERIOD not set in signal_settings. Using default of {max_lookback} minutes.")

    active_approaches = getattr(settings, 'ALERT_APPROACHES', [])
    if not active_approaches:
        logging.warning(f"No alert approaches configured; using lookback of {max_lookback} minutes.")
        return max_lookback

    lookbacks = [max_lookback]

    for approach in active_approaches:
        if approach.upper() == 'RCM':
            rcm_lookback = max(
                getattr(signal_settings, 'MA_LONG_PERIOD', 0),
                getattr(signal_settings, 'AVG_VOLUME_PERIOD', 0)
            )
            lookbacks.append(rcm_lookback)
            logging.info(f"RCM approach requires a lookback of at least {rcm_lookback} minutes.")

        elif approach.upper() == 'CONSISTENT_MOMENTUM':
            try:
                cm_lookback = signal_settings.APPROACH_CONFIG['CONSISTENT_MOMENTUM']['MOMENTUM_PERIOD_MINUTES']
                lookbacks.append(cm_lookback)
                logging.info(f"CONSISTENT_MOMENTUM approach requires a lookback of {cm_lookback} minutes.")
            except (AttributeError, KeyError):
                logging.warning("Could not find settings for CONSISTENT_MOMENTUM lookback.")

    max_lookback = max(lookbacks)
    logging.info(f"Calculated maximum required lookback period across all approaches: {max_lookback} minutes.")
    
    return max_lookback

def _generate_summary_report(result: AlertResult, date_str: str):
    """
    Calculates a summary for a single approach and appends or updates it in a persistent
    JSON report file for that approach.
    """
    if not result.has_alerts:
        logging.info(f"No alerts from {result.approach_name} to summarize for {date_str}.")
        return

    # --- Define the persistent file path for the approach ---
    reports_dir = os.path.join(project_root, "reports", settings.SYMBOL, settings.MODE.lower(), result.approach_name.lower())
    os.makedirs(reports_dir, exist_ok=True)
    filepath = os.path.join(reports_dir, f"alert_summary.json")

    # --- Calculate new summary ---
    total_alerts = len(result.alerts)
    successful_alerts = len(result.alerts[result.alerts['status'] == 'Success'])
    failed_alerts = total_alerts - successful_alerts
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
            # Since all alerts in a batch share the same validation setting, we can take it from the first one.
            min_expected_profit_loss = successful_df['min_expected_profit_loss'].iloc[0] if 'min_expected_profit_loss' in successful_df.columns else None

    new_summary = AlertSummary(
        approach=result.approach_name,
        date=date_str,
        total_alerts=total_alerts,
        successful_alerts=successful_alerts,
        failed_alerts=failed_alerts,
        success_rate_pct=round(success_rate, 2),
        average_profit_loss=round(avg_profit_loss, 4) if avg_profit_loss is not None else None,
        min_time_to_best_price=min_time_to_best,
        avg_time_to_best_price=avg_time_to_best,
        max_time_to_best_price=max_time_to_best,
        min_expected_profit_loss=min_expected_profit_loss
    )

    # --- Read-Modify-Write ---
    all_summaries = []
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                all_summaries = json.load(f)
                # Ensure it's a list
                if not isinstance(all_summaries, list):
                    all_summaries = []
                # Filter out any existing summary for the same date to prevent duplicates
                all_summaries = [s for s in all_summaries if s.get('date') != date_str]
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not read or parse existing summary file at {filepath}. A new file will be created. Error: {e}")
            all_summaries = []

    # Append the new summary and sort by date
    all_summaries.append(new_summary.to_dict())
    all_summaries.sort(key=lambda x: x.get('date', ''))

    # Write the updated list back to the file
    try:
        with open(filepath, 'w') as f:
            json.dump(all_summaries, f, indent=4)
        logging.info(f"Successfully updated alert summary for {result.approach_name} at {filepath}")
    except Exception as e:
        logging.error(f"Failed to save summary report for {result.approach_name}: {e}")

def _is_within_trading_hours() -> bool:
    """
    Checks if the current time is within the defined trading hours for the configured market.
    """
    try:
        sessions = MARKET_CONFIG.get("sessions")
        if not sessions:
            logging.warning(f"No trading sessions defined for market '{settings.MARKET_COUNTRY_CODE}'. Assuming it's always open.")
            return True

        now = datetime.now(TIMEZONE)
        current_time = now.time()
        
        # Check if it's a weekend (Saturday=5, Sunday=6)
        if now.weekday() >= 5:
            return False

        for session_name, hours in sessions.items():
            try:
                start_time = datetime.strptime(hours['start'], '%H:%M').time()
                end_time = datetime.strptime(hours['end'], '%H:%M').time()
                if start_time <= current_time <= end_time:
                    return True
            except (KeyError, ValueError) as e:
                logging.error(f"Invalid format for '{session_name}' session in TRADING_HOURS: {e}")
                continue
        
        return False
    except Exception as e:
        logging.error(f"Error checking trading hours: {e}")
        # Fail safe: if we can't check, assume it's open to not miss data.
        return True

def run_alerter(date_to_load: str = None):
    """
    Main function to run the alerter.
    - Loads data (either from files or live source).
    - In DEV mode, can process a single date or all dates in the dataset.
    - Executes the selected alert approaches for each date.
    - Sends notifications and saves reports for generated alerts.
    """
    _setup_logging()
    # --- Data Loading and Date Determination ---
    master_df = pd.DataFrame()
    dates_to_process = []

    if settings.MODE == "DEVELOPMENT":
        logging.info("Running in DEVELOPMENT mode. Loading all data from local files.")
        master_df = _load_all_data_from_files()
        
        if master_df.empty:
            logging.error("No data loaded from files, cannot proceed.")
            return

        # Determine which date(s) to process.
        # Priority: function argument > settings file > all dates in data.
        effective_date = date_to_load or settings.DATA_DATE

        if effective_date:
            try:
                datetime.strptime(effective_date, '%Y-%m-%d')
                dates_to_process = [effective_date]
                source = "command-line" if date_to_load else "settings file"
                logging.info(f"Processing specific date from {source}: {effective_date}")
            except (ValueError, TypeError):
                logging.error(f"Invalid date format for DATA_DATE: '{effective_date}'. Please use YYYY-MM-DD or None.")
                # Fallback to processing all dates to avoid silent failure
                dates_to_process = sorted(master_df['time'].dt.strftime('%Y-%m-%d').unique())
                logging.warning(f"Falling back to processing all {len(dates_to_process)} dates found in the data.")
        else:
            # If no date is specified anywhere, find all unique dates in the dataset.
            dates_to_process = sorted(master_df['time'].dt.strftime('%Y-%m-%d').unique())
            logging.info(f"No specific date provided. Processing all {len(dates_to_process)} dates found in the data.")

    elif settings.MODE == "DEPLOYMENT":
        # In deployment, we poll for live data in a loop.
        processing_date = date_to_load or settings.DATA_DATE or datetime.now(TIMEZONE).strftime('%Y-%m-%d')
        market_name = MARKET_CONFIG.get('name', settings.MARKET_COUNTRY_CODE)
        logging.info(f"Running in DEPLOYMENT mode. Starting real-time monitoring for {market_name} on {processing_date}")
        
        try:
            while True:
                # First, check if the market is open.
                if not _is_within_trading_hours():
                    logging.info(f"Market is currently closed. Waiting for 15 minutes...")
                    time.sleep(900)  # Sleep for 15 minutes
                    continue

                logging.info(f"\n--- New Interval: Fetching and Analyzing Data for {processing_date} ---")
                
                # Fetch the latest data for the day
                master_df = _load_live_data(settings.SYMBOL, processing_date)

                if master_df.empty:
                    logging.warning("No data returned from live fetch. Waiting for next interval.")
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                    continue

                # --- Slicing and Filtering ---
                max_lookback = _calculate_max_lookback_period()
                cutoff_time = master_df['time'].max() - timedelta(minutes=max_lookback)
                
                original_rows = len(master_df)
                processing_df = master_df[master_df['time'] >= cutoff_time].copy()
                logging.info(
                    f"Sliced live data to the last {max_lookback} minutes. "
                    f"Reduced rows from {original_rows} to {len(processing_df)}."
                )

                # Filter by trading hours (this is a redundant check now but safe to keep)
                time_col = processing_df['time'].dt.time
                
                # Dynamically build the filter condition from settings
                sessions = MARKET_CONFIG.get("sessions", {})
                session_filters = []
                for session_name, hours in sessions.items():
                    try:
                        start_time = datetime.strptime(hours['start'], '%H:%M').time()
                        end_time = datetime.strptime(hours['end'], '%H:%M').time()
                        session_filters.append(f"(@time_col >= @start_time and @time_col <= @end_time)")
                    except (KeyError, ValueError):
                        continue # Skip misconfigured sessions
                
                if session_filters:
                    processing_df = processing_df.query(" or ".join(session_filters))

                if processing_df.empty:
                    logging.warning("No data available within trading hours in the current lookback window. Waiting.")
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                    continue
                
                # --- Run Approaches ---
                approaches_to_run = getattr(settings, 'ALERT_APPROACHES', [DEFAULT_APPROACH])
                if not approaches_to_run:
                    approaches_to_run = [DEFAULT_APPROACH]

                for approach_name in approaches_to_run:
                    logging.info(f"\n--- Running Approach: {approach_name} ---")
                    executor = _get_approach_executor(approach_name)
                    if not executor: continue

                    result = executor(processing_df.copy())
                    
                    if result.has_alerts:
                        # In DEPLOYMENT, we only notify, we don't validate or save reports.
                        _process_and_notify_for_approach(result)

                # --- Wait for the next interval ---
                logging.info(f"Interval finished. Waiting for {settings.MONITORING_INTERVAL_SECONDS} seconds...")
                time.sleep(settings.MONITORING_INTERVAL_SECONDS)

        except KeyboardInterrupt:
            logging.info("Stopping real-time monitor.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            # In case of a critical error, you might want to break or wait longer
            time.sleep(settings.MONITORING_INTERVAL_SECONDS * 2)
        
        # This part will only be reached if the loop is broken (e.g., by KeyboardInterrupt)
        return

    if master_df.empty:
        logging.error("No data available to process, cannot proceed.")
        return

    # --- Get Approaches to Run ---
    approaches_to_run = getattr(settings, 'ALERT_APPROACHES', [DEFAULT_APPROACH])
    if not approaches_to_run:
        approaches_to_run = [DEFAULT_APPROACH]
        logging.warning(f"ALERT_APPROACHES was empty. Defaulting to '{DEFAULT_APPROACH}'.")

    # --- Main Processing Loop (Iterates over each date) ---
    total_alerts_all_days = 0
    for processing_date in dates_to_process:
        logging.info(f"\n{'='*20} Processing Date: {processing_date} {'='*20}")

        # Filter the master dataframe for the current processing date.
        # Ensure the start/end dates are timezone-aware to match the dataframe's index.
        start_date = pd.Timestamp(processing_date, tz=TIMEZONE).replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        daily_df = master_df[(master_df['time'] >= start_date) & (master_df['time'] < end_date)].copy()

        if daily_df.empty:
            logging.warning(f"No data found for {processing_date}. Skipping.")
            continue

        # --- Filter by Vietnam Trading Hours (UTC+7) ---
        # This filter is now dynamic based on the market configuration
        sessions = MARKET_CONFIG.get("sessions", {})
        if sessions:
            session_filters = []
            time_col = daily_df['time'].dt.time
            for session_name, hours in sessions.items():
                try:
                    start_time = datetime.strptime(hours['start'], '%H:%M').time()
                    end_time = datetime.strptime(hours['end'], '%H:%M').time()
                    session_filters.append(f"(@time_col >= @start_time and @time_col < @end_time)")
                except (KeyError, ValueError):
                    logging.error(f"Skipping misconfigured trading session '{session_name}'")
                    continue
            
            if session_filters:
                original_rows = len(daily_df)
                daily_df = daily_df.query(" or ".join(session_filters))
                logging.info(
                    f"Filtered by trading hours. "
                    f"Reduced rows from {original_rows} to {len(daily_df)}."
                )
        
        if daily_df.empty:
            logging.warning(f"No data available for {processing_date} after filtering by trading hours. Skipping.")
            continue
        
        logging.info(f"Loaded {len(daily_df)} data points for {processing_date}.")

        # --- Run Alert Approaches for the day ---
        for approach_name in approaches_to_run:
            logging.info(f"\n--- Running Approach: {approach_name} for {processing_date} ---")
            executor = _get_approach_executor(approach_name)
            if not executor:
                continue

            # Execute the analysis for the current approach on daily data.
            result = executor(daily_df.copy())
            
            if result.has_alerts:
                # In Development mode, run performance validation on each alert.
                if settings.MODE == "DEVELOPMENT":
                    validated_alerts = []
                    for _, alert_row in result.alerts.iterrows():
                        alert_data = AlertData(**alert_row.to_dict())
                        # Use the full daily dataframe for look-forward validation.
                        validated_alert = calculate_alert_performance(
                            alert_data, 
                            daily_df, 
                            signal_settings.VALIDATION_PERIOD_MINUTES
                        )
                        validated_alerts.append(validated_alert.to_dict())
                    
                    result.alerts = pd.DataFrame(validated_alerts)

                # 1. Send a notification for the single latest alert.
                # In DEV mode, we don't want to spam with duplicate alerts from past data
                if settings.MODE == "DEVELOPMENT":
                    _process_and_notify_for_approach(result)
                
                # 2. Save a detailed report of all alerts for the day.
                _save_report_for_approach(result, processing_date)
                
                # 3. If in development, generate and save a summary report for the day.
                if settings.MODE == "DEVELOPMENT":
                    _generate_summary_report(result, processing_date)

                total_alerts_all_days += len(result.alerts)

    logging.info(f"\n--- Alerter Run Finished ---")
    logging.info(f"Total alerts generated across all dates and approaches: {total_alerts_all_days}")

if __name__ == "__main__":
    run_alerter()
