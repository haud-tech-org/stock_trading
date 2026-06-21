from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach


class DojiAnchorSignalCandleSettings(BaseSettings):
    """Settings for DOJI_ANCHOR_SIGNAL_CANDLE (Doji-first → anchor-backward).

    All keys are required in JSON config and will throw exception if missing.
    """

    def __init__(self, symbol: str) -> None:
        """Initialize settings for DOJI_ANCHOR_SIGNAL_CANDLE approach.
        
        Args:
            symbol: Trading symbol (e.g., 'VN30F1M')
            
        Raises:
            KeyError: If any required configuration key is missing
        """
        super().__init__(symbol, Approach.DOJI_ANCHOR_SIGNAL_CANDLE)

        # Lookback window size (number of candles)
        self.lookback_window: int = self.get("LOOKBACK_WINDOW")

        # Cooldown validation (minutes)
        self.cooldown_window: int = self.get("COOLDOWN_WINDOW")

        # Doji detection thresholds
        self.max_doji_body_ratio: float = self.get("MAX_DOJI_BODY_RATIO")
        self.min_doji_range: float = self.get("MIN_DOJI_RANGE")

        # Anchor backward search
        self.anchor_search_limit: int = self.get("ANCHOR_SEARCH_LIMIT")
        self.trend_window: int = self.get("TREND_WINDOW")

        # Momentum validation (absolute price move)
        self.momentum_min_price_move: float = self.get("MOMENTUM_MIN_PRICE_MOVE")

        # Trend candle validation
        self.trend_candle_range_multiplier: float = self.get("TREND_CANDLE_RANGE_MULTIPLIER")
        self.trend_candle_min_body: float = self.get("TREND_CANDLE_MIN_BODY")

        # Alert candle validation (reversal confirmation)
        self.alert_candle_close_to_extreme_threshold: float = self.get("ALERT_CANDLE_CLOSE_TO_EXTREME_THRESHOLD")
        self.alert_candle_max_volume_ratio: float = self.get("ALERT_CANDLE_MAX_VOLUME_RATIO")
        self.min_alert_body_size: float = self.get("MIN_ALERT_BODY_SIZE")

