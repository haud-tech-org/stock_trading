"""
Centralized Summary Report Generator

Purpose:
This script automates the process of generating individual daily trade simulation
reports and then creating a single consolidated performance summary over a specified
date range. It orchestrates the execution of `individual_trade_simulator.py` for
each day and then runs `consolidate_reports.py` for the entire period.

As a final optional step, it can also trigger the `support_resistance_detector.py`
script to update the price alert levels based on a longer historical period.

Command to run:
python3 -m src.tools.centralized_report_generator \\
    --execution-symbol <SYMBOL> \\
    --alert-sources <SOURCE_1> <SOURCE_2> ... \\
    --from-date <YYYY-MM-DD> \\
    --to-date <YYYY-MM-DD> \\
    --mode <development|deployment> \\
    [--run-sr-detector] \\
    [--sr-start-time "YYYY-MM-DD HH:MM:SS"] \\
    [--sr-end-time "YYYY-MM-DD HH:MM:SS"] \\
    [--sr-resolution <MINUTES>] \\
    [--sr-min-touches <TOUCHES>]
"""
import argparse
import logging
from datetime import datetime
import pandas as pd
import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.stockreports.utils.time_utils import get_market_timezone
from src.tools.centralized_report_generator.consolidate_reports import consolidate_reports
from src.tools.centralized_report_generator.individual_trade_simulator import run_individual_trade_simulation
from src.tools.centralized_report_generator.support_resistance_detector import run_sr_detection_for_symbols
from src.tools.centralized_report_generator.update_alert_files_with_suggestion import update_alerts_with_suggested_prices


