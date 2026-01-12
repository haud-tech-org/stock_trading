import argparse
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import logging
import glob
import pytz
from dataclasses import asdict
import sys
from typing import Optional

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Project Imports ---
from src.stockreports.utils.data_utils import fetch_intraday_data, TIMEZONE_STR, SESSIONS
from src.stockreports.config import loader
from src.stockreports.config.signal_settings import APPROACH_CONFIG
from src.stockreports.config.validation_settings import VALIDATION_PERIOD_MINUTES, MAX_TIME_TO_TRIGGER_MINUTES
from src.stockreports.utils.report_utils import get_report_directory, get_default_thresholds
from src.stockreports.alert.model.models import ProfitabilityReport, Trade
from src.stockreports.utils.alert_utils import calculate_suggested_prices, get_primary_suggested_price


def calculate_performance_by_approach(trades: list) -> dict:
    """
    Analyzes trades to calculate performance metrics grouped by entry approach.
    """
    if not trades:
        return {}

    # Use pandas for efficient grouping and aggregation
    trades_df = pd.DataFrame([asdict(t) for t in trades])
    
    if 'entry_approach' not in trades_df.columns or trades_df.empty:
        return {}

    # Group by entry approach and calculate stats using named aggregation
    performance_summary = trades_df.groupby('entry_approach').agg(
        min_profit_loss=('actual_profit_loss', 'min'),
        max_profit_loss=('actual_profit_loss', 'max'),
        avg_profit_loss=('actual_profit_loss', 'mean'),
        min_worst_loss_price=('worst_loss_price', 'min'),
        max_worst_loss_price=('worst_loss_price', 'max'),
        avg_worst_loss_price=('worst_loss_price', 'mean'),
        total_trades=('entry_approach', 'count')
    ).to_dict(orient='index')

    # Round the averages for cleaner output
    for approach, stats in performance_summary.items():
        stats['avg_profit_loss'] = round(stats.get('avg_profit_loss', 0), 4)
        stats['avg_worst_loss_price'] = round(stats.get('avg_worst_loss_price', 0), 4)

    return performance_summary


