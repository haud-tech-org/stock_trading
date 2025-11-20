from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ComparisonSignalSettings:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('COMPARISON', {}).get(symbol, {})
        self.lookback_window = self.approach_settings.get('LOOKBACK_WINDOW', 10)
        self.cooldown_period = self.approach_settings.get('COOLDOWN_PERIOD', 10)
        self.ma_short_period = self.approach_settings.get('MA_SHORT_PERIOD', 5)
        self.referenced_symbol = self.approach_settings.get('REFERENCED_SYMBOL')
