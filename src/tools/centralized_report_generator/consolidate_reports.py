"""
A tool to aggregate individual trade simulation reports into a consolidated summary.

Purpose:
This script scans for individual simulation reports (e.g., 'simulation_summary_individual_trade_*.json')
for a specific symbol within a given date range and mode. It then aggregates the data from these
reports into a single, comprehensive summary file (e.g., 'SYMBOL_overall_performance_YYYY-MM-DD_to_YYYY-MM-DD.json').

Optionally, it can also update the 'price_alert_settings.py' configuration file with the newly
calculated performance metrics, specifically the 'avg_worst_loss_price' for each trading approach.

Usage Examples:
1. Consolidate reports for a symbol in development mode without updating settings:
   python3 -m src.tools.centralized_report_generator.consolidate_reports \\
       --symbol 41I1G1000 \\
       --mode development \\
       --from-date 2026-01-05 \\
       --to-date 2026-01-08

2. Consolidate reports and update the price alert settings file:
   python3 -m src.tools.centralized_report_generator.consolidate_reports \\
       --symbol 41I1G1000 \\
       --mode deployment \\
       --from-date 2026-01-05 \\
       --to-date 2026-01-08 \\
       --update-price-alert-settings
"""
import argparse
import json
import os
import glob
from datetime import datetime
from collections import defaultdict
import logging
import importlib
import sys

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def _run_update_price_alert_settings(performance_data: dict, settings_file_path: str):
    """
    Safely updates the price_alert_settings.py file with the latest
    performance data, preserving the exact human-readable format.
    """
    logging.info(f"Starting update of settings file: {settings_file_path}")

    # 1. Prepare the data to be inserted
    performance_update = {}
    for approach, data in performance_data.items():
        if 'avg_worst_loss_price' in data and data['avg_worst_loss_price'] is not None:
            # Use .upper() as requested for the key and ensure the value is positive
            performance_update[approach.upper()] = {
                'avg_worst_loss_price': abs(data['avg_worst_loss_price'])
            }

    if not performance_update:
        logging.warning("No performance data with 'avg_worst_loss_price' found. Skipping settings file update.")
        return

    # It's crucial to reload the module to get the most recent version of other dictionaries
    try:
        from src.stockreports.config import price_alert_settings
        importlib.reload(price_alert_settings)
        # Safely get existing data, default to empty dict if not found
        current_data = getattr(price_alert_settings, 'PERFORMANCE_BY_APPROACH', {})
    except (ImportError, AttributeError):
        current_data = {}
        logging.info("'PERFORMANCE_BY_APPROACH' not found in current settings, will create it.")

    # Merge new data into existing data
    current_data.update(performance_update)

    # 2. Manually format the dictionary string to the exact desired style
    new_perf_str = "PERFORMANCE_BY_APPROACH = {\n"
    
    items = list(current_data.items())
    for i, (key, value) in enumerate(items):
        # --- FIX: Check if the key exists before accessing it ---
        if 'avg_worst_loss_price' in value:
            # Format the inner dictionary on a single line
            inner_dict_str = f"{{'avg_worst_loss_price': {value['avg_worst_loss_price']}}}"
            # Add the line with 4-space indentation
            new_perf_str += f"    '{key}': {inner_dict_str}"
            # Add a comma and newline for all but the last item
            if i < len(items) - 1:
                new_perf_str += ",\n"
            else:
                new_perf_str += "\n"
        # --- END FIX ---
            
    new_perf_str += "}\n"

    try:
        with open(settings_file_path, 'r') as f:
            lines = f.readlines()
    except IOError as e:
        logging.error(f"Could not read settings file {settings_file_path}: {e}")
        return

    # 3. Find the start and end of the old PERFORMANCE_BY_APPROACH dictionary
    start_index, end_index = -1, -1
    in_dict = False
    brace_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("PERFORMANCE_BY_APPROACH = {"):
            start_index = i
            in_dict = True
        if in_dict:
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count == 0 and start_index != -1:
                end_index = i
                break
    
    # 4. Replace the old block or append if not found
    if start_index != -1 and end_index != -1:
        logging.info("Found existing 'PERFORMANCE_BY_APPROACH' block. Replacing it.")
        new_lines = lines[:start_index] + [new_perf_str] + lines[end_index+1:]
    else:
        logging.info("'PERFORMANCE_BY_APPROACH' block not found. Appending to the end of the file.")
        new_lines = lines
        if new_lines and not new_lines[-1].endswith('\n'):
            new_lines.append('\n') # Add a newline if the file doesn't end with one
        new_lines.append('\n' + new_perf_str)

    # 5. Write the updated content back to the file
    try:
        with open(settings_file_path, 'w') as f:
            f.writelines(new_lines)
        logging.info(f"Successfully updated {settings_file_path} with new performance data.")
    except IOError as e:
        logging.error(f"Failed to write updated settings to {settings_file_path}: {e}")


