from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach


class IchimokuSettings(BaseSettings):
    """
    Ichimoku approach settings.
    Loads all configuration parameters from signal_settings.py
    """
    
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.ICHIMOKU)
        
        # Core Ichimoku periods
        self.tenkan_period = self.get("TENKAN_PERIOD")
        self.kijun_period = self.get("KIJUN_PERIOD")
        self.senkou_b_period = self.get("SENKOU_B_PERIOD")
        self.chikou_period = self.get("CHIKOU_PERIOD")
        
        # Senkou shift period (forward shift for cloud boundaries)
        self.senkou_shift_period = self.get("SENKOU_SHIFT_PERIOD")
        
        # Validation flags
        self.skip_chikou_confirmation = self.get("SKIP_CHIKOU_CONFIRMATION")
        self.skip_cloud_validation = self.get("SKIP_CLOUD_VALIDATION")
    
    @property
    def lookback_window_size(self) -> int:
        """
        Calculate the lookback window size required for Ichimoku analysis.
        
        Ichimoku requires:
        - Senkou B period: 52 candles for longest moving average
        - Chikou period: 26 candles for confirmation context
        - Total: 52 + 26 = 78 candles minimum
        
        Returns:
            int: Window size in candles
        """
        return max(
            self.tenkan_period,
            self.kijun_period,
            self.senkou_b_period
        ) + self.chikou_period
