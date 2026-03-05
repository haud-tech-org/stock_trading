from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach


class ConsistentVolumeAnchorSettings(BaseSettings):
    """
    Settings for the CVA (Consistent Volume Anchor) approach.
    Detects reversal signals by identifying anchor candles with consistent volume patterns,
    then confirming with alert candles showing volume spikes and strong body sizes.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSISTENT_VOLUME_ANCHOR)

        # --- Main Logic Parameters ---
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        
        # --- Consistent Volume Window Parameters ---
        self.max_consistent_volume_multiplier = self.get("MAX_CONSISTENT_VOLUME_MULTIPLIER")
        self.consistent_candle_percentage = self.get("CONSISTENT_CANDLE_PERCENTAGE")
        self.max_consistent_window_size = self.get("MAX_CONSISTENT_WINDOW_SIZE")
        
        # --- Consistent Window Body Size Validation ---
        self.max_consistent_body_size_candle = self.get("MAX_CONSISTENT_BODY_SIZE_CANDLE")
        
        # --- Alert Candle Validation Parameters ---
        self.min_volume_confirmation_multiplier = self.get("MIN_VOLUME_CONFIRMATION_MULTIPLIER")
        self.min_body_size_alert_candle = self.get("MIN_BODY_SIZE_ALERT_CANDLE")
        self.min_body_ratio = self.get("MIN_BODY_RATIO")
        
        # --- Alert Magnitude ---
        self.min_alert_magnitude = self.get("MIN_ALERT_MAGNITUDE")
        
        # --- Cooldown Window ---
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