def generate_reports_for_period(
    execution_symbol: str, 
    alert_sources: list, 
    from_date_str: str, 
    to_date_str: str, 
    mode: str,
    run_sr: bool,
    sr_start_time: str,
    sr_end_time: str,
    sr_resolution: int,
    sr_min_touches: int,
    update_suggestions: bool,
    override_suggestions: bool
):
    """
    Orchestrates the generation of daily and consolidated reports.

    This script performs a series of actions for a given date range:
    1.  Runs an individual trade simulator for each day to generate daily trade reports.
    2.  Consolidates the daily reports into a single summary report.
    3.  Optionally, runs a support and resistance level detector.
    4.  Optionally, updates all alert notification files within the date range
        with performance and structural suggested prices.

    Args:
        from_date_str (str): The start date in YYYY-MM-DD format.
        to_date_str (str): The end date in YYYY-MM-DD format.
        execution_symbol (str): The primary symbol for execution reports.
        alert_sources (list): A list of symbols to use as alert sources.
        mode (str): The simulation mode ('backtest' or 'deployment').
        run_sr_detector (bool): Whether to run the S/R detector.
        sr_start_time (str): Start time for S/R analysis.
        sr_end_time (str): End time for S/R analysis.
        sr_resolution (int): Time resolution for S/R analysis in minutes.
        sr_min_touches (int): Minimum touches for a significant S/R level.
        update_suggestions (bool): If True, runs the process to update alert
                                   files with suggested entry prices.
        override_suggestions (bool): If True (and update_suggestions is True),
                                     it will overwrite existing suggested prices.
    """
    logging.info(f"--- Starting centralized report generation from {from_date_str} to {to_date_str} ---")

    # --- 1. Run Individual Trade Simulator for each day ---
    logging.info("--- Step 1: Running Individual Trade Simulator for each day. ---")
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    date_range = pd.date_range(start=from_date, end=to_date)

    for current_date in date_range:
        day_str = current_date.strftime('%Y-%m-%d')
        logging.info(f"--- Generating report for {execution_symbol} on {day_str} ---")
        try:
            run_individual_trade_simulation(
                execution_symbol=execution_symbol,
                alert_sources=alert_sources,
                date_str=day_str,
                mode=mode
            )
        except Exception as e:
            logging.error(f"Failed to generate individual report for {day_str}. Error: {e}")
            # Continue to the next day
            continue
    
    logging.info("--- Finished generating all individual daily reports. ---")

    # --- 2. Generate Consolidated Report ---
    logging.info(f"--- Starting generation of consolidated report for {execution_symbol} from {from_date_str} to {to_date_str} ---")
    try:
        consolidate_reports(
            symbol=execution_symbol,
            mode=mode,
            from_date_str=from_date_str,
            to_date_str=to_date_str
        )
        logging.info("--- Successfully generated the consolidated report. ---")
    except Exception as e:
        logging.error(f"Failed to generate consolidated report. Error: {e}")
        # Even if consolidation fails, we might still want to run the SR detector
    
    # --- 3. Run Support/Resistance Detector (if requested) ---
    if run_sr:
        logging.info("--- Starting Support/Resistance detection process. ---")
        if not sr_start_time:
            logging.error("Support/Resistance detector requires a start time (--sr-start-time). Skipping.")
            return

        # Combine and deduplicate all symbols for the detector
        sr_symbols = list(set([execution_symbol] + alert_sources))
        
        # Use the current time as the end time if not provided
        sr_end_time_final = sr_end_time if sr_end_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            # Call the detector function directly with arguments
            run_sr_detection_for_symbols(
                symbols=sr_symbols,
                start_time=sr_start_time,
                end_time=sr_end_time_final,
                resolution=sr_resolution,
                min_touches=sr_min_touches,
                update_settings=True  # Always update settings when run from here
            )
            logging.info("--- Successfully ran the Support/Resistance detector. ---")
        except Exception as e:
            logging.error(f"Support/Resistance detector failed. Error: {e}")

    # --- 4. Update Alert Files with Suggested Prices (if requested) ---
    if update_suggestions:
        logging.info("--- Starting update of alert files with suggested prices. ---")
        try:
            update_alerts_with_suggested_prices(
                from_date_str=from_date_str,
                to_date_str=to_date_str,
                override=override_suggestions
            )
            logging.info("--- Successfully updated alert files with suggested prices. ---")
        except Exception as e:
            logging.error(f"An unexpected error occurred while updating suggested prices: {e}", exc_info=True)

    logging.info("--- Centralized report generation process finished. ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a centralized report generation process for a given period."
    )
    parser.add_argument(
        "--execution-symbol",
        type=str,
        required=True,
        help="The symbol to simulate trading on (e.g., '41I1G1000')."
    )
    parser.add_argument(
        "--alert-sources",
        nargs='+',
        required=True,
        help="A list of symbols to use as alert sources (e.g., 'VN30' '41I1G1000')."
    )
    parser.add_argument(
        "--from-date",
        type=str,
        required=True,
        help="The start date for the reports in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--to-date",
        type=str,
        required=True,
        help="The end date for the reports in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=['development', 'deployment'],
        required=True,
        help="The run mode ('development' or 'deployment') for consolidation."
    )
    # --- New arguments for Support/Resistance Detector ---
    parser.add_argument(
        "--run-sr-detector",
        action='store_true',
        help="If set, run the support/resistance detector at the end."
    )
    parser.add_argument(
        "--sr-start-time",
        type=str,
        help="Start time for the S/R detector (YYYY-MM-DD HH:MM:SS)."
    )
    parser.add_argument(
        "--sr-end-time",
        type=str,
        help="Optional end time for the S/R detector (YYYY-MM-DD HH:MM:SS)."
    )
    parser.add_argument(
        "--sr-resolution",
        type=int,
        default=15,
        help="Data resolution for the S/R detector in minutes."
    )
    parser.add_argument(
        "--sr-min-touches",
        type=int,
        default=3,
        help="Minimum touches for a significant S/R level."
    )
    # --- New arguments for Suggested Price Update ---
    parser.add_argument(
        "--update-suggestions",
        action='store_true',
        help="If set, run the script to update alert files with suggested prices."
    )
    parser.add_argument(
        "--override-suggestions",
        action='store_true',
        help="If set, override existing suggested prices in alert files."
    )

    args = parser.parse_args()

    generate_reports_for_period(
        execution_symbol=args.execution_symbol,
        alert_sources=args.alert_sources,
        from_date_str=args.from_date,
        to_date_str=args.to_date,
        mode=args.mode,
        run_sr=args.run_sr_detector,
        sr_start_time=args.sr_start_time,
        sr_end_time=args.sr_end_time,
        sr_resolution=args.sr_resolution,
        sr_min_touches=args.sr_min_touches,
        update_suggestions=args.update_suggestions,
        override_suggestions=args.override_suggestions
    )
