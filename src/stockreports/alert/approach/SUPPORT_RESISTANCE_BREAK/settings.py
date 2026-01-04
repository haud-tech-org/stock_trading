from src.stockreports.alert.common.confirmation.settings import ConfirmationSettings
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader

settings = loader.get_settings()
signal_settings = loader.get_signal_settings()

class SupportResistanceBreakSettings(ConfirmationSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.SUPPORT_RESISTANCE_BREAK)
        
        self.lookback_period = self.get("LOOKBACK_PERIOD")
        self.confirmation_window = self.get("CONFIRMATION_WINDOW")
        self.consistency_threshold = self.get("CONSISTENCY_THRESHOLD")
        
        self.use_bb_squeeze_confirmation = self.get("USE_BB_SQUEEZE_CONFIRMATION")
        self.bb_squeeze_lookback = self.get("BB_SQUEEZE_LOOKBACK")
        self.bb_squeeze_threshold_ratio = self.get("BB_SQUEEZE_THRESHOLD_RATIO")
        
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION")
        self.use_last_candle_max_volume_confirmation = self.get("USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION")
        self.use_volume_increasing_confirmation = self.get("USE_VOLUME_INCREASING_CONFIRMATION")
