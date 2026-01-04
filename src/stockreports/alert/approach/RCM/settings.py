from src.stockreports.alert.common.confirmation.settings import ConfirmationSettings
from src.stockreports.alert.common.constants import Approach

class RcmSettings(ConfirmationSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.RCM)
        
        self.confirmation_window = self.get("CONFIRMATION_WINDOW")
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE")
        self.confirmation_min_consistency = self.get("CONFIRMATION_MIN_CONSISTENCY")
        self.peak_bottom_lookback_period = self.get('PEAK_BOTTOM_LOOKBACK_PERIOD')
        self.min_alert_magnitude = self.get("MIN_ALERT_MAGNITUDE")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
        self.use_divergence_confirmation = self.get("USE_DIVERGENCE_CONFIRMATION")
