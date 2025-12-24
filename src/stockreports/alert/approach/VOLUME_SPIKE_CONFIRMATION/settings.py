from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class VolumeSpikeConfirmationSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION)
        
        self.volume_spike_multiplier = self.get("VOLUME_SPIKE_MULTIPLIER", 2.5)
        self.min_confirmation_body_size = self.get("MIN_CONFIRMATION_BODY_SIZE", 1.0)
        self.min_confirmation_body_ratio = self.get("MIN_CONFIRMATION_BODY_RATIO", 0.6)
        self.signal_lookback_period = self.get("SIGNAL_LOOKBACK_PERIOD", 3)
        self.cooldown_period = self.get("COOLDOWN_PERIOD", 2)
        self.min_lookback_data = self.get("MIN_LOOKBACK_DATA", 30)
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", 0.5)
