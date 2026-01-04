from src.stockreports.alert.confirmation.reversal_trend.settings import ReversalConfirmationSettings
from src.stockreports.alert.common.confirmation.settings import ConfirmationSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ConsistentMomentumSettings(ConfirmationSettings, ReversalConfirmationSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSISTENT_MOMENTUM)

        # --- Momentum Window Settings ---
        self.confirmation_window = self.get("CONFIRMATION_WINDOW")
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")

        # --- Forward Window Confirmation Settings ---
        self.use_forward_window_confirmation = self.get("USE_FORWARD_WINDOW_CONFIRMATION")
        self.peak_bottom_lookback_period = self.get("PEAK_BOTTOM_LOOKBACK_PERIOD")
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE")
        self.significant_price_change_threshold = self.get("SIGNIFICANT_PRICE_CHANGE_THRESHOLD")

        # --- Cooldown Settings ---
        self.cooldown_period = self.get("COOLDOWN_PERIOD")
