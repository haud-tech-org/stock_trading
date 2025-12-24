# src/stockreports/alert/approach/PRICE_GAP/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class PriceGapSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.PRICE_GAP)
        
        # --- Core Logic Parameters ---
        self.min_gap_size = self.get("MIN_GAP_SIZE", 1.0)
        self.use_breakout_confirmation = self.get("USE_BREAKOUT_CONFIRMATION", True)
        self.lookback_period = self.get("LOOKBACK_PERIOD", 30)
        self.confirmation_forward_window = self.get("CONFIRMATION_FORWARD_WINDOW", 3)
        self.min_confirmation_body_size = self.get("MIN_CONFIRMATION_BODY_SIZE", 1.0)
        
        # --- Standard Optional Filter Flags ---
        # (Add any standard filters if needed, e.g., volume confirmation)
