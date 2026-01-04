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
        self.validation_settings = loader.get_validation_settings()
        
        # Expose common properties
        self.MODE = self.settings.MODE
        
        # Load approach-specific configuration
        # All configurations are now flat structures.
        self.approach_settings = self.signal_settings.APPROACH_CONFIG.get(approach_name, {})

        # --- Common Reversal Confirmation Settings ---
        # These settings are used by the common reversal functions in the parent Executor.
        # They can be overridden by specific approach configurations.
        self.long_forward_window = self.get('LONG_FORWARD_WINDOW')
        self.short_forward_window = self.get('SHORT_FORWARD_WINDOW')
        self.gap_price = self.get('GAP_PRICE')
        self.adjacent_gap_price = self.get('ADJACENT_GAP_PRICE')
        self.reversal_volume_multiplier = self.get('REVERSAL_VOLUME_MULTIPLIER')
        self.reversal_body_ratio_threshold = self.get('REVERSAL_BODY_RATIO_THRESHOLD')
        self.reversal_price_diff_threshold = self.get('REVERSAL_PRICE_DIFF_THRESHOLD')

    def get(self, key: str):
        """
        Provides a generic getter to access any setting.
        It searches for the key in the following order of priority:
        1. Approach-specific settings (`approach_settings`)
        2. General signal settings (`signal_settings`)
        3. Validation settings (`validation_settings`)
        4. Global settings (`settings`)
        
        Raises a KeyError if the setting is not found in any of the configurations.
        """
        # 1. Check approach-specific settings
        if key in self.approach_settings:
            return self.approach_settings[key]

        # 2. Check general signal settings
        if hasattr(self.signal_settings, key):
            return getattr(self.signal_settings, key)

        # 3. Check validation settings
        if hasattr(self.validation_settings, key):
            return getattr(self.validation_settings, key)

        # 4. Check global settings
        if hasattr(self.settings, key):
            return getattr(self.settings, key)

        # If not found anywhere, raise an error
        raise KeyError(f"Setting '{key}' not found for approach '{self.approach_name}' in any configuration.")
