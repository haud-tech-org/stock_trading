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
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
        self.min_trend_magnitude = self.get("MIN_TREND_MAGNITUDE")
        self.trend_window_edge_slice = self.get("TREND_WINDOW_EDGE_SLICE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.min_confirmation_window_candles = self.get("MIN_CONFIRMATION_WINDOW_CANDLES")
        self.volume_multiplier_by_reversal_trend = self.get("VOLUME_MULTIPLIER_BY_REVERSAL_TREND")
        self.min_peak_trough_prominence = self.get("MIN_PEAK_TROUGH_PROMINENCE")
        self.max_peak_trough_prominence = self.get("MAX_PEAK_TROUGH_PROMINENCE")
