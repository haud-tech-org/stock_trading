from src.stockreports.alert.common.base_settings import BaseSettings

class ReversalConfirmationSettings(BaseSettings):
    """
    An abstract settings class that provides all configuration properties
    required by the reversal confirmation logic in `ReversalConfirmationExecutor`.
    """
    def __init__(self, symbol: str, approach_name: str):
        super().__init__(symbol, approach_name)

        self.long_forward_window = self.get('LONG_FORWARD_WINDOW')
        self.short_forward_window = self.get('SHORT_FORWARD_WINDOW')
        self.gap_price = self.get('GAP_PRICE')
        self.adjacent_gap_price = self.get('ADJACENT_GAP_PRICE')
        self.reversal_volume_multiplier = self.get('REVERSAL_VOLUME_MULTIPLIER')
        self.reversal_price_diff_threshold = self.get('REVERSAL_PRICE_DIFF_THRESHOLD')
        self.reversal_body_ratio_threshold = self.get('REVERSAL_BODY_RATIO_THRESHOLD')
        self.min_reversal_body_size = self.get('MIN_REVERSAL_BODY_SIZE')
        self.peak_trough_prominence = self.get('PEAK_TROUGH_PROMINENCE')
