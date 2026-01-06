from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.confirmation.reversal_trend.settings import ReversalConfirmationSettings

class VolumeSpikeConfirmationSettings(ReversalConfirmationSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.VOLUME_SPIKE_CONFIRMATION)
        
        # --- Main Lookback & Cooldown ---
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.cooldown_period = self.get("COOLDOWN_PERIOD")
        self.max_forward_window_size = self.get("MAX_FORWARD_WINDOW_SIZE")

        # --- Climax Event (Max Volume Candle) Conditions ---
        self.previous_candles_volume_multiplier = self.get("PREVIOUS_CANDLES_VOLUME_MULTIPLIER")
        self.avg_volume_multiplier = self.get("AVG_VOLUME_MULTIPLIER")

        # --- Optional Signal Disabling ---
        self.disable_buy_signal = self.get("DISABLE_BUY_SIGNAL")
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL")
