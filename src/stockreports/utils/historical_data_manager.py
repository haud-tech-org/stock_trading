"""
Backward compatibility module for HistoricalDataManager.

This module has been moved to src.stockreports.data_services._internal.fetching._manager
and is now accessed through the public DataServiceOrchestrator API.

This file exists ONLY for backward compatibility with existing code and tests.
New code should use: from src.stockreports.data_services import DataServiceOrchestrator
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "Importing from src.stockreports.utils.historical_data_manager is deprecated. "
    "Please use: from src.stockreports.data_services import DataServiceOrchestrator",
    DeprecationWarning,
    stacklevel=2
)

# Re-export from new location for backward compatibility
from src.stockreports.data_services._internal.fetching._manager import (
    HistoricalDataManager,
    get_historical_data,
    update_historical_data,
    get_manager,
)

__all__ = [
    'HistoricalDataManager',
    'get_historical_data',
    'update_historical_data',
    'get_manager',
]
