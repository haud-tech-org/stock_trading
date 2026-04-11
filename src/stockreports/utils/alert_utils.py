# src/stockreports/utils/alert_utils.py
import logging
import pandas as pd
from typing import Optional, Tuple, Union
from datetime import datetime
import importlib

from src.stockreports.config.validation_settings import VALIDATION_MIN_PROFIT_FOR_SUCCESS, VALIDATION_MAGNITUDE_PROFIT_FACTOR
from src.stockreports.alert.common.constants import Trend, Signal
from src.stockreports.config import price_alert_settings, settings, loader
from src.stockreports.data_services import DataServiceOrchestrator
from src.stockreports.alert.model.models import AlertData

logger = logging.getLogger(__name__)
data_provider_settings = loader.get_data_provider_settings()

def get_reversal_trend(trend: Trend) -> Trend:
    """
    Returns the reversal of the given trend.
    DOWNTREND -> UPTREND, UPTREND -> DOWNTREND, else NEUTRAL.
    """
    if trend == Trend.DOWNTREND:
        return Trend.UPTREND
    elif trend == Trend.UPTREND:
        return Trend.DOWNTREND
    else:
        return Trend.NEUTRAL

def get_reversal_signal(signal: Signal) -> Signal:
    """
    Returns the reversal of the given signal.
    BUY -> SELL, SELL -> BUY, else NEUTRAL.
    """
    if signal == Signal.BUY:
        return Signal.SELL
    elif signal == Signal.SELL:
        return Signal.BUY
    else:
        return Signal.NEUTRAL

def get_suggested_take_profit(magnitude: float) -> float:
    """
    Returns the suggested take-profit (success) threshold for the given alert.
    Logic:
        - If alert_data.magnitude is set, use max(magnitude * VALIDATION_MAGNITUDE_PROFIT_FACTOR, VALIDATION_MIN_PROFIT_FOR_SUCCESS)
        - Otherwise, use VALIDATION_MIN_PROFIT_FOR_SUCCESS
    Args:
        alert_data (AlertData): The alert data object (can be updated by logic if needed)
    Returns:
        float: The suggested take-profit threshold for this alert
    """
    return max(abs(magnitude * VALIDATION_MAGNITUDE_PROFIT_FACTOR), VALIDATION_MIN_PROFIT_FOR_SUCCESS)

def _apply_price_offset(base_price: float, adjustment: float, signal: str, min_offset: float, max_offset: float) -> float:
    """
    Clamps a positive adjustment value and applies it to the base price based on the signal.
    """
    # Get the additional fixed offset and add it to the adjustment
    fixed_offset = getattr(price_alert_settings, 'PRICE_LEVEL_OFFSET_FIXED', 0.0)
    total_adjustment = adjustment + fixed_offset

    # Clamp the total adjustment between the min and max offsets
    clamped_adjustment = max(min(total_adjustment, max_offset), min_offset)
    
    if signal.upper() == 'BUY':
        # For BUY, subtract the adjustment for a lower, safer entry price
        suggested_price = base_price - clamped_adjustment
        # Ensure the final price is not higher than the base price
        final_price = min(suggested_price, base_price)
    else: # For 'SELL'
        # For SELL, add the adjustment for a higher, safer entry price
        suggested_price = base_price + clamped_adjustment
        # Ensure the final price is not lower than the base price
        final_price = max(suggested_price, base_price)

    return round(final_price, 1)


def get_execution_symbol() -> str:
    """
    Retrieves the primary execution symbol from the settings.
    """
    return settings.SYMBOLS[0]

