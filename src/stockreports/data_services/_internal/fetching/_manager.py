"""
Manages a centralized, in-memory cache for historical market data.

This module provides a single source of truth for historical dataframes,
preventing redundant data queries and ensuring consistency across different
parts of the application, especially for approaches that need to reference
data from other symbols.

The manager is intelligent: if requested data is not in the cache or is
insufficient, it will automatically fetch the required data and update
the cache.

Architecture:
- HistoricalDataManager: Class-based hub for cache management
- Singleton pattern: Module-level instance for backward compatibility
- All public methods available as both class methods and module functions

Data Flow:
1. Fetch raw data: HistoricalDataManager → Coordinator → Provider
2. Process data: HistoricalDataManager → DataProcessor (timezone + price adjustment)
3. Cache & return: HistoricalDataManager stores processed data
"""
import pandas as pd
from typing import Optional, Dict
import logging
from datetime import datetime

from src.stockreports.config import loader
from src.stockreports.data_services._internal.providing._coordinator import DataProviderCoordinator
from src.stockreports.data_services._internal.processing._processor import DataProcessor
from src.stockreports.alert.common.constants import Mode

# --- Logger ---
logger = logging.getLogger(__name__)
settings = loader.get_settings()


class HistoricalDataManager:
    """
    Centralized hub for managing historical market data with intelligent caching.
    
    Features:
    - In-memory cache with configurable size limit
    - Intelligent partial fetching (only missing segments)
    - Cache statistics and monitoring
    - Clean API for data operations
    - Encapsulated state management
    
    Example:
        manager = HistoricalDataManager()
        manager.update('VCB', df)
        data = manager.get('VCB', start_time, end_time)
        stats = manager.get_cache_stats()
    """
    
    def __init__(
        self,
        cache_size: int = 1000,
        ttl_seconds: int = 3600,
        enable_monitoring: bool = True
    ):
        """
        Initialize the HistoricalDataManager.
        
        Args:
            cache_size: Maximum number of cache entries (not enforced yet)
            ttl_seconds: Time-to-live for cache entries in seconds
            enable_monitoring: Whether to track cache statistics
        """
        self._data_cache: Dict[tuple[str, Optional[int]], pd.DataFrame] = {}
        self._cache_size = cache_size
        self._ttl_seconds = ttl_seconds
        self._enable_monitoring = enable_monitoring
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'updates': 0,
            'last_cleared': None,
            'created_at': datetime.now()
        }
        self.logger = logging.getLogger(__name__)
    
    # ============================================================================
    # PUBLIC API: Retrieve Methods
    # ============================================================================
    
    def get(
        self,
        symbol: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves historical data for a given symbol and time range using
        the default resolution (None).
        
        Args:
            symbol: Stock symbol (e.g., 'VCB', 'BTCUSDT')
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            pd.DataFrame with columns [time, open, high, low, close, volume]
            or None if no data available
        """
        return self.get_with_resolution(symbol, start_time, end_time, resolution=None)
    
    def get_with_resolution(
        self,
        symbol: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        resolution: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Retrieves historical data for a given symbol and time range with
        optional resolution specification.
        
        This method intelligently checks the cache:
        1. If data exists and covers the range → return cached data
        2. If data missing or incomplete → fetch missing segments
        3. Merge new data with cache and return
        
        Args:
            symbol: Stock symbol (e.g., 'VCB', 'BTCUSDT')
            start_time: Start of time range
            end_time: End of time range
            resolution: Optional resolution (1, 5, 15, 60 min etc)
            
        Returns:
            pd.DataFrame with the requested data, or None
        """
        cache_key = (symbol, resolution)
        cached_df = self._data_cache.get(cache_key)

        # --- Case 1: No data in cache for this key ---
        if cached_df is None or cached_df.empty:
            self.logger.info(
                f"Cache miss for '{symbol}' (res: {resolution}). "
                f"Fetching full range: {start_time} to {end_time}."
            )
            if self._enable_monitoring:
                self._cache_stats['misses'] += 1
            
            if settings.MODE == Mode.DEVELOPMENT:
                from src.stockreports.utils.data_utils import load_data_for_development
                fetched_df = load_data_for_development(symbol)
            else:
                from_ts = int(start_time.timestamp())
                to_ts = int(end_time.timestamp())
                fetched_df = self._fetch_and_process_data(
                    symbol, from_ts, to_ts, resolution=resolution
                )

            if fetched_df is not None:
                # Cache both empty and non-empty DataFrames
                # Empty DataFrame is a valid response indicating:
                # - API worked, but no data available for this symbol/resolution/time
                # - (e.g., non-trading hours, market closed, or symbol not available at this resolution)
                self._merge_and_cache(symbol, fetched_df, resolution)
            else:
                # None = actual fetch failure (network error, API exception, timeout)
                self.logger.error(
                    f"Initial fetch failed for '{symbol}' (res: {resolution})."
                )
                return None

        # --- Case 2: Data exists in cache, check for missing segments ---
        cached_df = self._data_cache.get(cache_key)  # Re-read from cache
        if cached_df is None or cached_df.empty:
            return None
        
        cache_start = cached_df.index.min()
        cache_end = cached_df.index.max()

        # Check if the full range is already cached
        if cache_start <= start_time and cache_end >= end_time:
            self.logger.debug(
                f"Full range cache hit for '{symbol}' (res: {resolution})."
            )
            if self._enable_monitoring:
                self._cache_stats['hits'] += 1
            return cached_df[
                (cached_df.index >= start_time) & (cached_df.index <= end_time)
            ].copy()

        # Determine and fetch missing segments
        segments_to_fetch = []
        if end_time > cache_end:
            segments_to_fetch.append((cache_end + pd.Timedelta(seconds=1), end_time))
            self.logger.info(
                f"Fetching missing data for '{symbol}' at the end: "
                f"{cache_end} to {end_time}."
            )

        for seg_start, seg_end in segments_to_fetch:
            if settings.MODE == Mode.DEVELOPMENT:
                self.logger.debug(
                    "In dev mode, full data file is loaded, no partial fetch needed."
                )
                continue

            from_ts = int(seg_start.timestamp())
            to_ts = int(seg_end.timestamp())
            
            self.logger.debug(
                f"Fetching segment for '{symbol}' (res: {resolution}): "
                f"{seg_start} to {seg_end}"
            )
            segment_df = self._fetch_and_process_data(
                symbol, from_ts, to_ts, resolution=resolution
            )
            
            if segment_df is not None and not segment_df.empty:
                self._merge_and_cache(symbol, segment_df, resolution)
            else:
                self.logger.warning(
                    f"Failed to fetch segment for '{symbol}' "
                    f"from {seg_start} to {seg_end}."
                )

        # --- Final retrieval from updated cache ---
        final_df = self._data_cache.get(cache_key)
        if final_df is not None:
            partial_df = final_df[
                (final_df.index >= start_time) & (final_df.index <= end_time)
            ].copy()
            
            if partial_df.empty:
                self.logger.warning(
                    f"No data available for '{symbol}' in the requested window "
                    f"{start_time} to {end_time} after fetch attempts."
                )
                return None
                
            if not (partial_df.index.min() <= start_time and 
                   partial_df.index.max() >= end_time):
                self.logger.warning(
                    f"Returning incomplete data for '{symbol}'. "
                    f"Requested: {start_time} to {end_time}, "
                    f"Available: {partial_df.index.min()} to {partial_df.index.max()}."
                )

            return partial_df
            
        self.logger.error(
            f"Cache for '{symbol}' is unexpectedly empty after processing."
        )
        return None
    
    # ============================================================================
    # PUBLIC API: Update Methods
    # ============================================================================
    
    def update(
        self,
        symbol: str,
        data_df: pd.DataFrame
    ) -> None:
        """
        Updates the cache for a given symbol using the default resolution.
        
        Args:
            symbol: Stock symbol
            data_df: DataFrame with new data to cache
        """
        self.update_with_resolution(symbol, data_df, resolution=None)
    
    def update_with_resolution(
        self,
        symbol: str,
        data_df: pd.DataFrame,
        resolution: Optional[int] = None
    ) -> None:
        """
        Updates the cache for a given symbol with optional resolution.
        
        Args:
            symbol: Stock symbol
            data_df: DataFrame with new data to cache
            resolution: Optional resolution specification
        """
        self._merge_and_cache(symbol, data_df, resolution)
    
    # ============================================================================
    # PUBLIC API: Cache Management Methods
    # ============================================================================
    
    def clear_cache(self) -> None:
        """Clear entire cache and reset statistics."""
        self._data_cache.clear()
        if self._enable_monitoring:
            self._cache_stats['last_cleared'] = datetime.now()
        self.logger.info("Cache cleared")
    
    def clear_symbol(self, symbol: str) -> None:
        """
        Clear cache for a specific symbol (all resolutions).
        
        Args:
            symbol: Stock symbol to clear
        """
        keys_to_remove = [k for k in self._data_cache.keys() if k[0] == symbol]
        for key in keys_to_remove:
            del self._data_cache[key]
        self.logger.info(f"Cache cleared for symbol '{symbol}'")
    
    def get_cache_size(self) -> Dict:
        """
        Get cache size information.
        
        Returns:
            {
                'num_keys': Number of cache entries,
                'num_symbols': Number of unique symbols,
                'memory_estimate_mb': Approximate memory usage,
                'entries': List of (symbol, resolution, num_rows) tuples
            }
        """
        num_keys = len(self._data_cache)
        symbols = set(k[0] for k in self._data_cache.keys())
        
        total_rows = 0
        entries = []
        
        for (symbol, resolution), df in self._data_cache.items():
            rows = len(df)
            total_rows += rows
            entries.append((symbol, resolution, rows))
        
        # Rough estimate: ~100 bytes per row per column, assuming 6 columns
        memory_estimate = (total_rows * 6 * 100) / (1024 * 1024)  # MB
        
        return {
            'num_keys': num_keys,
            'num_symbols': len(symbols),
            'total_rows': total_rows,
            'memory_estimate_mb': round(memory_estimate, 2),
            'entries': entries
        }
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics.
        
        Returns:
            {
                'hits': Number of cache hits,
                'misses': Number of cache misses,
                'hit_rate': Hit rate percentage,
                'updates': Number of updates,
                'created_at': When manager was created,
                'last_cleared': When cache was last cleared
            }
        """
        if not self._enable_monitoring:
            return {'enabled': False}
        
        total_requests = self._cache_stats['hits'] + self._cache_stats['misses']
        hit_rate = (
            (self._cache_stats['hits'] / total_requests * 100) 
            if total_requests > 0 else 0
        )
        
        return {
            'hits': self._cache_stats['hits'],
            'misses': self._cache_stats['misses'],
            'hit_rate': round(hit_rate, 2),
            'updates': self._cache_stats['updates'],
            'created_at': self._cache_stats['created_at'].isoformat(),
            'last_cleared': (
                self._cache_stats['last_cleared'].isoformat()
                if self._cache_stats['last_cleared'] else None
            )
        }
    
    # ============================================================================
    # PRIVATE API: Internal Methods
    # ============================================================================
    
    def _fetch_and_process_data(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: Optional[int] = None
    ) -> Optional[pd.DataFrame]:
        """
        Fetch raw data from Coordinator and process through DataProcessor.
        
        This method implements the core data flow:
        1. Fetch raw OHLCV data from Coordinator (which routes to appropriate Provider)
        2. Process data through DataProcessor (timezone conversion, price adjustment, etc.)
        3. Return processed DataFrame ready for caching
        
        Args:
            symbol: Stock/crypto symbol
            from_timestamp: Start Unix timestamp
            to_timestamp: End Unix timestamp
            resolution: Optional resolution in minutes
            
        Returns:
            pd.DataFrame: Processed OHLCV data, or None if fetch/processing failed
        """
        try:
            # Step 1: Fetch raw data from provider via Coordinator
            coordinator = DataProviderCoordinator()
            resolution_minutes = resolution if resolution is not None else 1
            
            self.logger.debug(
                f"Fetching raw data for '{symbol}' from {from_timestamp} to {to_timestamp} "
                f"(resolution: {resolution_minutes} min)"
            )
            
            raw_df = coordinator.fetch_ohlcv(
                symbol=symbol,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                resolution=resolution_minutes
            )
            
            if raw_df is None or raw_df.empty:
                self.logger.warning(f"No raw data returned for '{symbol}' from Coordinator")
                return None
            
            # Step 2: Process data through DataProcessor
            processor = DataProcessor(symbol)
            processed_df = processor.process(raw_df)
            
            if processed_df is None or processed_df.empty:
                self.logger.warning(f"Data processing failed for '{symbol}'")
                return None
            
            self.logger.debug(
                f"Successfully fetched and processed {len(processed_df)} rows for '{symbol}'"
            )
            return processed_df
            
        except Exception as e:
            self.logger.error(
                f"Failed to fetch and process data for '{symbol}': {str(e)}",
                exc_info=True
            )
            return None
    
    # ============================================================================
    def _merge_and_cache(
        self,
        symbol: str,
        data_df: pd.DataFrame,
        resolution: Optional[int] = None
    ) -> None:
        """
        Internal method to merge new data with existing cache and update.
        
        Args:
            symbol: Stock symbol
            resolution: Optional resolution
            
        Note:
            - data_df has 'time' as the index
            - Index is pd.DatetimeIndex with pd.Timestamp elements
        """
        cache_key = (symbol, resolution)
        
        if cache_key in self._data_cache:
            # Merge with existing cache
            cached_data = self._data_cache[cache_key]
            
            # Append, drop duplicates, and sort by index
            combined_df = pd.concat([cached_data, data_df])
            combined_df = combined_df[~combined_df.index.duplicated(keep='last')]
            combined_df = combined_df.sort_index()
            self._data_cache[cache_key] = combined_df
            
            self.logger.debug(
                f"Merged new data for '{symbol}'. "
                f"Cached size: {len(cached_data)} → {len(combined_df)}"
            )
        else:
            # First time caching this symbol/resolution
            self._data_cache[cache_key] = data_df.copy()
            
            self.logger.debug(
                f"Cached new data for '{symbol}' (resolution: {resolution}). "
                f"Size: {len(data_df)}"
            )
        
        if self._enable_monitoring:
            self._cache_stats['updates'] += 1


# ============================================================================
# MODULE-LEVEL SINGLETON FOR BACKWARD COMPATIBILITY
# ============================================================================

# Single instance to maintain backward compatibility with existing code
_manager = HistoricalDataManager()


def get_historical_data(
    symbol: str,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp
) -> Optional[pd.DataFrame]:
    """
    Retrieves a historical DataFrame using the default resolution.
    
    This is a backward compatible wrapper for HistoricalDataManager.get().
    
    Args:
        symbol: Stock symbol
        start_time: Start of time range
        end_time: End of time range
        
    Returns:
        Historical data or None
    """
    return _manager.get(symbol, start_time, end_time)


def update_historical_data(
    symbol: str,
    data_df: pd.DataFrame
) -> None:
    """
    Updates the cache for a given symbol using the default resolution.
    
    This is a backward compatible wrapper for HistoricalDataManager.update().
    
    Args:
        symbol: Stock symbol
        data_df: DataFrame with new data to cache
    """
    _manager.update(symbol, data_df)


def get_manager() -> HistoricalDataManager:
    """
    Get the module-level singleton manager instance.
    
    This allows code to access the manager directly if needed:
        manager = get_manager()
        manager.clear_symbol('VCB')
        stats = manager.get_cache_stats()
    
    Returns:
        The HistoricalDataManager singleton instance
    """
    return _manager
