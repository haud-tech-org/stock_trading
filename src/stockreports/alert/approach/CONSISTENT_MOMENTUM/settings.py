from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings


class ConsistentMomentumSettings(BaseSettings):
    """
    Settings for the Consistent Momentum approach.
    All configuration parameters are loaded from the centralized signal_settings.py.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSISTENT_MOMENTUM)
        
        # Lookback window size
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        
        # Consistency validations
        self.min_consistent_candles = self.get("MIN_CONSISTENT_CANDLES")
        
        # Magnitude threshold for alert creation
        self.magnitude_threshold = self.get("MAGNITUDE_THRESHOLD")
        
        # Cooldown validation
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        
        # Volume validation
        self.max_multiplier_difference_volume_threshold = self.get("MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD")
        
        # Confirmation window price range validation
        self.min_confirmation_window_price_threshold = self.get("MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD")
        self.max_confirmation_window_price_threshold = self.get("MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD")
