from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class IchimokuSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.ICHIMOKU)
        
        self.tenkan_period = self.get('TENKAN_PERIOD', 9)
        self.kijun_period = self.get('KIJUN_PERIOD', 26)
        self.senkou_b_period = self.get('SENKOU_B_PERIOD', 52)
        self.chikou_lag = self.get('CHIKOU_LAG', 26)
        
        self.use_cloud_confirmation = self.get('USE_CLOUD_CONFIRMATION', True)
        self.use_chikou_confirmation = self.get('USE_CHIKOU_CONFIRMATION', True)
        self.use_volume_confirmation = self.get('USE_VOLUME_CONFIRMATION', False)
        self.use_last_candle_max_volume_confirmation = self.get('USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION', False)
        self.use_volume_increasing_confirmation = self.get('USE_VOLUME_INCREASING_CONFIRMATION', False)
        self.use_divergence_confirmation = self.get('USE_DIVERGENCE_CONFIRMATION', False)
        self.min_bars_between_alerts = self.get('MIN_BARS_BETWEEN_ALERTS', 5)
        self.use_divergence_filter = self.get("USE_DIVERGENCE_FILTER", False)
        self.use_confirmation_candle_filter = self.get("USE_CONFIRMATION_CANDLE_FILTER", False)
        self.confirmation_candle_count = self.get("CONFIRMATION_CANDLE_COUNT", 1)
        self.skip_chikou_confirmation = self.get("SKIP_CHIKOU_CONFIRMATION", False)
