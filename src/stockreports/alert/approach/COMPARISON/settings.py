from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ComparisonSignalSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.COMPARISON)
        
        self.lookback_window = self.get('LOOKBACK_WINDOW', 10)
        self.cooldown_period = self.get('COOLDOWN_PERIOD', 10)
        self.ma_short_period = self.get('MA_SHORT_PERIOD', 5)
        self.primary_symbol = self.get('PRIMARY_SYMBOL', None)
        self.referenced_symbol = self.get('REFERENCED_SYMBOL')
        self.disable_sell_signal = self.get('DISABLE_SELL_SIGNAL', True)
        self.use_volume_confirmation = self.get('USE_VOLUME_CONFIRMATION', False)
        self.use_increasing_volume_confirmation = self.get('USE_INCREASING_VOLUME_CONFIRMATION', False)
        self.use_last_candle_max_volume_confirmation = self.get('USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION', False)
        self.min_price_difference = self.get('MIN_PRICE_DIFFERENCE', 2.0)
