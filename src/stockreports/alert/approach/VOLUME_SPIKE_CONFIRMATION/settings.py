from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class VolumeSpikeConfirmationSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION)

        # --- Main Lookback & Cooldown ---
        self.lookback_window = self.get("LOOKBACK_WINDOW")  # int: Number of candles for lookback
        self.cooldown_period = self.get("COOLDOWN_WINDOW")  # int: Cooldown period in minutes

        # --- Trend Confirmation Window ---
        self.min_trend_window_size = self.get("MIN_TREND_WINDOW_SIZE")  # int: Minimum window size for trend confirmation
        self.min_trend_candle_slices = self.get("MIN_TREND_CANDLE_SLICES")  # int: Minimum number of same-color candles
        self.trend_volume_multiplier = self.get("TREND_VOLUME_MULTIPLIER")  # float: Volume multiplier for trend window
