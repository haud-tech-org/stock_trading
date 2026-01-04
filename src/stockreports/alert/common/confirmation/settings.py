# src/stockreports/alert/common/confirmation/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings

class ConfirmationSettings(BaseSettings):
    """
    An abstract settings class that provides all configuration properties
    required by the confirmation logic in `confirmation.py`.
    """
    def __init__(self, symbol: str, approach_name: str):
        super().__init__(symbol, approach_name)

        # Initialize all settings used by the confirmation script
        self.use_short_term_ma_confirmation = self.get("USE_SHORT_TERM_MA_CONFIRMATION")
        self.use_ma_confirmation = self.get("USE_MA_CONFIRMATION")
        self.use_long_term_ma_confirmation = self.get("USE_LONG_TERM_MA_CONFIRMATION")
        self.use_rsi_confirmation = self.get("USE_RSI_CONFIRMATION")
        self.num_candles_for_rsi_check = self.get("NUM_CANDLES_FOR_RSI_CHECK")
        self.rsi_oversold_threshold = self.get("RSI_OVERSOLD_THRESHOLD")
        self.rsi_overbought_threshold = self.get("RSI_OVERBOUGHT_THRESHOLD")
        self.use_macd_confirmation = self.get("USE_MACD_CONFIRMATION")
        self.use_adx_confirmation = self.get("USE_ADX_CONFIRMATION")