def simulate_individual_profitability(
    alerts: list, 
    trade_data: pd.DataFrame,
    profit_threshold: float,
    loss_threshold: float
) -> ProfitabilityReport:
    """
    Simulates profitability by treating each alert as an independent trade
    and evaluating its outcome within a fixed validation window.
    """
    trades = []
    total_actual_profit_loss = 0
    total_best_profit_price = 0
    total_worst_loss_price = 0
    successful_trades = 0
    failed_trades = 0
    ignored_trades = 0
    trade_counter = 0

    last_trade_end_time = pd.Timestamp.min.tz_localize('UTC')

    alerts_df = pd.DataFrame(alerts)
    
    for i, alert in alerts_df.iterrows():
        entry_signal = alert.get('signal')
        entry_time = alert.get('alert_time')

        # Skip alerts that occur before the last trade's validation window has ended
        if entry_time < last_trade_end_time:
            logging.info(f"Skipping alert at {entry_time} as it falls within the cooldown period of a previous trade (until {last_trade_end_time}).")
            continue

        # Find the candle corresponding to the alert time
        try:
            entry_candle = trade_data.asof(entry_time)
            if pd.isna(entry_candle.name): # Check if asof returned a valid row
                 raise KeyError
        except KeyError:
            logging.warning(f"Could not find data for entry time {entry_time}. Skipping trade.")
            continue
        except Exception as e:
            logging.error(f"Error finding candle for alert at {entry_time}: {e}")
            continue

        # --- Definitive Entry Price & Suggested Price Logic ---
        
        # 1. Determine the definitive entry price for the simulation.
        # This logic handles alerts from both old and new file formats.
        entry_price = None
        if 'performance_suggested_price' in alert and 'structural_suggested_price' in alert:
            # New format: two price fields exist. Use the primary selection logic.
            entry_price = get_primary_suggested_price(alert)
            logging.info(f"Using primary suggested price for entry: {entry_price}")
        elif 'suggested_price' in alert and alert['suggested_price'] is not None:
            # Old format: only the 'suggested_price' field exists. Use it directly.
            entry_price = alert['suggested_price']
            logging.info(f"Using legacy 'suggested_price' for entry: {entry_price}")
        else:
            # Fallback: if no price info exists, calculate it dynamically.
            logging.warning(f"No suggested price found for alert at {entry_time}. Calculating dynamically.")
            perf_price, struct_price = calculate_suggested_prices(entry_signal, entry_time, alert.get('approach'))
            # Create a temporary series to use the selection logic
            temp_alert_row = pd.Series({
                'performance_suggested_price': perf_price,
                'structural_suggested_price': struct_price
            })
            entry_price = get_primary_suggested_price(temp_alert_row)
            logging.info(f"Using dynamically calculated primary price for entry: {entry_price}")

        # If no entry price could be determined, ignore the trade.
        if entry_price is None:
            logging.warning(f"Could not determine a valid entry price for alert at {entry_time}. Ignoring trade.")
            continue

        # --- End of Definitive Entry Logic ---

        # Define the validation window
        validation_start_time = entry_time
        validation_end_time = validation_start_time + pd.Timedelta(minutes=VALIDATION_PERIOD_MINUTES)

        # --- This is the new logic to prevent overlapping trades ---

        initial_validation_window_df = trade_data.loc[validation_start_time:validation_end_time]

        if initial_validation_window_df.empty:
            logging.warning(f"No data found in initial validation window for alert at {entry_time}. Skipping.")
            continue

        # --- New: Find the exact trigger time and adjust the validation window ---
        trigger_timestamp = None

        # Separate the first candle from the rest of the window
        first_candle = initial_validation_window_df.iloc[0]
        remaining_candles = initial_validation_window_df.iloc[1:]

        if entry_signal == 'BUY':
            # 1. Check the first candle's close price
            if first_candle['close'] <= entry_price:
                trigger_timestamp = first_candle.name
            # 2. If not triggered, check the remaining candles' low price
            elif not remaining_candles.empty:
                triggered_in_remaining = remaining_candles[remaining_candles['low'] <= entry_price]
                if not triggered_in_remaining.empty:
                    trigger_timestamp = triggered_in_remaining.index[0]

        elif entry_signal == 'SELL':
            # 1. Check the first candle's close price
            if first_candle['close'] >= entry_price:
                trigger_timestamp = first_candle.name
            # 2. If not triggered, check the remaining candles' high price
            elif not remaining_candles.empty:
                triggered_in_remaining = remaining_candles[remaining_candles['high'] >= entry_price]
                if not triggered_in_remaining.empty:
                    trigger_timestamp = triggered_in_remaining.index[0]

        if trigger_timestamp is None:
            logging.info(f"Trade at {entry_time} for {entry_signal} was IGNORED. Entry price {entry_price} not met in validation window.")
            ignored_trades += 1
            continue

        # --- Moved & Refactored: Check if the trade took too long to trigger ---
        time_to_trigger_minutes = (trigger_timestamp - entry_time).total_seconds() / 60
        if time_to_trigger_minutes > MAX_TIME_TO_TRIGGER_MINUTES:
            logging.info(f"Trade at {entry_time} for {entry_signal} was IGNORED. Time to trigger ({time_to_trigger_minutes:.2f} min) exceeded limit of {MAX_TIME_TO_TRIGGER_MINUTES} min.")
            ignored_trades += 1
            continue
        # --- End of Moved Check ---
        
        logging.info(f"Trade triggered at {trigger_timestamp}. Adjusting validation window.")
        # The new validation window starts from the moment the price was crossed
        validation_window_df = initial_validation_window_df.loc[trigger_timestamp:]
        # --- End of Trigger Time and Window Adjustment ---

        # --- Best Possible Entry/Exit Price & Worst Loss Calculation ---
        best_possible_entry_price = None
        best_possible_exit_price = None
        if entry_signal == 'BUY':
            # For a BUY, the best possible entry is the lowest price in the window.
            best_possible_entry_price = validation_window_df['low'].min()
            # The best possible exit is the highest price in the window.
            best_possible_exit_price = validation_window_df['high'].max()
        elif entry_signal == 'SELL':
            # For a SELL, the best possible entry is the highest price in the window.
            best_possible_entry_price = validation_window_df['high'].max()
            # The best possible exit is the lowest price in the window.
            best_possible_exit_price = validation_window_df['low'].min()

        worst_loss_price = None
        if best_possible_entry_price is not None:
            # This represents the potential loss if the entry was mistimed.
            # It should always be a negative value.
            worst_loss_price = -abs(entry_price - best_possible_entry_price)
        
        best_profit_price = None
        if best_possible_exit_price is not None:
            if entry_signal == 'BUY':
                best_profit_price = best_possible_exit_price - entry_price
            else: # SELL
                best_profit_price = entry_price - best_possible_exit_price
        # --- End of Calculation ---

        # --- New "Take-Profit or Stop-Loss" Exit Logic ---
        exit_time = None
        exit_price = None
        status = "Failed"  # Default to Failed, will be updated if profit target is hit

        if entry_signal == 'BUY':
            profit_target = entry_price + profit_threshold
            loss_target = entry_price - loss_threshold
            
            # Find the first candle to hit either target
            for time, candle in validation_window_df.iterrows():
                # Check for loss first
                if candle['low'] <= loss_target:
                    exit_time = time
                    exit_price = loss_target # Exit at the target price
                    status = "Failed"
                    break # Exit the loop
                # Check for profit
                if candle['high'] >= profit_target:
                    exit_time = time
                    exit_price = profit_target # Exit at the target price
                    status = "Success"
                    break # Exit the loop

        elif entry_signal == 'SELL':
            profit_target = entry_price - profit_threshold
            loss_target = entry_price + loss_threshold

            # Find the first candle to hit either target
            for time, candle in validation_window_df.iterrows():
                # Check for loss first
                if candle['high'] >= loss_target:
                    exit_time = time
                    exit_price = loss_target # Exit at the target price
                    status = "Failed"
                    break # Exit the loop
                # Check for profit
                if candle['low'] <= profit_target:
                    exit_time = time
                    exit_price = profit_target # Exit at the target price
                    status = "Success"
                    break # Exit the loop

        # If no target was hit, the trade times out and exits at the last candle's close
        if exit_time is None:
            exit_candle = validation_window_df.iloc[-1]
            exit_price = exit_candle['close']
            exit_time = exit_candle.name
            status = "Failed" # It remains a failed trade
            logging.info(f"Trade timed out at {exit_time}. Exiting at close price {exit_price}.")
        else:
            logging.info(f"Trade exited at {exit_time} with status '{status}' at price {exit_price}.")
        
        # We need the exit_candle for later calculations
        exit_candle = trade_data.asof(exit_time)
        # --- End of New Exit Logic ---

        # --- Calculate Durations ---
        time_in_trade_minutes = None
        if exit_time and pd.notna(exit_time) and trigger_timestamp and pd.notna(trigger_timestamp):
            time_in_trade_minutes = (exit_time - trigger_timestamp).total_seconds() / 60
        # --- End of Duration Calculation ---

        # --- Definitive Exit Suggested Price Logic ---
        exit_signal = 'SELL' if entry_signal == 'BUY' else 'BUY'

        # Calculate final profit/loss based on the determined exit
        if entry_signal == 'BUY':
            actual_profit_loss = exit_price - entry_price
        else: # SELL
            actual_profit_loss = entry_price - exit_price
        
        trade_counter += 1
        # Create and append the trade object
        trade = Trade(
            trade_index=trade_counter,
            entry_signal=entry_signal,
            entry_price=entry_price,
            entry_timestamp=entry_time.isoformat(),
            entry_approach=alert.get('approach'),
            exit_signal=exit_signal,
            exit_price=exit_price,
            exit_timestamp=exit_time.isoformat(),
            exit_approach='VALIDATION_EXIT',
            actual_profit_loss=actual_profit_loss,
            status=status,
            entry_source_symbol=alert.get('symbol'),
            exit_source_symbol='SYNTHETIC',
            entry_signal_status=status,
            exit_signal_status='N/A',
            improvement_suggestion='N/A',
            best_possible_entry_price=best_possible_entry_price,
            best_possible_exit_price=best_possible_exit_price,
            worst_loss_price=worst_loss_price,
            best_profit_price=best_profit_price,
            trigger_timestamp=trigger_timestamp.isoformat() if trigger_timestamp else None,
            time_to_trigger_minutes=time_to_trigger_minutes,
            time_in_trade_minutes=time_in_trade_minutes
        )
        trades.append(trade)

        # --- Aggregate Results ---
        total_actual_profit_loss += actual_profit_loss
        if best_profit_price is not None:
            total_best_profit_price += best_profit_price
        if worst_loss_price is not None:
            total_worst_loss_price += worst_loss_price
            
        if status == "Success":
            successful_trades += 1
        elif status == "Failed":
            failed_trades += 1
        # --- End Aggregation ---

        # --- New: Update the cooldown period based on the actual exit time ---
        if exit_time:
            last_trade_end_time = exit_time
        # --- End of New Cooldown Logic ---

    total_trades = successful_trades + failed_trades # Only count triggered trades
    success_rate = f"{(successful_trades / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%"
    failure_rate = f"{(failed_trades / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%"

    return ProfitabilityReport(
        total_trades=total_trades,
        successful_trades=successful_trades,
        failed_trades=failed_trades,
        ignored_trades=ignored_trades,
        success_rate=success_rate,
        failure_rate=failure_rate,
        total_actual_profit_loss=total_actual_profit_loss,
        total_best_profit_price=total_best_profit_price,
        total_worst_loss_price=total_worst_loss_price,
        trades=trades
    )


