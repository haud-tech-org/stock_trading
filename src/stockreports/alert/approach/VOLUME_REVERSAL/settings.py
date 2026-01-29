from src.stockreports.alert.common.base_settings import BaseSettings
from stockreports.alert.common.constants import Approach

class VolumeReversalSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VOLUME_REVERSAL)
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.max_volume_multiplier = self.get("MAX_VOLUME_MULTIPLIER")
        self.min_volume_multiplier = self.get("MIN_VOLUME_MULTIPLIER")
        self.max_window_size_threshold = self.get("MAX_WINDOW_SIZE_THRESHOLD")
        self.min_window_size_threshold = self.get("MIN_WINDOW_SIZE_THRESHOLD")
