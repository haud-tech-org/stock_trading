from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ComparisonSignalSettings:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('COMPARISON', {}).get(symbol, {})
        self.lookback_window = self.approach_settings.get('LOOKBACK_WINDOW', 10)
        self.cooldown_period = self.approach_settings.get('COOLDOWN_PERIOD', 10)
        self.ma_short_period = self.approach_settings.get('MA_SHORT_PERIOD', 5)
        self.referenced_symbol = self.approach_settings.get('REFERENCED_SYMBOL')
        self.disable_sell_signal = self.approach_settings.get('DISABLE_SELL_SIGNAL', True)
        self.use_volume_confirmation = self.approach_settings.get('USE_VOLUME_CONFIRMATION', False)
        self.use_increasing_volume_confirmation = self.approach_settings.get('USE_INCREASING_VOLUME_CONFIRMATION', False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get('USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION', False)
        self.min_price_difference = self.approach_settings.get('MIN_PRICE_DIFFERENCE', 2.0)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
