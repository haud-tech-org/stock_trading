# src/stockreports/alert/approach/VRA/analyzer.py
"""
VRA (Volume Reversal Analysis) Analyzer - Pure calculation functions.

This module contains all pure calculation and analysis functions for the
VRA approach. These functions have no side effects and can be tested
independently.

Inherits common calculation methods from the base Analyzer class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.alert.common.constants import Trend, CandleColumn, CandleColor
from src.stockreports.utils import window_utils


class VraAnalyzer(Analyzer):
    """
    Analyzer for VRA (Volume Reversal Analysis) approach.

    Inherits common calculation functions from base Analyzer:
    - Body ratio and size calculations
    - Window size and trend determination
    - Candle color classification
    - Candle filtering operations
    - Window and volume calculations

    This class extends the base Analyzer with VRA-specific calculation
    methods.
    """

    @staticmethod
    def find_max_volume_candle(
        window_df: pd.DataFrame
    ) -> Optional[pd.Series]:
        """
        Find candle with maximum volume in window.

        Returns the Series representing the candle with the highest
        volume.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[pd.Series]: Candle with max volume, or None if
                window empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 200, 150]})
            >>> max_c = VraAnalyzer.find_max_volume_candle(df)
            >>> max_c['volume']
            200

        Note:
            Returns None if window empty.

        Guidelines:
            Used to identify candle with volume spike for VRA signal.
        """
        if window_df.empty:
            return None

        max_idx = window_df['volume'].idxmax()
        return window_df.loc[max_idx]

    @staticmethod
    def find_min_volume_candle(
        window_df: pd.DataFrame
    ) -> Optional[pd.Series]:
        """
        Find candle with minimum volume in window.

        Returns the Series representing the candle with the lowest
        volume.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[pd.Series]: Candle with min volume, or None if
                window empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 200, 150]})
            >>> min_c = VraAnalyzer.find_min_volume_candle(df)
            >>> min_c['volume']
            100

        Note:
            Returns None if window empty.

        Guidelines:
            Used as baseline for volume ratio calculation.
        """
        if window_df.empty:
            return None

        min_idx = window_df['volume'].idxmin()
        return window_df.loc[min_idx]

    @staticmethod
    def calculate_volume_ratio(
        max_volume: float,
        min_volume: float
    ) -> float:
        """
        Calculate volume ratio between max and min volume candles.

        Computes max_volume / min_volume to measure the magnitude of the
        volume spike between the highest and lowest volume candles.

        Args:
            max_volume (float): Maximum volume in the window.
            min_volume (float): Minimum volume in the window.

        Returns:
            float: Volume ratio. Returns float('inf') if min_volume is 0
                and max_volume > 0, returns 1.0 if both are 0.

        Example:
            >>> ratio = VraAnalyzer.calculate_volume_ratio(200, 100)
            >>> ratio
            2.0
            >>> ratio = VraAnalyzer.calculate_volume_ratio(200, 0)
            >>> ratio == float('inf')
            True

        Note:
            Matches original candle_utils.validate_volume_ratio edge
            case handling for zero volume scenarios.

        Guidelines:
            Ratio >= multiplier threshold indicates valid spike.
        """
        if min_volume == 0:
            # If the min candle's volume is 0, return infinite ratio if max_volume
            # > 0, otherwise return 1.0 (matching original logic)
            if max_volume > 0:
                return float('inf')
            else:
                return 1.0

        return max_volume / min_volume

    @staticmethod
    def get_window_trend_and_magnitude(
        window_df: pd.DataFrame
    ) -> Optional[Tuple[float, Trend]]:
        """
        Get trend direction and magnitude of window.

        Calculates the price movement direction and size using
        window utilities.

        Args:
            window_df (pd.DataFrame): Window with OHLC data.

        Returns:
            Optional[Tuple[float, Trend]]: (magnitude, trend) or None.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100],
            ...     'open': [100, 101, 102],
            ...     'close': [103, 102, 104]
            ... })
            >>> result = VraAnalyzer.get_window_trend_and_magnitude(
            ...     df
            ... )
            >>> result[0] > 0  # Positive magnitude
            True

        Note:
            Returns None if window empty or calculation fails.

        Guidelines:
            Trend window must show meaningful price movement.
        """
        if window_df.empty:
            return None

        window_size, trend = window_utils.get_window_size_and_trend(
            window_df
        )

        if trend is None or window_size is None:
            return None

        return (abs(window_size), trend)

    @staticmethod
    def find_anchor_candle(
        confirmation_window_df: pd.DataFrame,
        window_trend: Trend
    ) -> Optional[pd.Series]:
        """
        Find anchor candle in confirmation window based on trend direction and price validation.

        The anchor candle must satisfy strict criteria:
        - For UPTREND: The candle with the highest high price AND highest close price 
          AND the longest upper wick (high - close) AND must be GREEN (close > open)
        - For DOWNTREND: The candle with the lowest low price AND lowest close price 
          AND the longest lower wick (close - low) AND must be RED (close < open)

        The anchor candle serves as the reference point for validating
        reversal trend consistency in the confirmation window.

        Args:
            confirmation_window_df (pd.DataFrame): Confirmation window from
                max volume candle to end of lookback window.
            window_trend (Trend): The trend direction (UPTREND or DOWNTREND).

        Returns:
            Optional[pd.Series]: Anchor candle, or None if window is empty,
                trend is invalid, or no candle satisfies the criteria.

        Example:
            >>> import pandas as pd
            >>> from src.stockreports.alert.common.constants import Trend, CandleColumn
            >>> df = pd.DataFrame({
            ...     'high': [105, 110, 108],
            ...     'close': [104, 109, 107],
            ...     'open': [102, 105, 106],
            ...     'low': [100, 103, 101]
            ... })
            >>> anchor = VraAnalyzer.find_anchor_candle(df, Trend.UPTREND)
            >>> anchor[CandleColumn.HIGH]
            110
            >>> anchor[CandleColumn.CLOSE]
            109

        Note:
            Returns None if window is empty, trend is None/NEUTRAL, or if no candle
            satisfies all criteria (high/low + close + longest wick + correct color).

        Guidelines:
            Used to establish the pivot point for reversal consistency checks.
            The anchor must show both high wick and strong close for uptrend (green),
            or both low wick and weak close for downtrend (red).
        """
        if confirmation_window_df.empty or window_trend is None:
            return None

        try:
            if window_trend == Trend.UPTREND:
                # Find candle with highest high price
                max_high_idx = confirmation_window_df[CandleColumn.HIGH].idxmax()
                
                # Find candle with highest close price
                max_close_idx = confirmation_window_df[CandleColumn.CLOSE].idxmax()
                
                # Check if they're the same candle (satisfies high and close criteria)
                if max_high_idx != max_close_idx:
                    return None
                
                # Now check if this candle also has the longest upper wick
                # Upper wick = high - close
                confirmation_window_df_copy = confirmation_window_df.copy()
                confirmation_window_df_copy['upper_wick'] = (
                    confirmation_window_df_copy[CandleColumn.HIGH] - 
                    confirmation_window_df_copy[CandleColumn.CLOSE]
                )
                max_upper_wick_idx = confirmation_window_df_copy['upper_wick'].idxmax()
                
                # Check if it's the same candle with max high, max close, and longest upper wick
                if max_high_idx != max_upper_wick_idx:
                    return None
                
                # Finally, check if the anchor candle is GREEN (close > open) for uptrend
                anchor_candle = confirmation_window_df.loc[max_high_idx]
                candle_color = Analyzer.get_candle_color(anchor_candle)
                
                if candle_color == CandleColor.GREEN:
                    return anchor_candle
                else:
                    return None
                    
            elif window_trend == Trend.DOWNTREND:
                # Find candle with lowest low price
                min_low_idx = confirmation_window_df[CandleColumn.LOW].idxmin()
                
                # Find candle with lowest close price
                min_close_idx = confirmation_window_df[CandleColumn.CLOSE].idxmin()
                
                # Check if they're the same candle (satisfies low and close criteria)
                if min_low_idx != min_close_idx:
                    return None
                
                # Now check if this candle also has the longest lower wick
                # Lower wick = close - low
                confirmation_window_df_copy = confirmation_window_df.copy()
                confirmation_window_df_copy['lower_wick'] = (
                    confirmation_window_df_copy[CandleColumn.CLOSE] - 
                    confirmation_window_df_copy[CandleColumn.LOW]
                )
                max_lower_wick_idx = confirmation_window_df_copy['lower_wick'].idxmax()
                
                # Check if it's the same candle with min low, min close, and longest lower wick
                if min_low_idx != max_lower_wick_idx:
                    return None
                
                # Finally, check if the anchor candle is RED (close < open) for downtrend
                anchor_candle = confirmation_window_df.loc[min_low_idx]
                candle_color = Analyzer.get_candle_color(anchor_candle)
                
                if candle_color == CandleColor.RED:
                    return anchor_candle
                else:
                    return None
            else:
                return None
        except (KeyError, AttributeError):
            return None

