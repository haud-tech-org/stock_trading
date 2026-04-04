"""
Provider enumeration for centralized provider identification.

This module defines all available data providers as an enum, ensuring
a single source of truth for provider names throughout the application.
"""

from enum import Enum


class Provider(Enum):
    """
    Enumeration of available data providers.
    
    Each provider is identified by a unique name that is used consistently
    throughout the application instead of hardcoded strings.
    
    Examples:
        Provider.VIETSTOCK.value  # "vietstock"
        Provider.BINANCE.value    # "binance"
        Provider.BINANCE_CCXT.value  # "binance_ccxt"
    """
    
    VIETSTOCK = "vietstock"
    BINANCE = "binance"
    BINANCE_CCXT = "binance_ccxt"
    
    def __str__(self) -> str:
        """Return the provider name string."""
        return self.value
    
    @classmethod
    def from_string(cls, name: str) -> "Provider":
        """
        Get a Provider enum from string value.
        
        Args:
            name (str): Provider name (e.g., "vietstock", "binance")
        
        Returns:
            Provider: The corresponding Provider enum
        
        Raises:
            ValueError: If provider name is not recognized
        
        Examples:
            Provider.from_string("vietstock")  # Provider.VIETSTOCK
            Provider.from_string("binance")    # Provider.BINANCE
        """
        for provider in cls:
            if provider.value == name.lower():
                return provider
        raise ValueError(f"Unknown provider: {name}. Available: {', '.join(p.value for p in cls)}")
    
    @classmethod
    def get_all_names(cls) -> list:
        """
        Get list of all provider names.
        
        Returns:
            list: List of provider name strings
        
        Examples:
            Provider.get_all_names()  # ["vietstock", "binance", "binance_ccxt"]
        """
        return [p.value for p in cls]
