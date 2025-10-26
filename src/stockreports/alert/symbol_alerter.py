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
from src.stockreports.utils.data_utils import (
    fetch_intraday_data, calculate_max_lookback_period, 
    load_data_for_development, load_live_data
)
from src.stockreports.utils.time_utils import is_trading_hours, TIMEZONE_STR, SESSIONS
from src.stockreports.alert.model.models import AlertNotification, AlertResult, AlertData, AlertSummary
from src.stockreports.alert.common.validation.validation import calculate_alert_performance
from src.stockreports.alert.common.validation.price_adjustment import adjust_prices_by_symbol
from src.stockreports.alert.common.profitability_simulator import simulate_profitability
from src.stockreports.utils.report_utils import save_profitability_report, save_alert_report, update_alert_summary
from src.stockreports.utils.alert_utils import calculate_suggested_price
from src.stockreports.alert.price_movement_alerter import PriceMovementAlerter

# --- Constants & Configuration ---
# The primary timezone is now driven by the market setting
TIMEZONE = pytz.timezone(TIMEZONE_STR)
DEFAULT_APPROACH = "RCM"


class SymbolAlerter:
    """
    Manages the entire alerting lifecycle for a single stock symbol.
    """
    def __init__(self, symbol: str):
        """
        Initializes the alerter for a specific symbol.
        """
        self.symbol = symbol
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

    def _get_approach_executor(self, approach_name: str):
        try:
            module_path = f"src.stockreports.alert.approach.{approach_name.upper()}.executor"
            executor_module = importlib.import_module(module_path)
            return getattr(executor_module, 'run_analysis')
        except (ImportError, AttributeError) as e:
            self.logger.error(f"Could not load approach '{approach_name}'. Error: {e}")
            return None

    def execute(self):
        self.logger.info(f"Executing alerter for symbol: {self.symbol}...")
        if settings.MODE == "DEVELOPMENT":
            self._run_development_mode()
        elif settings.MODE == "DEPLOYMENT":
            self._run_deployment_mode()
        self.logger.info(f"Execution finished for symbol: {self.symbol}.")

    def _enrich_and_save_reports(self, result: AlertResult, market_data: pd.DataFrame, processing_date: str):
        """
        Enriches the alert result with suggested prices and saves all relevant reports.
        """
        # Calculate suggested prices for all alerts in the result
        suggested_prices = []
        for _, alert_row in result.alerts.iterrows():
            price = calculate_suggested_price(
                signal=alert_row['signal'],
                alert_time=alert_row['alert_time'],
                market_data=market_data
            )
            suggested_prices.append(price)
        
        # Add the list of prices as a new column to the DataFrame
        result.alerts['suggested_price'] = suggested_prices

        # Save the reports using the now-enriched result object
        save_alert_report(result, self.symbol, processing_date)
        if settings.MODE == "DEVELOPMENT":
            update_alert_summary(result, self.symbol, processing_date)

    def _run_development_mode(self):
        self.logger.info(f"Running in DEVELOPMENT mode for {self.symbol}.")
        master_df = load_data_for_development(self.symbol)
        if master_df.empty:
            self.logger.error(f"No data loaded for {self.symbol} in development mode, cannot proceed.")
            return
        
        dates_to_process = sorted(master_df['time'].dt.strftime('%Y-%m-%d').unique())
        
        for processing_date in dates_to_process:
            self._process_date(master_df, processing_date)

    def _run_deployment_mode(self):
        """
        Acts as a resilient supervisor for the real-time monitoring session.
        If the session crashes for any reason, this function logs the error,
        waits, and then starts a completely new session.
        """
        self.logger.info(f"Entering resilient deployment mode for {self.symbol}.")
        while True:
            try:
                # The actual monitoring work is delegated to a separate function.
                self._perform_monitoring_session()
            except KeyboardInterrupt:
                self.logger.info(f"Stopping real-time monitor for {self.symbol}.")
                break  # Exit the supervisor loop.
            except Exception as e:
                self.logger.critical(
                    f"The monitoring session for {self.symbol} crashed. Restarting... Error: {e}",
                    exc_info=True
                )
                self.logger.info(f"Waiting for {settings.MONITORING_INTERVAL_SECONDS} seconds before restarting...")
                time.sleep(settings.MONITORING_INTERVAL_SECONDS)

    def _perform_monitoring_session(self):
        """
        Executes a single, continuous real-time monitoring session for the symbol.
        This function is designed to run indefinitely until an error occurs.
        """
        # Initialization happens here, ensuring a clean state for each new session.
        processing_date = datetime.now(pytz.utc).astimezone(TIMEZONE).strftime('%Y-%m-%d')
        self.logger.info(f"Starting new monitoring session for {self.symbol} on {processing_date}")
        
        master_df = pd.DataFrame()
        triggered_levels_today = set()

        # This is the main operational loop for fetching and analyzing data.
        while True:
            if not is_trading_hours():
                self.logger.info(f"Market is currently closed for {self.symbol}. Waiting 15 minutes...")
                time.sleep(900)
                continue
            
            self.logger.info(f"\n--- New Interval for {self.symbol}: Fetching and Analyzing Data ---")

            # Define the time window for the data fetch
            to_dt = datetime.now(pytz.utc).astimezone(TIMEZONE)
            if master_df.empty:
                # First run: fetch all data from the start of the day
                all_starts = [times['start'] for times in SESSIONS.values()]
                start_time_str = min(all_starts)
                start_h, start_m = map(int, start_time_str.split(':'))
                from_dt = to_dt.replace(hour=start_h, minute=start_m, second=0, microsecond=0)
            else:
                # Subsequent runs: fetch data from the last known point in time
                last_known_time = master_df['time'].max()
                from_dt = last_known_time

            from_timestamp = int(from_dt.timestamp())
            to_timestamp = int(to_dt.timestamp())

            # Fetch the latest data slice
            latest_df = load_live_data(self.symbol, from_timestamp, to_timestamp)

            if latest_df.empty:
                self.logger.warning("The latest DataFrame is still empty. Waiting for data.")
                time.sleep(settings.MONITORING_INTERVAL_SECONDS)
                continue
            
            new_candle_count = len(latest_df)
            
            # Append new data and remove duplicates, keeping the last entry
            master_df = pd.concat([master_df, latest_df]).drop_duplicates(subset=['time'], keep='last').sort_values(by='time').reset_index(drop=True)

            # --- Price Movement Alerter ---
            price_alerter = PriceMovementAlerter(self.symbol, triggered_levels_today)
            price_alerts = price_alerter.execute(master_df)
            if price_alerts:
                self.logger.info(f"Found {len(price_alerts)} price movement alerts.")
                price_alerts_data = []
                for msg in price_alerts:
                    price_alerts_data.append({
                        'alert_time': master_df['time'].iloc[-1],
                        'signal': 'Price Level Cross',
                        'alert_price': master_df['close'].iloc[-1],
                        'approach': 'PriceMovement',
                        'details': json.dumps({'message': msg})
                    })
                
                price_alert_result = AlertResult(
                    alerts=pd.DataFrame(price_alerts_data),
                    approach_name="PriceMovement"
                )
                self.notification_manager.process_and_notify(price_alert_result, self.symbol, master_df)


            # --- Standard Approach Alerter ---
            max_lookback = calculate_max_lookback_period()
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
                result = executor(df=processing_df.copy(), new_candle_count=new_candle_count)
                if result.has_alerts:
                    # Send notification immediately for low latency.
                    self.notification_manager.process_and_notify(result, self.symbol, processing_df)
                    # Then, enrich data and save the report.
                    self._enrich_and_save_reports(result, processing_df, processing_date)
            
            self.logger.info(f"Interval finished. Waiting {settings.MONITORING_INTERVAL_SECONDS}s...")
            time.sleep(settings.MONITORING_INTERVAL_SECONDS)

    def _process_date(self, master_df, processing_date):
        self.logger.info(f"\n{'='*20} Processing Date: {processing_date} for {self.symbol} {'='*20}")
        start_date = pd.Timestamp(processing_date, tz=TIMEZONE).replace(hour=0, minute=0, second=0)
        end_date = start_date + timedelta(days=1)
        daily_df = master_df[(master_df['time'] >= start_date) & (master_df['time'] < end_date)].copy()

        if daily_df.empty:
            self.logger.warning(f"No data found for {self.symbol} on {processing_date}.")
            return

                        # Filter by trading hours
        if SESSIONS:
            combined_mask = pd.Series([False] * len(daily_df), index=daily_df.index)
            time_col = daily_df['time'].dt.time
            for session_name, hours in SESSIONS.items():
                start_time = datetime.strptime(hours['start'], '%H:%M').time()
                end_time = datetime.strptime(hours['end'], '%H:%M').time()
                session_mask = (time_col >= start_time) & (time_col <= end_time)
                combined_mask = combined_mask | session_mask
            daily_df = daily_df[combined_mask]

        if daily_df.empty:
            self.logger.warning(f"No data for {self.symbol} on {processing_date} after filtering by trading hours.")
            return
        
        self.logger.info(f"Loaded {len(daily_df)} data points for {self.symbol} on {processing_date}.")
        
        all_alerts_for_day = []
        approaches_to_run = getattr(settings, 'ALERT_APPROACHES', [DEFAULT_APPROACH])
        
        for approach_name in approaches_to_run:
            self.logger.info(f"\n--- Running Approach: {approach_name} for {self.symbol} on {processing_date} ---")
            executor = self._get_approach_executor(approach_name)
            if not executor: continue
            
            # Pass the full length of the daily dataframe as new_candle_count in development mode
            result = executor(df=daily_df.copy(), new_candle_count=len(daily_df))
            
            if result.has_alerts:
                # Step 1: Send notifications (fire-and-forget)
                self.notification_manager.process_and_notify(result, self.symbol, daily_df)

                # Step 2: Enrich data and save reports
                if settings.MODE == "DEVELOPMENT":
                    validated_alerts = []
                    for _, alert_row in result.alerts.iterrows():
                        alert_data = AlertData(**alert_row.to_dict())
                        alert_data.symbol = self.symbol
                        validated_alert = calculate_alert_performance(alert_data, daily_df, signal_settings.VALIDATION_PERIOD_MINUTES)
                        validated_alerts.append(validated_alert.to_dict())
                    result.alerts = pd.DataFrame(validated_alerts)
                
                self._enrich_and_save_reports(result, daily_df, processing_date)
                
                # Collect alerts for end-of-day profitability simulation
                all_alerts_for_day.extend(result.alerts.to_dict('records'))

        if settings.MODE == "DEVELOPMENT" and all_alerts_for_day:
            self.logger.info(f"\n--- Running Profitability Simulation for {self.symbol} on {processing_date} ---")
            simulation_summary = simulate_profitability(all_alerts_for_day, daily_df)
            
            # Log the summary in a readable format
            self.logger.info("Profitability Simulation Summary:")
            self.logger.info(f"  Total Trades: {simulation_summary.total_trades}")
            self.logger.info(f"  Successful Trades: {simulation_summary.successful_trades} ({simulation_summary.success_rate})")
            self.logger.info(f"  Failed Trades: {simulation_summary.failed_trades} ({simulation_summary.failure_rate})")
            self.logger.info(f"  Total Profit/Loss: {simulation_summary.total_profit_loss:.2f}")

            # Save the detailed report using the new utility function
            save_profitability_report(
                summary_data=simulation_summary,
                symbol=self.symbol,
                date_str=processing_date,
                logger_instance=self.logger
            )
