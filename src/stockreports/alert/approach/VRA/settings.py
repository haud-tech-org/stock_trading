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
