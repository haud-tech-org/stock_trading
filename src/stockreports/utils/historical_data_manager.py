"""
Manages a centralized, in-memory cache for historical market data.

This module provides a single source of truth for historical dataframes,
preventing redundant data queries and ensuring consistency across different
parts of the application, especially for approaches that need to reference
data from other symbols.

The manager is intelligent: if requested data is not in the cache or is
insufficient, it will automatically fetch the required data and update
the cache.
"""
import pandas as pd
from typing import Optional, Dict
import logging

from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_data_for_development, load_live_data
from src.stockreports.alert.common.constants import Mode

# --- Module-level private cache ---
_data_cache: Dict[str, pd.DataFrame] = {}

# --- Logger ---
logger = logging.getLogger(__name__)
settings = loader.get_settings()

def update_historical_data(symbol: str, data_df: pd.DataFrame):
    """
    Updates the cache for a given symbol with a new or updated DataFrame.

    This function merges the new data with existing cached data, removes
    duplicates, and ensures the result is sorted by time.

    Args:
        symbol (str): The stock symbol.
        data_df (pd.DataFrame): The new data to add to the cache.
    """
    if symbol in _data_cache:
        # Append, drop duplicates, and sort
        combined_df = pd.concat([_data_cache[symbol], data_df])
        combined_df.drop_duplicates(subset=['time'], keep='last', inplace=True)
        combined_df.sort_values(by='time', inplace=True)
        _data_cache[symbol] = combined_df
    else:
        _data_cache[symbol] = data_df.copy()
    
    logger.debug(f"Cache updated for symbol '{symbol}'. New length: {len(_data_cache[symbol])}")

def get_historical_data(symbol: str, start_time: pd.Timestamp, end_time: pd.Timestamp) -> Optional[pd.DataFrame]:
    """
    Retrieves a historical DataFrame for a symbol for a precise time window.

    If the cached data fully covers the requested window, it's returned.
    Otherwise, it triggers a targeted fetch for the missing data segments
    and updates the cache.

    Args:
        symbol (str): The stock symbol to retrieve data for.
        start_time (pd.Timestamp): The start of the desired time window.
        end_time (pd.Timestamp): The end of the desired time window.

    Returns:
        Optional[pd.DataFrame]: A DataFrame covering the requested time window,
                                or None if data cannot be fetched.
    """
    cached_df = _data_cache.get(symbol)

    # Check if the cache already contains the full required range
    if cached_df is not None:
        cache_start = cached_df['time'].min()
        cache_end = cached_df['time'].max()
        if cache_start <= start_time and cache_end >= end_time:
            logger.debug(f"Cache hit for '{symbol}' for the window {start_time} to {end_time}.")
            # Return a copy of the relevant slice
            return cached_df[(cached_df['time'] >= start_time) & (cached_df['time'] <= end_time)].copy()

    # --- Cache Miss or Incomplete Data: Fetch the required data ---
    logger.info(f"Cache miss or incomplete data for '{symbol}' for window {start_time} to {end_time}. Fetching.")

    if settings.MODE == Mode.DEVELOPMENT:
        # In development, we load the entire file once and cache it.
        # Subsequent calls will be served from the cache.
        fetched_df = load_data_for_development(symbol)
    else:
        # In deployment, fetch the specific live data window.
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        fetched_df = load_live_data(symbol, from_timestamp, to_timestamp)

    if fetched_df is None or fetched_df.empty:
        logger.error(f"Manual fetch failed for symbol '{symbol}' for window {start_time} to {end_time}.")
        return None

    # Update the cache with the newly fetched data
    update_historical_data(symbol, fetched_df)

    # After updating, retrieve the requested slice from the now-updated cache
    final_df = _data_cache.get(symbol)
    if final_df is not None:
        # Return a copy of the relevant slice
        return final_df[(final_df['time'] >= start_time) & (final_df['time'] <= end_time)].copy()

    return None
