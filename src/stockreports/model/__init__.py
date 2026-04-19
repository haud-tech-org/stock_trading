"""
Centralized data models for the stock trading system.

This package contains shared data models that are used across the application
to ensure consistency and type safety.

Models:
    - Session: Normalized representation of a trading session
    - TradingHoursConfig: Complete trading hours with multiple sessions and timezone
    - ApproachSymbolConfiguration: Complete executor configuration for symbol-approach combo

Usage:
    from src.stockreports.model import Session, TradingHoursConfig, ApproachSymbolConfiguration
    
    # Create a configuration
    config = ApproachSymbolConfiguration(...)
    
    # Access trading hours
    trading_hours = config.get_trading_hours()
"""

from .session import Session
from .trading_hours import TradingHoursConfig
from .configuration import ApproachSymbolConfiguration

__all__ = [
    'Session',
    'TradingHoursConfig',
    'ApproachSymbolConfiguration',
]

