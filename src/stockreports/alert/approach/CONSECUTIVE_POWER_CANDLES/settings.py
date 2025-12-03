from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class ConsecutivePowerCandlesSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('CONSECUTIVE_POWER_CANDLES', {})
        
        self.candle_count = self.approach_settings.get("CANDLE_COUNT", 3)
        self.min_body_to_range_ratio = self.approach_settings.get("MIN_BODY_TO_RANGE_RATIO", 0.7)
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.min_pre_candle_body_sizes = self.approach_settings.get("MIN_PRE_CANDLE_BODY_SIZES", [])
        self.use_rsi_exhaustion_filter = self.approach_settings.get("USE_RSI_EXHAUSTION_FILTER", False)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
