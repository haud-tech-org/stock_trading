from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ComparisonSettings(BaseSettings):
    """
    Settings for the COMPARISON approach.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.COMPARISON)

        # --- Main Logic Parameters ---
        self.primary_symbol = self.get("PRIMARY_SYMBOL")
        self.reference_symbol = self.get("REFERENCE_SYMBOL")
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.max_primary_trend_magnitude = self.get("MAX_PRIMARY_TREND_MAGNITUDE")
        self.min_primary_trend_magnitude = self.get("MIN_PRIMARY_TREND_MAGNITUDE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
        self.disable_buy_signal = self.get("DISABLE_BUY_SIGNAL")
        self.disable_sell_signal = self.get("DISABLE_SELL_SIGNAL")
        self.min_alert_body_size = self.get("MIN_ALERT_BODY_SIZE")
        self.max_distance_close_price = self.get("MAX_DISTANCE_CLOSE_PRICE")
        self.enable_market_trend_validation = self.get("ENABLE_MARKET_TREND_VALIDATION")
        self.min_market_price_change = self.get("MIN_MARKET_PRICE_CHANGE")
        self.impact_symbols_min_body_to_range_ratio = self.get("IMPACT_SYMBOLS_MIN_BODY_TO_RANGE_RATIO")
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
