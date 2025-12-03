from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class ConsistentMomentumSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('CONSISTENT_MOMENTUM', {})
        
        self.window_size = self.approach_settings.get("WINDOW_SIZE", 3)
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.approach_settings.get("USE_VOLUME_INCREASING_CONFIRMATION", False)
        self.strong_close_threshold_range = signal_settings.STRONG_CLOSE_THRESHOLD_RANGE
        self.peak_bottom_lookback_period = self.approach_settings.get("PEAK_BOTTOM_LOOKBACK_PERIOD")
        self.peak_trough_prominence = self.approach_settings.get("PEAK_TROUGH_PROMINENCE", 5)
        self.body_to_range_min_ratio = self.approach_settings.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
        self.reversal_candle_body_ratio = self.approach_settings.get("REVERSAL_CANDLE_BODY_RATIO", 0.6)
        self.use_realtime_reversal_confirmation = self.approach_settings.get("USE_REALTIME_REVERSAL_CONFIRMATION", False)
        self.realtime_reversal_confirmation_window = self.approach_settings.get("REALTIME_REVERSAL_CONFIRMATION_WINDOW", 3)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
