import pandas as pd
from typing import List, Dict, Any
import pytz
from datetime import timedelta
from src.stockreports.utils.time_utils import get_market_timezone_str
from src.stockreports.alert.model.models import Trade, ProfitabilityReport
from src.stockreports.config.validation_settings import VALIDATION_PERIOD_MINUTES, VALIDATION_PRICE_THRESHOLD_PROFIT

TIMEZONE = pytz.timezone(get_market_timezone_str())

def calculate_trade_metrics(trade: Dict[str, Any], trade_data: pd.DataFrame) -> Dict[str, Any]:
    """
    Calculates advanced metrics for a single trade, such as best/worst profit
    and signal status, based on historical price data.

    Args:
        trade: A dictionary representing a single trade, containing timestamps and prices.
        trade_data: A DataFrame of historical price data for the relevant day.

    Returns:
        A dictionary with the newly calculated metrics.
    """
    entry_time = trade.get('entry_timestamp')
    exit_time = trade.get('exit_timestamp')
    entry_price = trade.get('entry_price')
    exit_price = trade.get('exit_price')
    current_position = trade.get('entry_signal') # 'BUY' or 'SELL'
    exit_signal = trade.get('exit_signal')

    entry_best_profit, entry_worst_loss = None, None
    exit_best_profit, exit_worst_loss = None, None
    entry_signal_status, exit_signal_status = "Unknown", "Unknown"
    improvement_suggestion = "None"

    if not all([entry_time, exit_time, entry_price, exit_price, current_position, exit_signal]):
        return {}

    # --- Calculate for Entry Signal ---
    entry_validation_end = entry_time + timedelta(minutes=VALIDATION_PERIOD_MINUTES)
    
    # The trade_data.index is timezone-aware. We must ensure our slicing keys are also aware.
    # The timestamps from alerts should already be aware, but we ensure it here for robustness.
    if entry_time.tzinfo is None:
        entry_time = TIMEZONE.localize(entry_time)
    
    entry_validation_end = min(entry_validation_end, trade_data.index[-1])
    entry_window_data = trade_data.loc[entry_time:entry_validation_end]

    if not entry_window_data.empty:
        max_price_in_entry_window = entry_window_data['high'].max()
        min_price_in_entry_window = entry_window_data['low'].min()

        if current_position == 'BUY':
            entry_best_profit = max_price_in_entry_window - entry_price
            entry_worst_loss = min_price_in_entry_window - entry_price
        else:  # SELL
            entry_best_profit = entry_price - min_price_in_entry_window
            entry_worst_loss = entry_price - max_price_in_entry_window
        
        if entry_best_profit is not None and entry_best_profit >= VALIDATION_PRICE_THRESHOLD_PROFIT:
            entry_signal_status = "Success"
        else:
            entry_signal_status = "Failed"

    # --- Calculate for Exit Signal ---
    exit_validation_end = exit_time + timedelta(minutes=VALIDATION_PERIOD_MINUTES)

    if exit_time.tzinfo is None:
        exit_time = TIMEZONE.localize(exit_time)

    exit_validation_end = min(exit_validation_end, trade_data.index[-1])
    exit_window_data = trade_data.loc[exit_time:exit_validation_end]

    if not exit_window_data.empty:
        max_price_in_exit_window = exit_window_data['high'].max()
        min_price_in_exit_window = exit_window_data['low'].min()

        if exit_signal == 'BUY': # Closing a SELL trade
            exit_best_profit = exit_price - min_price_in_exit_window
            exit_worst_loss = exit_price - max_price_in_exit_window
        else: # Closing a BUY trade
            exit_best_profit = max_price_in_exit_window - exit_price
            exit_worst_loss = min_price_in_exit_window - exit_price

        if exit_best_profit is not None and exit_best_profit >= VALIDATION_PRICE_THRESHOLD_PROFIT:
            exit_signal_status = "Success"
        else:
            exit_signal_status = "Failed"

    # --- Improvement Suggestion Logic ---
    profit_loss = trade.get('profit_loss', 0)
    if profit_loss <= 0:
        if entry_signal_status == "Failed":
            improvement_suggestion = f"Improve entry signal: {trade.get('entry_approach', 'N/A')}"
        elif exit_signal_status == "Failed":
            improvement_suggestion = f"Improve exit signal: {trade.get('exit_approach', 'N/A')}"
        else:
            improvement_suggestion = "Review trade timing; both signals were individually successful."

    return {
        "entry_best_profit": entry_best_profit,
        "entry_worst_loss": entry_worst_loss,
        "exit_best_profit": exit_best_profit,
        "exit_worst_loss": exit_worst_loss,
        "entry_signal_status": entry_signal_status,
        "exit_signal_status": exit_signal_status,
        "improvement_suggestion": improvement_suggestion
    }

