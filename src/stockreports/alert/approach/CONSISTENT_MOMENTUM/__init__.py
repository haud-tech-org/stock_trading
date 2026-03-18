# src/stockreports/alert/approach/CONSISTENT_MOMENTUM/__init__.py
"""
CONSISTENT_MOMENTUM Alert Approach Package.

Exports:
- ConsistentMomentumExecutor: Main executor for alert detection
- ConsistentMomentumAnalyzer: Pure calculation functions
- ConsistentMomentumValidator: Pure validation functions
- ConsistentMomentumSettings: Configuration settings
"""

from .executor import ConsistentMomentumExecutor
from .analyzer import ConsistentMomentumAnalyzer
from .validator import ConsistentMomentumValidator
from .settings import ConsistentMomentumSettings

__all__ = [
    'ConsistentMomentumExecutor',
    'ConsistentMomentumAnalyzer',
    'ConsistentMomentumValidator',
    'ConsistentMomentumSettings'
]
