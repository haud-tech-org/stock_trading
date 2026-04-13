"""Configuration settings for REVERSAL_ANCHOR_SIGNAL_CANDLE approach."""

from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach


class ReversalAnchorSignalCandleSettings(BaseSettings):
    """Configuration settings for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.
    
    Loads all configuration parameters from centralized signal_settings.py
    using the approach name "REVERSAL_ANCHOR_SIGNAL_CANDLE".
    """

    def __init__(self, symbol: str) -> None:
        """Initialize settings for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT:USDT')
            
        Raises:
            ValueError: If configuration not found in signal_settings.py
        """
        super().__init__(symbol, Approach.REVERSAL_ANCHOR_SIGNAL_CANDLE)

        # Lookback window size (number of candles)
        self.lookback_window: int = self.get("LOOKBACK_WINDOW")

        # Validation 1: Window size threshold (price range)
        self.min_size_price_window: float = self.get("MIN_SIZE_PRICE_WINDOW")

        # Validation 2: Anchor candle thresholds
        self.min_size_candle: float = self.get("MIN_SIZE_CANDLE")
        self.multiplier_size: float = self.get("MULTIPLIER_SIZE")

        # Validation 3: Signal candle thresholds
        self.min_volume: float = self.get("MIN_VOLUME")
        self.multiplier_volume: float = self.get("MULTIPLIER_VOLUME")

        # Validation 4: Alert candle wick thresholds
        self.min_percentage: float = self.get("MIN_PERCENTAGE")
        self.max_percentage: float = self.get("MAX_PERCENTAGE")

        # Cooldown validation (minutes)
        self.cooldown_window: int = self.get("COOLDOWN_WINDOW")
