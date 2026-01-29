from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class SessionExtremeVolumeReversalSettings(BaseSettings):
    """
    Settings for the SESSION_EXTREME_VOLUME_REVERSAL approach.
    All parameters are loaded from centralized config (signal_settings.py).
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.SESSION_EXTREME_VOLUME_REVERSAL)

        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_volume_multiplier = self.get("MIN_VOLUME_MULTIPLIER")
        self.magnitude_threshold = self.get("MAGNITUDE_THRESHOLD")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
