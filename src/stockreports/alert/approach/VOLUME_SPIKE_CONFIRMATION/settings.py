from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class VolumeSpikeConfirmationSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION)
        
        # --- Main Lookback & Cooldown ---
        self.lookback_window = self.get("LOOKBACK_WINDOW", 10)
        self.cooldown_period = self.get("COOLDOWN_PERIOD", 5)

        # --- Climax Event (Max Volume Candle) Conditions ---
        self.previous_candles_volume_multiplier = self.get("PREVIOUS_CANDLES_VOLUME_MULTIPLIER", 2.0)
        self.avg_volume_multiplier = self.get("AVG_VOLUME_MULTIPLIER", 2.0)

        # --- Trend Confirmation Conditions (leading up to climax) ---
        peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", 2.0)
        self.peak_trough_prominence = peak_trough_prominence if peak_trough_prominence and peak_trough_prominence > 0 else None

        # --- Reversal Confirmation Conditions ---
        self.min_reversal_body_size = self.get("MIN_REVERSAL_BODY_SIZE", 0.3)
        self.max_forward_window_size = self.get("MAX_FORWARD_WINDOW_SIZE", 3)
        
        # --- Optional Signal Disabling ---
        self.disable_buy_signal = self.get("DISABLE_BUY_SIGNAL", False)
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL", False)
