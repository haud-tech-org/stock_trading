"""
Symbol Validator - Provider configuration registry for symbol support.

This module provides access to provider-specific symbol configurations.
Each provider is responsible for its own symbol validation logic.

Features:
- Registry pattern for efficient provider lookup
- Single source of truth: src/stockreports/config/data_provider_settings.py
- Provides configuration access to providers for validation

Note: Each provider implements validate_symbol() using its own rules.
This module provides configuration data only, not validation logic.
"""

from typing import Dict, List, Optional
from src.stockreports.config.loader import get_data_provider_settings


class SymbolValidator:
    """
    Provider symbol configuration registry.
    
    Provides centralized access to provider-defined symbol configurations.
    Each provider implements its own validation logic using validate_symbol().
    
    This class is used to look up which symbols are supported by each provider,
    but validation is delegated to the provider implementation.
    """
    
    @classmethod
    def _get_provider_config(cls, provider_name: str) -> Optional[Dict]:
        """
        Get provider configuration from settings.
        
        Args:
            provider_name (str): Provider name (case-insensitive)
        
        Returns:
            Dict: Provider configuration or None if not found
        """
        provider_name = provider_name.lower().strip()
        settings = get_data_provider_settings()
        config = settings.PROVIDER_SYMBOLS_CONFIG.get(provider_name)
        return config
    
    @classmethod
    def get_supported_symbols(cls, provider_name: str) -> List[str]:
        """
        Get list of supported symbols for a provider.
        
        Args:
            provider_name (str): Provider name
        
        Returns:
            List[str]: List of supported symbols
        
        Raises:
            ValueError: If provider not found
        """
        config = cls._get_provider_config(provider_name)
        if config is None:
            available = cls.list_providers()
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {available}"
            )
        return config.get("supported_symbols", [])
    
    @classmethod
    def get_config(cls, provider_name: str) -> Optional[Dict]:
        """
        Get full configuration for a provider.
        
        Args:
            provider_name (str): Provider name (case-insensitive)
        
        Returns:
            Dict: Provider configuration or None if not found
        """
        return cls._get_provider_config(provider_name)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """
        Get list of all registered providers.
        
        Returns:
            List[str]: Sorted list of provider names
        """
        settings = get_data_provider_settings()
        return sorted(list(settings.PROVIDER_SYMBOLS_CONFIG.keys()))
    
    @classmethod
    def get_all_configs(cls) -> Dict[str, Dict]:
        """
        Get all registered provider configurations.
        
        Returns:
            Dict[str, Dict]: All provider configurations
        """
        settings = get_data_provider_settings()
        return dict(settings.PROVIDER_SYMBOLS_CONFIG)
    
    @classmethod
    def validate_symbol(cls, provider_name: str, symbol: str) -> bool:
        """
        Check if symbol is in the provider's supported symbols list.
        
        This method checks if a symbol is listed as supported by a provider.
        It does NOT validate symbol format - that's each provider's responsibility.
        
        Args:
            provider_name (str): Provider name
            symbol (str): Symbol to check
        
        Returns:
            bool: True if symbol is in supported_symbols list
        
        Raises:
            ValueError: If provider not found or symbol not supported
        """
        if not symbol or not isinstance(symbol, str):
            raise ValueError(
                f"Symbol must be a non-empty string, got: {symbol}"
            )
        
        # Normalize symbol
        symbol = symbol.upper().strip()
        
        # Get provider config
        config = cls._get_provider_config(provider_name)
        if config is None:
            available = cls.list_providers()
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {available}"
            )
        
        # Get supported symbols for this provider
        supported_symbols = config.get("supported_symbols", [])
        
        # Check if symbol is supported
        if symbol not in supported_symbols:
            raise ValueError(
                f"Symbol '{symbol}' is not supported by provider '{provider_name}'. "
                f"Supported symbols: {supported_symbols}"
            )
        
        return True
