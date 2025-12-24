from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class RcmSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.RCM)
        
        self.confirmation_window = self.get("CONFIRMATION_WINDOW", 3)
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", 5)
        self.confirmation_min_consistency = self.get("CONFIRMATION_MIN_CONSISTENCY", 2)
        self.peak_bottom_lookback_period = self.get('PEAK_BOTTOM_LOOKBACK_PERIOD')
        self.min_alert_magnitude = self.get("MIN_ALERT_MAGNITUDE", 0)
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION", False)
        self.use_divergence_confirmation = self.get("USE_DIVERGENCE_CONFIRMATION", False)
