"""
Phase 3 Integration Tests - Data Caching Layer

Tests the HistoricalDataManager and its caching system that sits above
the data providers (Phase 1 & 2).

Test coverage:
- Manager initialization and configuration
- Cache operations (get, update, merge)
- Multiple resolutions support
- Cache management (clear, clear_symbol)
- Cache statistics and monitoring
- Backward compatibility functions
- Module-level singleton pattern
"""

import sys
import pytest
import pandas as pd
import logging
import warnings
from datetime import datetime, timedelta

from src.stockreports.data_services._internal.fetching._manager import (
    HistoricalDataManager,
    get_historical_data,
    update_historical_data,
    get_manager,
)

# Suppress CCXT exchange cleanup warnings
logging.getLogger('ccxt.base.exchange').setLevel(logging.ERROR)

# Suppress ResourceWarning for unclosed connections from CCXT
warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture
def sample_data():
    """Create sample OHLCV data."""
    dates = pd.date_range('2024-01-01', periods=10, freq='h')
    return pd.DataFrame({
        'time': dates,
        'open': [100 + i for i in range(10)],
        'high': [102 + i for i in range(10)],
        'low': [99 + i for i in range(10)],
        'close': [101 + i for i in range(10)],
        'volume': [1000 + i * 100 for i in range(10)],
    }).set_index('time')


@pytest.fixture
def manager():
    """Create a fresh manager instance for each test."""
    return HistoricalDataManager()


class TestManagerInitialization:
    """Test HistoricalDataManager initialization."""
    
    def test_manager_creates_with_defaults(self):
        """Manager initializes with correct defaults."""
        mgr = HistoricalDataManager()
        assert mgr._cache_size == 1000
        assert mgr._ttl_seconds == 3600
        assert mgr._enable_monitoring is True
        assert len(mgr._data_cache) == 0
    
    def test_manager_creates_with_custom_config(self):
        """Manager initializes with custom configuration."""
        mgr = HistoricalDataManager(cache_size=500, ttl_seconds=1800, enable_monitoring=False)
        assert mgr._cache_size == 500
        assert mgr._ttl_seconds == 1800
        assert mgr._enable_monitoring is False


class TestCacheOperations:
    """Test basic cache operations."""
    
    def test_update_and_retrieve_basic(self, manager, sample_data):
        """Can update cache and retrieve data."""
        manager.update('VCB', sample_data)
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        
        retrieved = manager.get('VCB', start, end)
        
        assert retrieved is not None
        assert len(retrieved) == len(sample_data)
        assert list(retrieved['close']) == list(sample_data['close'])
    
    def test_update_with_resolution(self, manager, sample_data):
        """Can update cache with specific resolution."""
        manager.update_with_resolution('VCB', sample_data, resolution=5)
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        
        retrieved = manager.get_with_resolution('VCB', start, end, resolution=5)
        
        assert retrieved is not None
        assert len(retrieved) == len(sample_data)
    
    def test_multiple_resolutions_same_symbol(self, manager, sample_data):
        """Can handle same symbol with different resolutions."""
        manager.update_with_resolution('VCB', sample_data, resolution=1)
        manager.update_with_resolution('VCB', sample_data, resolution=5)
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        
        data_1min = manager.get_with_resolution('VCB', start, end, resolution=1)
        data_5min = manager.get_with_resolution('VCB', start, end, resolution=5)
        
        assert data_1min is not None
        assert data_5min is not None
        assert len(data_1min) == len(sample_data)
        assert len(data_5min) == len(sample_data)
    
    def test_multiple_symbols(self, manager, sample_data):
        """Can handle multiple symbols."""
        manager.update('VCB', sample_data)
        manager.update('HBC', sample_data)
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        
        vcb_data = manager.get('VCB', start, end)
        hbc_data = manager.get('HBC', start, end)
        
        assert vcb_data is not None
        assert hbc_data is not None


class TestCacheManagement:
    """Test cache management operations."""
    
    def test_clear_entire_cache(self, manager, sample_data):
        """Clear cache removes all entries."""
        manager.update('VCB', sample_data)
        manager.update('HBC', sample_data)
        
        assert len(manager._data_cache) == 2
        
        manager.clear_cache()
        
        assert len(manager._data_cache) == 0
    
    def test_clear_specific_symbol(self, manager, sample_data):
        """Clear symbol removes only that symbol."""
        manager.update('VCB', sample_data)
        manager.update('HBC', sample_data)
        manager.update_with_resolution('VCB', sample_data, resolution=5)
        
        assert len(manager._data_cache) == 3
        
        manager.clear_symbol('VCB')
        
        # VCB with None and 5 resolutions should be gone
        # HBC with None should remain
        assert len(manager._data_cache) == 1
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        remaining = manager.get('HBC', start, end)
        assert remaining is not None
    
    def test_get_cache_size(self, manager, sample_data):
        """Get cache size information."""
        manager.update('VCB', sample_data)
        manager.update_with_resolution('HBC', sample_data, resolution=5)
        
        size_info = manager.get_cache_size()
        
        assert size_info['num_keys'] == 2
        assert size_info['num_symbols'] == 2
        assert size_info['total_rows'] == 20
        assert 'memory_estimate_mb' in size_info
        assert len(size_info['entries']) == 2


