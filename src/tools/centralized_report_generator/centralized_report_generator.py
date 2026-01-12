"""
Centralized Report Generation and Backtesting Orchestrator

Purpose:
This script is the main entry point for running a comprehensive backtesting and
reporting workflow. It automates the process of simulating trades across multiple
scenarios (profit/loss thresholds) and can perform several key tasks in sequence:

1.  **Batch Trade Simulation**: Iterates through profit/loss scenarios defined in
    `validation_settings.py`. For each scenario, it runs `individual_trade_simulator.py`
    for every day in a given date range.
2.  **Batch Consolidated Reporting**: After each scenario's daily simulations are
    complete, it runs `consolidate_reports.py` to aggregate the results into a
    single performance summary for that scenario.
3.  **Support/Resistance Detection**: Optionally, it can run a historical analysis
    to detect and update significant support and resistance price levels.
4.  **Suggested Price Backfilling**: Optionally, it can trigger a maintenance
    script to backfill or update suggested entry prices in existing alert files.

Usage Examples:

1. Simplified - Run backtesting for a date range with default settings:
   python3 -m src.tools.centralized_report_generator.centralized_report_generator \\
       --execution-symbol 41I1G1000 \\
       --alert-sources VN30 \\
       --from-date 2026-01-05 \\
       --to-date 2026-01-08 \\
       --mode deployment

2. Full Arguments - Run the complete workflow with all optional tasks:
   python3 -m src.tools.centralized_report_generator.centralized_report_generator \\
       --execution-symbol 41I1G1000 \\
       --alert-sources VN30 41I1G1000 \\
       --from-date 2026-01-08 \\
       --to-date 2026-01-08 \\
       --mode deployment \\
       --run-sr-detector \\
       --sr-start-time "2026-01-01 09:00:00" \\
       --suggestion-type all \\
       --update-price-alert-settings
"""
import argparse
import logging
from datetime import datetime
import pandas as pd
import sys
import os
from typing import Optional

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)

from src.stockreports.config.validation_settings import VALIDATION_PRICE_THRESHOLD_PROFIT, VALIDATION_PRICE_THRESHOLD_LOSS
# from src.stockreports.utils.file_utils import clear_files_in_directory
# from src.stockreports.utils.report_utils import get_consolidated_scenario_directory
from src.stockreports.utils.time_utils import get_market_timezone
from src.tools.centralized_report_generator.consolidate_reports import consolidate_reports
from src.tools.centralized_report_generator.individual_trade_simulator import run_individual_trade_simulation
from src.tools.centralized_report_generator.support_resistance_detector import run_sr_detection_for_symbols
from src.tools.centralized_report_generator.update_alert_files_with_suggestion import update_alerts_with_suggested_prices
from src.tools.analysis.analyze_overall_performance import run_analysis


