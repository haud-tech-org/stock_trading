from src.stockreports.alert.common.base_settings import BaseSettings
from src.stockreports.alert.common.constants import Approach

class ConsolidationBreakoutSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.CONSOLIDATION_BREAKOUT)
        
        self.consolidation_lookback = self.get("CONSOLIDATION_LOOKBACK", [50])
        if not isinstance(self.consolidation_lookback, list):
            self.consolidation_lookback = [self.consolidation_lookback]
            
        self.breakout_confirmation_candles = self.get("BREAKOUT_CONFIRMATION_CANDLES", 1)
        self.max_deviation_from_center = self.get("MAX_DEVIATION_FROM_CENTER")
        self.min_clustered_candle_ratio = self.get("MIN_CLUSTERED_CANDLE_RATIO")
        
        self.use_channel_consistency_check = self.get("USE_CHANNEL_CONSISTENCY_CHECK", False)
        self.max_channel_outlier_ratio = self.get("MAX_CHANNEL_OUTLIER_RATIO", 0.1)
        
        self.use_balanced_sideways_check = self.get("USE_BALANCED_SIDEWAYS_CHECK", False)
        self.max_regression_slope = self.get("MAX_REGRESSION_SLOPE", 0.05)
        self.max_time_balance_deviation_ratio = self.get("MAX_TIME_BALANCE_DEVIATION_RATIO", 0.3)
        
        self.use_consecutive_trend_check = self.get("USE_CONSECUTIVE_TREND_CHECK", False)
        self.max_consecutive_trend_candles = self.get("MAX_CONSECUTIVE_TREND_CANDLES", 7)
        
        self.min_peaks_troughs = self.get("MIN_PEAKS_TROUGHS", 0)
        self.peak_trough_prominence = self.get("PEAK_TROUGH_PROMINENCE", None)
        self.use_alternating_peaks_troughs_check = self.get("USE_ALTERNATING_PEAKS_TROUGHS_CHECK", False)
        
        self.use_adx_filter = self.get("USE_ADX_FILTER", False)
        self.adx_threshold = self.get("ADX_THRESHOLD")
        self.adx_confirmation_ratio = self.get("ADX_CONFIRMATION_RATIO", 0.8)

        self.use_bb_width_filter = self.get("USE_BB_WIDTH_FILTER", False)
        self.bb_width_threshold_percent = self.get("BB_WIDTH_THRESHOLD_PERCENT", 5.0)
        self.bb_squeeze_confirmation_ratio = self.get("BB_SQUEEZE_CONFIRMATION_RATIO", 0.8)

        self.use_volume_spike_confirmation = self.get("USE_VOLUME_SPIKE_CONFIRMATION", False)
        self.volume_spike_multiplier = self.get("VOLUME_SPIKE_MULTIPLIER", 1.5)
        self.min_volume_spike_confirmation_ratio = self.get("MIN_VOLUME_SPIKE_CONFIRMATION_RATIO", 0.1)
