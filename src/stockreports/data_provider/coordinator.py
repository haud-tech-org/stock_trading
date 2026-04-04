"""
Central coordinator for data providers.

The DataProviderCoordinator manages provider selection, switching, and coordinates
data retrieval across multiple providers. It acts as a single point of entry for
all data retrieval operations.
"""

import logging
from typing import Dict, Any, List, Union
import pandas as pd

from src.stockreports.data_provider.provider_factory import ProviderFactory
from src.stockreports.data_provider.providers import Provider
from src.stockreports.data_provider.base_provider import BaseDataProvider
from src.stockreports.data_provider.registry import register_all_providers
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
            pd.DataFrame: Normalized OHLCV data (empty DataFrame if error)
        
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
            # Ensure 'time' is always a column (not index) for consistency
            # across all downstream consumers (historical manager, executors, etc.)
            # This is the single point where format is standardized.
            if df.index.name == 'time':
                df = df.reset_index()
                self.logger.debug(
                    f"Standardized DataFrame for {symbol}: converted 'time' from index to column"
                )
            
            self.logger.info(
                f"Successfully fetched {len(df)} candles for {symbol} via {provider_name}"
            )
            
            return df
        
        except Exception as e:
            self.logger.error(
                f"Failed to fetch {symbol} via {provider_name}: {e}"
            )
            raise
    
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
