# src/stockreports/alert/common/base_settings.py

from src.stockreports.services.executor_configuration_service.orchestrator import ExecutorConfigurationOrchestrator
from src.stockreports.config import loader

class BaseSettings:
    """
    Base class for all approach-specific settings.
    Handles loading of global settings and provides a common interface for accessing configuration.
    """
    def __init__(self, symbol: str, approach_name: str):
        self.symbol = symbol
        self.approach_name = approach_name

        # Load configuration via orchestrator
        executor_config = ExecutorConfigurationOrchestrator.get(self.symbol, self.approach_name)
        self.approach_settings = executor_config.get_approach_config()

        # Restore global settings using loader for other settings
        self.global_settings = loader.get_settings()
        self.MODE = self.global_settings.MODE

    def get(self, key: str):
        """
        Provides a generic getter to access any setting.
        Only searches approach-specific settings loaded from the orchestrator.
        Raises a KeyError if the setting is not found.
        """
        if key in self.approach_settings:
            return self.approach_settings[key]
        raise KeyError(f"Setting '{key}' not found for approach '{self.approach_name}' in approach configuration.")
