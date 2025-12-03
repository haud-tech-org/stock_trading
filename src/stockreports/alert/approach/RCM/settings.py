from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class RcmSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('RCM', {})
        
        self.confirmation_window = self.approach_settings.get("CONFIRMATION_WINDOW", 3)
        self.peak_trough_prominence = self.approach_settings.get("PEAK_TROUGH_PROMINENCE", 5)
        self.confirmation_min_consistency = self.approach_settings.get("CONFIRMATION_MIN_CONSISTENCY", 2)
        self.peak_bottom_lookback_period = self.approach_settings.get('PEAK_BOTTOM_LOOKBACK_PERIOD')
        self.min_alert_magnitude = self.approach_settings.get("MIN_ALERT_MAGNITUDE", 0)
        
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.approach_settings.get("USE_VOLUME_INCREASING_CONFIRMATION", False)
        self.use_divergence_confirmation = self.approach_settings.get("USE_DIVERGENCE_CONFIRMATION", False)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
