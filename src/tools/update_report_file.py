#!/usr/bin/env python3
import argparse
import json
import os
import sys
import re
from datetime import datetime
import pandas as pd

# Add project root to Python path to allow relative imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(PROJECT_ROOT)

from src.stockreports.utils.data_utils import load_data_for_development
from src.stockreports.alert.common.profitability_simulator import calculate_trade_metrics
from src.stockreports.utils.time_utils import get_market_timezone

def update_report_file(file_path: str):
    """
    Loads a specific simulation report file, calculates new analytics fields,
    and overwrites the file with the enriched data.
    """
    if not os.path.exists(file_path):
        print(f"Error: Report file not found at {file_path}")
        sys.exit(1)

    # --- Extract symbol and date from filename ---
    filename = os.path.basename(file_path)
    match = re.search(r'simulation_summary_(\w+)_(\d{8})', filename)
    if not match:
        print(f"Error: Could not parse symbol and date from filename: {filename}")
        print("Expected format: simulation_summary_[SYMBOL]_[YYYYMMDD]*.json")
        sys.exit(1)
    
    symbol = match.group(1)
    date_str_yyyymmdd = match.group(2)
    date_str = datetime.strptime(date_str_yyyymmdd, "%Y%m%d").strftime("%Y-%m-%d")
    
    print(f"Processing file: {filename}")
    print(f"  - Symbol: {symbol}")
    print(f"  - Date: {date_str}")

    # --- Load Report and Price Data ---
    with open(file_path, 'r') as f:
        report_data = json.load(f)

    trades = report_data.get("trades")
    if not trades:
        print("No trades found in the report. Nothing to update.")
        return

    print(f"Loading historical price data for {symbol} on {date_str}...")
    full_day_data = load_data_for_development(symbol, start_date=date_str, end_date=date_str)
    if full_day_data.empty:
        print(f"Error: Could not load price data for {symbol} on {date_str}. Cannot calculate new fields.")
        return

    # Ensure the dataframe index is a timezone-aware DatetimeIndex
    if 'time' in full_day_data.columns and not isinstance(full_day_data.index, pd.DatetimeIndex):
        full_day_data = full_day_data.set_index('time')
    if not full_day_data.index.tz:
        print("Error: Price data index is not timezone-aware.")
        return

    # --- Calculate New Fields for Each Trade ---
    market_tz = get_market_timezone()
    updated_trades = []
    for trade in trades:
        # Convert timestamps and ensure they are localized to the same timezone as the price data
        entry_time = pd.to_datetime(trade['entry_timestamp']).tz_convert(market_tz)
        exit_time = pd.to_datetime(trade.get('exit_timestamp')) if trade.get('exit_timestamp') else None
        if exit_time:
            exit_time = exit_time.tz_convert(market_tz)

        temp_trade_obj = {
            "entry_timestamp": entry_time,
            "entry_price": trade["entry_price"],
            "entry_signal": trade["entry_signal"],
            "exit_timestamp": exit_time,
            "exit_price": trade.get("exit_price"),
            "exit_signal": trade.get("exit_signal"),
            "profit_loss": trade.get("profit_loss"),
            "entry_approach": trade.get("entry_approach"),
            "exit_approach": trade.get("exit_approach"),
        }

        updated_trade_metrics = calculate_trade_metrics(temp_trade_obj, full_day_data)

        # Merge the newly calculated metrics back into the original trade object
        trade.update(updated_trade_metrics)
        updated_trades.append(trade)

    report_data["trades"] = updated_trades
    
    # --- Overwrite the Original File ---
    print(f"Saving updated report with new fields to: {file_path}")
    with open(file_path, 'w') as f:
        json.dump(report_data, f, indent=4, default=str) # Use default=str to handle numpy types

    print("Report update complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Update a specific historical simulation report with new analytical fields.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--file", required=True, help="Full path to the simulation summary JSON file.")

    args = parser.parse_args()
    update_report_file(args.file)
