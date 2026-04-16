"""
Executor Configuration Service Adapter Layer - Backward Compatibility Bridge.

Provides backward-compatible interfaces that translate old API calls to
use the new ExecutorConfigurationOrchestrator service. This allows gradual migration
without breaking existing code.

Two-Phase Approach:
1. Old API stays the same but delegates to new service
2. Code is gradually updated to use new API directly
3. Old API can be deprecated once migration is complete
"""

import logging
from typing import Dict, Any, Optional

from .orchestrator import ExecutorConfigurationOrchestrator
from ...model import ApproachSymbolConfiguration
from .exceptions import ExecutorConfigurationNotFoundError



logger = logging.getLogger(__name__)


def get_configuration_v2(
    symbol: str,
    approach: str
) -> ApproachSymbolConfiguration:
    """
    Get configuration using the ExecutorConfigurationOrchestrator service.
    
    Recommended for new code. Provides full type safety and all features
    of the configuration service.
    
    Args:
        symbol: Trading symbol (e.g., "BTC/USDT:USDT", "VN30F1M")
        approach: Approach name (e.g., "REVERSAL_ANCHOR_SIGNAL_CANDLE", "VRA")
    
    Returns:
        ApproachSymbolConfiguration object
    
    Raises:
        ExecutorConfigurationNotFoundError: If configuration not found
    
    Example:
        config = get_configuration_v2(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
    """
    return ExecutorConfigurationOrchestrator.get(
        symbol=symbol,
        approach=approach
    )


def get_approach_executor_v2(
    config: ApproachSymbolConfiguration
) -> Any:
    """
    NEW API: Get executor using the new configuration service.
    
    Takes a configuration object and returns the appropriate executor
    instance pre-configured with all settings.
    
    Args:
        config: ApproachSymbolConfiguration object
    
    Returns:
        Configured executor instance
    
    Note:
        This is a placeholder. The actual implementation depends on
        the executor factory pattern used in the codebase.
    """
    # Note: Implementation depends on executor factory in the codebase
    # This function will be updated based on actual executor pattern
    logger.debug(
        f"Creating executor for {config.get_symbol()} "
        f"with {config.get_approach()} approach"
    )
    return None


def get_configuration_legacy(
    symbol: str,
    approach: str
) -> Dict[str, Any]:
    """
    OLD API ADAPTER: Maintain backward compatibility with existing code.
    
    This function maintains the old interface but delegates to the new
    ExecutorConfigurationOrchestrator internally. Code using this function
    continues to work without changes.
    
    Args:
        symbol: Trading symbol
        approach: Approach name
    
    Returns:
        Dictionary with configuration (backward compatible format)
    
    Deprecated:
        Use get_configuration_v2() instead for new code.
        This function will be removed in a future version.
    
    Note:
        Returns a dictionary instead of ApproachSymbolConfiguration
        to maintain compatibility with old code expecting dict access.
    """
    try:
        config = ExecutorConfigurationOrchestrator.get(
            symbol=symbol,
            approach=approach
        )
        
        # Convert to dictionary for backward compatibility
        return config.to_dict()
    
    except ExecutorConfigurationNotFoundError:
        logger.warning(
            f"Configuration not found: symbol={symbol}, approach={approach}"
        )
        return {}


class ConfigurationAdapter:
    """
    Configuration adapter for gradual migration from old to new system.
    
    This class provides methods to bridge old and new configuration
    systems, making it easier to gradually migrate code.
    
    Usage:
        adapter = ConfigurationAdapter()
        
        # Old way (still works)
        config_dict = adapter.get_approach_config_legacy(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
        
        # New way (recommended)
        config_obj = adapter.get_approach_config(
            symbol="BTC/USDT:USDT",
            approach="REVERSAL_ANCHOR_SIGNAL_CANDLE"
        )
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def get_approach_config_legacy(
        self,
        symbol: str,
        approach: str
    ) -> Dict[str, Any]:
        """
        Get approach configuration (legacy format).
        
        Returns dictionary for backward compatibility with old code
        that expects: config = APPROACH_CONFIG[approach]
        """
        try:
            config = ExecutorConfigurationOrchestrator.get(symbol=symbol, approach=approach)
            return config.get_approach_config()
        except ExecutorConfigurationNotFoundError:
            self.logger.warning(
                f"Configuration not found for {symbol}:{approach}"
            )
            return {}
    
    def get_approach_config(
        self,
        symbol: str,
        approach: str
    ) -> ApproachSymbolConfiguration:
        """
        Get approach configuration.
        
        Returns ApproachSymbolConfiguration object with full type safety
        and all features of the configuration service.
        """
        return ExecutorConfigurationOrchestrator.get(symbol=symbol, approach=approach)
    
    def get_resolution(
        self,
        symbol: str,
        approach: str
    ) -> int:
        """
        Get resolution for an approach.
        
        Replaces: APPROACH_RESOLUTION_MAPPING[approach]
        """
        config = ExecutorConfigurationOrchestrator.get(symbol=symbol, approach=approach)
        return config.get_resolution()
    
    def get_trading_hours(
        self,
        symbol: str,
        approach: str
    ) -> Dict[str, Any]:
        """
        Get trading hours for a symbol-approach combination.
        
        Replaces: TRADING_HOURS[market_code]
        """
        config = ExecutorConfigurationOrchestrator.get(symbol=symbol, approach=approach)
        trading_hours = config.get_trading_hours()
        
        # Convert to dictionary format for backward compatibility
        return {
            "name": trading_hours.name,
            "timezone": trading_hours.timezone,
            "sessions": [
                {
                    "name": session.name,
                    "start": session.start_time,
                    "end": session.end_time
                }
                for session in trading_hours.sessions
            ]
        }
    
    @classmethod
    def get_supported_symbols(cls) -> list:
        """Get all supported symbols"""
        return ExecutorConfigurationOrchestrator.get_supported_symbols()
    
    @classmethod
    def get_supported_approaches(cls, symbol: str) -> list:
        """Get all supported approaches for a symbol"""
        return ExecutorConfigurationOrchestrator.get_supported_approaches(symbol)


# Singleton instance for convenient access
_adapter_instance = None

def get_adapter() -> ConfigurationAdapter:
    """Get singleton adapter instance"""
    global _adapter_instance
    if _adapter_instance is None:
        _adapter_instance = ConfigurationAdapter()
    return _adapter_instance
