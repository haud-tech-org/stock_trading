# src/stockreports/alert/approach/MOMENTUM_EXHAUSTION/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class MomentumExhaustionSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.MOMENTUM_EXHAUSTION)
        
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.pre_window_volume_multiplier = self.get("PRE_WINDOW_VOLUME_MULTIPLIER")
        self.post_window_volume_multiplier = self.get("POST_WINDOW_VOLUME_MULTIPLIER")
        self.reversal_volume_multiplier = self.get("REVERSAL_VOLUME_MULTIPLIER")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.post_climax_price_proximity_threshold = self.get("POST_CLIMAX_PRICE_PROXIMITY_THRESHOLD")
