"""
Base provider abstract class defining the provider interface.

All data providers must inherit from this class and implement all abstract methods.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import pandas as pd
import logging

from src.stockreports.data_provider.validation import SymbolValidator
from src.stockreports.data_provider.providers import Provider


class BaseDataProvider(ABC):
    """
    Abstract base class for data providers.
    
    All providers must implement this interface to ensure consistent behavior
    across different data sources.
    
    Attributes:
        provider_name (str): Instance property defining the provider identifier
        logger (logging.Logger): Logger instance for this provider
    """
    
    def __init__(self, provider_name: str):
        """
        Initialize the data provider.
        
        Args:
            provider_name (str): Name identifier for this provider (from Provider enum).
        """
        self.provider_name = provider_name
        self.logger = logging.getLogger(f"DataProvider.{provider_name}")
    
    def get_provider_name(self) -> str:
        """
        Get the provider name for this provider instance.
        
        Returns:
            str: Provider name identifier
        """
        return self.provider_name
    
    @abstractmethod
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: int = 1
    ) -> pd.DataFrame:
        """
        Fetch OHLCV (Open, High, Low, Close, Volume) data for a symbol.
        
        Args:
            symbol (str): Symbol identifier (format depends on provider)
                         Examples: "VN30" (Vietstock), "BTC/USDT" (Binance)
            from_timestamp (int): Start time as Unix timestamp in seconds
            to_timestamp (int): End time as Unix timestamp in seconds
            resolution (int): Candle resolution in minutes (default: 1).
                             Supported values: 1, 5, 15, 30, 60, 240, 1440
                             Each provider converts this to its own timeframe format internally.
                             Examples:
                             - 1 → Vietstock: "1", Binance: "1m"
                             - 60 → Vietstock: "60", Binance: "1h"
                             - 1440 → Vietstock: "D", Binance: "1d"
        
        Returns:
            pd.DataFrame: DataFrame with columns [time, open, high, low, close, volume]
                         - time: datetime64[ns] with timezone (market timezone)
                         - open/high/low/close: float (price values)
                         - volume: int (trading volume)
        
        Raises:
            ValueError: If resolution is not supported by this provider
            Exception: If API request fails or data cannot be retrieved
        """
        pass
    
    @abstractmethod
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate symbol format for this provider.
        
        Args:
            symbol (str): Symbol to validate
        
        Returns:
            bool: True if symbol format is valid, False otherwise
        
        Examples:
            VietstockProvider: "VN30", "VN30F1M" → True, "BTC/USDT" → False
            BinanceProvider: "BTC/USDT", "ETH/USDT" → True, "VN30" → False
        """
        pass
    
    @abstractmethod
    def get_supported_timeframes(self) -> List[str]:
        """
        Get list of supported timeframe strings for this provider.
        
        Returns:
            List[str]: List of supported timeframe identifiers
        
        Examples:
            VietstockProvider: ["1", "5", "15", "60", "D"]
            BinanceProvider: ["1m", "5m", "15m", "1h", "1d", "1w", "1M"]
        """
        pass
    
    @abstractmethod
    def normalize_response(self, raw_data: Any) -> pd.DataFrame:
        """
        Convert provider-specific response to standard OHLCV DataFrame.
        
        This method handles:
        - Parsing timestamps and converting to seconds
        - Localizing to UTC
        - Converting to market timezone (Asia/Ho_Chi_Minh)
        - Extracting and validating OHLCV columns
        - Volume conversion to standard format
        
        Args:
            raw_data (Any): Raw response from provider API
                           Format depends on provider:
                           - Vietstock: dict {s, t, o, h, l, c, v}
                           - Binance: list of lists [[ts_ms, o, h, l, c, v], ...]
        
        Returns:
            pd.DataFrame: Normalized DataFrame with columns [time, open, high, low, close, volume]
                         Empty DataFrame if input is invalid
        
        Notes:
            - All timestamps must be timezone-aware (market timezone)
            - No NaN values should be present
            - Volume should be integer type
            - Prices should be float type
        """
        pass
    
    def validate_configuration(self) -> bool:
        """
        Validate provider configuration (credentials, URLs, etc).
        
        This method is called during provider initialization to ensure
        all required configuration is available before attempting API calls.
        
        Returns:
            bool: True if configuration is valid, False otherwise
        
        Override this method in subclasses to check provider-specific requirements.
        Default implementation returns True (no validation).
        """
        return True
    
    def _validate_symbol_common(self, symbol: str) -> bool:
        """
        Validate symbol against provider's supported symbols list.
        
        This helper validates that a symbol is in the provider's supported_symbols
        configuration. Each provider can call this method to leverage the centralized
        configuration, or implement custom validation logic.
        
        Validates symbol according to provider configuration defined in:
            src/stockreports/config/data_provider_settings.py
        
        Args:
            symbol (str): Symbol to validate
        
        Returns:
            bool: True if symbol is in supported_symbols list
        
        Raises:
            ValueError: If symbol is not supported by this provider
            RuntimeError: If provider not registered in configuration
        
        Example Usage (in derived provider):
            def validate_symbol(self, symbol: str) -> bool:
                # Call to check against supported_symbols config
                self._validate_symbol_common(symbol)
                # Add any additional custom validation here
                return True
        """
        try:
            result = SymbolValidator.validate_symbol(self.provider_name, symbol)
            self.logger.debug(f"Symbol '{symbol}' validated successfully")
            return result
        except ValueError as e:
            self.logger.warning(f"Symbol validation failed: {e}")
            raise
        except RuntimeError as e:
            self.logger.error(f"Provider not registered in SymbolValidator: {e}")
            raise