class TestCacheStatistics:
    """Test cache statistics and monitoring."""
    
    def test_cache_stats_initially_zero(self, manager):
        """Cache stats initialized to zero."""
        stats = manager.get_cache_stats()
        
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0
        assert stats['updates'] == 0
    
    def test_stats_tracked_on_operations(self, manager, sample_data):
        """Statistics tracked on cache operations."""
        # First update
        manager.update('VCB', sample_data)
        stats = manager.get_cache_stats()
        assert stats['updates'] == 1
        
        # First retrieval (should be hit since we just updated)
        start = sample_data.index.min()
        end = sample_data.index.max()
        manager.get('VCB', start, end)
        stats = manager.get_cache_stats()
        assert stats['hits'] == 1
        
        # Request for different symbol (miss)
        data_2025 = pd.DataFrame({
            'time': pd.date_range('2025-01-01', periods=10, freq='1h'),
            'open': [100 + i for i in range(10)],
            'high': [102 + i for i in range(10)],
            'low': [99 + i for i in range(10)],
            'close': [101 + i for i in range(10)],
            'volume': [1000 + i * 100 for i in range(10)],
        }).set_index('time')
        manager.get('HBC', data_2025.index.min(), data_2025.index.max())
        stats = manager.get_cache_stats()
        assert stats['misses'] == 1
    
    def test_monitoring_disabled(self):
        """Statistics not tracked when monitoring disabled."""
        mgr = HistoricalDataManager(enable_monitoring=False)
        
        dates = pd.date_range('2024-01-01', periods=10, freq='1h')
        sample_data = pd.DataFrame({
            'time': dates,
            'open': [100 + i for i in range(10)],
            'high': [102 + i for i in range(10)],
            'low': [99 + i for i in range(10)],
            'close': [101 + i for i in range(10)],
            'volume': [1000 + i * 100 for i in range(10)],
        })
        
        mgr.update('VCB', sample_data)
        stats = mgr.get_cache_stats()
        
        assert stats['enabled'] is False


class TestBackwardCompatibility:
    """Test backward compatibility with module-level functions."""
    
    def test_module_level_functions_work(self, sample_data):
        """Module-level functions (get/update) work correctly."""
        # Clear the singleton cache first
        manager = get_manager()
        manager.clear_cache()
        
        # Use module-level functions
        update_historical_data('VCB', sample_data)
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        retrieved = get_historical_data('VCB', start, end)
        
        assert retrieved is not None
        assert len(retrieved) == len(sample_data)
    
    def test_get_manager_returns_singleton(self):
        """get_manager returns the singleton instance."""
        mgr1 = get_manager()
        mgr2 = get_manager()
        
        # Should be the same instance
        assert mgr1 is mgr2
    
    def test_manager_singleton_persistence(self, sample_data):
        """Data persists across get_manager calls."""
        manager1 = get_manager()
        manager1.clear_cache()
        
        manager1.update('VCB', sample_data)
        
        # Get new reference
        manager2 = get_manager()
        
        start = sample_data.index.min()
        end = sample_data.index.max()
        retrieved = manager2.get('VCB', start, end)
        
        assert retrieved is not None
        assert len(retrieved) == len(sample_data)


class TestDataMerging:
    """Test data merging and duplicate handling."""
    
    def test_merge_removes_duplicates(self, manager):
        """Merging removes duplicate timestamps."""
        dates = pd.date_range('2024-01-01', periods=5, freq='1h')
        data1 = pd.DataFrame({
            'time': dates,
            'open': [100, 101, 102, 103, 104],
            'high': [102, 103, 104, 105, 106],
            'low': [99, 100, 101, 102, 103],
            'close': [101, 102, 103, 104, 105],
            'volume': [1000, 1100, 1200, 1300, 1400],
        }).set_index('time')
        
        # Overlapping data with different values
        data2 = pd.DataFrame({
            'time': dates[2:],  # Starts at index 2
            'open': [102.5, 103.5, 104.5],
            'high': [104.5, 105.5, 106.5],
            'low': [101.5, 102.5, 103.5],
            'close': [103.5, 104.5, 105.5],
            'volume': [1250, 1350, 1450],
        }).set_index('time')
        
        manager.update('VCB', data1)
        manager.update('VCB', data2)
        
        # Should keep the last version (from data2)
        start = dates[0]
        end = dates[-1]
        result = manager.get('VCB', start, end)
        
        assert len(result) == 5  # No duplicate rows
        # Check that duplicates used keep='last'
        assert result.loc[result.index == dates[2], 'close'].values[0] == 103.5
    
    def test_merge_sorts_by_time(self, manager):
        """Merging sorts data by time."""
        # Create non-sequential data
        dates_first = pd.date_range('2024-01-01', periods=3, freq='1h')
        dates_second = pd.date_range('2024-01-01 05:00', periods=3, freq='1h')
        
        data1 = pd.DataFrame({
            'time': dates_second,  # Later dates first
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200],
        }).set_index('time')
        
        data2 = pd.DataFrame({
            'time': dates_first,  # Earlier dates
            'open': [100, 101, 102],
            'high': [102, 103, 104],
            'low': [99, 100, 101],
            'close': [101, 102, 103],
            'volume': [1000, 1100, 1200],
        }).set_index('time')
        
        manager.update('VCB', data1)
        manager.update('VCB', data2)
        
        start = dates_first[0]
        end = dates_second[-1]
        result = manager.get('VCB', start, end)
        
        # Should be sorted by time
        assert list(result.index) == sorted(result.index)


