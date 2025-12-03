from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class IchimokuSettings:
    def __init__(self, symbol: str):
        self.MODE = settings.MODE
        self.primary_symbol = symbol
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('ICHIMOKU', {})
        
        self.tenkan_period = self.approach_settings.get('TENKAN_PERIOD', 9)
        self.kijun_period = self.approach_settings.get('KIJUN_PERIOD', 26)
        self.senkou_b_period = self.approach_settings.get('SENKOU_B_PERIOD', 52)
        self.chikou_lag = self.approach_settings.get('CHIKOU_LAG', 26)
        
        self.use_cloud_confirmation = self.approach_settings.get('USE_CLOUD_CONFIRMATION', True)
        self.use_chikou_confirmation = self.approach_settings.get('USE_CHIKOU_CONFIRMATION', True)
        self.use_volume_confirmation = self.approach_settings.get('USE_VOLUME_CONFIRMATION', False)
        self.use_last_candle_max_volume_confirmation = self.approach_settings.get('USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION', False)
        self.use_volume_increasing_confirmation = self.approach_settings.get('USE_VOLUME_INCREASING_CONFIRMATION', False)
        self.use_divergence_confirmation = self.approach_settings.get('USE_DIVERGENCE_CONFIRMATION', False)
        self.min_bars_between_alerts = self.approach_settings.get('MIN_BARS_BETWEEN_ALERTS', 5)
        self.use_divergence_filter = self.approach_settings.get("USE_DIVERGENCE_FILTER", False)
        self.use_confirmation_candle_filter = self.approach_settings.get("USE_CONFIRMATION_CANDLE_FILTER", False)
        self.confirmation_candle_count = self.approach_settings.get("CONFIRMATION_CANDLE_COUNT", 1)
        self.skip_chikou_confirmation = self.approach_settings.get("SKIP_CHIKOU_CONFIRMATION", False)

    def get(self, key, default=None):
        return self.approach_settings.get(key, default)
