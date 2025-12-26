from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ConsistentMomentumSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSISTENT_MOMENTUM)
        
        self.window_size = self.get("WINDOW_SIZE", 3)
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION", False)
        self.strong_close_threshold_range = signal_settings.STRONG_CLOSE_THRESHOLD_RANGE
        self.peak_bottom_lookback_period = self.get("PEAK_BOTTOM_LOOKBACK_PERIOD")
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", 2)
        self.body_to_range_min_ratio = self.get("BODY_TO_RANGE_MIN_RATIO", 0.5)
        self.use_breakout_confirmation = self.get("USE_BREAKOUT_CONFIRMATION", True)
        self.breakout_forward_window = self.get("BREAKOUT_FORWARD_WINDOW", 15)
        self.cooldown_period = self.get("COOLDOWN_PERIOD", 5) # In minutes
        self.breakout_volume_multiplier = self.get("BREAKOUT_VOLUME_MULTIPLIER", 0.8)
        self.reversal_volume_multiplier = self.get("REVERSAL_VOLUME_MULTIPLIER", 2.0)

        # --- General Confirmation Settings ---
        self.use_ma_confirmation = self.get("USE_MA_CONFIRMATION", False)
        self.use_adx_confirmation = self.get("USE_ADX_CONFIRMATION", False)
