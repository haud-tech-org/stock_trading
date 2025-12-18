# src/stockreports/alert/approach/PROMINENT_PEAK_REVERSAL/settings.py
from src.stockreports.config.signal_settings import APPROACH_CONFIG

class ProminentPeakReversalSignalSettings:
    """
    Manages and provides access to the settings for the Prominent Peak Reversal signal approach.
    """
    def __init__(self, symbol: str):
        """
        Initializes the settings object for a specific symbol.

        Args:
            symbol (str): The stock symbol for which to load settings.
        """
        self.symbol = symbol
        self.approach_settings = APPROACH_CONFIG.get("PROMINENT_PEAK_REVERSAL", {})

        # Load all the specific settings from the configuration
        self.lookback_window = self.approach_settings.get("LOOKBACK_WINDOW", 50)
        self.confirmation_window = self.approach_settings.get("CONFIRMATION_WINDOW", 10)
        self.peak_prominence = self.approach_settings.get("PEAK_PROMINENCE", 3.0)
        self.use_peak_in_lookback_validation = self.approach_settings.get("USE_PEAK_IN_LOOKBACK_VALIDATION", True)
        self.wick_to_body_ratio = self.approach_settings.get("WICK_TO_BODY_RATIO", 1.5)
        self.min_body_point_price = self.approach_settings.get("MIN_BODY_POINT_PRICE", 0.5)
        self.min_reversal_price_diff = self.approach_settings.get("MIN_REVERSAL_PRICE_DIFF", 1.0)
        self.volume_multiplier = self.approach_settings.get("VOLUME_MULTIPLIER", 1.5)
        self.cooldown_window = self.approach_settings.get("COOLDOWN_WINDOW", 5) # Default 60 minutes
        self.disable_sell_signal = self.approach_settings.get("DISABLE_SELL_SIGNAL", False)
        self.disable_buy_signal = self.approach_settings.get("DISABLE_BUY_SIGNAL", False)

    def get(self, key, default=None):
        """
        Provides a generic getter to access any setting.
        """
        return self.approach_settings.get(key, default)