class TestPartialRangeRetrieval:
    """Test retrieval of partial data ranges."""
    
    def test_get_partial_range(self, manager, sample_data):
        """Can retrieve partial time range from cached data."""
        manager.update('VCB', sample_data)
        
        # Request only first 5 items
        start = sample_data.index.min()
        end = start + pd.Timedelta(hours=4)
        
        result = manager.get('VCB', start, end)
        
        assert result is not None
        assert len(result) == 5
        assert result.index.min() == start
        assert result.index.max() == end
    
    def test_get_empty_range(self, manager, sample_data):
        """Returns None for completely out-of-range request."""
        manager.update('VCB', sample_data)
        
        # Request way in the future
        start = sample_data.index.max() + pd.Timedelta(days=10)
        end = start + pd.Timedelta(hours=1)
        
        result = manager.get('VCB', start, end)
        
        # Should return None or empty
        assert result is None or result.empty


class TestBTCUSDTRealDataFetching:
    """Test real data fetching for BTCUSDT cryptocurrency pair."""
    
    def test_get_with_resolution_btcusdt_realtime(self):
        """
        Test fetching real BTCUSDT data with 1-minute resolution.
        
        Scenario:
        - Symbol: BTCUSDT
        - Time Range: 2026-04-07 20:00:00 to 21:00:00 GMT+7
        - Resolution: 1 minute
        
        Validation:
        - Response data is not empty
        - Processed data contains OHLCV columns
        - Data rows > 0
        """
        manager = HistoricalDataManager()
        
        # Define time range: 2026-04-07 20:00:00 to 21:00:00 GMT+7
        # Convert GMT+7 to UTC: subtract 7 hours
        start_time_gmt7 = pd.Timestamp('2026-04-07 20:00:00', tz='UTC+07:00')
        end_time_gmt7 = pd.Timestamp('2026-04-07 21:00:00', tz='UTC+07:00')
        
        # Convert to UTC for data fetching
        start_time_utc = start_time_gmt7.tz_convert('UTC')
        end_time_utc = end_time_gmt7.tz_convert('UTC')
        
        print("\n" + "=" * 70)
        print("BTCUSDT Real Data Fetching Test")
        print("=" * 70)
        print(f"Symbol: BTCUSDT")
        print(f"Time Range (GMT+7): {start_time_gmt7} to {end_time_gmt7}")
        print(f"Time Range (UTC): {start_time_utc} to {end_time_utc}")
        print(f"Resolution: 1 minute")
        print("-" * 70)
        
        # Fetch data with resolution
        processed_df = manager.get_with_resolution(
            symbol='BTCUSDT',
            start_time=start_time_utc,
            end_time=end_time_utc,
            resolution=1
        )
        
        # Validation: Response is not empty
        assert processed_df is not None, "Data response should not be None"
        assert not processed_df.empty, "Data response should not be empty"
        
        print(f"Data Response Status: ✓ NOT EMPTY")
        print(f"Total Rows Retrieved: {len(processed_df)}")
        
        # Validation: Processed data is not empty
        assert len(processed_df) > 0, "Processed data should contain rows"
        
        print(f"Processed Data Status: ✓ NOT EMPTY")
        print(f"\nProcessed Data (first 10 rows):")
        print("-" * 70)
        print(processed_df.head(10).to_string())
        
        # Display summary statistics
        print("\n" + "-" * 70)
        print("Data Summary:")
        print(f"  Shape: {processed_df.shape}")
        print(f"  Time Range: {processed_df.index.min()} to {processed_df.index.max()}")
        print(f"  Columns: {list(processed_df.columns)}")
        print(f"  Open Price Range: {processed_df['open'].min():.2f} - {processed_df['open'].max():.2f}")
        print(f"  Close Price Range: {processed_df['close'].min():.2f} - {processed_df['close'].max():.2f}")
        print(f"  High Price Range: {processed_df['high'].min():.2f} - {processed_df['high'].max():.2f}")
        print(f"  Low Price Range: {processed_df['low'].min():.2f} - {processed_df['low'].max():.2f}")
        print(f"  Volume Range: {processed_df['volume'].min():.0f} - {processed_df['volume'].max():.0f}")
        print("=" * 70 + "\n")


def run_phase3_tests():
    """Run all Phase 3 integration tests."""
    print("=" * 70)
    print("Phase 3 Integration Tests - Data Caching Layer")
    print("=" * 70)
    
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-ra"
    ])
    
    return exit_code


if __name__ == "__main__":
    exit_code = run_phase3_tests()
    sys.exit(exit_code)
