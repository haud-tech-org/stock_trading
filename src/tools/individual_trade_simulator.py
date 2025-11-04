import argparse
import json
import os
from datetime import datetime, timedelta
import pandas as pd
import logging
import glob
import pytz
from dataclasses import asdict

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Project Imports ---
from src.stockreports.utils.data_utils import fetch_intraday_data, TIMEZONE_STR, SESSIONS
from src.stockreports.config import loader
from src.stockreports.config.signal_settings import APPROACH_CONFIG
from src.stockreports.config.validation_settings import VALIDATION_PERIOD_MINUTES, VALIDATION_PRICE_THRESHOLD
from src.stockreports.alert.model.models import ProfitabilityReport, Trade
from src.stockreports.utils.alert_utils import calculate_suggested_price


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

    # Group by entry approach and calculate stats
    performance_summary = trades_df.groupby('entry_approach')['profit_loss'].agg(
        min_profit_loss='min',
        max_profit_loss='max',
        avg_profit_loss='mean',
        total_trades='count'
    ).to_dict(orient='index')

    # Round the avg_profit_loss for cleaner output
    for approach, stats in performance_summary.items():
        stats['avg_profit_loss'] = round(stats['avg_profit_loss'], 4)

    return performance_summary


def simulate_individual_profitability(execution_symbol: str, alerts: list, trade_data: pd.DataFrame) -> ProfitabilityReport:
    """
    Simulates profitability by treating each alert as an independent trade
    and evaluating its outcome within a fixed validation window.
    """
    trades = []
    total_profit_loss = 0
    successful_trades = 0
    failed_trades = 0

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
        # 1. Set the actual entry_price for the trade.
        #    Priority: Use price from alert data if it exists, otherwise fallback to candle open.
        if 'price' in alert and alert['price'] is not None:
            entry_price = alert['price']
        else:
            entry_price = entry_candle['open']

        # 2. Determine the entry_suggested_price for analysis.
        #    Priority: Use 'suggested_price' from alert data if symbols match.
        #    Fallback: Calculate it dynamically.
        if alert.get('source_symbol') == execution_symbol and 'suggested_price' in alert and alert['suggested_price'] is not None:
            calculated_entry_suggested_price = alert['suggested_price']
        else:
            # Fallback to dynamic calculation
            calculated_entry_suggested_price = calculate_suggested_price(entry_signal, entry_time, trade_data.reset_index())

        if calculated_entry_suggested_price is None:
            # If suggestion calculation fails or wasn't available, log it.
            logging.warning(f"Could not determine suggested entry price for alert at {entry_time}. It will be null in the report.")
        # --- End of Definitive Entry Logic ---

        # Define the validation window
        validation_start_time = entry_time
        validation_end_time = validation_start_time + pd.Timedelta(minutes=VALIDATION_PERIOD_MINUTES)

        # --- This is the new logic to prevent overlapping trades ---
        # Set the cooldown period. No new trades can start before this time.
        last_trade_end_time = validation_end_time
        # --- End of new logic ---

        validation_window_df = trade_data.loc[validation_start_time:validation_end_time]

        if validation_window_df.empty:
            logging.warning(f"No data found in validation window for alert at {entry_time}. Skipping.")
            continue

        # --- New "Take-Profit or Timeout" Exit Logic ---
        target_reached = False
        if entry_signal == 'BUY':
            if validation_window_df['high'].max() >= entry_price + VALIDATION_PRICE_THRESHOLD:
                target_reached = True
        elif entry_signal == 'SELL':
            if validation_window_df['low'].min() <= entry_price - VALIDATION_PRICE_THRESHOLD:
                target_reached = True

        if target_reached:
            # If the target was met, exit at the BEST price in the window
            status = "Success"
            if entry_signal == 'BUY':
                exit_candle = validation_window_df.loc[validation_window_df['high'].idxmax()]
                exit_price = exit_candle['high']
                exit_time = exit_candle.name
            else:  # SELL
                exit_candle = validation_window_df.loc[validation_window_df['low'].idxmin()]
                exit_price = exit_candle['low']
                exit_time = exit_candle.name
        else:
            # If the target was NOT met, exit at the close of the last candle (timeout)
            status = "Failed"
            exit_candle = validation_window_df.iloc[-1]
            exit_price = exit_candle['close']
            exit_time = exit_candle.name
        
        # --- End of New Exit Logic ---

        # --- Definitive Exit Suggested Price Logic ---
        exit_signal = 'SELL' if entry_signal == 'BUY' else 'BUY'
        calculated_exit_suggested_price = calculate_suggested_price(exit_signal, exit_time, trade_data.reset_index())
        if calculated_exit_suggested_price is None:
            # If calculation fails, use the actual exit price as the suggested one
            calculated_exit_suggested_price = exit_price
        # --- End of Definitive Exit Suggested Price Logic ---

        # Calculate final profit/loss based on the determined exit
        if entry_signal == 'BUY':
            profit_loss = exit_price - entry_price
        else: # SELL
            profit_loss = entry_price - exit_price

        # --- `entry_best_profit` and `entry_worst_loss` on the entry candle ---
        if entry_signal == 'BUY':
            # Best profit is how much it went down (potential for cheaper buy)
            entry_best_profit = entry_price - entry_candle['low']
            # Worst loss is how much it went up against you
            entry_worst_loss = entry_price - entry_candle['high']
        else:  # SELL
            # Best profit is how much it went up (potential for more expensive sell)
            entry_best_profit = entry_candle['high'] - entry_price
            # Worst loss is how much it went down against you
            entry_worst_loss = entry_candle['low'] - entry_price
        
        # --- `exit_best_profit` and `exit_worst_loss` on the exit candle ---
        if exit_signal == 'SELL': # Exiting a BUY trade
            # Best profit is how much it went up (potential for more expensive sell)
            exit_best_profit = exit_candle['high'] - exit_price
            # Worst loss is how much it went down against you
            exit_worst_loss = exit_candle['low'] - exit_price
        else: # BUY (Exiting a SELL trade)
            # Best profit is how much it went down (potential for cheaper buy)
            exit_best_profit = exit_price - exit_candle['low']
            # Worst loss is how much it went up against you
            exit_worst_loss = exit_price - exit_candle['high']
        # --- End of New Calculation ---
        
        # Create and append the trade object
        trade = Trade(
            trade_index=i + 1,
            entry_signal=entry_signal,
            entry_price=entry_price,
            entry_timestamp=entry_time.isoformat(),
            entry_approach=alert.get('approach'),
            exit_signal=exit_signal,
            exit_price=exit_price,
            exit_timestamp=exit_time.isoformat(),
            exit_approach='VALIDATION_EXIT',
            profit_loss=profit_loss,
            status=status,
            entry_source_symbol=alert.get('source_symbol'),
            exit_source_symbol='SYNTHETIC',
            entry_suggested_price=calculated_entry_suggested_price,
            exit_suggested_price=calculated_exit_suggested_price,
            entry_best_profit=entry_best_profit,
            entry_worst_loss=entry_worst_loss,
            exit_best_profit=exit_best_profit,
            exit_worst_loss=exit_worst_loss,
            entry_signal_status=status,
            exit_signal_status='N/A',
            improvement_suggestion='N/A'
        )
        trades.append(trade)

        # --- Aggregate Results ---
        total_profit_loss += profit_loss
        if status == "Success":
            successful_trades += 1
        elif status == "Failed":
            failed_trades += 1
        # --- End Aggregation ---

    total_trades = len(trades)
    success_rate = f"{(successful_trades / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%"
    failure_rate = f"{(failed_trades / total_trades * 100):.2f}%" if total_trades > 0 else "0.00%"

    return ProfitabilityReport(
        total_trades=total_trades,
        successful_trades=successful_trades,
        failed_trades=failed_trades,
        success_rate=success_rate,
        failure_rate=failure_rate,
        total_profit_loss=total_profit_loss,
        trades=trades
    )


