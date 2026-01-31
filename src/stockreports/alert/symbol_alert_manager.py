#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import concurrent.futures
import time
from datetime import timedelta
import pytz
import pandas as pd
import json
import gc

# --- Project Imports ---
from .symbol_alerter import SymbolAlerter
from ..config import loader
from ..utils.data_utils import load_data_for_development
from ..utils.report_utils import save_profitability_report
from ..alert.common.profitability_simulator import simulate_profitability


class SymbolAlertManager:
    """
    Orchestrates the execution of SymbolAlerter instances for multiple symbols,
    handling concurrent execution in deployment mode and sequential in development.
    """
    def __init__(self):
        """
        Initializes the manager.
        """
        self.settings = loader.get_settings()
        self.symbols = self.settings.SYMBOLS
        
        market_code = self.settings.MARKET_COUNTRY_CODE
        timezone_str = self.settings.TRADING_HOURS[market_code]['timezone']
        self.timezone = pytz.timezone(timezone_str)
        
        self._configure_logging()

    def _configure_logging(self):
        """
        Configures logging.
        - Always logs to stdout.
        - If running in an interactive terminal, also logs to a file.
        This prevents duplicate file logging when run via launchd, which handles redirection.
        """
        logger = logging.getLogger()
        # Use the log level from settings, not a hardcoded value
        log_level = getattr(logging, self.settings.LOG_LEVEL, logging.INFO)
        logger.setLevel(log_level)

        # Prevent adding handlers multiple times
        if logger.hasHandlers():
            logger.handlers.clear()

        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # 1. Always log to stdout.
        # When run via launchd, this stream is redirected to the file specified in the .plist.
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # 2. If running in an interactive terminal, also log to a file.
        # sys.stdout.isatty() is False when run by launchd or with output redirection.
        if sys.stdout.isatty():
            mode_name = self.settings.MODE.capitalize()
            log_dir = os.path.join(self.settings.LOGS_DIR, mode_name)
            log_file_name = 'alerter.log'

            os.makedirs(log_dir, exist_ok=True)
            log_file_path = os.path.join(log_dir, log_file_name)

            file_handler = logging.FileHandler(log_file_path, mode='w')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logging.info(f"Interactive session detected. Logging to console and {log_file_path}")
        else:
            logging.info(f"Non-interactive session (e.g., launchd). Logging to stdout only.")

    def _execute_for_symbol(self, symbol: str):
        """
        Wrapper function to instantiate and execute the alerter for a single symbol.
        """
        try:
            alerter = SymbolAlerter(symbol=symbol)
            alerter.execute()
            
            # Explicitly trigger garbage collection after executing alerter for a symbol
            gc.collect()
        except Exception as e:
            logging.critical(f"A critical error occurred in the process for symbol {symbol}: {e}", exc_info=True)

    def _run_deployment(self):
        """
        Runs the alerters concurrently using a ThreadPoolExecutor.
        """
        max_workers = len(self.symbols)
        logging.info(f"Running in DEPLOYMENT mode with a thread pool of size {max_workers}.")
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                for symbol in self.symbols:
                    executor.submit(self._execute_for_symbol, symbol)
                
                logging.info("All monitoring threads are running. Press Ctrl+C to exit.")
                while True:
                    time.sleep(1)
        except KeyboardInterrupt:
            logging.info("\nKeyboardInterrupt received. Shutting down...")
        
        logging.info("Alerter manager has been shut down.")

    def _run_development(self):
        """
        Runs the alerters sequentially for debugging and testing.
        """
        logging.info("Running in DEVELOPMENT mode. Processing symbols sequentially...")
        try:
            for symbol in self.symbols:
                self._execute_for_symbol(symbol)
            logging.info("All symbols processed successfully.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred during sequential processing: {e}", exc_info=True)
            sys.exit(1)

    def run_alert_generation(self):
        """
        Starts the alert manager for alert generation.
        """
        if not self.symbols:
            logging.error("No symbols configured in settings.py. Exiting.")
            sys.exit(1)

        logging.info(f"Starting Alerter Manager for symbols: {self.symbols}")

        if self.settings.MODE == "DEPLOYMENT":
            self._run_deployment()
        else:
            self._run_development()

    def run_analysis(self):
        """
        Runs the consolidated profitability analysis.
        """
        if self.settings.MODE == "DEVELOPMENT" and self.settings.CONSOLIDATED_PROFITABILITY.get('ENABLED', False):
            self._run_consolidated_profitability_analysis()
        else:
            logging.info("Consolidated profitability analysis is disabled or not in DEVELOPMENT mode.")

    def _run_consolidated_profitability_analysis(self):
        """
        Runs a special profitability simulation by reading entry signals from
        existing profitability reports of source symbols and simulating trades
        on a single target execution symbol.
        """
        config = self.settings.CONSOLIDATED_PROFITABILITY
        source_symbols = config["ALERT_SOURCE_SYMBOLS"]
        trade_symbol = config["TRADE_EXECUTION_SYMBOL"]
        mode_str = self.settings.MODE.lower()

        logging.info(f"--- Running Consolidated Profitability Analysis ---")
        logging.info(f"Alert Sources: {source_symbols}, Trade Execution on: {trade_symbol}")

        # Determine the date range from settings
        start_date = pd.to_datetime(self.settings.DEV_DATA_DATE_RANGE['start_date'])
        end_date = pd.to_datetime(self.settings.DEV_DATA_DATE_RANGE['end_date'])
        
        processing_dates = pd.date_range(start_date, end_date)

        trade_data = load_data_for_development(trade_symbol)
        if trade_data.empty:
            logging.error(f"No data for trade execution symbol {trade_symbol}. Cannot proceed.")
            return

        # 2. Process each date
        for process_date in processing_dates:
            date_str = process_date.strftime('%Y-%m-%d')
            logging.info(f"\n--- Processing Consolidated Date: {date_str} ---")
            
            all_signals_for_day = []

            # Gather signals from all source symbols' profitability reports
            for symbol in source_symbols:
                report_filename = f"profitability_summary_{date_str.replace('-', '')}.json"
                report_path = os.path.join(
                    self.settings.REPORTS_DIR,
                    symbol,
                    mode_str,
                    "profitability",
                    report_filename
                )

                if not os.path.exists(report_path):
                    logging.warning(f"Profitability report not found for {symbol} on {date_str} at {report_path}. Skipping.")
                    continue

                try:
                    with open(report_path, 'r') as f:
                        report_data = json.load(f)
                    
                    trades = report_data.get("trades", [])
                    
                    # Enumerate through trades to identify the last one
                    for i, trade in enumerate(trades):
                        # Always add the entry signal for every trade
                        all_signals_for_day.append({
                            "alert_time": pd.to_datetime(trade["entry_timestamp"]),
                            "signal": trade["entry_signal"],
                            "approach": trade.get("entry_approach"),
                            "source_symbol": symbol,  # Tag with the source symbol
                            "suggested_price": trade.get("entry_suggested_price") # Get suggested price directly from the trade
                        })

                        # For the last trade only, add the exit signal to ensure it's included
                        if i == len(trades) - 1 and "exit_timestamp" in trade and "exit_timestamp" in trade and trade["exit_timestamp"]:
                            all_signals_for_day.append({
                                "alert_time": pd.to_datetime(trade["exit_timestamp"]),
                                "signal": trade["exit_signal"],
                                "approach": trade.get("exit_approach"),
                                "source_symbol": symbol,  # Tag with the source symbol
                                "suggested_price": trade.get("exit_suggested_price") # Get suggested price directly from the trade
                            })
                    
                    logging.info(f"Loaded signals from {symbol} for {date_str}, including last exit.")

                except (json.JSONDecodeError, KeyError) as e:
                    logging.error(f"Error reading or parsing report {report_path}: {e}")

            if not all_signals_for_day:
                logging.info(f"No signals found from any source for {date_str}. Nothing to simulate.")
                continue

            # Sort signals by time to process them chronologically
            all_signals_for_day.sort(key=lambda x: x['alert_time'])

            # Filter the trading data for the specific day
            day_start = process_date.replace(hour=0, minute=0, second=0, tzinfo=self.timezone)
            day_end = day_start + timedelta(days=1)
            daily_trade_df = trade_data[(trade_data['time'] >= day_start) & (trade_data['time'] < day_end)].copy()

            if daily_trade_df.empty:
                logging.warning(f"No trading data for {trade_symbol} on {date_str}. Skipping simulation.")
                continue

            # --- Add END_OF_DAY signal if a position is left open ---
            if all_signals_for_day:
                last_signal_direction = all_signals_for_day[-1]['signal']
                last_data_point = daily_trade_df.iloc[-1]
                
                end_of_day_signal = {
                    "alert_time": pd.to_datetime(last_data_point['time']),
                    "signal": "SELL" if last_signal_direction == "BUY" else "BUY",
                    "approach": "END_OF_DAY",
                    "source_symbol": "SYNTHETIC"  # Identify synthetic signals
                }
                all_signals_for_day.append(end_of_day_signal)
                logging.info("Appended END_OF_DAY signal to close the final trade.")

            logging.info(f"Simulating {len(all_signals_for_day)} combined signals on {trade_symbol} for {date_str}.")
            simulation_summary = simulate_profitability(all_signals_for_day, daily_trade_df)

            # Log and save the consolidated report
            logging.info("Consolidated Profitability Simulation Summary:")
            logging.info(f"  Total Trades: {simulation_summary.total_trades}")
            logging.info(f"  Successful Trades: {simulation_summary.successful_trades} ({simulation_summary.success_rate})")
            logging.info(f"  Failed Trades: {simulation_summary.failed_trades} ({simulation_summary.failure_rate})")
            logging.info(f"  Total Profit/Loss: {simulation_summary.total_profit_loss:.2f}")

            save_profitability_report(
                summary_data=simulation_summary,
                symbol="consolidated", # Special name for the report folder
                date_str=date_str,
                logger_instance=logging.getLogger()
            )

    def run(self):
        """
        Starts the alert manager, running both alert generation and analysis.
        """
        self.run_alert_generation()
        self.run_analysis()

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Symbol Alert Manager - Generation and Analysis")
    parser.add_argument('--generate-alerts', action='store_true', help='Run only the alert generation process.')
    parser.add_argument('--run-analysis', action='store_true', help='Run only the consolidated profitability analysis.')
    args = parser.parse_args()

    manager = SymbolAlertManager()

    # Decide which part of the process to run based on arguments
    if args.generate_alerts and args.run_analysis:
        logging.info("Running both alert generation and analysis.")
        manager.run()
    elif args.generate_alerts:
        logging.info("Running alert generation ONLY.")
        manager.run_alert_generation()
    elif args.run_analysis:
        logging.info("Running analysis ONLY.")
        manager.run_analysis()
    else:
        logging.info("No specific task selected. Running the full process (generation and analysis).")
        manager.run()
