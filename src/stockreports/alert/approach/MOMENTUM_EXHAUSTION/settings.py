from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class MomentumExhaustionSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.MOMENTUM_EXHAUSTION)
        
        self.momentum_candle_count = self.get("MOMENTUM_CANDLE_COUNT")
        self.exhaustion_candle_count = self.get("EXHAUSTION_CANDLE_COUNT")
        self.sma_slope_threshold = self.get("SMA_SLOPE_THRESHOLD")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_long_term_ma_filter = self.get("USE_LONG_TERM_MA_FILTER")
