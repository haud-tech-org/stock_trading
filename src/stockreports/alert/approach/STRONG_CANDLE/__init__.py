# src/stockreports/alert/approach/STRONG_CANDLE/__init__.py
"""
STRONG_CANDLE Alert Approach Package.

Exports:
- StrongCandleExecutor: Main executor for alert detection
- StrongCandleAnalyzer: Pure calculation functions
- StrongCandleValidator: Pure validation functions
- StrongCandleSettings: Configuration settings
"""

from .executor import StrongCandleExecutor
from .analyzer import StrongCandleAnalyzer
from .validator import StrongCandleValidator
from .settings import StrongCandleSettings

__all__ = [
    'StrongCandleExecutor',
    'StrongCandleAnalyzer',
    'StrongCandleValidator',
    'StrongCandleSettings'
]