def run_individual_trade_simulation(execution_symbol: str, alert_sources: list, date_str: str):
    """
    Runs a profitability simulation using individual alerts to execute trades
    on a single target symbol.
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    reports_dir = os.path.join(project_root, "reports")
    
    # --- 1. Load and Combine Alerts ---
    all_alerts = []
    date_file_str = date_str.replace('-', '')
    
    for source_symbol in alert_sources:
        source_dir = os.path.join(reports_dir, source_symbol, "deployment")
        glob_pattern = os.path.join(source_dir, "**", f"alert_notification_{date_file_str}.json")
        alert_files = glob.glob(glob_pattern, recursive=True)
        
        if not alert_files:
            logging.warning(f"No alert files found for {source_symbol} on {date_str} in {source_dir}. Skipping.")
            continue

        for alert_file_path in alert_files:
            if os.path.exists(alert_file_path):
                try:
                    with open(alert_file_path, 'r') as f:
                        alerts = json.load(f)
                        # --- Fix: Inject the source symbol into each alert ---
                        for alert in alerts:
                            alert['source_symbol'] = source_symbol
                        # --- End of Fix ---
                        all_alerts.extend(alerts)
                        logging.info(f"Loaded {len(alerts)} alerts from {alert_file_path}")
                except json.JSONDecodeError:
                    logging.warning(f"Could not decode JSON from {alert_file_path}. Skipping.")

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
        execution_symbol=execution_symbol,
        alerts=all_alerts,
        trade_data=price_data_df
    )

    # --- 4. Generate and Save Report ---
    output_dir = os.path.join(reports_dir, "consolidated", "deployment")
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
            validation_config = {
                "VALIDATION_PERIOD_MINUTES": VALIDATION_PERIOD_MINUTES,
                "VALIDATION_PRICE_THRESHOLD": VALIDATION_PRICE_THRESHOLD
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
        required=True,
        help="The date to process in YYYY-MM-DD format (e.g., '2025-10-27')."
    )

    args = parser.parse_args()

    run_individual_trade_simulation(
        execution_symbol=args.execution_symbol,
        alert_sources=args.alert_sources,
        date_str=args.date
    )
