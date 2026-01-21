# src/stockreports/alert/approach/PRICE_GAP/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class PriceGapSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.PRICE_GAP)
        
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_gap_size = self.get("MIN_GAP_CANDLE_SIZE")
        self.min_alert_body_size = self.get("MIN_ALERT_BODY_SIZE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.enable_market_trend_validation = self.get("ENABLE_MARKET_TREND_VALIDATION")
        self.impact_symbols_min_body_to_range_ratio = self.get("IMPACT_SYMBOLS_MIN_BODY_TO_RANGE_RATIO")
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
