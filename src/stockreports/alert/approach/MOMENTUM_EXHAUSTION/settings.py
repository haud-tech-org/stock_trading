from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class MomentumExhaustionSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('MOMENTUM_EXHAUSTION', {})
        
        self.momentum_candle_count = self.approach_settings.get("MOMENTUM_CANDLE_COUNT", 2)
        self.exhaustion_candle_count = self.approach_settings.get("EXHAUSTION_CANDLE_COUNT", 2)
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", True)
        self.sma_slope_threshold = self.approach_settings.get("SMA_SLOPE_THRESHOLD", 0.05)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
