# src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/__init__.py
"""
VOLUME_SPIKE_CONFIRMATION (VSC) Alert Approach Package.

Exports:
- VolumeSpikeConfirmationExecutor: Main executor for alert detection
- VolumeSpikeConfirmationAnalyzer: Pure calculation functions
- VolumeSpikeConfirmationValidator: Pure validation functions
- VolumeSpikeConfirmationSettings: Configuration settings
"""

from .executor import VolumeSpikeConfirmationExecutor
from .analyzer import VolumeSpikeConfirmationAnalyzer
from .validator import VolumeSpikeConfirmationValidator
from .settings import VolumeSpikeConfirmationSettings

__all__ = [
    'VolumeSpikeConfirmationExecutor',
    'VolumeSpikeConfirmationAnalyzer',
    'VolumeSpikeConfirmationValidator',
    'VolumeSpikeConfirmationSettings'
]
