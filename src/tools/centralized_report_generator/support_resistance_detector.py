"""
Support and Resistance Level Detector

Purpose:
This script analyzes historical price data for one or more stock symbols to identify significant
support and resistance levels. It uses a pivot-based algorithm that can be fine-tuned through
command-line arguments. It can also automatically update the `price_alert_settings.py`
configuration file with the newly detected levels.

Command to run:
python3 src/tools/support_resistance_detector.py \
    --symbols <SYMBOL_1> <SYMBOL_2> ... \
    --start-time "YYYY-MM-DD HH:MM:SS" \
    --end-time "YYYY-MM-DD HH:MM:SS" \
    [--resolution <MINUTES>] \
    [--window <CANDLES>] \
    [--tolerance-percent <PERCENT>] \
    [--min-touches <TOUCHES>] \
    [--update-settings]

Sample:
python3 src/tools/support_resistance_detector.py \
    --symbols VN30 HPG \
    --start-time "2025-11-01 09:00:00" \
    --end-time "2025-11-20 14:30:00" \
    --resolution 15 \
    --min-touches 3 \
    --update-settings
"""
import argparse
import logging
import sys
import os
from datetime import datetime

import pandas as pd

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, project_root)


from src.stockreports.utils.data_utils import TIMEZONE_STR
from src.stockreports.config import loader
from src.stockreports.config import price_alert_settings
from src.stockreports.utils.historical_data_manager import _get_historical_data_with_resolution
import importlib
import pprint

# Load settings
settings = loader.get_settings()

# Configure logging
logging.basicConfig(level=settings.LOG_LEVEL, format='%(asctime)s - %(levelname)s - %(message)s')

def find_support_resistance(data: pd.DataFrame, window: int = 10, tolerance_percent: float = 0.5, min_touches: int = 2):
    """
    Identifies significant support and resistance levels from price data based on pivot strength.

    Args:
        data (pd.DataFrame): DataFrame with 'high' and 'low' price columns.
        window (int): Number of candles to check on each side for a more significant pivot.
        tolerance_percent (float): The percentage tolerance to cluster potential levels.
        min_touches (int): The minimum number of times a level must be touched to be considered significant.

    Returns:
        list: A sorted list of significant support and resistance levels.
    """
    if data.empty:
        return []

    pivots = []
    for i in range(window, len(data) - window):
        is_pivot_high = data['high'][i] == data.iloc[i-window:i+window+1]['high'].max()
        if is_pivot_high:
            pivots.append(data['high'][i])

        is_pivot_low = data['low'][i] == data.iloc[i-window:i+window+1]['low'].min()
        if is_pivot_low:
            pivots.append(data['low'][i])
    
    if not pivots:
        return []

    pivots.sort()
    
    # Cluster levels and count touches
    clusters = []
    if not pivots:
        return []

    current_cluster = [pivots[0]]
    for price in pivots[1:]:
        if price <= current_cluster[0] * (1 + tolerance_percent / 100):
            current_cluster.append(price)
        else:
            clusters.append(current_cluster)
            current_cluster = [price]
    if current_cluster:
        clusters.append(current_cluster)

    # Filter clusters by minimum touches and calculate the average level
    significant_levels = []
    for cluster in clusters:
        if len(cluster) >= min_touches:
            level = sum(cluster) / len(cluster)
            significant_levels.append(level)

    # Round to a reasonable number of decimal places
    significant_levels = [round(level, 2) for level in significant_levels]
    
    return sorted(list(set(significant_levels)))


def run_sr_detection_for_symbols(
    symbols: list,
    start_time: str,
    end_time: str,
    resolution: int = 15,
    window: int = 10,
    tolerance_percent: float = 0.5,
    min_touches: int = 3,
    update_settings: bool = False
):
    """
    A callable function to run the S/R detection logic for a list of symbols.
    """
    try:
        # Convert to datetime and make them timezone-aware
        start_dt = pd.to_datetime(start_time).tz_localize(TIMEZONE_STR)
        end_dt = pd.to_datetime(end_time).tz_localize(TIMEZONE_STR)
    except Exception as e:
        logging.error(f"Invalid date format or timezone issue: {e}. Please use 'YYYY-MM-DD HH:MM:SS'.")
        return

    for symbol in symbols:
        logging.info(f"--- Processing symbol: {symbol} ---")
        logging.info(f"Starting support/resistance analysis with resolution '{resolution or 'default'}'.")
        logging.info(f"Fetching data from {start_time} to {end_time}...")
        
        df = _get_historical_data_with_resolution(
            symbol=symbol,
            start_time=start_dt,
            end_time=end_dt,
            resolution=resolution
        )

        if df is None or df.empty:
            logging.error(f"Failed to fetch data for {symbol} or no data returned. Skipping.")
            continue

        # --- Find Levels ---
        levels = find_support_resistance(
            df,
            window=window,
            tolerance_percent=tolerance_percent,
            min_touches=min_touches
        )

        if levels:
            logging.info(f"Identified Support/Resistance Levels for {symbol}:")
            clean_levels = [float(level) for level in levels]
            print(f'"{symbol}": {clean_levels}')

            # --- Update Settings File (if requested) ---
            if update_settings:
                last_close = df['close'].iloc[-1]
                update_price_alert_settings(symbol, clean_levels, last_close)

        else:
            logging.info(f"No significant support or resistance levels were found for {symbol} in the given time range.")


