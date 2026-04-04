"""
Provider Factory - Creates and manages data provider instances.

Implements the Factory pattern with a registry of available providers.
Handles provider instantiation, caching, and configuration validation.
"""

import logging
from typing import Dict, Optional, Type, List

from src.stockreports.data_provider.base_provider import BaseDataProvider
from src.stockreports.data_provider.providers import Provider


class ProviderFactory:
    """
    Factory for creating and managing data provider instances.
    
    Uses a registry pattern to support extensibility.
    Implements singleton pattern per provider (instance caching).
    """
    
    # Provider registry mapping provider enums to classes
    _providers: Dict[Provider, Type[BaseDataProvider]] = {}
    
    # Cached instances (singleton per provider)
    _instances: Dict[Provider, BaseDataProvider] = {}
    
    logger = logging.getLogger(__name__)
    
    @classmethod
    def get_provider(cls, provider_name: Provider) -> Optional[BaseDataProvider]:
        """
        Get or create a provider instance.
        
        Implements singleton pattern per provider - multiple calls
        with the same provider_name return the same instance.
        
        Args:
            provider_name: Provider enum (e.g., Provider.VIETSTOCK, Provider.BINANCE)
        
        Returns:
            Provider instance or None if not found
            
        Raises:
            ValueError: If provider_name is not registered
            RuntimeError: If provider configuration is invalid
        """
        # Check if provider is registered
        if provider_name not in cls._providers:
            available = cls.list_available_providers()
            raise ValueError(
                f"Unknown provider: '{provider_name.value}'. "
                f"Available providers: {available}"
            )
        
        # Return cached instance if it exists
        if provider_name in cls._instances:
            cls.logger.debug(f"Returning cached instance for provider: {provider_name.value}")
            return cls._instances[provider_name]
        
        # Create new instance (providers don't take provider_name as parameter)
        cls.logger.info(f"Creating new instance for provider: {provider_name.value}")
        provider_class = cls._providers[provider_name]
        instance = provider_class()
        
        # Validate configuration
        if not instance.validate_configuration():
            raise RuntimeError(
                f"Provider '{provider_name.value}' configuration is invalid. "
                f"Please check settings and environment variables."
            )
        
        # Cache the instance
        cls._instances[provider_name] = instance
        cls.logger.info(f"Provider instance created and cached: {provider_name.value}")
        
        return instance
    
    @classmethod
    def list_available_providers(cls) -> List[str]:
        """
        Return list of available provider names.
        
        Returns:
            List of registered provider name strings
        """
        return sorted([p.value for p in cls._providers.keys()])
    
    @classmethod
    def register_provider(
        cls,
        name: Provider,
        provider_class: Type[BaseDataProvider]
    ) -> None:
        """
        Register a new provider class in the factory.
        
        Args:
            name: Provider enum
            provider_class: Provider class extending BaseDataProvider
        """
        # Validate that provider_class extends BaseDataProvider
        if not issubclass(provider_class, BaseDataProvider):
            raise TypeError(
                f"Provider class must extend BaseDataProvider, "
                f"got {provider_class}"
            )
        
        cls._providers[name] = provider_class
        # Clear cached instances so they're recreated with new registration
        cls._instances.clear()
        
        cls.logger.info(f"Provider registered: {name.value} -> {provider_class.__name__}")
    
    @classmethod
    def clear_cache(cls) -> None:
        """
        Clear all cached provider instances.
        
        Useful for testing or when you want to force recreation.
        """
        cls._instances.clear()
        cls.logger.debug("Provider instance cache cleared")
    
    @classmethod
    def get_provider_info(cls, provider_name: Provider) -> Optional[Dict]:
        """
        Get information about a registered provider.
        
        Args:
            provider_name: Provider enum
        
        Returns:
            Dict with provider info or None
        """
        if provider_name not in cls._providers:
            return None
        
        provider_class = cls._providers[provider_name]
        
        return {
            'name': provider_name.value,
            'class': provider_class.__name__,
            'module': provider_class.__module__,
            'cached': provider_name in cls._instances,
        }
