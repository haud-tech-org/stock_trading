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

        # --- Common Reversal Confirmation Settings ---
        # These settings are used by the common reversal functions in the parent Executor.
        # They can be overridden by specific approach configurations.
        self.long_forward_window = self.get('LONG_FORWARD_WINDOW', 9)
        self.short_forward_window = self.get('SHORT_FORWARD_WINDOW', 6)
        self.gap_price = self.get('GAP_PRICE', 0.5)
        self.adjacent_gap_price = self.get('ADJACENT_GAP_PRICE', 0.5)
        self.reversal_volume_multiplier = self.get('REVERSAL_VOLUME_MULTIPLIER', 2.5)
        self.reversal_body_ratio_threshold = self.get('REVERSAL_BODY_RATIO_THRESHOLD', 0.6)
        self.reversal_price_diff_threshold = self.get('REVERSAL_PRICE_DIFF_THRESHOLD', 2.0)

    def get(self, key, default=None):
        """
        Provides a generic getter to access any setting for this approach.
        """
        return self.approach_settings.get(key, default)
