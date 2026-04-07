"""
Vietstock data provider - implements BaseDataProvider for Vietstock API.

This provider fetches historical OHLCV data from the Vietstock API and normalizes
it to the standard format for use by the data retrieval system.
"""

import logging
from typing import Optional
import pandas as pd
import pytz

from src.stockreports.config import loader
from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing.vietstock.normalizer import VietstockNormalizer
from src.stockreports.utils.api_request_utils import execute_api_request
from src.stockreports.utils.time_utils import get_market_timezone_str


# Get settings for API parameters
settings = loader.get_settings()


class VietstockProvider(BaseDataProvider):
    """
    Vietstock data provider implementation.
    
    Fetches OHLCV data from Vietstock API and normalizes it to standard format.
    Supports Vietnamese stock symbols (e.g., VN30, VNM, TPB, etc.).
    """
    
    # API endpoint for Vietstock
    API_BASE_URL = "https://api.vietstock.vn"
    
    def __init__(self):
        """
        Initialize Vietstock provider.
        
        Uses Provider.VIETSTOCK enum value as the provider name.
        """
        super().__init__(Provider.VIETSTOCK.value)
        self.normalizer = VietstockNormalizer()
        self.market_tz = pytz.timezone(get_market_timezone_str())
        self.logger.info(f"Initialized {self.provider_name} provider")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: int = 1
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Vietstock API.
        
        Args:
            symbol (str): Stock symbol (e.g., "VN30", "VNM", "TPB")
            from_timestamp (int): Start time as Unix timestamp in seconds
            to_timestamp (int): End time as Unix timestamp in seconds
            resolution (int): Candle resolution in minutes (default: 1).
                             Supported values: 1, 5, 15, 30, 60, 240, 1440
        
        Returns:
            pd.DataFrame: OHLCV data with timezone-aware datetime index
        
        Raises:
            ValueError: If symbol is not supported
            RuntimeError: If API request fails
        """
        # Validate inputs
        self.validate_symbol(symbol)
        
        self.logger.info(
            f"Fetching {symbol} resolution={resolution}min data from {from_timestamp} to {to_timestamp}"
        )
        
        try:
            # Resolution is already in minutes format that Vietstock API expects
            # Pass it directly without further conversion
            api_resolution = resolution
            
            # Prepare API parameters with resolution
            api_params = settings.API_PARAMS.copy()
            if api_resolution is not None:
                api_params["resolution"] = str(api_resolution)
            
            # Fetch data from Vietstock API with custom parameters
            raw_data = execute_api_request(
                symbol=symbol,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                custom_params=api_params
            )
            
            # Handle no-data response gracefully (API returned valid no_data status)
            # This is normal behavior for data gaps in market history
            if raw_data is None:
                self.logger.warning(
                    f"No data available for {symbol} from {from_timestamp} to {to_timestamp}. "
                    f"This may indicate a gap in market data (e.g., non-trading hours)."
                )
                # Return empty DataFrame with correct structure and timezone
                return pd.DataFrame(
                    columns=['open', 'high', 'low', 'close', 'volume'],
                    index=pd.DatetimeIndex([], name='time', tz=self.market_tz)
                )
            
            # Validate response is a dict (actual API error)
            if not isinstance(raw_data, dict):
                raise RuntimeError(f"Invalid response format from Vietstock API: {type(raw_data)}")
            
            # Normalize raw data to standard format
            df = self.normalizer.normalize(raw_data, symbol)
            
            self.logger.info(
                f"Successfully fetched {len(df)} candles for {symbol} resolution={resolution}min"
            )
            
            return df
        
        except Exception as e:
            self.logger.error(
                f"Error fetching data from Vietstock API for {symbol}: {e}"
            )
            raise RuntimeError(
                f"Failed to fetch {symbol} data from Vietstock: {str(e)}"
            )
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate that symbol is supported by Vietstock.
        
        Vietstock supports Vietnamese stock market symbols (1-5 alphanumeric characters).
        Examples: "VN30", "VN30F1M", "HPG", "ACB"
        
        Uses centralized configuration from SymbolConfigRegistry.
        
        Args:
            symbol (str): Symbol to validate
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If symbol is invalid
        """
        return self._validate_symbol_common(symbol)
    
    def get_supported_timeframes(self) -> list:
        """
        Get list of supported resolutions (in minutes).
        
        Returns:
            list: Supported resolution values in minutes
        """
        return [1, 5, 15, 30, 60, 240, 1440]
    
    def normalize_response(self, raw_data: dict) -> pd.DataFrame:
        """
        Normalize raw Vietstock API response to standard DataFrame format.
        
        Args:
            raw_data (dict): Raw API response containing OHLCV data
        
        Returns:
            pd.DataFrame: Normalized OHLCV DataFrame
        
        Raises:
            ValueError: If data format is invalid
        """
        # Extract symbol from raw data (required for validation)
        symbol = raw_data.get('s', 'UNKNOWN')
        
        try:
            return self.normalizer.normalize(raw_data, symbol)
        except Exception as e:
            self.logger.error(f"Error normalizing response for {symbol}: {e}")
            raise ValueError(f"Failed to normalize Vietstock response: {str(e)}")
    
    def validate_configuration(self) -> bool:
        """
        Validate provider configuration.
        
        Checks that:
        - API endpoint is accessible
        - Required dependencies are available
        - Configuration is valid
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            RuntimeError: If configuration is invalid
        """
        try:
            # Check that normalizer is initialized
            if not self.normalizer:
                raise RuntimeError("Normalizer not initialized")
            
            # Check that API base URL is valid
            if not self.API_BASE_URL or not self.API_BASE_URL.startswith("http"):
                raise RuntimeError(f"Invalid API base URL: {self.API_BASE_URL}")
            
            # Check that timezone is valid
            try:
                pytz.timezone(get_market_timezone_str())
            except pytz.exceptions.UnknownTimeZoneError:
                raise RuntimeError(f"Invalid timezone: {get_market_timezone_str()}")
            
            self.logger.info("Configuration validation passed")
            return True
        
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
