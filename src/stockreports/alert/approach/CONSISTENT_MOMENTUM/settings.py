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
        self.peak_trough_prominence = self.approach_settings.get("PEAK_TROUGH_PROMINENCE", 2)
        self.body_to_range_min_ratio = self.approach_settings.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
        self.use_breakout_confirmation = self.approach_settings.get("USE_BREAKOUT_CONFIRMATION", False)
        self.breakout_forward_window = self.approach_settings.get("BREAKOUT_FORWARD_WINDOW", 3)

        # --- General Confirmation Settings ---
        self.use_ma_confirmation = self.approach_settings.get("USE_MA_CONFIRMATION", False)
        self.use_adx_confirmation = self.approach_settings.get("USE_ADX_CONFIRMATION", False)
        self.cooldown_period = self.approach_settings.get("COOLDOWN_PERIOD", 10)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