def run_individual_trade_simulation(
    execution_symbol: str, 
    alert_sources: list, 
    date_str: str, 
    mode: str = 'deployment',
    profit_threshold: Optional[float] = None,
    loss_threshold: Optional[float] = None
):
    """
    Runs a profitability simulation for a single day and a specific scenario.

    This script fetches all alerts for a given day from various sources, then
    simulates trades on a single execution symbol based on those alerts. The
    simulation's behavior (take-profit and stop-loss) is defined by the
    profit and loss thresholds.

    The resulting daily report is saved to a scenario-specific directory,
    e.g., `reports/consolidated/deployment/profit_3.0_loss_3.0/`. This allows
    for easy aggregation by the `consolidate_reports.py` script.

    It can be run independently for debugging or testing a single day's performance.

    Usage Examples:

    1. Simplified - Run for a specific date with default thresholds:
       python3 -m src.tools.centralized_report_generator.individual_trade_simulator \\
           --execution-symbol 41I1G1000 \\
           --alert-sources VN30 \\
           --date 2026-01-08

    2. Full Arguments - Run for a specific date with custom thresholds and mode:
       python3 -m src.tools.centralized_report_generator.individual_trade_simulator \\
           --execution-symbol 41I1G1000 \\
           --alert-sources VN30 41I1G1000 \\
           --date 2026-01-08 \\
           --mode development \\
           --profit-threshold 5.0 \\
           --loss-threshold 2.5
    """
    # --- Use the centralized function to ensure thresholds are valid ---
    profit_threshold, loss_threshold = get_default_thresholds(profit_threshold, loss_threshold)

    # Correctly define project_root by navigating up from the current file's location
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    base_reports_dir = os.path.join(project_root, "reports")
    
    # --- 1. Load and Combine Alerts ---
    all_alerts = []
    date_file_str = date_str.replace('-', '')
    
    for source_symbol in alert_sources:
        # Construct the path to the specific mode directory (deployment or development)
        # --- FIX: Use base_reports_dir which is correctly defined ---
        source_dir = os.path.join(base_reports_dir, source_symbol, mode)
        
        # Check if the specific mode directory exists before searching for alerts
        if not os.path.isdir(source_dir):
            logging.warning(f"Directory not found for source '{source_symbol}' with mode '{mode}': {source_dir}. Skipping.")
            continue

        glob_pattern = os.path.join(source_dir, "**", f"alert_notification_{date_file_str}.json")
        alert_files = glob.glob(glob_pattern, recursive=True)
        
        if not alert_files:
            logging.warning(f"No alert files found for {source_symbol} on {date_str} in {source_dir}. Skipping.")
            continue

        for alert_file_path in alert_files:
            if os.path.exists(alert_file_path):
                try:
                    with open(alert_file_path, 'r') as f:
                        content = json.load(f)
                        
                        # The alerts might be under a key (e.g., 'alerts') or be the root object
                        alerts = []
                        if isinstance(content, dict) and 'alerts' in content and isinstance(content['alerts'], list):
                            alerts = content['alerts']
                        elif isinstance(content, list):
                            alerts = content
                        else:
                            logging.warning(f"Alerts in {alert_file_path} are not in a recognized list format. Skipping file.")
                            continue

                        # --- Fix: Inject the source symbol and approach into each alert ---
                        # Extract approach from the file path (e.g., .../strong_candle/alert.json -> strong_candle)
                        parent_dir_name = os.path.basename(os.path.dirname(alert_file_path))

                        for alert in alerts:
                            if 'approach' not in alert or not alert['approach']:
                                alert['approach'] = parent_dir_name
                        # --- End of Fix ---
                        all_alerts.extend(alerts)
                        logging.info(f"Loaded {len(alerts)} alerts from {alert_file_path}")
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode JSON from {alert_file_path}. Skipping.")
                except Exception as e:
                    logging.error(f"An unexpected error occurred while processing {alert_file_path}: {e}")

    if not all_alerts:
        logging.error("No alerts found for any of the specified sources. Aborting simulation.")
        return

    from dateutil import parser as date_parser
    parsed_alerts = []
    for alert in all_alerts:
        try:
            alert['alert_time'] = date_parser.isoparse(alert['alert_time'])
            parsed_alerts.append(alert)
        except (date_parser.ParserError, TypeError):
            logging.warning(f"Could not parse alert_time '{alert.get('alert_time')}'. Skipping this alert.")
    
    parsed_alerts.sort(key=lambda x: x['alert_time'])
    
    # --- Deduplicate alerts by timestamp, keeping the first one ---
    final_alerts = []
    processed_timestamps = set()
    for alert in parsed_alerts:
        if alert['alert_time'] not in processed_timestamps:
            final_alerts.append(alert)
            processed_timestamps.add(alert['alert_time'])
            
    all_alerts = final_alerts
    
    logging.info(f"Total of {len(all_alerts)} unique, sorted alerts from all sources will be simulated individually.")

    # --- 2. Load Price Data for the Execution Symbol ---
    settings = loader.get_settings()
    simulation_date = datetime.strptime(date_str, '%Y-%m-%d')
    market_tz = pytz.timezone(TIMEZONE_STR)
    
    all_starts = [times['start'] for times in SESSIONS.values()]
    all_ends = [times['end'] for times in SESSIONS.values()]
    start_time_str = min(all_starts)
    end_time_str = max(all_ends)
    start_h, start_m = map(int, start_time_str.split(':'))
    end_h, end_m = map(int, end_time_str.split(':'))

    from_dt = market_tz.localize(simulation_date.replace(hour=start_h, minute=start_m, second=0))
    to_dt = from_dt.replace(hour=end_h, minute=end_m, second=1)
    from_timestamp = int(from_dt.timestamp())
    to_timestamp = int(to_dt.timestamp())

    raw_data = fetch_intraday_data(execution_symbol, from_timestamp, to_timestamp)

    if settings.SAVE_DEV_API_RESPONSE_TO_FILE and raw_data and raw_data.get('s') == 'ok':
        data_path = os.path.join(project_root, settings.DATA_DIR, execution_symbol)
        os.makedirs(data_path, exist_ok=True)
        file_date_str = simulation_date.strftime('%y%m%d')
        file_path = os.path.join(data_path, f"{execution_symbol.lower()}_response_{file_date_str}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(raw_data, f, indent=4)
            logging.info(f"Successfully saved simulation source data to {file_path}")
        except IOError as e:
            logging.error(f"Failed to save simulation source data to {file_path}: {e}")
    
    price_data_df = pd.DataFrame()
    if raw_data and raw_data.get('s') == 'ok':
        keys = ["t", "o", "h", "l", "c", "v"]
        min_len = min(len(raw_data.get(k, [])) for k in keys)
        if min_len > 0:
            price_data_df = pd.DataFrame({
                "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
                "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
                "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
                "volume": raw_data["v"][:min_len],
            })
            price_data_df['time'] = price_data_df['time'].dt.tz_localize('UTC').dt.tz_convert(market_tz)
            price_data_df = price_data_df.set_index('time')

    if price_data_df.empty:
        logging.error(f"Could not load price data for execution symbol '{execution_symbol}' on {date_str}. Aborting.")
        return

    # --- 3. Run Simulation ---
    summary = simulate_individual_profitability(
        alerts=all_alerts,
        trade_data=price_data_df,
        profit_threshold=profit_threshold,
        loss_threshold=loss_threshold
    )

    # --- 4. Generate and Save Report ---
    # --- New: Use the utility function to get the correct output directory ---
    output_dir = get_report_directory(
        base_dir=base_reports_dir,
        report_type="consolidated",
        mode=mode,
        profit_threshold=profit_threshold,
        loss_threshold=loss_threshold
    )
    # --- End New ---
    os.makedirs(output_dir, exist_ok=True)
    
    file_date_str = date_str.replace('-', '')
    output_filename = f"simulation_summary_individual_trade_{execution_symbol}_{file_date_str}.json"
    output_path = os.path.join(output_dir, output_filename)

    try:
        with open(output_path, 'w') as f:
            summary_dict = asdict(summary)
            
            # --- New: Calculate and add performance by approach ---
            performance_by_approach = calculate_performance_by_approach(summary.trades)
            summary_dict['performance_by_approach'] = performance_by_approach
            # --- End of New Section ---

            summary_dict['app_config'] = APPROACH_CONFIG
            # --- Updated: Reflect the actual thresholds used in the simulation ---
            validation_config = {
                "VALIDATION_PERIOD_MINUTES": VALIDATION_PERIOD_MINUTES,
                "VALIDATION_PRICE_THRESHOLD_PROFIT": profit_threshold,
                "VALIDATION_PRICE_THRESHOLD_LOSS": loss_threshold
            }
            summary_dict['validation_config'] = validation_config
            json.dump(summary_dict, f, indent=4, default=str) # Use default=str to handle datetime
        logging.info(f"Successfully saved individual trade simulation report to {output_path}")
    except Exception as e:
        logging.error(f"Failed to save report to {output_path}: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run an individual trade profitability simulation."
    )
    parser.add_argument(
        "--execution-symbol",
        type=str,
        required=True,
        help="The symbol to simulate trading on (e.g., '41I1FB000')."
    )
    parser.add_argument(
        "--alert-sources",
        nargs='+',
        required=True,
        help="A list of symbols to use as alert sources (e.g., 'VN30' '41I1FB000')."
    )
    parser.add_argument(
        "--date",
        type=str,
        default=datetime.now().strftime('%Y-%m-%d'),
        help="The date for which to run the simulation in YYYY-MM-DD format. Defaults to today."
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=['development', 'deployment'],
        default='deployment',
        help="The run mode ('development' or 'deployment'). Defaults to 'deployment'."
    )
    # --- New arguments for running specific scenarios ---
    parser.add_argument(
        "--profit-threshold",
        type=float,
        default=None,
        help="The take-profit threshold for the simulation. Overrides settings file."
    )
    parser.add_argument(
        "--loss-threshold",
        type=float,
        default=None,
        help="The stop-loss threshold for the simulation. Overrides settings file."
    )

    args = parser.parse_args()

    run_individual_trade_simulation(
        execution_symbol=args.execution_symbol,
        alert_sources=args.alert_sources,
        date_str=args.date,
        mode=args.mode,
        profit_threshold=args.profit_threshold,
        loss_threshold=args.loss_threshold
    )
