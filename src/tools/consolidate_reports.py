
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

    # --- 2. Aggregate Trade Data ---
    # Use defaultdict to easily initialize stats for new approaches
    performance_by_approach = defaultdict(lambda: {
        "total_trades": 0,
        "successful_trades": 0,
        "failed_trades": 0,
        "total_profit_loss": 0.0,
        "profit_loss_values": []
    })

    all_trades = []
    for report_file in filtered_files:
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
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
        stats["total_profit_loss"] += trade.get("profit_loss", 0.0)
        stats["profit_loss_values"].append(trade.get("profit_loss", 0.0))
        
        if trade.get("status") == "Success":
            stats["successful_trades"] += 1
        elif trade.get("status") == "Failed":
            stats["failed_trades"] += 1

    # Finalize calculations
    final_summary = {}
    for approach, stats in performance_by_approach.items():
        total_trades = stats["total_trades"]
        profit_loss_values = stats.pop("profit_loss_values") # Remove the list from final output

        final_summary[approach] = {
            "total_trades": total_trades,
            "successful_trades": stats["successful_trades"],
            "failed_trades": stats["failed_trades"],
            "success_rate": f"{(stats['successful_trades'] / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%",
            "total_profit_loss": round(stats["total_profit_loss"], 4),
            "average_profit_loss": round(stats["total_profit_loss"] / total_trades, 4) if total_trades > 0 else 0.0,
            "best_trade_profit": round(max(profit_loss_values), 4) if profit_loss_values else 0.0,
            "worst_trade_loss": round(min(profit_loss_values), 4) if profit_loss_values else 0.0,
        }

    # --- 4. Generate and Save Master Summary File ---
    output_filename = f"{symbol}_overall_performance_{from_date_str}_to_{to_date_str}.json"
    output_path = os.path.join(reports_dir, output_filename)

    try:
        with open(output_path, 'w') as f:
            json.dump(final_summary, f, indent=4)
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
