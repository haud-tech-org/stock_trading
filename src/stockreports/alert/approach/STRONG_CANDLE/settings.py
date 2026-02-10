from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings


class StrongCandleSettings(BaseSettings):
    """
    Settings for the Strong Candle approach.
    All configuration parameters are loaded from the centralized signal_settings.py.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.STRONG_CANDLE)
        
        # Lookback window size
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        
        # Alert candle body validations
        self.min_body_ratio = self.get("MIN_BODY_RATIO")
        self.min_body_size = self.get("MIN_BODY_SIZE")
        
        # Conditional window validations
        self.max_opposite_color_candle_body_size = self.get("MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE")
        self.min_window_size_threshold = self.get("MIN_DIFFERENCE_PRICE_THRESHOLD")
        self.max_window_size_threshold = self.get("MAX_DIFFERENCE_PRICE_THRESHOLD")
        
        # Volume validation
        self.max_volume_multiplier = self.get("MAX_VOLUME_MULTIPLIER")
        
        # Magnitude threshold for alert creation
        self.magnitude_threshold = self.get("MAGNITUDE_THRESHOLD")
        
        # Cooldown validation
        self.cooldown_window = self.get("COOLDOWN_WINDOW")

