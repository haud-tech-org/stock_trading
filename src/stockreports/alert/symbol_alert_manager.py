#!/usr/bin/env python3
import os
import sys
import logging
import argparse
import concurrent.futures
import time

# --- Project Imports ---
from .symbol_alerter import SymbolAlerter
from ..config import loader

class SymbolAlertManager:
    """
    Orchestrates the execution of SymbolAlerter instances for multiple symbols,
    handling concurrent execution in deployment mode and sequential in development.
    """
    def __init__(self, date_to_load: str = None):
        """
        Initializes the manager.
        """
        self.settings = loader.get_settings()
        self.date_to_load = date_to_load
        self.symbols = self.settings.SYMBOLS
        
        logging.basicConfig(level="INFO", format="%(asctime)s - %(levelname)s - %(message)s", stream=sys.stdout)

    def _execute_for_symbol(self, symbol: str):
        """
        Wrapper function to instantiate and execute the alerter for a single symbol.
        """
        try:
            alerter = SymbolAlerter(symbol=symbol, date_to_load=self.date_to_load)
            alerter.execute()
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

    def run(self):
        """

        Starts the alert manager, choosing the execution mode based on settings.
        """
        if not self.symbols:
            logging.error("No symbols configured in settings.py. Exiting.")
            sys.exit(1)

        logging.info(f"Starting Alerter Manager for symbols: {self.symbols}")

        if self.settings.MODE == "DEPLOYMENT":
            self._run_deployment()
        else:
            self._run_development()

# --- Main Execution ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the stock trading alerter for one or more symbols.")
    parser.add_argument(
        '--date', type=str, default=None,
        help="The date to process data for, in YYYY-MM-DD format."
    )
    args = parser.parse_args()

    # Instantiate and run the manager
    manager = SymbolAlertManager(date_to_load=args.date)
    manager.run()
