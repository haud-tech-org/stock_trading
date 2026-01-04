from src.stockreports.alert.common.confirmation.settings import ConfirmationSettings
from src.stockreports.alert.common.constants import Approach

class ConsecutivePowerCandlesSettings(ConfirmationSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSECUTIVE_POWER_CANDLES)
        
        self.candle_count = self.get("CANDLE_COUNT")
        self.min_body_to_range_ratio = self.get("MIN_BODY_TO_RANGE_RATIO")
        self.min_pre_candle_body_sizes = self.get("MIN_PRE_CANDLE_BODY_SIZES")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        
        self.use_rsi_exhaustion_filter = self.get("USE_RSI_CONFIRMATION")
