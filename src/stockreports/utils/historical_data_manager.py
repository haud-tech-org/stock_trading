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
from src.stockreports.utils.data_utils import _load_live_data_with_resolution, load_data_for_development
from src.stockreports.alert.common.constants import Mode

# --- Module-level private cache ---
_data_cache: Dict[tuple[str, Optional[int]], pd.DataFrame] = {}

# --- Logger ---
logger = logging.getLogger(__name__)
settings = loader.get_settings()

def _update_historical_data_with_resolution(symbol: str, data_df: pd.DataFrame, resolution: Optional[int] = None):
    """
    Internal function to update the cache for a given symbol and resolution.
    """
    cache_key = (symbol, resolution)
    if cache_key in _data_cache:
        # Append, drop duplicates, and sort
        combined_df = pd.concat([_data_cache[cache_key], data_df])
        combined_df.drop_duplicates(subset=['time'], keep='last', inplace=True)
        combined_df.sort_values(by='time', inplace=True)
        _data_cache[cache_key] = combined_df
    else:
        _data_cache[cache_key] = data_df.copy()
    
    logger.debug(f"Cache updated for symbol '{symbol}' with resolution '{resolution}'. New length: {len(_data_cache[cache_key])}")

def update_historical_data(symbol: str, data_df: pd.DataFrame):
    """
    Updates the cache for a given symbol using the default resolution. This is a
    wrapper for backward compatibility.
    """
    _update_historical_data_with_resolution(symbol, data_df, resolution=None)


def _get_historical_data_with_resolution(symbol: str, start_time: pd.Timestamp, end_time: pd.Timestamp, resolution: Optional[int] = None) -> Optional[pd.DataFrame]:
    """
    Internal function to retrieve historical data with an optional resolution.
    """
    cache_key = (symbol, resolution)
    cached_df = _data_cache.get(cache_key)

    # Check if the cache already contains the full required range
    if cached_df is not None:
        cache_start = cached_df['time'].min()
        cache_end = cached_df['time'].max()
        if cache_start <= start_time and cache_end >= end_time:
            logger.debug(f"Cache hit for '{symbol}' with resolution '{resolution}' for the window {start_time} to {end_time}.")
            return cached_df[(cached_df['time'] >= start_time) & (cached_df['time'] <= end_time)].copy()

    logger.info(f"Cache miss or incomplete data for '{symbol}' with resolution '{resolution}' for window {start_time} to {end_time}. Fetching.")

    if settings.MODE == Mode.DEVELOPMENT:
        fetched_df = load_data_for_development(symbol)
    else:
        from_timestamp = int(start_time.timestamp())
        to_timestamp = int(end_time.timestamp())
        fetched_df = _load_live_data_with_resolution(symbol, from_timestamp, to_timestamp, resolution=resolution)

    if fetched_df is None or fetched_df.empty:
        logger.error(f"Manual fetch failed for symbol '{symbol}' for window {start_time} to {end_time}.")
        return None

    _update_historical_data_with_resolution(symbol, fetched_df, resolution=resolution)

    final_df = _data_cache.get(cache_key)
    if final_df is not None:
        return final_df[(final_df['time'] >= start_time) & (final_df['time'] <= end_time)].copy()

    return None


def get_historical_data(symbol: str, start_time: pd.Timestamp, end_time: pd.Timestamp) -> Optional[pd.DataFrame]:
    """
    Retrieves a historical DataFrame using the default resolution. This is a wrapper
    for backward compatibility.
    """
    return _get_historical_data_with_resolution(symbol, start_time, end_time, resolution=None)
