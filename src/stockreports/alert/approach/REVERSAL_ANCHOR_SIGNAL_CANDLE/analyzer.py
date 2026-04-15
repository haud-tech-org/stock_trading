"""Analysis methods for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.

Pure calculation methods with no state. All analysis operations on candle data.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.common.constants import CandleColumn, Trend
from src.stockreports.utils import candle_utils, window_utils


class ReversalAnchorSignalCandleAnalyzer:
    """Analyzer for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.
    
    Provides static methods for analyzing price data and identifying
    anchor candles, signal candles, and alert candle characteristics.
    """

    @staticmethod
    def analyze_window_trend(
        window_df: pd.DataFrame,
    ) -> Tuple[Optional[Trend], float]:
        """Determine trend direction and window price range.
        
        Uses window_utils.get_trend() to determine trend based on
        first and last candle prices. Window size (HIGH - LOW range)
        is calculated using window_utils.get_window_high_low_range().
        
        Args:
            window_df: DataFrame slice representing lookback window
            
        Returns:
            Tuple of (trend, window_size) where:
            - trend: Trend.UPTREND or Trend.DOWNTREND
            - window_size: MAX(HIGH) - MIN(LOW) for entire window
            
        Raises:
            ValueError: If window_df is empty or has < 2 candles
        """
        if window_df.empty or len(window_df) < 2:
            raise ValueError("Window must have at least 2 candles for trend analysis")

        trend: Optional[Trend] = window_utils.get_trend(window_df)
        if trend is None:
            raise ValueError("Cannot determine trend from window")
        
        # Use utility to calculate window HIGH-LOW range
        window_size: float = window_utils.get_window_high_low_range(window_df)

        return trend, window_size

    @staticmethod
    def analyze_candle_body_size(candle: pd.Series) -> float:
        """Calculate body size for a candle.
        
        Body size = HIGH - LOW (full range, not close-open).
        
        Args:
            candle: Single OHLC candle (pd.Series)
            
        Returns:
            float: Body size in price points
            
        Raises:
            ValueError: If candle is missing required columns
        """
        if CandleColumn.HIGH not in candle.index or CandleColumn.LOW not in candle.index:
            raise ValueError("Candle must contain HIGH and LOW columns")

        body_size: float = candle[CandleColumn.HIGH] - candle[CandleColumn.LOW]
        return body_size

    @staticmethod
    def find_anchor_candle(window_df: pd.DataFrame) -> Tuple[pd.Timestamp, float]:
        """Find anchor candle (largest body in window).
        
        Uses candle_utils.find_biggest_body_candle() to locate the candle
        with maximum body size (close-open), then calculates HIGH-LOW range.
        
        Args:
            window_df: DataFrame slice with DatetimeIndex (pd.Timestamp) representing lookback window
            
        Returns:
            Tuple of (anchor_timestamp, anchor_body_size) where:
            - anchor_timestamp: pd.Timestamp matching DataFrame index type
            - anchor_body_size: float (HIGH-LOW range)
            
        Raises:
            ValueError: If window is empty
        """
        if window_df.empty:
            raise ValueError("Cannot find anchor in empty window")

        # Use utility to find biggest body candle
        anchor_candle: pd.Series = candle_utils.find_biggest_body_candle(window_df)
        
        # Get timestamp from index (matches DataFrame's DatetimeIndex type)
        anchor_timestamp: pd.Timestamp = anchor_candle.name
        
        # Validate it's a Timestamp
        if not isinstance(anchor_timestamp, pd.Timestamp):
            raise ValueError(
                f"Anchor index must be pd.Timestamp, got {type(anchor_timestamp).__name__}. "
                f"DataFrame index must be DatetimeIndex with Timestamp values."
            )
        
        # Use utility to calculate candle HIGH-LOW range
        anchor_body: float = candle_utils.get_candle_high_low_range(anchor_candle)
        
        return anchor_timestamp, anchor_body

    @staticmethod
    def find_signal_candle(
        window_df: pd.DataFrame,
        anchor_idx: pd.Timestamp,
    ) -> Tuple[pd.Timestamp, float]:
        """Find signal candle (max volume at or after anchor).
        
        Extracts window from anchor onwards, then uses
        candle_utils.find_max_volume_candle() to identify max volume candle.
        
        Args:
            window_df: DataFrame slice with DatetimeIndex (pd.Timestamp)
            anchor_idx: pd.Timestamp of anchor candle (must match window_df.index type)
            
        Returns:
            Tuple of (signal_timestamp, signal_volume) where:
            - signal_timestamp: pd.Timestamp matching DataFrame index type
            - signal_volume: float (volume value)
            
        Raises:
            ValueError: If anchor_idx out of bounds or type mismatch
        """
        if not isinstance(anchor_idx, pd.Timestamp):
            raise ValueError(
                f"anchor_idx must be pd.Timestamp, got {type(anchor_idx).__name__}. "
                f"Must match the DataFrame's DatetimeIndex type."
            )
        
        if anchor_idx not in window_df.index:
            raise ValueError(f"Anchor timestamp {anchor_idx} not in window")

        # Get window from anchor onwards
        after_anchor: pd.DataFrame = window_df.loc[anchor_idx:]
        
        if after_anchor.empty:
            raise ValueError("No candles found at or after anchor")

        # Use utility to find max volume candle
        signal_candle: pd.Series = candle_utils.find_max_volume_candle(after_anchor)
        
        # Get timestamp from index (matches DataFrame's DatetimeIndex type)
        signal_timestamp: pd.Timestamp = signal_candle.name
        
        # Validate it's a Timestamp
        if not isinstance(signal_timestamp, pd.Timestamp):
            raise ValueError(
                f"Signal index must be pd.Timestamp, got {type(signal_timestamp).__name__}. "
                f"DataFrame index must be DatetimeIndex with Timestamp values."
            )
        
        signal_volume: float = signal_candle[CandleColumn.VOLUME]

        return signal_timestamp, signal_volume

    @staticmethod
    def calculate_wick_percentage(
        alert_candle: pd.Series,
        trend: Trend,
    ) -> float:
        """Calculate wick percentage for alert candle.
        
        For uptrend: upper_wick / candle_range (HIGH - CLOSE) / (HIGH - LOW)
        For downtrend: lower_wick / candle_range (CLOSE - LOW) / (HIGH - LOW)
        
        Args:
            alert_candle: The final candle in window
            trend: Trend instance (UPTREND or DOWNTREND)
            
        Returns:
            float: Wick percentage (0.0 to 1.0)
            
        Raises:
            ValueError: If invalid trend or candle_range is 0
        """
        if trend not in (Trend.UPTREND, Trend.DOWNTREND):
            raise ValueError(f"Invalid trend: {trend}")

        high: float = alert_candle[CandleColumn.HIGH]
        low: float = alert_candle[CandleColumn.LOW]
        close: float = alert_candle[CandleColumn.CLOSE]

        candle_range: float = high - low
        
        if candle_range == 0:
            return 0.0

        if trend == Trend.UPTREND:
            # Upper wick: distance from close to high
            wick: float = high - close
        else:  # downtrend
            # Lower wick: distance from low to close
            wick = close - low

        wick_percentage: float = wick / candle_range
        return wick_percentage

    @staticmethod
    def calculate_average_body_size(window_df: pd.DataFrame) -> float:
        """Calculate average body size in window.
        
        Used as baseline for anchor candle validation.
        Uses window_utils.get_average_candle_range() to calculate average
        HIGH-LOW range for all candles in the window.
        
        Args:
            window_df: DataFrame slice representing lookback window
            
        Returns:
            float: Average body size (average HIGH - LOW)
            
        Raises:
            ValueError: If window is empty
        """
        if window_df.empty:
            raise ValueError("Cannot calculate average body size for empty window")

        # Use utility to calculate average candle range (HIGH - LOW)
        average_body: float = window_utils.get_average_candle_range(window_df)
        return average_body

    @staticmethod
    def calculate_average_volume(window_df: pd.DataFrame) -> float:
        """Calculate average volume in window.
        
        Used as baseline for signal candle validation.
        Direct calculation using pandas (no specific utility available).
        
        Args:
            window_df: DataFrame slice representing lookback window
            
        Returns:
            float: Average volume
            
        Raises:
            ValueError: If window is empty
        """
        if window_df.empty:
            raise ValueError("Cannot calculate average volume for empty window")

        average_vol: float = window_df[CandleColumn.VOLUME].mean()
        return average_vol