def calculate_suggested_prices(signal: str, alert_time: pd.Timestamp, approach: Optional[str] = None, symbol: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates both performance-based and structural suggested prices.

    Args:
        signal (str): The alert signal ('BUY' or 'SELL').
        alert_time (pd.Timestamp): The timestamp of the alert.
        approach (Optional[str]): The name of the alert approach.
        symbol (Optional[str]): The trading symbol. If provided, overrides the default execution symbol.
                               If None, uses the primary execution symbol from settings.

    Returns:
        Tuple[Optional[float], Optional[float]]: A tuple containing:
            - performance_suggested_price
            - structural_suggested_price
    """
    execution_symbol = symbol if symbol is not None else get_execution_symbol()
    performance_price = None
    structural_price = None

    # *** DEFENSIVE FIX: Ensure alert_time is pd.Timestamp (not int) ***
    # alert_time needs to support arithmetic operations with pd.Timedelta
    if isinstance(alert_time, int):
        # Convert Unix timestamp to pd.Timestamp
        alert_time = pd.Timestamp(alert_time, unit='s', tz='UTC')
        logger.warning(
            f"Converted alert_time from int Unix timestamp to Timestamp. "
            f"This indicates upstream data type issue."
        )
    elif not isinstance(alert_time, pd.Timestamp):
        # Try to convert other types
        try:
            alert_time = pd.Timestamp(alert_time)
            logger.warning(
                f"Converted alert_time from {type(alert_time).__name__} to Timestamp."
            )
        except Exception as e:
            logger.error(f"Unable to convert alert_time to Timestamp: {e}. Type: {type(alert_time)}")
            return None, None

    # --- Unified Data Fetch ---
    # Fetch a single, wider window that covers both performance (T) and structural (T, T-1) needs.
    start_fetch_time = alert_time - pd.Timedelta(minutes=5)
    end_fetch_time = alert_time + pd.Timedelta(minutes=2)
    
    orchestrator = DataServiceOrchestrator()
    market_data = orchestrator.fetch_and_process(
        symbol=execution_symbol,
        start_time=start_fetch_time,
        end_time=end_fetch_time,
        resolution=data_provider_settings.MONITORING_DATA_RESOLUTION_MINUTES
    )

    # If no data is fetched, we can't proceed with either calculation.
    if market_data is None or market_data.empty:
        logger.warning(f"Could not get market data for any price calculation at {alert_time}.")
        return None, None

    # --- Common Settings ---
    importlib.reload(price_alert_settings)
    max_offset = getattr(price_alert_settings, 'MAX_PRICE_ADJUSTMENT_OFFSET')
    min_offset = getattr(price_alert_settings, 'MIN_PRICE_ADJUSTMENT_OFFSET')

    df_indexed = market_data

    # --- Performance-Based Logic ---
    if approach:
        performance_config = getattr(price_alert_settings, 'PERFORMANCE_BY_APPROACH', {})
        approach_perf = performance_config.get(approach.upper())

        if approach_perf and 'avg_worst_loss_price' in approach_perf:
            try:
                current_candle = df_indexed.loc[alert_time]
                close_price = current_candle['close']
                # Ensure adjustment is always positive, _apply_price_offset handles direction
                adjustment = abs(approach_perf['avg_worst_loss_price'])
                
                performance_price = _apply_price_offset(close_price, adjustment, signal, min_offset, max_offset)
                logger.info(f"Calculated performance price for '{approach}': {performance_price}")

            except Exception as e:
                logger.error(f"Error during performance price calculation: {e}", exc_info=True)

    # --- Structural Logic ---
    try:
        current_candle_index = df_indexed.index.get_loc(alert_time)
        
        # We need at least 3 candles for the new logic (current + 2 previous)
        if current_candle_index >= 2:
            current_candle = df_indexed.iloc[current_candle_index]
            close_price = current_candle['close']

            # Get the last 3 candles (T-2, T-1, T)
            last_3_candles = df_indexed.iloc[current_candle_index - 2 : current_candle_index + 1]

            # The 'adjustment' for structural price is based on the last 3 candles' range.
            if signal.upper() == 'BUY':
                # For BUY, find the lowest point in the last 3 candles as support
                lowest_low = last_3_candles['low'].min()
                adjustment = abs(close_price - lowest_low)
            elif signal.upper() == 'SELL':
                # For SELL, find the highest point in the last 3 candles as resistance
                highest_high = last_3_candles['high'].max()
                adjustment = abs(highest_high - close_price)
            else:
                adjustment = 0

            # Apply the same offset logic as the performance price
            structural_price = _apply_price_offset(close_price, adjustment, signal, min_offset, max_offset)
            logger.info(f"Calculated structural price: {structural_price}")
        else:
            logger.warning("Not enough data for structural price (needs at least 3 candles).")
    except Exception as e:
        logger.error(f"Error during structural price calculation: {e}", exc_info=True)

    return performance_price, structural_price


def get_primary_suggested_price(
    alert_row: Union[AlertData, pd.Series, dict]
) -> Optional[float]:
    """
    Selects the primary suggested price based on the USE_PERFORMANCE_BY_APPROACH flag.

    Supports multiple input types for flexibility:
    - AlertData: Refactored alert objects (recommended)
    - pd.Series: Legacy DataFrame rows (backward compatibility)
    - dict: Legacy dictionary format (backward compatibility)

    Args:
        alert_row (Union[AlertData, pd.Series, dict]): Alert data containing
                               'performance_suggested_price' and 'structural_suggested_price' fields.

    Returns:
        Optional[float]: The chosen suggested price, or None if neither is available.
    """
    # Get the price fields based on input type
    if isinstance(alert_row, AlertData):
        performance_price = alert_row.performance_suggested_price
        structural_price = alert_row.structural_suggested_price
    else:
        # Works for both pd.Series and dict
        performance_price = alert_row.get('performance_suggested_price')
        structural_price = alert_row.get('structural_suggested_price')

    # Reload settings to ensure the flag is current
    importlib.reload(price_alert_settings)
    
    if price_alert_settings.USE_PERFORMANCE_BY_APPROACH:
        # Check if performance_price is valid (not None and not NaN)
        if performance_price is not None and (isinstance(performance_price, (int, float)) and not pd.isna(performance_price)):
            return performance_price
        else:
            logger.warning("Performance price preferred but is None/NaN; falling back to structural price.")
            return structural_price
    else:
        return structural_price


def adjust_price_by_signal(price: float, signal: str) -> float:
    """
    Adjusts a price based on the signal (BUY or SELL) using a configured offset.

    The offset is retrieved from `price_alert_settings.PRICE_LEVEL_OFFSET_FIXED`.
    For 'BUY' signals, the offset is subtracted.
    For 'SELL' signals (or any other signal), the offset is added.

    Args:
        price (float): The initial price to adjust.
        signal (str): The signal ('BUY' or 'SELL').

    Returns:
        float: The adjusted price.
    """
    price_level = getattr(price_alert_settings, 'PRICE_LEVEL_OFFSET_FIXED', 0.0)
    if signal.upper() == 'BUY':
        return price - price_level
    return price + price_level


def is_in_cooldown(
    new_alert_time: datetime,
    new_signal: Signal,
    latest_alert: Optional[AlertData],
    cooldown_window: int
) -> bool:
    """
    Checks if a new alert is within the cooldown period of the last alert.

    Args:
        new_alert_time: The timestamp of the potential new alert.
        new_signal: The signal (BUY/SELL) of the potential new alert.
        latest_alert: The last recorded AlertData object.
        cooldown_window: The cooldown period in minutes.

    Returns:
        True if the new alert should be skipped due to cooldown, False otherwise.
    """
    if latest_alert is None:
        return False

    time_since_last_alert = (new_alert_time - latest_alert.alert_time).total_seconds() / 60
    is_in_cooldown_period = time_since_last_alert < cooldown_window
    is_same_signal = new_signal == latest_alert.signal

    return is_in_cooldown_period and is_same_signal
