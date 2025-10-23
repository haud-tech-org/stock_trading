# src/stockreports/utils/alert_utils.py
import logging
import pandas as pd
from typing import Optional

logger = logging.getLogger(__name__)

def calculate_suggested_price(signal: str, alert_time: pd.Timestamp, market_data: pd.DataFrame) -> Optional[float]:
    """
    Calculates the suggested entry/exit price based on the signal and market data.

    Args:
        signal (str): The alert signal ('BUY' or 'SELL').
        alert_time (pd.Timestamp): The timestamp of the alert.
        market_data (pd.DataFrame): The market data containing OHLC prices.

    Returns:
        Optional[float]: The calculated suggested price, or None if it cannot be determined.
    """
    if market_data.empty or 'time' not in market_data.columns:
        return None

    df_indexed = market_data.set_index('time')

    try:
        # Find the current (T) and previous (T-1) candles
        current_candle_index = df_indexed.index.get_loc(alert_time)
        if current_candle_index == 0:
            logger.warning("Cannot calculate suggested price; alert is on the first candle of the dataset.")
            return None

        current_candle = df_indexed.iloc[current_candle_index]
        prev_candle = df_indexed.iloc[current_candle_index - 1]

        open_t1 = prev_candle['open']
        low_t = current_candle['low']
        high_t = current_candle['high']

        if signal.upper() == 'BUY':
            return max(float(open_t1), float(low_t))
        elif signal.upper() == 'SELL':
            return min(float(open_t1), float(high_t))

    except KeyError:
        logger.warning(f"Could not find alert time {alert_time} in market data index for suggested price calculation.")
        return None
    except (ValueError, TypeError, IndexError) as e:
        logger.error(f"Error calculating suggested price: {e}")
        return None
        
    return None
