"""
Provider initialization and registration.

This module handles the registration of all available data providers
with the ProviderFactory.
"""

from src.stockreports.data_provider.provider_factory import ProviderFactory
from src.stockreports.data_provider.providers import Provider
from src.stockreports.data_provider.vietstock.provider import VietstockProvider
from src.stockreports.data_provider.binance.api_provider import BinanceAPIProvider
from src.stockreports.data_provider.binance.ccxt_provider import BinanceCCXTProvider


def register_all_providers() -> None:
    """
    Register all available data providers with the factory.
    
    This function should be called once during application initialization
    to ensure all providers are registered and ready for use.
    
    Raises:
        ValueError: If a provider registration fails
    """
    # Register Vietstock provider
    try:
        ProviderFactory.register_provider(Provider.VIETSTOCK, VietstockProvider)
    except ValueError as e:
        raise ValueError(f"Failed to register Vietstock provider: {e}")
    
    # Register Binance REST API provider
    try:
        ProviderFactory.register_provider(Provider.BINANCE, BinanceAPIProvider)
    except ValueError as e:
        raise ValueError(f"Failed to register Binance API provider: {e}")
    
    # Register Binance CCXT provider (optional - depends on ccxt library)
    try:
        ProviderFactory.register_provider(Provider.BINANCE_CCXT, BinanceCCXTProvider)
    except ValueError as e:
        raise ValueError(f"Failed to register Binance CCXT provider: {e}")
    except RuntimeError as e:
        # CCXT might not be installed - log and continue
        import logging
        logger = logging.getLogger("ProviderRegistry")
        logger.warning(f"Could not register CCXT provider (optional): {e}")


def get_provider(name: Provider):
    """
    Get a provider instance by name.
    
    Convenience function that calls ProviderFactory.get_provider().
    Converts string provider names to Provider enum if needed.
    
    Args:
        name (Provider): Provider enum (e.g., Provider.VIETSTOCK, Provider.BINANCE, Provider.BINANCE_CCXT)
    
    Returns:
        BaseDataProvider: Provider instance
    
    Raises:
        ValueError: If provider is not registered
    """
    # If a string is passed (for backward compatibility), convert it to Provider enum
    if isinstance(name, str):
        name = Provider.from_string(name)
    
    return ProviderFactory.get_provider(name)


def list_providers() -> list:
    """
    List all registered providers.
    
    Convenience function that calls ProviderFactory.list_available_providers().
    
    Returns:
        list: List of provider names
    """
    return ProviderFactory.list_available_providers()
