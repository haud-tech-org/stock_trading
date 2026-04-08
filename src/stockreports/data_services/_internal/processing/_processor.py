# src/stockreports/data_processor/data_processor.py
"""
DataProcessor Module

Transforms raw OHLCV data through a configurable pipeline:
1. Timezone conversion (if enabled)
2. Price adjustment (if enabled)
"""

import logging
import pandas as pd
from typing import Optional

from src.stockreports.alert.common.validation.price_adjustment import adjust_prices_by_symbol
from src.stockreports.utils.time_utils import convert_dataframe_to_market_timezone


logger = logging.getLogger(__name__)


class DataProcessor:
    """Processes raw OHLCV data through a transformation pipeline."""
    
    def __init__(self, symbol: str):
        """
        Initialize DataProcessor for a specific symbol.
        
        Args:
            symbol: Stock symbol (e.g., 'VCB', 'VN30F1M')
        """
        from src.stockreports.data_services._internal.processing._settings import get_processor_settings
        
        self.symbol = symbol
        self.settings = get_processor_settings()
    
    def process(self, df: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        Process raw OHLCV data through the transformation pipeline.
        
        Args:
            df: Raw OHLCV DataFrame with datetime index
            
        Returns:
            Processed DataFrame with transformations applied
        """
        try:
            # Apply timezone conversion if enabled
            if self.settings.is_enabled_timezone_conversion():
                df = self._convert_timezone(df)
            
            # Apply price adjustment if enabled
            if self.settings.is_enabled_price_adjustment():
                df = self._adjust_prices(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error processing data for '{self.symbol}': {str(e)}", exc_info=True)
            return None
    
    def _convert_timezone(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert DataFrame index to market timezone by calling time_utils."""
        try:
            # Orchestration: call time_utils to handle timezone conversion logic
            df = convert_dataframe_to_market_timezone(df)
            logger.debug(f"Timezone conversion completed for '{self.symbol}'")
            return df
            
        except Exception as e:
            logger.error(f"Timezone conversion failed for '{self.symbol}': {str(e)}", exc_info=True)
            raise
    
    def _adjust_prices(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply symbol-specific price adjustments."""
        try:
            df = adjust_prices_by_symbol(df, self.symbol)
            logger.debug(f"Price adjustment completed for '{self.symbol}'")
            return df
            
        except Exception as e:
            logger.error(f"Price adjustment failed for '{self.symbol}': {str(e)}", exc_info=True)
            raise

