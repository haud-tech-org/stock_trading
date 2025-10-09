import pandas as pd
import logging
from datetime import timedelta

from src.stockreports.alert.model.models import AlertData
from src.stockreports.config import validation_settings

# Get the minimum expected profit from settings, with a default of 2.0 if not set or None.
MIN_PROFIT_LOSS = getattr(validation_settings, 'MIN_EXPECTED_PROFIT_LOSS', 2.0)
if MIN_PROFIT_LOSS is None:
    MIN_PROFIT_LOSS = 2.0

def calculate_alert_performance(alert: AlertData, historical_data: pd.DataFrame, validation_period_minutes: int) -> AlertData:
    """
    Calculates the profit/loss and status of an alert by finding the best possible
    outcome within a specified future time window.

    Args:
        alert: The AlertData object to be validated.
        historical_data: The full DataFrame of historical price data, indexed by time.
        validation_period_minutes: The time in minutes to look ahead for performance calculation.

    Returns:
        The updated AlertData object with profit_loss, status, and validation details populated.
    """
    # Define the validation window
    start_time = alert.alert_time
    end_time = start_time + timedelta(minutes=validation_period_minutes)
    
    # Ensure the historical data has a DatetimeIndex for efficient slicing
    if not isinstance(historical_data.index, pd.DatetimeIndex):
        historical_data = historical_data.set_index('time')

    # Filter the data to the validation window
    validation_window_df = historical_data.loc[start_time:end_time]
    
    if validation_window_df.empty:
        logging.warning(f"No data available in validation window for alert {alert.id}. Cannot calculate performance.")
        alert.status = "Inconclusive"
        return alert

    validation_price = None
    validation_price_time = None
    profit_loss = 0.0

    if alert.signal.upper() == 'BUY':
        # For a BUY signal, find the highest high in the window
        peak_candle = validation_window_df.loc[validation_window_df['high'].idxmax()]
        validation_price = peak_candle['high']
        validation_price_time = peak_candle.name
        
        # Profit is the difference between the peak and the alert price
        profit_loss = validation_price - alert.alert_price
        if profit_loss >= MIN_PROFIT_LOSS:
            alert.status = 'Success'
        else:
            alert.status = 'Failed'

    elif alert.signal.upper() == 'SELL':
        # For a SELL signal, find the lowest low in the window
        bottom_candle = validation_window_df.loc[validation_window_df['low'].idxmin()]
        validation_price = bottom_candle['low']
        validation_price_time = bottom_candle.name
        
        # Profit is the difference between the alert price and the bottom
        profit_loss = alert.alert_price - validation_price
        if profit_loss >= MIN_PROFIT_LOSS:
            alert.status = 'Success'
        else:
            alert.status = 'Failed'

    # Populate the alert object with validation results
    alert.profit_loss = round(profit_loss, 2)
    alert.period_time = validation_period_minutes
    alert.validation_price_time = validation_price_time
    alert.min_expected_profit_loss = MIN_PROFIT_LOSS
    
    if validation_price_time:
        time_diff = validation_price_time - alert.alert_time
        alert.time_to_best_price = int(time_diff.total_seconds() / 60)

    logging.info(
        f"Validation for alert {alert.id} ({alert.signal}): "
        f"Profit/Loss = {alert.profit_loss:.2f}, Status = {alert.status}, "
        f"Time to best price = {alert.time_to_best_price} mins"
    )

    return alert
