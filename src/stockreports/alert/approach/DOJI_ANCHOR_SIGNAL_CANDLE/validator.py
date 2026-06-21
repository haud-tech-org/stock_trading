from typing import Optional
import pandas as pd

from src.stockreports.alert.common.constants import CandleColumn, Trend
from src.stockreports.utils import window_utils
from .analyzer import DojiAnchorSignalCandleAnalyzer


class DojiAnchorSignalCandleValidator:
    """Pure validation functions for DOJI_ANCHOR_SIGNAL_CANDLE."""

    @staticmethod
    def validate_momentum(df: pd.DataFrame, anchor_idx: int, doji_idx: int, min_price_move: float) -> bool:
        """Validate momentum window range between anchor and doji.
        
        Validates that the price range of the window from anchor to doji exceeds the minimum
        momentum threshold. This ensures sufficient price movement volatility exists in the
        anchor-to-doji window for a valid trade signal.
        
        Window Range = MAX(HIGH) - MIN(LOW) in [anchor_idx, doji_idx]
        
        Args:
            df: OHLCV DataFrame
            anchor_idx: index of anchor candle
            doji_idx: index of doji candle
            min_price_move: minimum required window range (momentum threshold)
            
        Returns:
            True if window_range > min_price_move, False otherwise
        """
        
        # Calculate window range from anchor to doji
        window_start = min(anchor_idx, doji_idx)
        window_end = max(anchor_idx, doji_idx)
        window_df = df.iloc[window_start:window_end+1]
        window_range = window_utils.get_window_high_low_range(window_df)
        
        # Validate: window range must exceed minimum price move threshold
        if window_range >= min_price_move:
            return True
        
        return False

    @staticmethod
    def validate_trend_candle(df: pd.DataFrame, trend_idx: int, start_idx: int, end_idx: int, range_multiplier: float, min_body: float) -> bool:
        if trend_idx is None:
            return False
        high = float(df.iloc[trend_idx][CandleColumn.HIGH])
        low = float(df.iloc[trend_idx][CandleColumn.LOW])
        body = abs(float(df.iloc[trend_idx][CandleColumn.CLOSE]) - float(df.iloc[trend_idx][CandleColumn.OPEN]))
        candle_range = high - low
        avg_range = float(df[CandleColumn.HIGH].subtract(df[CandleColumn.LOW]).iloc[start_idx:end_idx+1].mean())
        if avg_range == 0 or avg_range is None:
            return body >= min_body
        return (candle_range >= avg_range * range_multiplier) and (body >= min_body)

    @staticmethod
    def validate_alert_candle(df: pd.DataFrame, alert_idx: int, doji_idx: int, trend: str, reversal_confirmation_threshold: float, max_volume_ratio: float, min_body: float, avg_momentum_volume: Optional[float]) -> bool:
        """Validate alert candle based on reversed trend direction.
        
        Alert candle validates for a REVERSAL of the anchor trend:
        - If anchor trend is UPTREND → expect alert to reverse to DOWNTREND (bearish below doji_low)
        - If anchor trend is DOWNTREND → expect alert to reverse to UPTREND (bullish above doji_high)
        
        Args:
            df: OHLCV DataFrame
            alert_idx: index of alert candle
            doji_idx: index of doji candle
            trend: original trend direction from anchor (Trend.UPTREND or Trend.DOWNTREND)
            reversal_confirmation_threshold: threshold for computing reversal bounds from doji close
            max_volume_ratio: maximum volume ratio check
            min_body: minimum body size
            avg_momentum_volume: average volume for volume ratio check
            
        Returns:
            True if alert candle passes reversal validations, False otherwise
        """
        if alert_idx is None:
            return False
        
        # Determine expected reversal trend
        if trend == Trend.UPTREND:
            reversal_trend = Trend.DOWNTREND
        elif trend == Trend.DOWNTREND:
            reversal_trend = Trend.UPTREND
        else:
            # no clear trend, cannot validate
            return False
        
        alert_close = float(df.iloc[alert_idx][CandleColumn.CLOSE])
        doji_open = float(df.iloc[doji_idx][CandleColumn.OPEN])
        doji_close = float(df.iloc[doji_idx][CandleColumn.CLOSE])
        doji_high = float(df.iloc[doji_idx][CandleColumn.HIGH])
        doji_low = float(df.iloc[doji_idx][CandleColumn.LOW])
        body = abs(float(df.iloc[alert_idx][CandleColumn.CLOSE]) - float(df.iloc[alert_idx][CandleColumn.OPEN]))
        
        # Pre-validate volume and body size before checking direction
        # volume check
        if avg_momentum_volume is not None and avg_momentum_volume > 0:
            alert_vol = float(df.iloc[alert_idx][CandleColumn.VOLUME])
            if alert_vol > avg_momentum_volume * max_volume_ratio:
                return False
        
        # body size check
        if body < min_body:
            return False
        
        # Now validate direction based on reversal_trend
        if reversal_trend == Trend.DOWNTREND:
            # For downtrend reversal, expect bearish (alert_close below doji_low)
            # Use max of doji_low or (doji_close - reversal_confirmation_threshold)
            lower_bound = max(doji_low, doji_close - reversal_confirmation_threshold)
            return alert_close < lower_bound
        elif reversal_trend == Trend.UPTREND:
            # For uptrend reversal, expect bullish (alert_close above doji_high)
            # Use min of doji_high or (doji_close + reversal_confirmation_threshold)
            upper_bound = min(doji_high, doji_close + reversal_confirmation_threshold)
            return alert_close > upper_bound
