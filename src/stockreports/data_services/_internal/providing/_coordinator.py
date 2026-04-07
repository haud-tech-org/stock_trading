"""
Central coordinator for data providers.

The DataProviderCoordinator manages provider selection, switching, and coordinates
data retrieval across multiple providers. It acts as a single point of entry for
all data retrieval operations.
"""

import logging
from typing import Dict, Any, List, Union
import pandas as pd
import numpy as np

from src.stockreports.data_services._internal.providing._provider_factory import ProviderFactory
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._registry import register_all_providers
from src.stockreports.config.loader import get_data_provider_settings


class DataProviderCoordinator:
    """
    Central coordinator for managing data providers.
    
    Provides a unified interface for provider-specific data retrieval.
    
    Responsibilities:
    - Route data requests to appropriate providers
    - Cache provider instances
    - Validate symbol and configuration for providers
    """
    
    def __init__(self):
        """
        Initialize the stateless coordinator.
        
        This coordinator provides a unified interface for multi-provider data retrieval.
        All data operations require explicit provider specification - NO state management.
        """
        self.logger = logging.getLogger("DataProviderCoordinator")
        
        # Register all providers on first coordinator instantiation
        register_all_providers()
        
        # Local caching (keyed by Provider enum)
        self._provider_cache: Dict[Provider, BaseDataProvider] = {}
        
        self.logger.info("Initialized stateless DataProviderCoordinator")
    
    def _get_provider_for_symbol(self, symbol: str) -> Provider:
        """
        Detect the appropriate data provider for a given symbol by checking
        PROVIDER_SYMBOLS_CONFIG configuration.
        
        Strategy:
        1. Load PROVIDER_SYMBOLS_CONFIG from data_provider_settings
        2. Check enabled providers for supported symbols
        3. Return the provider that supports this symbol
        4. Raise error if symbol not supported by any enabled provider
        
        Args:
            symbol: Stock/crypto symbol (e.g., 'VCB', 'BTCUSDT', 'BTC/USDT')
        
        Returns:
            Provider enum indicating which provider handles this symbol
        
        Raises:
            ValueError: If symbol is not supported by any enabled provider
        """
        from src.stockreports.config.data_provider_settings import (
            PROVIDER_SYMBOLS_CONFIG,
            ENABLED_DATA_PROVIDERS
        )
        
        # Check each enabled provider's supported symbols
        for provider_name in ENABLED_DATA_PROVIDERS:
            if provider_name not in PROVIDER_SYMBOLS_CONFIG:
                continue
            
            provider_config = PROVIDER_SYMBOLS_CONFIG[provider_name]
            supported_symbols = provider_config.get("supported_symbols", [])
            
            # Check if symbol is in this provider's supported list
            if symbol in supported_symbols:
                # Map provider name to Provider enum
                if provider_name.lower() == "vietstock":
                    return Provider.VIETSTOCK
                elif provider_name.lower() == "binance":
                    return Provider.BINANCE
                elif provider_name.lower() == "binance_ccxt":
                    return Provider.BINANCE_CCXT
        
        # Symbol not found in any enabled provider
        raise ValueError(
            f"Symbol '{symbol}' is not supported by any enabled data provider. "
            f"Enabled providers: {ENABLED_DATA_PROVIDERS}. "
            f"Supported symbols: {self._get_all_supported_symbols()}"
        )
    
    def _get_all_supported_symbols(self) -> Dict[str, list]:
        """
        Helper to get all supported symbols grouped by enabled provider.
        Useful for error messages and debugging.
        
        Returns:
            Dict mapping provider names to their supported symbols
        """
        from src.stockreports.config.data_provider_settings import (
            PROVIDER_SYMBOLS_CONFIG,
            ENABLED_DATA_PROVIDERS
        )
        
        supported = {}
        for provider_name in ENABLED_DATA_PROVIDERS:
            if provider_name in PROVIDER_SYMBOLS_CONFIG:
                supported[provider_name] = PROVIDER_SYMBOLS_CONFIG[provider_name]["supported_symbols"]
        return supported
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        provider: Provider = None,
        resolution: int = 1
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for a symbol. Provider is auto-detected if not specified.
        
        Args:
            symbol (str): Stock/crypto symbol (e.g., 'VCB', 'BTC/USDT')
            from_timestamp (int): Start time as Unix timestamp
            to_timestamp (int): End time as Unix timestamp
            provider (Provider): Specific provider to use (as Provider enum).
                                If None, auto-detect from PROVIDER_SYMBOLS_CONFIG.
            resolution (int): Candle resolution in minutes (default: 1).
                             Supported values: 1, 5, 15, 30, 60, 240, 1440
                             Each provider converts to its own format internally.
        
        Returns:
            pd.DataFrame: Normalized OHLCV data with guaranteed type compatibility:
                - 'time' column: datetime64[ns] (converted from index if needed)
                - 'open', 'high', 'low', 'close': float64
                - 'volume': float64 (or int64 if original)
                - All values are valid numeric/datetime types (no NaN in critical fields)
        
        Raises:
            ValueError: If symbol is not supported by any enabled provider (when auto-detecting)
        """
        # Auto-detect provider if not specified
        if provider is None:
            try:
                provider = self._get_provider_for_symbol(symbol)
                self.logger.info(f"Auto-detected provider for {symbol}: {provider.value}")
            except ValueError as ve:
                self.logger.error(f"Provider detection failed for {symbol}: {ve}")
                return pd.DataFrame()
        
        provider_name = provider.value
        
        self.logger.info(
            f"Fetching {symbol} resolution={resolution}min via {provider_name} "
            f"({from_timestamp} to {to_timestamp})"
        )
        
        try:
            # Get provider instance
            prov = self._get_provider(provider)
            
            # Fetch data - provider internally converts resolution to its format
            df = prov.fetch_ohlcv(symbol, from_timestamp, to_timestamp, resolution)
            
            # *** STANDARDIZATION POINT ***
            # Ensure 'time' is the index (not a column) for consistency
            # across all downstream consumers (historical manager, executors, etc.)
            # This is the single point where format is standardized.
            # Migration requirement: time MUST be index for datetime operations.
            if 'time' in df.columns and df.index.name != 'time':
                # Convert 'time' column to index
                df = df.set_index('time')
                self.logger.debug(
                    f"Standardized DataFrame for {symbol}: converted 'time' from column to index"
                )
            elif df.index.name != 'time':
                # If index is neither named 'time' nor 'time' column exists, something is wrong
                self.logger.warning(
                    f"DataFrame for {symbol} has unexpected index: {df.index.name}. "
                    f"Columns: {df.columns.tolist()}"
                )
            
            # *** TYPE COMPATIBILITY VALIDATION ***
            # Ensure downstream processes receive compatible data types
            df = self._ensure_type_compatibility(df, symbol)
            
            self.logger.info(
                f"Successfully fetched {len(df)} candles for {symbol} via {provider_name}"
            )
            
            return df
        
        except Exception as e:
            self.logger.error(
                f"Failed to fetch {symbol} via {provider_name}: {e}"
            )
            raise
    
    def _ensure_type_compatibility(self, df: pd.DataFrame, symbol: str) -> pd.DataFrame:
        """
        VALIDATOR: Verify the returned DataFrame has correct types for all downstream processes.
        
        This method validates (does NOT convert) that:
        1. 'time' is the index (not a column)
        2. Index is pd.DatetimeIndex with pd.Timestamp elements
        3. OHLCV columns exist and are numeric
        4. No NaN values in critical fields ('time' index, 'close' column)
        5. No infinity values in any numeric column
        
        **IMPORTANT:** This is a VALIDATOR, not a converter. If types are incorrect,
        it raises ValueError. The provider is responsible for returning correct types.
        
        Args:
            df (pd.DataFrame): DataFrame from provider with 'time' as index
            symbol (str): Symbol for logging context
        
        Returns:
            pd.DataFrame: Same DataFrame (unchanged) after validation
        
        Raises:
            ValueError: If any type validation fails
        """
        if df.empty:
            return df
        
        try:
            # *** VALIDATION #1: 'time' must be the index (not a column) ***
            if df.index.name != 'time':
                raise ValueError(
                    f"Provider error for {symbol}: 'time' must be the index. "
                    f"Current index name: {df.index.name}. "
                    f"Available columns: {df.columns.tolist()}"
                )
            
            # *** VALIDATION #2: Index must be DatetimeIndex with pd.Timestamp elements ***
            # This is required for downstream processes that call .timestamp() method
            if not isinstance(df.index, pd.DatetimeIndex):
                raise ValueError(
                    f"Provider error for {symbol}: 'time' index must be pd.DatetimeIndex. "
                    f"Current type: {type(df.index).__name__}. "
                    f"Current dtype: {df.index.dtype}"
                )
            
            # Validate that index elements are pd.Timestamp (sample check first 3)
            # DatetimeIndex naturally contains pd.Timestamp elements
            sample_size = min(3, len(df))
            if sample_size > 0:
                sample_timestamps = df.index[:sample_size]
                if not all(isinstance(ts, pd.Timestamp) for ts in sample_timestamps):
                    raise ValueError(
                        f"Provider error for {symbol}: 'time' index elements are not pd.Timestamp. "
                        f"Sample types: {[type(ts).__name__ for ts in sample_timestamps]}"
                    )
            
            # *** VALIDATION #3: OHLCV columns must exist and be numeric ***
            required_numeric_cols = ['open', 'high', 'low', 'close', 'volume']
            missing_cols = [col for col in required_numeric_cols if col not in df.columns]
            
            if missing_cols:
                raise ValueError(
                    f"Provider error for {symbol}: Missing required OHLCV columns: {missing_cols}. "
                    f"Available columns: {df.columns.tolist()}"
                )
            
            # Validate numeric columns are actually numeric
            for col in required_numeric_cols:
                if not pd.api.types.is_numeric_dtype(df[col]):
                    raise ValueError(
                        f"Provider error for {symbol}: Column '{col}' must be numeric. "
                        f"Current dtype: {df[col].dtype}"
                    )
            
            # *** VALIDATION #4: No NaN in critical fields ***
            index_nan_count = df.index.isna().sum()
            if index_nan_count > 0:
                raise ValueError(
                    f"Provider error for {symbol}: Found {index_nan_count} NaN values in 'time' index. "
                    f"Provider must return complete time index."
                )
            
            close_nan_count = df['close'].isna().sum()
            if close_nan_count > 0:
                raise ValueError(
                    f"Provider error for {symbol}: Found {close_nan_count} NaN values in 'close' column. "
                    f"Provider must return complete close prices."
                )
            
            # *** VALIDATION #5: No infinity values ***
            for col in required_numeric_cols:
                col_inf = np.isinf(df[col]).sum()
                if col_inf > 0:
                    raise ValueError(
                        f"Provider error for {symbol}: Found {col_inf} infinity values in '{col}'. "
                        f"Provider must return finite values only."
                    )
            
            # *** FINAL VALIDATION: Log type summary (for debugging) ***
            self.logger.debug(
                f"Type validation passed for {symbol}. "
                f"Schema: time(index=DatetimeIndex[{df.index.dtype}]), "
                f"open({df['open'].dtype}), high({df['high'].dtype}), "
                f"low({df['low'].dtype}), close({df['close'].dtype}), "
                f"volume({df['volume'].dtype})"
            )
            
            return df
            
        except ValueError:
            # Re-raise ValueError as-is (validation failure)
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error during type validation for {symbol}: {e}"
            )
            raise ValueError(
                f"Type validation failed for {symbol}: {e}"
            )
    
    def list_available_providers(self) -> List[str]:
        """
        List all available providers.
        
        Returns:
            List[str]: List of provider names
        """
        return ProviderFactory.list_available_providers()
    
    def get_provider_instance(self, provider: Provider) -> BaseDataProvider:
        """
        Get provider instance for the specified provider.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            BaseDataProvider: Provider instance
        """
        return self._get_provider(provider)
    
    def validate_symbol(self, symbol: str, provider: Provider) -> bool:
        """
        Validate symbol with specified provider.
        
        Args:
            symbol (str): Symbol to validate
            provider (Provider): Provider enum to use for validation
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If symbol is invalid
        """
        prov = self._get_provider(provider)
        return prov.validate_symbol(symbol)
    
    def get_supported_timeframes(self, provider: Provider) -> List[str]:
        """
        Get supported timeframes for specified provider.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            List[str]: List of supported timeframes
        """
        prov = self._get_provider(provider)
        return prov.get_supported_timeframes()
    
    def validate_configuration(self, provider: Provider) -> bool:
        """
        Validate provider configuration.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            bool: True if configuration is valid
        """
        prov = self._get_provider(provider)
        return prov.validate_configuration()
    
    def _get_provider(self, provider: Provider) -> BaseDataProvider:
        """
        Get provider instance, with local caching.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            BaseDataProvider: Provider instance
        
        Raises:
            ValueError: If provider is not registered or not enabled
        """
        # Check if provider is enabled
        if not self._is_provider_enabled(provider):
            data_provider_settings = get_data_provider_settings()
            raise ValueError(
                f"Provider '{provider.value}' is not enabled in settings. "
                f"Enabled providers: {data_provider_settings.ENABLED_DATA_PROVIDERS}"
            )
        
        if provider not in self._provider_cache:
            self._provider_cache[provider] = ProviderFactory.get_provider(provider)
        
        return self._provider_cache[provider]
    
    def _is_provider_enabled(self, provider: Provider) -> bool:
        """
        Check if provider is enabled in settings via loader.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            bool: True if provider is enabled
        """
        # Read fresh from data_provider_settings via loader each time (allows dynamic updates during tests)
        data_provider_settings = get_data_provider_settings()
        return provider.value in data_provider_settings.ENABLED_DATA_PROVIDERS
    
    def clear_provider_cache(self) -> None:
        """Clear local provider cache."""
        self._provider_cache.clear()
        ProviderFactory.clear_cache()
        self.logger.info("Cleared provider cache")
    
    def get_provider_info(self, provider: Provider) -> Dict[str, Any]:
        """
        Get information about a provider including configuration.
        
        Args:
            provider (Provider): Provider enum
        
        Returns:
            Dict[str, Any]: Provider information and configuration
        """
        data_provider_settings = get_data_provider_settings()
        
        provider_name = provider.value
        
        # Get provider configuration from settings
        config = data_provider_settings.DATA_PROVIDER_CONFIG.get(provider_name, {})
        
        info = {
            "name": provider_name,
            "enabled": self._is_provider_enabled(provider),
            "supported_timeframes": self.get_supported_timeframes(provider),
            "configured": self.validate_configuration(provider),
            "config": {
                "timeout": config.get("timeout"),
                "retries": config.get("retries"),
                "cache_ttl": config.get("cache_ttl"),
                "description": config.get("description")
            }
        }
        return info
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check health and availability of all providers.
        
        Returns:
            Dict[str, Any]: Health status and configuration of each provider
        """
        data_provider_settings = get_data_provider_settings()
        
        health = {
            "available_providers": self.list_available_providers(),
            "enabled_providers": data_provider_settings.ENABLED_DATA_PROVIDERS,
            "provider_status": {}
        }
        
        for provider_name in self.list_available_providers():
            try:
                provider_enum = Provider.from_string(provider_name)
                is_configured = self.validate_configuration(provider_enum)
                is_enabled = self._is_provider_enabled(provider_enum)
                
                health["provider_status"][provider_name] = {
                    "available": True,
                    "configured": is_configured,
                    "enabled": is_enabled
                }
            except Exception as e:
                provider_enum = Provider.from_string(provider_name)
                health["provider_status"][provider_name] = {
                    "available": False,
                    "enabled": self._is_provider_enabled(provider_enum),
                    "error": str(e)
                }
        
        return health
