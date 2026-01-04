from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class IchimokuSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.ICHIMOKU)
        
        self.tenkan_sen_period = self.get("TENKAN_SEN_PERIOD")
        self.kijun_sen_period = self.get("KIJUN_SEN_PERIOD")
        self.senkou_span_b_period = self.get("SENKOU_SPAN_B_PERIOD")
        self.chikou_span_period = self.get("CHIKOU_SPAN_PERIOD")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
        
        self.skip_chikou_confirmation = self.get("SKIP_CHIKOU_CONFIRMATION")
        self.min_bars_between_alerts = self.get("MIN_BARS_BETWEEN_ALERTS")
        
        self.use_adx_confirmation = self.get("USE_ADX_CONFIRMATION")
        self.use_ma_confirmation = self.get("USE_MA_CONFIRMATION")
        
        self.use_rsi_exhaustion_filter = self.get("USE_RSI_EXHAUSTION_FILTER")
        self.rsi_oversold_threshold = self.get("RSI_OVERSOLD_THRESHOLD")
        self.rsi_overbought_threshold = self.get("RSI_OVERBOUGHT_THRESHOLD")
        
        self.use_macd_confirmation = self.get("USE_MACD_CONFIRMATION")
        
        self.use_divergence_filter = self.get("USE_DIVERGENCE_FILTER")
        self.divergence_lookback_period = self.get("DIVERGENCE_LOOKBACK_PERIOD")
        self.divergence_rsi_period = self.get("DIVERGENCE_RSI_PERIOD")
        self.divergence_price_prominence = self.get("DIVERGENCE_PRICE_PROMINENCE")
        self.divergence_rsi_prominence = self.get("DIVERGENCE_RSI_PROMINENCE")
        
        self.use_confirmation_candle_filter = self.get("USE_CONFIRMATION_CANDLE_FILTER")
        self.confirmation_candle_count = self.get("CONFIRMATION_CANDLE_COUNT")
