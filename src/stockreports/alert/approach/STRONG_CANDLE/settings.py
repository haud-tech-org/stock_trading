from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class StrongCandleSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('STRONG_CANDLE', {})
        
        self.confirmation_window = self.approach_settings.get("CONFIRMATION_WINDOW", 4)
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.approach_settings.get("USE_VOLUME_INCREASING_CONFIRMATION", False)
        self.use_divergence_confirmation = self.approach_settings.get("USE_DIVERGENCE_CONFIRMATION", False)
        self.trend_strength_strong_close_tail_ratio = signal_settings.TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO
        self.min_alert_magnitude = self.approach_settings.get("MIN_ALERT_MAGNITUDE", 2)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