# def _clear_scenario_reports(mode: str, profit_threshold: float, loss_threshold: float):
#     """A helper to clear old reports for a specific scenario."""
#     logging.info(f"--- Clearing old reports for scenario Profit: {profit_threshold}, Loss: {loss_threshold} ---")
#     scenario_dir = get_consolidated_scenario_directory(
#         mode=mode,
#         profit_threshold=profit_threshold,
#         loss_threshold=loss_threshold
#     )
#     clear_files_in_directory(scenario_dir)


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
    suggestion_type: Optional[str],
    update_price_alert_settings: bool,
    run_analysis_flag: bool
):
    """
    Orchestrates the generation of daily reports, consolidated summaries,
    and optional maintenance tasks like S/R detection and suggested price updates.

    Args:
        execution_symbol (str): The primary symbol for execution reports.
        alert_sources (list): A list of symbols to use as alert sources.
        from_date_str (str): The start date in YYYY-MM-DD format.
        to_date_str (str): The end date in YYYY-MM-DD format.
        mode (str): The simulation mode ('development' or 'deployment').
        run_sr (bool): If True, runs the support and resistance detector.
        sr_start_time (str): Start time for S/R analysis.
        sr_end_time (str): End time for S/R analysis.
        sr_resolution (int): Time resolution for S/R analysis in minutes.
        sr_min_touches (int): Minimum touches for a significant S/R level.
        suggestion_type (Optional[str]): If provided, runs the process to update
            alert files with the specified type of suggested price ('performance',
            'structural', or 'all').
        update_price_alert_settings (bool): If True, the consolidation step will
            update the 'price_alert_settings.py' file with new performance data.
        run_analysis_flag (bool): If True, runs the performance analysis script
            after all other steps are complete.
    """
    logging.info(f"--- Starting centralized report generation from {from_date_str} to {to_date_str} ---")

    profit_thresholds = VALIDATION_PRICE_THRESHOLD_PROFIT
    loss_thresholds = VALIDATION_PRICE_THRESHOLD_LOSS

    for profit_threshold in profit_thresholds:
        for loss_threshold in loss_thresholds:
            if profit_threshold <= loss_threshold:
                logging.info(f"--- Skipping simulation for Profit: {profit_threshold}, Loss: {loss_threshold} (profit <= loss) ---")
                continue

            # # Clear old reports for the current scenario before running
            # _clear_scenario_reports(mode, profit_threshold, loss_threshold)

            logging.info(f"--- Running simulation for Profit: {profit_threshold}, Loss: {loss_threshold} ---")

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
                        mode=mode,
                        profit_threshold=profit_threshold,
                        loss_threshold=loss_threshold
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
                    to_date_str=to_date_str,
                    update_price_alert_settings=update_price_alert_settings,
                    profit_threshold=profit_threshold,
                    loss_threshold=loss_threshold
                )
                logging.info("--- Successfully generated the consolidated report. ---")
            except Exception as e:
                logging.error(f"Failed to generate consolidated report. Error: {e}")
                # Even if consolidation fails, we might still want to run the SR detector
    
    # --- 3. Run Performance Analysis (if requested) ---
    if run_analysis_flag:
        logging.info("--- Starting performance analysis. ---")
        try:
            # The analysis script will find the reports based on the mode
            base_reports_dir = os.path.join(project_root, "reports")
            run_analysis(mode=mode, base_reports_dir=base_reports_dir)
            logging.info("--- Successfully ran performance analysis. ---")
        except Exception as e:
            logging.error(f"Performance analysis failed. Error: {e}", exc_info=True)

    # --- 4. Run Support/Resistance Detector (if requested) ---
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

    # --- 5. Update Alert Files with Suggested Prices (if requested) ---
    if suggestion_type:
        logging.info("--- Starting update of alert files with suggested prices. ---")
        try:
            update_alerts_with_suggested_prices(
                from_date_str=from_date_str,
                to_date_str=to_date_str,
                suggestion_type=suggestion_type
            )
            logging.info("--- Successfully updated alert files with suggested prices. ---")
        except Exception as e:
            logging.error(f"An unexpected error occurred while updating suggested prices: {e}", exc_info=True)

    logging.info("--- Centralized report generation process finished. ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run a centralized report generation and backtesting process for multiple scenarios.",
        formatter_class=argparse.RawTextHelpFormatter
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
        help="The run mode ('development' or 'deployment') for all sub-processes."
    )
    # --- Optional Sub-process Triggers ---
    parser.add_argument(
        "--run-sr-detector",
        action='store_true',
        help="If set, run the support/resistance detector after all scenarios are complete."
    )
    parser.add_argument(
        "--sr-start-time",
        type=str,
        help="Start time for the S/R detector (YYYY-MM-DD HH:MM:SS). Required if --run-sr-detector is set."
    )
    parser.add_argument(
        "--sr-end-time",
        type=str,
        help="Optional end time for the S/R detector (YYYY-MM-DD HH:MM:SS). Defaults to now."
    )
    parser.add_argument(
        "--sr-resolution",
        type=int,
        default=15,
        help="Data resolution for the S/R detector in minutes. Default: 15."
    )
    parser.add_argument(
        "--sr-min-touches",
        type=int,
        default=3,
        help="Minimum touches for a significant S/R level. Default: 3."
    )
    parser.add_argument(
        "--suggestion-type",
        type=str,
        choices=['performance', 'structural', 'all'],
        default=None,
        help="If provided, runs the suggestion updater to backfill prices after all scenarios are complete."
    )
    parser.add_argument(
        "--update-price-alert-settings",
        action='store_true',
        help="If set, each consolidated report step will attempt to update 'price_alert_settings.py'."
    )
    parser.add_argument(
        "--run-analysis",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run the performance analysis script after all reports are generated. Disable with --no-run-analysis."
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
        suggestion_type=args.suggestion_type,
        update_price_alert_settings=args.update_price_alert_settings,
        run_analysis_flag=args.run_analysis
    )
