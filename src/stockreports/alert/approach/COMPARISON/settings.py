from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ComparisonSettings(BaseSettings):
    """
    Settings for the COMPARISON approach.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.COMPARISON)

        # --- Main Logic Parameters ---
        self.primary_symbol = self.get("PRIMARY_SYMBOL")
        self.reference_symbol = self.get("REFERENCE_SYMBOL")
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_divergence_threshold = self.get("MIN_DIVERGENCE_THRESHOLD")
        self.max_primary_trend_magnitude = self.get("MAX_PRIMARY_TREND_MAGNITUDE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.disable_buy_signal = self.get("DISABLE_BUY_SIGNAL")
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL")
