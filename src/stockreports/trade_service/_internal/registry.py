"""
TradingPlatformRegistry - Handles registration and lookup of trading platforms.
"""

# --- Python Standard Library ---
import logging
from typing import Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from .platforms.demo_trading import DemoTrading
from .platforms.binance_perpetual_trading import BinancePerpetualTrading
from .base_trading import BaseTrading

logger = logging.getLogger(__name__)

class TradingPlatformRegistry:
    """
    Registry for trading platform implementations.
    """
    _platforms = None  # class-level

    def __init__(self):
        # Example: hardcoded mapping; replace with config-driven logic as needed
        if TradingPlatformRegistry._platforms is None:
            TradingPlatformRegistry._platforms = {
                'BTCUSDT-PERP': BinancePerpetualTrading,
                # Add more symbol-to-platform mappings here
            }

    def get_platform_for_symbol(self, symbol: str) -> Optional[BaseTrading]:
        """
        Returns a new platform instance for the given symbol, or None if the
        symbol has no registered platform.

        Args:
            symbol: The trading symbol (e.g. 'BTCUSDT-PERP').

        Returns:
            A fresh ``BaseTrading`` instance, or ``None`` if the symbol is
            not registered.
        """
        platform_class = TradingPlatformRegistry._platforms.get(symbol)
        if platform_class is None:
            logger.warning(f"No trading platform registered for symbol '{symbol}'. Returning None.")
            return None
        return platform_class()
