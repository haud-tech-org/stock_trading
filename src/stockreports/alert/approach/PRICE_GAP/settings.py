# src/stockreports/alert/approach/PRICE_GAP/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class PriceGapSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.PRICE_GAP)
        
        self.min_gap_size = self.get("MIN_GAP_SIZE")
        self.use_breakout_confirmation = self.get("USE_BREAKOUT_CONFIRMATION")
        self.lookback_period = self.get("LOOKBACK_PERIOD")
        self.confirmation_forward_window = self.get("CONFIRMATION_FORWARD_WINDOW")
        self.min_confirmation_body_size = self.get("MIN_CONFIRMATION_BODY_SIZE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
