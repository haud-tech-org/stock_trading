from src.stockreports.alert.common.confirmation.settings import ConfirmationSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader
from stockreports.alert.common.base_settings import BaseSettings

signal_settings = loader.get_signal_settings()

class StrongCandleSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.STRONG_CANDLE)
        
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_body_ratio = self.get("MIN_BODY_RATIO")
        self.min_body_size = self.get("MIN_BODY_SIZE")
        self.max_conditional_candle_body_size = self.get("MAX_CONDITIONAL_CANDLE_BODY_SIZE")
        self.max_difference_price_threshold = self.get("MAX_DIFFERENCE_PRICE_THRESHOLD")
        self.trend_window_edge_slice = self.get("TREND_WINDOW_EDGE_SLICE")
        self.max_volume_multiplier = self.get("MAX_VOLUME_MULTIPLIER")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
