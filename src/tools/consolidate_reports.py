import argparse
import json
import os
import glob
from datetime import datetime
from collections import defaultdict
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def consolidate_reports(symbol: str, mode: str, from_date_str: str, to_date_str: str):
    """
    Aggregates individual trade simulation reports into a single summary file
    for a given symbol, mode, and date range.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
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
        "total_synthetic_profit_loss": 0.0,
        "total_actual_profit_loss": 0.0,
    }

    # Use defaultdict to easily initialize stats for new approaches
    performance_by_approach = defaultdict(lambda: {
        "total_trades": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "total_synthetic_profit_loss": 0.0,
        "total_actual_profit_loss": 0.0,
        "synthetic_profit_loss_values": [],
        "actual_profit_loss_values": []
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
                overall_summary["total_synthetic_profit_loss"] += data.get("total_synthetic_profit_loss", 0.0)
                overall_summary["total_actual_profit_loss"] += data.get("total_actual_profit_loss", 0.0)

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
        stats["total_synthetic_profit_loss"] += trade.get("synthetic_profit_loss", 0.0)
        stats["total_actual_profit_loss"] += trade.get("actual_profit_loss", 0.0)
        stats["synthetic_profit_loss_values"].append(trade.get("synthetic_profit_loss", 0.0))
        stats["actual_profit_loss_values"].append(trade.get("actual_profit_loss", 0.0))
        
        if trade.get("status") == "Success":
            stats["successful_trades"] += 1
        elif trade.get("status") == "Failed":
            stats["failed_trades"] += 1

    # Finalize calculations
    final_performance_by_approach = {}
    for approach, stats in performance_by_approach.items():
        total_trades = stats["total_trades"]
        synthetic_profit_loss_values = stats.pop("synthetic_profit_loss_values")
        actual_profit_loss_values = stats.pop("actual_profit_loss_values")

        final_performance_by_approach[approach] = {
            "total_trades": total_trades,
            "successful_trades": stats["successful_trades"],
            "failed_trades": stats["failed_trades"],
            "success_rate": f"{(stats['successful_trades'] / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%",
            "total_synthetic_profit_loss": round(stats["total_synthetic_profit_loss"], 4),
            "average_synthetic_profit_loss": round(stats["total_synthetic_profit_loss"] / total_trades, 4) if total_trades > 0 else 0.0,
            "best_synthetic_profit": round(max(synthetic_profit_loss_values), 4) if synthetic_profit_loss_values else 0.0,
            "worst_synthetic_loss": round(min(synthetic_profit_loss_values), 4) if synthetic_profit_loss_values else 0.0,
            "total_actual_profit_loss": round(stats["total_actual_profit_loss"], 4),
            "average_actual_profit_loss": round(stats["total_actual_profit_loss"] / total_trades, 4) if total_trades > 0 else 0.0,
            "best_actual_profit": round(max(actual_profit_loss_values), 4) if actual_profit_loss_values else 0.0,
            "worst_actual_loss": round(min(actual_profit_loss_values), 4) if actual_profit_loss_values else 0.0,
        }

    # --- 4. Generate and Save Master Summary File ---
    # Finalize overall summary calculations
    total_trades_overall = overall_summary["total_trades"]
    overall_summary["success_rate"] = f"{(overall_summary['successful_trades'] / total_trades_overall * 100):.2f}%" if total_trades_overall > 0 else "0.00%"
    overall_summary["failure_rate"] = f"{(overall_summary['failed_trades'] / total_trades_overall * 100):.2f}%" if total_trades_overall > 0 else "0.00%"
    overall_summary["total_synthetic_profit_loss"] = round(overall_summary["total_synthetic_profit_loss"], 4)
    overall_summary["total_actual_profit_loss"] = round(overall_summary["total_actual_profit_loss"], 4)

    # --- New: Get app_config from the first available report ---
    app_config = None
    if filtered_files:
        try:
            with open(filtered_files[0], 'r') as f:
                first_report_data = json.load(f)
                app_config = first_report_data.get("app_config")
        except (json.JSONDecodeError, IOError) as e:
            logging.warning(f"Could not read app_config from {filtered_files[0]}: {e}")
    # --- End New ---

    # Combine into a single output object
    final_report = {
        "overall_summary": overall_summary,
        "performance_by_approach": final_performance_by_approach,
        "app_config": app_config  # Add the config to the final report
    }

    output_filename = f"{symbol}_overall_performance_{from_date_str}_to_{to_date_str}.json"
    output_path = os.path.join(reports_dir, output_filename)

    try:
        with open(output_path, 'w') as f:
            json.dump(final_report, f, indent=4)
        logging.info(f"Successfully saved consolidated performance summary to: {output_path}")
    except IOError as e:
        logging.error(f"Failed to write summary report to {output_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Consolidate individual trade simulation reports into a single summary."
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

    args = parser.parse_args()

    consolidate_reports(
        symbol=args.symbol,
        mode=args.mode,
        from_date_str=args.from_date,
        to_date_str=args.to_date
    )
