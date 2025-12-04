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
    Retrieves historical data for a given symbol and time range, with optional resolution.
    This function intelligently fetches only the data missing from the cache.
    """
    cache_key = (symbol, resolution)
    cached_df = _data_cache.get(cache_key)

    # --- Case 1: No data in cache for this key ---
    if cached_df is None or cached_df.empty:
        logger.info(f"Cache empty for '{symbol}' (res: {resolution}). Fetching full range: {start_time} to {end_time}.")
        
        if settings.MODE == Mode.DEVELOPMENT:
            fetched_df = load_data_for_development(symbol)
        else:
            from_ts = int(start_time.timestamp())
            to_ts = int(end_time.timestamp())
            fetched_df = _load_live_data_with_resolution(symbol, from_ts, to_ts, resolution=resolution)

        if fetched_df is not None and not fetched_df.empty:
            _update_historical_data_with_resolution(symbol, fetched_df, resolution)
        else:
            logger.error(f"Initial fetch failed for '{symbol}' (res: {resolution}).")
            return None

    # --- Case 2: Data exists in cache, check for missing segments ---
    cached_df = _data_cache[cache_key] # Re-read from cache
    cache_start, cache_end = cached_df['time'].min(), cached_df['time'].max()

    # Check if the full range is already cached
    if cache_start <= start_time and cache_end >= end_time:
        logger.debug(f"Full range cache hit for '{symbol}' (res: {resolution}).")
        return cached_df[(cached_df['time'] >= start_time) & (cached_df['time'] <= end_time)].copy()

    # Determine and fetch missing segments
    segments_to_fetch = []
    # if start_time < cache_start:
    #     segments_to_fetch.append((start_time, cache_start - pd.Timedelta(seconds=1)))
    #     logger.info(f"Fetching missing data for '{symbol}' at the beginning: {start_time} to {cache_start}.")
        
    if end_time > cache_end:
        segments_to_fetch.append((cache_end + pd.Timedelta(seconds=1), end_time))
        logger.info(f"Fetching missing data for '{symbol}' at the end: {cache_end} to {end_time}.")

    for seg_start, seg_end in segments_to_fetch:
        if settings.MODE == Mode.DEVELOPMENT:
            # In dev mode, we load the whole file once, so this part is less critical
            # but we maintain the logic for consistency.
            logger.debug("In dev mode, full data file is loaded, no partial fetch needed.")
            continue

        from_ts = int(seg_start.timestamp())
        to_ts = int(seg_end.timestamp())
        
        logger.debug(f"Fetching segment for '{symbol}' (res: {resolution}): {seg_start} to {seg_end}")
        segment_df = _load_live_data_with_resolution(symbol, from_ts, to_ts, resolution=resolution)
        
        if segment_df is not None and not segment_df.empty:
            _update_historical_data_with_resolution(symbol, segment_df, resolution)
        else:
            logger.warning(f"Failed to fetch segment for '{symbol}' from {seg_start} to {seg_end}.")

    # --- Final retrieval from updated cache ---
    final_df = _data_cache.get(cache_key)
    if final_df is not None:
        # After fetch attempts, return whatever is available within the requested window,
        # even if it's incomplete. The calling function is responsible for handling it.
        partial_df = final_df[(final_df['time'] >= start_time) & (final_df['time'] <= end_time)].copy()
        
        if partial_df.empty:
            logger.warning(f"No data available for '{symbol}' in the requested window {start_time} to {end_time} after fetch attempts.")
            return None
            
        # Check if the returned data fully covers the request and log a warning if not.
        if not (partial_df['time'].min() <= start_time and partial_df['time'].max() >= end_time):
             logger.warning(f"Returning incomplete data for '{symbol}'. Requested: {start_time} to {end_time}, Available: {partial_df['time'].min()} to {partial_df['time'].max()}.")

        return partial_df
            
    logger.error(f"Cache for '{symbol}' is unexpectedly empty after processing.")
    return None


def get_historical_data(symbol: str, start_time: pd.Timestamp, end_time: pd.Timestamp) -> Optional[pd.DataFrame]:
    """
    Retrieves a historical DataFrame using the default resolution. This is a wrapper
    for backward compatibility.
    """
    return _get_historical_data_with_resolution(symbol, start_time, end_time, resolution=None)
