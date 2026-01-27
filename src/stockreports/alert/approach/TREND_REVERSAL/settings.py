from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class TrendReversalSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.TREND_REVERSAL)
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_pre_volume_multiplier = self.get("MIN_PRE_VOLUME_MULTIPLIER")
        self.min_post_volume_multiplier = self.get("MIN_POST_VOLUME_MULTIPLIER")
        self.min_adjacent_volume_multiplier = self.get("MIN_ADJACENT_VOLUME_MULTIPLIER")
        self.min_trend_magnitude = self.get("MIN_TREND_MAGNITUDE")
