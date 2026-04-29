"""
Alerter Base Class

Provides static utility to load approach configuration for a given symbol and approach.
"""

# --- Project Imports ---
from src.stockreports.services.executor_configuration_service.orchestrator import ConfigurationOrchestrator

class Alerter:
    """
    Base class for all alerters. Provides config loading utility.
    """
    @staticmethod
    def get_approach_config(symbol: str, approach_name: str) -> dict:
        """
        Load approach configuration for a given symbol and approach.
        """
        executor_config = ConfigurationOrchestrator.get(symbol, approach_name)
        return executor_config.get_approach_config()
