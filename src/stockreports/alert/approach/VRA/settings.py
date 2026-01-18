from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class VraSettings(BaseSettings):
    """
    Settings for the VRA (Volume-Reversal-Anchor) approach.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VRA)

        # --- Main Logic Parameters ---
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.min_trend_magnitude = self.get("MIN_TREND_MAGNITUDE")
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
        self.min_alert_body_size = self.get("MIN_ALERT_BODY_SIZE")
        self.max_distance_close_price = self.get("MAX_DISTANCE_CLOSE_PRICE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.enable_market_trend_validation = self.get("ENABLE_MARKET_TREND_VALIDATION")
        self.impact_symbols_min_body_to_range_ratio = self.get("IMPACT_SYMBOLS_MIN_BODY_TO_RANGE_RATIO")
        self.consistent_volume_window = self.get("CONSISTENT_VOLUME_WINDOW")
        self.consistent_volume_min_percentage = self.get("CONSISTENT_VOLUME_MIN_PERCENTAGE")
