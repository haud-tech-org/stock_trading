# src/stockreports/alert/approach/PRICE_GAP/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class PriceGapSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.PRICE_GAP)
        
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_gap_size = self.get("MIN_GAP_SIZE")
        self.min_alert_body_size = self.get("MIN_ALERT_BODY_SIZE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
