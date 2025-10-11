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
validation_settings = loader.get_validation_settings()

# --- Project Imports ---
from src.stockreports.notification.notification_manager import NotificationManager
from src.stockreports.utils.data_utils import fetch_intraday_data, is_trading_hours
from src.stockreports.alert.model.models import AlertNotification, AlertResult, AlertData, AlertSummary
from src.stockreports.alert.common.validation.validation import calculate_alert_performance
from src.stockreports.alert.common.validation.price_adjustment import adjust_prices_by_symbol

# --- Constants & Configuration ---
# The primary timezone is now driven by the market setting
MARKET_CONFIG = settings.TRADING_HOURS.get(settings.MARKET_COUNTRY_CODE, {})
TIMEZONE_STR = MARKET_CONFIG.get("timezone", "UTC")
TIMEZONE = pytz.timezone(TIMEZONE_STR)
DEFAULT_APPROACH = "RCM"


class SymbolAlerter:
    """
    Manages the entire alerting lifecycle for a single stock symbol.
    """
    def __init__(self, symbol: str, date_to_load: str = None):
        """
        Initializes the alerter for a specific symbol.
        """
        self.symbol = symbol
        self.date_to_load = date_to_load
        self.alerts_sent_in_session = set()
        self.notification_manager = NotificationManager()
        self._setup_logging()

    def _setup_logging(self):
        """Configures logging to file and console."""
        log_dir = os.path.join(project_root, "logs", settings.MODE.lower())
        os.makedirs(log_dir, exist_ok=True)
        log_file_path = os.path.join(log_dir, f"alerter_{self.symbol}.log")

        # Use a logger specific to this symbol instance
        self.logger = logging.getLogger(f"SymbolAlerter.{self.symbol}")
        self.logger.setLevel(logging.INFO)

        # Avoid adding handlers if they already exist
        if not self.logger.handlers:
            # File handler
            file_handler = logging.FileHandler(log_file_path)
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(file_handler)

            # Console handler
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
            self.logger.addHandler(stream_handler)
        
        self.logger.info(f"Logging configured for {self.symbol}. Log file: {log_file_path}")

    def _load_all_data_from_files(self):
        data_path = os.path.join(project_root, settings.DATA_DIR, self.symbol)
        all_files = glob.glob(f"{data_path}/*.json")
        if not all_files:
            self.logger.warning(f"No JSON data files found in {data_path}")
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
                        "time": pd.to_datetime(data["t"][:min_len], unit="s"), "open": data["o"][:min_len], "high": data["h"][:min_len],
                        "low": data["l"][:min_len], "close": data["c"][:min_len], "volume": data["v"][:min_len],
                    })
                    all_dfs.append(df_single)
                except Exception as e:
                    self.logger.error(f"Error processing {filename}: {e}")
        if not all_dfs: return pd.DataFrame()
        df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['time'], keep='first').sort_values(by='time').reset_index(drop=True)
        if not df.empty:
            df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(TIMEZONE)
            df = adjust_prices_by_symbol(df, self.symbol)
        return df

    def _load_live_data(self, date_str):
        self.logger.info(f"Fetching live data for {self.symbol} on {date_str}...")
        raw_data = fetch_intraday_data(self.symbol, date_str)
        if not raw_data or raw_data.get('s') != 'ok':
            self.logger.error("Failed to fetch or process live data.")
            return pd.DataFrame()
        keys = ["t", "o", "h", "l", "c", "v"]
        min_len = min(len(raw_data.get(k, [])) for k in keys)
        if min_len == 0:
            self.logger.warning("No data points in the live response.")
            return pd.DataFrame()
        df = pd.DataFrame({
            "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"), "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
            "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len], "volume": raw_data["v"][:min_len],
        })
        df.drop_duplicates(subset=['time'], keep='first', inplace=True)
        df = df.sort_values(by='time').reset_index(drop=True)
        if not df.empty:
            df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(TIMEZONE)
            df = adjust_prices_by_symbol(df, self.symbol)
        return df

    def _get_approach_executor(self, approach_name: str):
        try:
            module_path = f"src.stockreports.alert.approach.{approach_name.upper()}.executor"
            executor_module = importlib.import_module(module_path)
            return getattr(executor_module, 'run_analysis')
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Could not load approach '{approach_name}'. Error: {e}")
            return None

    def _process_and_notify_for_approach(self, result: AlertResult):
        if not result.has_alerts: return
        latest_alert_row = result.alerts.sort_values(by='alert_time', ascending=False).iloc[0]
        alert_key = (result.approach_name, latest_alert_row['alert_time'])
        if alert_key in self.alerts_sent_in_session:
            self.logger.info(f"Alert for {result.approach_name} at {latest_alert_row['alert_time']} already sent. Skipping.")
            return
        self.logger.info(f"Latest alert from {result.approach_name}: {latest_alert_row['signal']} at {latest_alert_row['alert_price']:.2f}")
        details_dict = json.loads(latest_alert_row['details']) if pd.notna(latest_alert_row.get('details')) and isinstance(latest_alert_row.get('details'), str) else {}
        notification = AlertNotification(
            symbol=self.symbol, signal=latest_alert_row['signal'], alert_price=latest_alert_row['alert_price'],
            alert_time=latest_alert_row['alert_time'], approach=latest_alert_row['approach'], details=details_dict
        )
        
        # Delegate sending to the NotificationManager
        self.notification_manager.send_alert(notification)
        
        # Add to session after successful dispatch to avoid re-sending
        self.alerts_sent_in_session.add(alert_key)

    def _save_report_for_approach(self, result: AlertResult, date_str: str):
        if not result.has_alerts: return
        reports_dir = os.path.join(project_root, "reports", self.symbol, settings.MODE.lower(), result.approach_name.lower())
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, f"alert_notification_{date_str.replace('-', '')}.json")
        try:
            alerts_to_save = result.alerts.copy()
            
            # Identify all datetime-like columns
            datetime_cols = alerts_to_save.select_dtypes(include=['datetime64[ns]', 'datetimetz']).columns

            # Convert to the configured timezone and then format to string
            for col in datetime_cols:
                # Ensure column is timezone-aware before converting
                if alerts_to_save[col].dt.tz is None:
                    alerts_to_save[col] = alerts_to_save[col].dt.tz_localize('UTC')
                
                alerts_to_save[col] = alerts_to_save[col].dt.tz_convert(TIMEZONE).dt.strftime('%Y-%m-%dT%H:%M:%S%z')

            alerts_to_save.to_json(filepath, orient='records', indent=4)
            self.logger.info(f"Successfully saved report for {result.approach_name} to {filepath}")
        except Exception as e:
            self.logger.error(f"Failed to save report for {result.approach_name}: {e}")

    def _calculate_max_lookback_period(self) -> int:
        max_lookback = getattr(signal_settings, 'DEFAULT_LOOKBACK_PERIOD', 60)
        active_approaches = getattr(settings, 'ALERT_APPROACHES', [])
        lookbacks = [max_lookback]
        for approach in active_approaches:
            if approach.upper() == 'RCM':
                rcm_lookback = max(getattr(signal_settings, 'MA_LONG_PERIOD', 0), getattr(signal_settings, 'AVG_VOLUME_PERIOD', 0))
                lookbacks.append(rcm_lookback)
            elif approach.upper() == 'CONSISTENT_MOMENTUM':
                try:
                    cm_lookback = signal_settings.APPROACH_CONFIG['CONSISTENT_MOMENTUM']['MOMENTUM_PERIOD_MINUTES']
                    lookbacks.append(cm_lookback)
                except (AttributeError, KeyError):
                    self.logger.warning("Could not find settings for CONSISTENT_MOMENTUM lookback.")
        max_lookback = max(lookbacks)
        self.logger.info(f"Calculated maximum required lookback period: {max_lookback} minutes.")
        return max_lookback

    def _generate_summary_report(self, result: AlertResult, date_str: str):
        if not result.has_alerts: return
        reports_dir = os.path.join(project_root, "reports", self.symbol, settings.MODE.lower(), result.approach_name.lower())
        os.makedirs(reports_dir, exist_ok=True)
        filepath = os.path.join(reports_dir, f"alert_summary.json")
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
                with open(filepath, 'r') as f: all_summaries = json.load(f)
                if not isinstance(all_summaries, list): all_summaries = []
                all_summaries = [s for s in all_summaries if s.get('date') != date_str]
            except (json.JSONDecodeError, IOError): all_summaries = []
        all_summaries.append(new_summary.to_dict())
        all_summaries.sort(key=lambda x: x.get('date', ''))
        with open(filepath, 'w') as f: json.dump(all_summaries, f, indent=4)
        self.logger.info(f"Successfully updated alert summary for {result.approach_name} at {filepath}")

    def execute(self):
        self.logger.info(f"Executing alerter for symbol: {self.symbol}...")
        if settings.MODE == "DEVELOPMENT":
            self._run_development_mode()
        elif settings.MODE == "DEPLOYMENT":
            self._run_deployment_mode()
        self.logger.info(f"Execution finished for symbol: {self.symbol}.")

    def _run_development_mode(self):
        self.logger.info(f"Running in DEVELOPMENT mode for {self.symbol}.")
        master_df = self._load_all_data_from_files()
        if master_df.empty:
            self.logger.error(f"No data loaded from files for {self.symbol}, cannot proceed.")
            return
        
        dates_to_process = []
        effective_date = self.date_to_load or settings.DATA_DATE
        if effective_date:
            dates_to_process = [effective_date]
        else:
            dates_to_process = sorted(master_df['time'].dt.strftime('%Y-%m-%d').unique())
        
        for processing_date in dates_to_process:
            self._process_date(master_df, processing_date)

    def _run_deployment_mode(self):
        processing_date = self.date_to_load or settings.DATA_DATE or datetime.now(TIMEZONE).strftime('%Y-%m-%d')
        self.logger.info(f"Running in DEPLOYMENT mode. Starting real-time monitoring for {self.symbol} on {processing_date}")
        try:
            while True:
                if not is_trading_hours():
                    self.logger.info(f"Market is currently closed for {self.symbol}. Waiting 15 minutes...")
                    time.sleep(900)
                    continue
                
                self.logger.info(f"\n--- New Interval for {self.symbol}: Fetching and Analyzing Data ---")
                master_df = self._load_live_data(processing_date)
                if master_df.empty:
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                    continue

                max_lookback = self._calculate_max_lookback_period()
                cutoff_time = master_df['time'].max() - timedelta(minutes=max_lookback)
                processing_df = master_df[master_df['time'] >= cutoff_time].copy()
                
                if processing_df.empty:
                    self.logger.warning("No data in lookback window. Waiting.")
                    time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                    continue

                approaches_to_run = getattr(settings, 'ALERT_APPROACHES', [DEFAULT_APPROACH])
                for approach_name in approaches_to_run:
                    self.logger.info(f"\n--- Running Approach: {approach_name} for {self.symbol} ---")
                    executor = self._get_approach_executor(approach_name)
                    if not executor: continue
                    result = executor(processing_df.copy())
                    if result.has_alerts:
                        self._process_and_notify_for_approach(result)
                
                self.logger.info(f"Interval finished. Waiting {settings.MONITORING_INTERVAL_SECONDS}s...")
                time.sleep(settings.MONITORING_INTERVAL_SECONDS)
        except KeyboardInterrupt:
            self.logger.info(f"Stopping real-time monitor for {self.symbol}.")
        except Exception as e:
            self.logger.critical(f"Critical error in deployment loop for {self.symbol}: {e}", exc_info=True)

    def _process_date(self, master_df, processing_date):
        self.logger.info(f"\n{'='*20} Processing Date: {processing_date} for {self.symbol} {'='*20}")
        start_date = pd.Timestamp(processing_date, tz=TIMEZONE).replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        daily_df = master_df[(master_df['time'] >= start_date) & (master_df['time'] < end_date)].copy()

        if daily_df.empty:
            self.logger.warning(f"No data found for {self.symbol} on {processing_date}.")
            return

        # Filter by trading hours
        sessions = MARKET_CONFIG.get("sessions", {})
        if sessions:
            combined_mask = pd.Series([False] * len(daily_df), index=daily_df.index)
            time_col = daily_df['time'].dt.time
            for session_name, hours in sessions.items():
                start_time = datetime.strptime(hours['start'], '%H:%M').time()
                end_time = datetime.strptime(hours['end'], '%H:%M').time()
                session_mask = (time_col >= start_time) & (time_col <= end_time)
                combined_mask = combined_mask | session_mask
            daily_df = daily_df[combined_mask]

        if daily_df.empty:
            self.logger.warning(f"No data for {self.symbol} on {processing_date} after filtering by trading hours.")
            return
        
        self.logger.info(f"Loaded {len(daily_df)} data points for {self.symbol} on {processing_date}.")
        approaches_to_run = getattr(settings, 'ALERT_APPROACHES', [DEFAULT_APPROACH])
        for approach_name in approaches_to_run:
            self.logger.info(f"\n--- Running Approach: {approach_name} for {self.symbol} on {processing_date} ---")
            executor = self._get_approach_executor(approach_name)
            if not executor: continue
            result = executor(daily_df.copy())
            if result.has_alerts:
                if settings.MODE == "DEVELOPMENT":
                    validated_alerts = []
                    for _, alert_row in result.alerts.iterrows():
                        alert_data = AlertData(**alert_row.to_dict())
                        alert_data.symbol = self.symbol
                        validated_alert = calculate_alert_performance(alert_data, daily_df, signal_settings.VALIDATION_PERIOD_MINUTES)
                        validated_alerts.append(validated_alert.to_dict())
                    result.alerts = pd.DataFrame(validated_alerts)
                    self._process_and_notify_for_approach(result)
                self._save_report_for_approach(result, processing_date)
                if settings.MODE == "DEVELOPMENT":
                    self._generate_summary_report(result, processing_date)
