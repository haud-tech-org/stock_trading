from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class StrongCandleSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.STRONG_CANDLE)
        
        self.confirmation_window = self.get("CONFIRMATION_WINDOW")
        self.min_alert_magnitude = self.get("MIN_ALERT_MAGNITUDE")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
        self.use_divergence_confirmation = self.get("USE_DIVERGENCE_CONFIRMATION")
        self.trend_strength_strong_close_tail_ratio = signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
