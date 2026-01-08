# src/stockreports/utils/alert_utils.py
import logging
import pandas as pd
from typing import Optional, Tuple
# Import the settings to access the performance data
from src.stockreports.config import price_alert_settings, settings
from src.stockreports.utils.historical_data_manager import get_historical_data
import importlib

logger = logging.getLogger(__name__)

def get_execution_symbol() -> str:
    """
    Retrieves the primary execution symbol from the settings.
    """
    return settings.SYMBOLS[0]

def calculate_suggested_prices(signal: str, alert_time: pd.Timestamp, approach: Optional[str] = None) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculates both performance-based and structural suggested prices.

    Args:
        signal (str): The alert signal ('BUY' or 'SELL').
        alert_time (pd.Timestamp): The timestamp of the alert.
        approach (Optional[str]): The name of the alert approach.

    Returns:
        Tuple[Optional[float], Optional[float]]: A tuple containing:
            - performance_suggested_price
            - structural_suggested_price
    """
    execution_symbol = get_execution_symbol()
    performance_price = None
    structural_price = None

    # --- Unified Data Fetch ---
    # Fetch a single, wider window that covers both performance (T) and structural (T, T-1) needs.
    start_fetch_time = alert_time - pd.Timedelta(minutes=5)
    end_fetch_time = alert_time + pd.Timedelta(minutes=1)
    market_data = get_historical_data(execution_symbol, start_fetch_time, end_fetch_time)

    # If no data is fetched, we can't proceed with either calculation.
    if market_data is None or market_data.empty:
        logger.warning(f"Could not get market data for any price calculation at {alert_time}.")
        return None, None

    # --- Performance-Based Logic ---
    if approach:
        importlib.reload(price_alert_settings)
        performance_config = getattr(price_alert_settings, 'PERFORMANCE_BY_APPROACH', {})
        approach_perf = performance_config.get(approach.upper())

        if approach_perf and 'avg_worst_loss_price' in approach_perf:
            try:
                current_candle = market_data.set_index('time').loc[alert_time]
                adjustment = approach_perf['avg_worst_loss_price']
                close_price = current_candle['close']
                
                if signal.upper() == 'BUY':
                    performance_price = round(close_price - adjustment, 1)
                elif signal.upper() == 'SELL':
                    performance_price = round(close_price + adjustment, 1)
                logger.info(f"Calculated performance price for '{approach}': {performance_price}")
            except Exception as e:
                logger.error(f"Error during performance price calculation: {e}", exc_info=True)

    # --- Structural Logic (Formerly Fallback) ---
    try:
        df_indexed = market_data.set_index('time')
        current_candle_index = df_indexed.index.get_loc(alert_time)
        if current_candle_index > 0:
            current_candle = df_indexed.iloc[current_candle_index]
            prev_candle = df_indexed.iloc[current_candle_index - 1]
            
            open_t1 = prev_candle['open']
            low_t = current_candle['low']
            high_t = current_candle['high']

            if signal.upper() == 'BUY':
                structural_price = round(max(float(open_t1), float(low_t)), 1)
            elif signal.upper() == 'SELL':
                structural_price = round(min(float(open_t1), float(high_t)), 1)
            
            if structural_price is not None:
                structural_price = adjust_price_by_signal(structural_price, signal)

            logger.info(f"Calculated structural price: {structural_price}")
        else:
            logger.warning("Not enough data for structural price (needs T-1 candle).")
    except Exception as e:
        logger.error(f"Error during structural price calculation: {e}", exc_info=True)

    return performance_price, structural_price


def get_primary_suggested_price(alert_row: pd.Series) -> Optional[float]:
    """
    Selects the primary suggested price based on the USE_PERFORMANCE_BY_APPROACH flag.

    Args:
        alert_row (pd.Series): A row from the alerts DataFrame, which must contain
                               'performance_suggested_price' and 'structural_suggested_price'.

    Returns:
        Optional[float]: The chosen suggested price, or None if neither is available.
    """
    performance_price = alert_row.get('performance_suggested_price')
    structural_price = alert_row.get('structural_suggested_price')

    # Reload settings to ensure the flag is current
    importlib.reload(price_alert_settings)
    
    if price_alert_settings.USE_PERFORMANCE_BY_APPROACH:
        if pd.notna(performance_price):
            return performance_price
        else:
            logger.warning("Performance price preferred but is NaN; falling back to structural price.")
            return structural_price
    else:
        return structural_price


def adjust_price_by_signal(price: float, signal: str) -> float:
    """
    Adjusts a price based on the signal (BUY or SELL) using a configured offset.

    The offset is retrieved from `price_alert_settings.STRUCTURAL_PRICE_LEVEL_OFFSET`.
    For 'BUY' signals, the offset is subtracted.
    For 'SELL' signals (or any other signal), the offset is added.

    Args:
        price (float): The initial price to adjust.
        signal (str): The signal ('BUY' or 'SELL').

    Returns:
        float: The adjusted price.
    """
    price_level = getattr(price_alert_settings, 'STRUCTURAL_PRICE_LEVEL_OFFSET', 0.0)
    if signal.upper() == 'BUY':
        return price - price_level
    return price + price_level
