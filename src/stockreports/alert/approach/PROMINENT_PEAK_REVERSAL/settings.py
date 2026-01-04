# src/stockreports/alert/approach/PROMINENT_PEAK_REVERSAL/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ProminentPeakReversalSignalSettings(BaseSettings):
    """
    Manages and provides access to the settings for the Prominent Peak Reversal signal approach.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.PROMINENT_PEAK_REVERSAL)

        # Load all the specific settings from the configuration
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.confirmation_window = self.get("CONFIRMATION_WINDOW")
        self.peak_prominence = self.get("PEAK_PROMINENCE")
        self.use_peak_in_lookback_validation = self.get("USE_PEAK_IN_LOOKBACK_VALIDATION")
        self.wick_to_body_ratio = self.get("WICK_TO_BODY_RATIO")
        self.min_body_point_price = self.get("MIN_BODY_POINT_PRICE")
        self.min_reversal_price_diff = self.get("MIN_REVERSAL_PRICE_DIFF")
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL")
        self.disable_buy_signal = self.get("DISABLE_BUY_SIGNAL")