def simulate_profitability(alerts: List[Dict[str, Any]], trade_data: pd.DataFrame = None) -> ProfitabilityReport:
    """
    Simulates trading based on a list of alerts to calculate overall profitability.

    Args:
        alerts: A list of alert dictionaries, each containing at least
                'alert_time' and 'signal'. If trade_data is not provided,
                it must also contain 'alert_price'.
        trade_data: An optional pandas DataFrame with 'time' and 'close' columns.
                    If provided, prices will be looked up from this dataframe
                    based on the alert's timestamp.

    Returns:
        A ProfitabilityReport object summarizing the simulation results.
    """
    if not alerts:
        return ProfitabilityReport(
            total_trades=0,
            successful_trades=0,
            failed_trades=0,
            success_rate="0.00%",
            failure_rate="0.00%",
            total_profit_loss=0.0,
            trades=[]
        )

    # Sort alerts by alert_time to process them in chronological order
    # The alert_time is expected to be a datetime object
    sorted_alerts = sorted(alerts, key=lambda x: x['alert_time'])

    trades = []
    current_position = None
    entry_price = 0
    entry_time = None
    entry_approach = None
    entry_source_symbol = None  # To store the source of the entry signal
    entry_suggested_price = None # To store the suggested price for the entry

    # Prepare trade_data for efficient lookup if provided
    if trade_data is not None:
        if not isinstance(trade_data.index, pd.DatetimeIndex):
            trade_data = trade_data.set_index('time')
        if not trade_data.index.is_monotonic_increasing:
            trade_data = trade_data.sort_index()

    for alert in sorted_alerts:
        signal = alert.get('signal')
        alert_time = alert.get('alert_time')
        # --- FIX: Ensure alert_time is a timezone-aware datetime object ---
        # If it's a string, parse it. This makes the function more robust.
        if isinstance(alert_time, str):
            from dateutil import parser as date_parser
            alert_time = date_parser.isoparse(alert_time)
        # --- END FIX ---
        
        approach = alert.get('approach')
        source_symbol = alert.get('source_symbol')  # Get the source symbol
        suggested_price = alert.get('suggested_price') # Get the suggested price
        
        if trade_data is not None:
            # Find the closest price in time from the trade_data
            # Use asof to find the last known price at or before the alert time
            price_match = trade_data.asof(alert_time)
            if pd.notna(price_match['close']):
                alert_price = price_match['close']
            else:
                # If no price is found (e.g., alert is before first data point), skip it
                continue
        else:
            alert_price = alert.get('alert_price')

        if not signal or alert_price is None or alert_time is None:
            continue

        if current_position is None:
            # Open a new position
            current_position = signal
            entry_price = alert_price
            entry_time = alert_time
            entry_approach = approach
            entry_source_symbol = source_symbol  # Store the entry source
            entry_suggested_price = suggested_price # Store the entry suggested price
        elif signal != current_position:
            # Close the current position (reversal signal)
            if current_position == 'BUY':
                profit_loss = alert_price - entry_price
            else:  # SELL
                profit_loss = entry_price - alert_price

            # --- ENHANCEMENT: Calculate metrics using the new function ---
            trade_metrics = {}
            if trade_data is not None:
                temp_trade_for_metrics = {
                    "entry_timestamp": entry_time,
                    "exit_timestamp": alert_time,
                    "entry_price": entry_price,
                    "exit_price": alert_price,
                    "entry_signal": current_position,
                    "exit_signal": signal,
                    "entry_approach": entry_approach,
                    "exit_approach": approach,
                    "profit_loss": profit_loss
                }
                trade_metrics = calculate_trade_metrics(temp_trade_for_metrics, trade_data)


            trades.append(Trade(
                trade_index=len(trades) + 1,
                entry_signal=current_position,
                entry_price=entry_price,
                entry_timestamp=entry_time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                entry_approach=entry_approach,
                entry_source_symbol=entry_source_symbol,
                entry_suggested_price=entry_suggested_price,
                exit_signal=signal,
                exit_price=alert_price,
                exit_timestamp=alert_time.strftime('%Y-%m-%dT%H:%M:%S%z'),
                exit_approach=approach,
                exit_source_symbol=source_symbol,
                exit_suggested_price=suggested_price,
                profit_loss=profit_loss,
                status="Success" if profit_loss > 0 else "Failed",
                **trade_metrics
            ))

            # Start a new position with the current alert
            current_position = signal
            entry_price = alert_price
            entry_time = alert_time
            entry_approach = approach
            entry_source_symbol = source_symbol  # Start new position with new source
            entry_suggested_price = suggested_price # Start new position with new suggested price

    # Calculate summary statistics
    total_trades = len(trades)
    successful_trades = sum(1 for trade in trades if trade.status == 'Success')
    failed_trades = total_trades - successful_trades
    success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
    failure_rate = (failed_trades / total_trades) * 100 if total_trades > 0 else 0
    total_profit_loss = sum(trade.profit_loss for trade in trades)

    return ProfitabilityReport(
        total_trades=total_trades,
        successful_trades=successful_trades,
        failed_trades=failed_trades,
        success_rate=f"{success_rate:.2f}%",
        failure_rate=f"{failure_rate:.2f}%",
        total_profit_loss=total_profit_loss,
        trades=trades
    )
