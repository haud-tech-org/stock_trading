"""
TradingCoordinator - Determines the correct trading platform for a symbol.
"""

# --- Python Standard Library ---
import logging
from typing import Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertData
from .base_trading import BaseTrading
from .registry import TradingPlatformRegistry

logger = logging.getLogger(__name__)

class TradingCoordinator:
    """
    Determines the correct trading platform for a given symbol (from AlertData).
    """

    _registry = None  # class-level singleton

    def __init__(self):
        if TradingCoordinator._registry is None:
            TradingCoordinator._registry = TradingPlatformRegistry()

    def get_trading_platform(self, alert: AlertData) -> Optional[BaseTrading]:
        """
        Returns the correct trading platform instance for the alert's symbol,
        or ``None`` if the symbol has no registered platform.

        Args:
            alert (AlertData): Alert data containing symbol and order info.

        Returns:
            BaseTrading instance, or None if no platform is registered for the symbol.
        """
        symbol = alert.symbol
        platform = TradingCoordinator._registry.get_platform_for_symbol(symbol)
        if platform is None:
            logger.warning(
                f"No trading platform found for symbol '{symbol}'. "
                f"Order will not be placed."
            )
        return platform
