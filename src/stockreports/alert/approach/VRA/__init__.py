# src/stockreports/alert/approach/VRA/__init__.py
"""
VRA (Volume Reversal Analysis) Approach Module.

This module implements the VRA (Volume Reversal Analysis) approach for
detecting volume reversal signals in trading.

The module is organized into:
- analyzer.py: Pure calculation functions
- validator.py: Pure validation functions
- executor.py: Alert orchestration and execution
- settings.py: Configuration and parameters

Public API exports the executor and settings classes for use in alert
processing pipelines.
"""

from .executor import VraExecutor
from .settings import VraSettings
from .analyzer import VraAnalyzer
from .validator import VraValidator


__all__ = [
    'VraExecutor',
    'VraSettings',
    'VraAnalyzer',
    'VraValidator',
]
