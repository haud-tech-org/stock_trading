# src/stockreports/alert/common/base_settings.py
from src.stockreports.config import loader

class BaseSettings:
    """
    Base class for all approach-specific settings.
    Handles loading of global settings and provides a common interface for accessing configuration.
    """
    def __init__(self, symbol: str, approach_name: str):
        self.symbol = symbol
        self.approach_name = approach_name
        
        # Load global settings
        self.settings = loader.get_settings()
        self.signal_settings = loader.get_signal_settings()
        
        # Expose common properties
        self.MODE = self.settings.MODE
        
        # Load approach-specific configuration
        # All configurations are now flat structures.
        self.approach_settings = self.signal_settings.APPROACH_CONFIG.get(approach_name, {})

    def get(self, key, default=None):
        """
        Provides a generic getter to access any setting for this approach.
        """
        return self.approach_settings.get(key, default)
