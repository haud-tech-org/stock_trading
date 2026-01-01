from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ConsistentMomentumSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSISTENT_MOMENTUM)
        
        self.confirmation_window = self.get("CONFIRMATION_WINDOW", 3)
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", 2)
        self.peak_bottom_lookback_period = self.get("PEAK_BOTTOM_LOOKBACK_PERIOD", 60)
        
        # Forward Window Confirmation
        self.use_forward_window_confirmation = self.get("USE_FORWARD_WINDOW_CONFIRMATION", True)
        self.long_forward_window = self.get("LONG_FORWARD_WINDOW", 9)
        self.short_forward_window = self.get("SHORT_FORWARD_WINDOW", 5)
        self.reversal_body_ratio_threshold = self.get("REVERSAL_BODY_RATIO_THRESHOLD", 0.7)
        self.reversal_volume_multiplier = self.get("REVERSAL_VOLUME_MULTIPLIER", 2.5)
        self.reversal_price_diff_threshold = self.get("REVERSAL_PRICE_DIFF_THRESHOLD", 2.0)
        self.significant_price_change_threshold = self.get("SIGNIFICANT_PRICE_CHANGE_THRESHOLD", 5.0)
        self.gap_price = self.get("GAP_PRICE", 0.5)

        # Volume Confirmation
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION", False)
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION", False)
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION", False)

        # General Confirmation Settings
        self.use_ma_confirmation = self.get("USE_MA_CONFIRMATION", False)
        self.use_adx_confirmation = self.get("USE_ADX_CONFIRMATION", False)
        self.use_rsi_exhaustion_filter = self.get("USE_RSI_EXHAUSTION_FILTER", False)
        self.rsi_oversold_threshold = self.get("RSI_OVERSOLD_THRESHOLD", 30)
        self.rsi_overbought_threshold = self.get("RSI_OVERBOUGHT_THRESHOLD", 70)

        # Misc
        self.cooldown_period = self.get("COOLDOWN_PERIOD", 5) # In minutes
