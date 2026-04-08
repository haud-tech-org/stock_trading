"""
DataServiceOrchestrator - Main public API for data services.

This module provides a clean, unified interface for external code to access
data fetching, processing, and caching services. All internal implementation
details are hidden behind this facade.

Architecture:
- Public API: DataServiceOrchestrator is the ONLY export from data_services
- Internal: All implementation details hidden in _internal/ package
- Pattern: Facade pattern wraps internal components
"""

import logging
from typing import Optional
import pandas as pd

from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager

logger = logging.getLogger(__name__)


class DataServiceOrchestrator:
    """
    Unified public API for data services.
    
    This orchestrator provides a clean interface for fetching historical OHLCV data
    with intelligent caching, automatic provider selection, and data processing.
    
    All internal complexity is hidden behind this facade. External code
    should ONLY import DataServiceOrchestrator, never access internal modules.
    
    Example:
        >>> orchestrator = DataServiceOrchestrator()
        >>> data = orchestrator.fetch_and_process(
        ...     symbol='VCB',
        ...     start_time=pd.Timestamp('2024-01-01'),
        ...     end_time=pd.Timestamp('2024-12-31'),
        ...     resolution=1
        ... )
    """
    
    def __init__(self):
        """Initialize the orchestrator with internal manager."""
        self._manager = HistoricalDataManager()
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized DataServiceOrchestrator")
    
    def fetch_and_process(
        self,
        symbol: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        resolution: int = 1,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch and process OHLCV data for a symbol.
        
        Handles the complete pipeline:
        1. Checks cache for existing data
        2. Fetches missing data from provider (auto-detected from symbol)
        3. Processes data (timezone conversion, price adjustment)
        4. Merges with cache and returns
        
        Args:
            symbol: Stock symbol (e.g., 'VCB', 'VN30F1M')
            start_time: Start time as pd.Timestamp
            end_time: End time as pd.Timestamp
            resolution: Candle resolution in minutes (default: 1)
            
        Returns:
            Processed OHLCV DataFrame or None if fetch failed
        """
        try:
            return self._manager.get_with_resolution(
                symbol=symbol,
                start_time=start_time,
                end_time=end_time,
                resolution=resolution,
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch and process {symbol}: {e}")
            return None
