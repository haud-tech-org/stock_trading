from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class VolumeSpikeConfirmationSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('VOLUME_SPIKE_CONFIRMATION', {})
        
        self.volume_spike_multiplier = self.approach_settings.get("VOLUME_SPIKE_MULTIPLIER", 2.5)
        self.min_confirmation_body_size = self.approach_settings.get("MIN_CONFIRMATION_BODY_SIZE", 1.0)
        self.min_confirmation_body_ratio = self.approach_settings.get("MIN_CONFIRMATION_BODY_RATIO", 0.6)
        self.signal_lookback_period = self.approach_settings.get("SIGNAL_LOOKBACK_PERIOD", 3)
        self.cooldown_period = self.approach_settings.get("COOLDOWN_PERIOD", 2)
        self.min_lookback_data = self.approach_settings.get("MIN_LOOKBACK_DATA", 30)
        self.peak_trough_prominence = self.approach_settings.get("PEAK_TROUGH_PROMINENCE", 0.5)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