def consolidate_reports(symbol: str, mode: str, from_date_str: str, to_date_str: str, update_price_alert_settings: bool = False):
    """
    Aggregates individual trade simulation reports and optionally updates settings.

    This function finds all individual simulation reports for a given symbol and mode
    within the specified date range. It calculates overall performance metrics and
    performance by approach, then saves the results to a consolidated JSON file.

    If `update_price_alert_settings` is True, it will also update the
    'PERFORMANCE_BY_APPROACH' dictionary in the 'price_alert_settings.py' file
    with the latest 'avg_worst_loss_price' for each approach.

    Args:
        symbol (str): The stock symbol to process.
        mode (str): The run mode ('development' or 'deployment').
        from_date_str (str): The start date for aggregation in 'YYYY-MM-DD' format.
        to_date_str (str): The end date for aggregation in 'YYYY-MM-DD' format.
        update_price_alert_settings (bool): If True, update the price alert settings file.
    """
    # Correctly define project_root by navigating up from the current file's location
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    
    # The reports to be consolidated are in the symbol's own directory, under the specified mode
    reports_dir = os.path.join(project_root, "reports", "consolidated", mode)

    if not os.path.exists(reports_dir):
        logging.error(f"Reports directory does not exist: {reports_dir}")
        return

    # --- 1. Discover and Filter Report Files ---
    try:
        from_date = datetime.strptime(from_date_str, '%Y-%m-%d').date()
        to_date = datetime.strptime(to_date_str, '%Y-%m-%d').date()
    except ValueError:
        logging.error("Invalid date format. Please use YYYY-MM-DD.")
        return

    glob_pattern = os.path.join(reports_dir, f"simulation_summary_individual_trade_{symbol}_*.json")
    all_files = glob.glob(glob_pattern)
    
    filtered_files = []
    for file_path in all_files:
        try:
            filename = os.path.basename(file_path)
            date_part = filename.split('_')[-1].replace('.json', '')
            file_date = datetime.strptime(date_part, '%Y%m%d').date()
            if from_date <= file_date <= to_date:
                filtered_files.append(file_path)
        except (ValueError, IndexError):
            logging.warning(f"Could not parse date from filename: {file_path}. Skipping.")
            continue

    if not filtered_files:
        logging.warning(f"No simulation reports found for symbol '{symbol}' in the specified date range.")
        return

    logging.info(f"Found {len(filtered_files)} reports to consolidate from {from_date_str} to {to_date_str}.")

    # --- 2. Aggregate Data ---
    # Overall summary stats
    overall_summary = {
        "total_trades": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "ignored_trades": 0,
        "total_actual_profit_loss": 0.0,
        "total_best_profit_price": 0.0,
        "total_worst_loss_price": 0.0,
    }

    # Use defaultdict to easily initialize stats for new approaches
    performance_by_approach = defaultdict(lambda: {
        "total_trades": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "total_actual_profit_loss": 0.0,
        "actual_profit_loss_values": [],
        "worst_loss_price_values": [],
        "best_profit_price_values": []
    })

    all_trades = []
    for report_file in filtered_files:
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
                
                # Aggregate overall summary fields
                overall_summary["total_trades"] += data.get("total_trades", 0)
                overall_summary["successful_trades"] += data.get("successful_trades", 0)
                overall_summary["failed_trades"] += data.get("failed_trades", 0)
                overall_summary["ignored_trades"] += data.get("ignored_trades", 0)
                overall_summary["total_actual_profit_loss"] += data.get("total_actual_profit_loss", 0.0)
                overall_summary["total_best_profit_price"] += data.get("total_best_profit_price", 0.0)
                overall_summary["total_worst_loss_price"] += data.get("total_worst_loss_price", 0.0)

                trades = data.get("trades", [])
                all_trades.extend(trades)
        except (json.JSONDecodeError, IOError) as e:
            logging.error(f"Error reading or parsing {report_file}: {e}")
            continue
    
    if not all_trades:
        logging.error("No trades found in any of the report files. Aborting.")
        return

    # --- 3. Calculate Overall Performance Statistics ---
    for trade in all_trades:
        approach = trade.get("entry_approach")
        if not approach:
            continue

        stats = performance_by_approach[approach]
        stats["total_trades"] += 1
        stats["total_actual_profit_loss"] += trade.get("actual_profit_loss", 0.0)
        stats["actual_profit_loss_values"].append(trade.get("actual_profit_loss", 0.0))
        
        # --- Aggregate worst_loss_price and best_profit_price ---
        if trade.get("worst_loss_price") is not None:
            stats["worst_loss_price_values"].append(trade.get("worst_loss_price"))
        if trade.get("best_profit_price") is not None:
            stats["best_profit_price_values"].append(trade.get("best_profit_price"))
        # --- End Aggregation ---

        if trade.get("status") == "Success":
            stats["successful_trades"] += 1
        elif trade.get("status") == "Failed":
            stats["failed_trades"] += 1

    # Finalize calculations
    final_performance_by_approach = {}
    for approach, stats in performance_by_approach.items():
        total_trades = stats["total_trades"]
        actual_profit_loss_values = stats.pop("actual_profit_loss_values")
        worst_loss_price_values = stats.pop("worst_loss_price_values")
        best_profit_price_values = stats.pop("best_profit_price_values")

        final_performance_by_approach[approach] = {
            "total_trades": total_trades,
            "successful_trades": stats["successful_trades"],
            "failed_trades": stats["failed_trades"],
            "success_rate": f"{(stats['successful_trades'] / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%",
            "total_actual_profit_loss": round(stats["total_actual_profit_loss"], 4),
            "average_actual_profit_loss": round(stats["total_actual_profit_loss"] / total_trades, 4) if total_trades > 0 else 0.0,
            "best_actual_profit": round(max(actual_profit_loss_values), 4) if actual_profit_loss_values else 0.0,
            "worst_actual_loss": round(min(actual_profit_loss_values), 4) if actual_profit_loss_values else 0.0,
            "min_worst_loss_price": round(min(worst_loss_price_values), 4) if worst_loss_price_values else 0.0,
            "max_worst_loss_price": round(max(worst_loss_price_values), 4) if worst_loss_price_values else 0.0,
            "avg_worst_loss_price": round(sum(worst_loss_price_values) / len(worst_loss_price_values), 4) if worst_loss_price_values else 0.0,
            "min_best_profit_price": round(min(best_profit_price_values), 4) if best_profit_price_values else 0.0,
            "max_best_profit_price": round(max(best_profit_price_values), 4) if best_profit_price_values else 0.0,
            "avg_best_profit_price": round(sum(best_profit_price_values) / len(best_profit_price_values), 4) if best_profit_price_values else 0.0,
        }

    # --- 4. Generate and Save Master Summary File ---
    # Finalize overall summary calculations
    total_trades_overall = overall_summary["total_trades"]
    overall_summary["success_rate"] = f"{(overall_summary['successful_trades'] / total_trades_overall * 100):.2f}%" if total_trades_overall > 0 else "0.00%"
    overall_summary["failure_rate"] = f"{(overall_summary['failed_trades'] / total_trades_overall * 100):.2f}%" if total_trades_overall > 0 else "0.00%"
    overall_summary["total_actual_profit_loss"] = round(overall_summary["total_actual_profit_loss"], 4)
    overall_summary["total_best_profit_price"] = round(overall_summary["total_best_profit_price"], 4)
    overall_summary["total_worst_loss_price"] = round(overall_summary["total_worst_loss_price"], 4)


    # --- New: Get app_config and validation_config from the first available report ---
    app_config = None
    validation_config = None
    if filtered_files:
        try:
            with open(filtered_files[0], 'r') as f:
                first_report_data = json.load(f)
                app_config = first_report_data.get("app_config")
                validation_config = first_report_data.get("validation_config")
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not read config from {filtered_files[0]}: {e}")
    # --- End New ---

    # Combine into a single output object
    final_report = {
        "overall_summary": overall_summary,
        "performance_by_approach": final_performance_by_approach,
        "app_config": app_config,
        "validation_config": validation_config
    }

    output_filename = f"{symbol}_overall_performance_{from_date_str}_to_{to_date_str}.json"
    output_path = os.path.join(reports_dir, output_filename)

    try:
        with open(output_path, 'w') as f:
            json.dump(final_report, f, indent=4)
        logging.info(f"Successfully saved consolidated performance summary to: {output_path}")
    except IOError as e:
        logging.error(f"Failed to write summary report to {output_path}: {e}")
        return # Do not proceed if saving the report fails

    # --- 5. Update Price Alert Settings File ---
    if update_price_alert_settings:
        settings_file_path = os.path.join(project_root, "src", "stockreports", "config", "price_alert_settings.py")
        _run_update_price_alert_settings(final_performance_by_approach, settings_file_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Consolidate individual trade simulation reports into a single summary.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--symbol",
        type=str,
        required=True,
        help="The stock symbol to process (e.g., '41I1FB000')."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=['development', 'deployment'],
        required=True,
        help="The run mode ('development' or 'deployment')."
    )
    parser.add_argument(
        "--from-date",
        type=str,
        required=True,
        help="The start date for the aggregation in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--to-date",
        type=str,
        required=True,
        help="The end date for the aggregation in YYYY-MM-DD format."
    )
    parser.add_argument(
        "--update-price-alert-settings",
        action='store_true',
        help="If set, the script will update 'price_alert_settings.py' with the new performance data."
    )

    args = parser.parse_args()

    consolidate_reports(
        symbol=args.symbol,
        mode=args.mode,
        from_date_str=args.from_date,
        to_date_str=args.to_date,
        update_price_alert_settings=args.update_price_alert_settings
    )
