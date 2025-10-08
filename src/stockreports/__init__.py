"""
StockReports - Multi-symbol stock market data processing and reporting system.

A comprehensive Python package for processing HAR files, extracting stock market data,
and generating detailed reports with support for multiple symbols and dynamic column detection.

Key Features:
- Multi-HAR file processing
- Dynamic symbol detection
- Vietnam timezone support
- Comprehensive reporting
- Extensible architecture

Example:
    Basic usage:
    
    ```python
    from stockreports import HARExtractor, StockDataAggregator
    
    # Extract data from HAR files
    extractor = HARExtractor("path/to/har/files")
    extractor.extract_all()
    
    # Generate reports
    aggregator = StockDataAggregator("path/to/responses")
    aggregator.generate_reports()
    ```
"""

__version__ = "1.0.0"
__author__ = "Stock Analysis Team"
__email__ = "team@stockreports.com"

from .utils import data_utils

__all__ = [
    "data_utils"
]