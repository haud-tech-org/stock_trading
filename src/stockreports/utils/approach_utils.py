"""
Utilities for managing alert approaches and executor instantiation.

Provides centralized functions for:
- Resolving approaches configured for a symbol
- Loading and instantiating approach executors
"""

import importlib
import logging
from typing import Optional

from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.executor import Executor

# Get settings
settings = loader.get_settings()

# Setup logger
logger = logging.getLogger(__name__)


def get_approaches_for_symbol(symbol: str) -> Optional[list[Approach]]:
    """
    Gets the list of approaches to run for a specific symbol.
    
    Returns approaches ONLY if symbol-specific configuration exists in SYMBOL_ALERT_APPROACHES.
    Otherwise returns None (symbol has no alerts configured).
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
    
    Returns:
        list[Approach]: List of Approach constants to run for this symbol, or None if not configured
        
    Raises:
        ValueError: If approach string cannot be converted to Approach constant
    """
    # Only priority 1: Symbol-specific configuration
    symbol_config = getattr(settings, 'SYMBOL_ALERT_APPROACHES', {})
    if isinstance(symbol_config, dict) and symbol in symbol_config:
        approaches = symbol_config[symbol]
        # Convert strings to Approach constants
        approach_constants = [Approach.from_string(a) for a in approaches if a]
        logger.info(f"Symbol-specific approaches for '{symbol}': {approach_constants}")
        return approach_constants
    
    # Symbol not configured
    logger.warning(f"Symbol '{symbol}' has no approaches configured in SYMBOL_ALERT_APPROACHES. Skipping...")
    return None


def get_approach_executor(symbol: str, approach: Approach, resolution: int) -> Optional[Executor]:
    """
    Dynamically loads and instantiates an executor for a specific approach.
    
    Converts approach constant (e.g., 'REVERSAL_ANCHOR_SIGNAL_CANDLE') to:
    1. Module path: src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.executor
    2. Class name: ReversalAnchorSignalCandleExecutor
    
    Args:
        symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
        approach: Approach constant (e.g., Approach.REVERSAL_ANCHOR_SIGNAL_CANDLE)
        resolution: Data resolution in minutes
    
    Returns:
        Executor: Instantiated executor of appropriate type, or None if loading failed
        
    Example:
        executor = get_approach_executor('BTC/USDT:USDT', Approach.VRA, 60)
        if executor:
            result = executor.run(df=price_data, new_candle_count=10)
    """
    try:
        # Build module path from approach constant
        # Example: 'REVERSAL_ANCHOR_SIGNAL_CANDLE' → 'src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.executor'
        module_path = f"src.stockreports.alert.approach.{approach.upper()}.executor"
        executor_module = importlib.import_module(module_path)
        
        # Convert approach to class name
        # Example: 'REVERSAL_ANCHOR_SIGNAL_CANDLE' → 'ReversalAnchorSignalCandleExecutor'
        class_name_parts = [part.capitalize() for part in approach.split('_')]
        executor_class_name = "".join(class_name_parts) + "Executor"
        executor_class = getattr(executor_module, executor_class_name)
        
        # Instantiate executor with symbol, approach constant, and resolution (all mandatory)
        return executor_class(symbol, approach, resolution)
    
    except (ImportError, AttributeError) as e:
        logger.error(f"Could not load approach '{approach}' for symbol '{symbol}'. Error: {e}")
        return None
