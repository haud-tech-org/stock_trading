from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ComparisonSignalSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.COMPARISON)
        
        self.primary_symbol = self.get("PRIMARY_SYMBOL")
        self.referenced_symbol = self.get("REFERENCED_SYMBOL")
        self.min_price_difference = self.get("MIN_PRICE_DIFFERENCE")
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.cooldown_period = self.get("COOLDOWN_PERIOD")
        self.ma_short_period = self.get("MA_SHORT_PERIOD")
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