def update_price_alert_settings(symbol: str, levels: list, reference_price: float):
    """
    Updates the price_alert_settings.py file with the new levels and reference price.
    """
    settings_path = os.path.join(project_root, 'src', 'stockreports', 'config', 'price_alert_settings.py')
    logging.info(f"Updating price alert settings file: {settings_path}")

    # It's crucial to reload the module to get the most recent version of the dictionary
    importlib.reload(price_alert_settings)
    
    current_alerts = price_alert_settings.PRICE_ALERTS
    absolute_interval = current_alerts.get(symbol, {}).get("absolute_interval", 9.0)

    # Update the dictionary in memory, ensuring all numbers are standard Python types
    current_alerts[symbol] = {
        "reference_price": float(round(reference_price, 2)),
        "fixed_levels": [float(level) for level in levels],
        "absolute_interval": float(absolute_interval),
    }

    # Read the original file content
    with open(settings_path, 'r') as f:
        lines = f.readlines()

    # Manually format the dictionary to match the desired style
    new_alerts_str = "PRICE_ALERTS = {\n"
    num_alerts = len(current_alerts)
    for i, (sym, config) in enumerate(current_alerts.items()):
        new_alerts_str += f'    "{sym}": {{\n'
        new_alerts_str += f'        "reference_price": {config["reference_price"]},\n'
        new_alerts_str += f'        "fixed_levels": {config["fixed_levels"]},\n'
        new_alerts_str += f'        "absolute_interval": {config["absolute_interval"]},\n'
        new_alerts_str += "    }"
        if i < num_alerts - 1:
            new_alerts_str += ",\n"
        else:
            new_alerts_str += "\n"
    new_alerts_str += "}\n"

    # Find the start and end of the old PRICE_ALERTS dictionary
    start_index, end_index = -1, -1
    in_dict = False
    brace_count = 0
    for i, line in enumerate(lines):
        if line.strip().startswith("PRICE_ALERTS = {"):
            start_index = i
            in_dict = True
        if in_dict:
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count == 0:
                end_index = i
                break
    
    if start_index != -1 and end_index != -1:
        # Replace the old dictionary with the new one
        new_lines = lines[:start_index] + [new_alerts_str] + lines[end_index+1:]
        
        # Write the updated content back to the file
        with open(settings_path, 'w') as f:
            f.writelines(new_lines)
        logging.info(f"Successfully updated '{symbol}' in price_alert_settings.py.")
    else:
        logging.error("Could not find the PRICE_ALERTS dictionary in the settings file. Update failed.")


def main():
    """
    Main function to run the support/resistance detection script from the command line.
    """
    parser = argparse.ArgumentParser(description="Detect support and resistance levels for given stock symbols.")
    parser.add_argument("--symbols", type=str, nargs='+', default=['VN30', '41I1G1000', 'VIC', 'HPG'], help="One or more stock symbols.")
    parser.add_argument("--start-time", type=str, default="2025-08-01 09:00:00", help="Start time for data fetching (YYYY-MM-DD HH:MM:SS).")
    parser.add_argument("--end-time", type=str, default=None, help="End time for data fetching (YYYY-MM-DD HH:MM:SS). Defaults to current time.")
    parser.add_argument("--resolution", type=int, default=5, help="Data resolution in minutes (e.g., 1, 5, 60).")
    parser.add_argument("--window", type=int, default=10, help="Number of candles to check on each side for a pivot.")
    parser.add_argument("--tolerance-percent", type=float, default=0.5, help="The percentage tolerance to cluster potential levels.")
    parser.add_argument("--min-touches", type=int, default=3, help="The minimum number of times a level must be touched to be significant.")
    parser.add_argument("--update-settings", action='store_true', help="If set, automatically update the price_alert_settings.py file.")
    args = parser.parse_args()

    # --- Handle default arguments ---
    end_time_str = args.end_time if args.end_time else datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    run_sr_detection_for_symbols(
        symbols=args.symbols,
        start_time=args.start_time,
        end_time=end_time_str,
        resolution=args.resolution,
        window=args.window,
        tolerance_percent=args.tolerance_percent,
        min_touches=args.min_touches,
        update_settings=args.update_settings
    )


if __name__ == "__main__":
    main()
