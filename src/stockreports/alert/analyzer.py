"""
Abstract base class for Analyzer implementations across all approaches.

This module provides the base Analyzer class with common static methods for
pure calculations that are shared across multiple trading approaches.
Subclasses implement approach-specific analysis logic while inheriting
common calculation utilities.
"""

from abc import ABC
import pandas as pd
from typing import List, Optional, Tuple
from src.stockreports.alert.common.constants import Trend, CandleColor, CandleColumn
from src.stockreports.utils import window_utils, candle_utils


class Analyzer(ABC):
    """
    Abstract base class for approach-specific Analyzers.
    
    Provides common static calculation methods that are reusable across
    different trading approaches. These are pure functions with no state
    mutations or side effects.
    
    Each approach subclasses this to inherit common calculations while
    adding approach-specific analysis methods.
    
    Color Constants:
        All candle color returns use CandleColor constants:
        - CandleColor.GREEN - Bullish candle (close > open)
        - CandleColor.RED - Bearish candle (close < open)
        - CandleColor.NEUTRAL - No change (close == open)
    
    Examples:
        - StrongCandleAnalyzer(Analyzer)
        - IchimokuAnalyzer(Analyzer) - purely approach-specific, no inheritance used
        - VRAAnalyzer(Analyzer)
    """
    
    # ===== COMMON CANDLE CALCULATIONS =====
    
    @staticmethod
    def calculate_body_ratio(candle: pd.Series) -> float:
        """
        Calculate the body ratio of a candle.
        
        Body ratio = body size / full candle range (high - low)
        
        Ratio of 1.0 = full range is body (no wicks)
        Ratio of 0.0 = no body (doji/cross)
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close', 'high', 'low'
            
        Returns:
            float: Body ratio (0.0 to 1.0)
        """
        high = candle[CandleColumn.HIGH]
        low = candle[CandleColumn.LOW]
        open_price = candle[CandleColumn.OPEN]
        close = candle[CandleColumn.CLOSE]
        
        full_range = high - low
        if full_range == 0:
            return 0.0
        
        body_size = abs(close - open_price)
        body_ratio = body_size / full_range
        
        return body_ratio
    
    @staticmethod
    def calculate_body_size(candle: pd.Series) -> float:
        """
        Calculate the absolute body size of a candle.
        
        Body size = absolute difference between close and open
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close'
            
        Returns:
            float: Absolute body size in price units
        """
        body_size = abs(candle[CandleColumn.CLOSE] - candle[CandleColumn.OPEN])
        return body_size
    
    @staticmethod
    def get_candle_color(candle: pd.Series) -> CandleColor:
        """
        Determine the color of a candle.
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close'
            
        Returns:
            CandleColor: One of the following:
                - CandleColor.GREEN if close > open (bullish)
                - CandleColor.RED if close < open (bearish)
                - CandleColor.NEUTRAL if close == open (no change)
        """
        if candle[CandleColumn.CLOSE] > candle[CandleColumn.OPEN]:
            return CandleColor.GREEN
        elif candle[CandleColumn.CLOSE] < candle[CandleColumn.OPEN]:
            return CandleColor.RED
        else:
            return CandleColor.NEUTRAL
    
    # ===== COMMON WINDOW CALCULATIONS =====
    
    @staticmethod
    def get_window_size_and_trend(
        lookback_window_df: pd.DataFrame
    ) -> Tuple[float, Optional[Trend]]:
        """
        Calculate window size and trend from close price extremes.
        
        Uses the minimum and maximum close prices in the window to determine:
        - Window size: max close - min close
        - Trend: UPTREND if close is rising, DOWNTREND if falling
        
        Args:
            lookback_window_df (pd.DataFrame): DataFrame with 'close' column
            
        Returns:
            Tuple[float, Optional[Trend]]: (window_size, trend)
                - window_size: Price range between min and max close
                - trend: UPTREND if first close < last close, DOWNTREND otherwise
                - trend: None if cannot determine
        """
        if len(lookback_window_df) == 0:
            return 0.0, None
        
        window_size_val, window_trend = window_utils.get_window_size_and_trend_by_close_extremes(
            lookback_window_df
        )
        
        return window_size_val, window_trend
    
    @staticmethod
    def calculate_window_price_range(df: pd.DataFrame) -> Optional[float]:
        """
        Calculate the price range of a window using high/low extremes.
        
        Args:
            df (pd.DataFrame): DataFrame with 'high', 'low' columns
            
        Returns:
            Optional[float]: Price range (max high - min low) or None if calculation fails
        """
        if len(df) == 0:
            return None
        
        try:
            min_low = df[CandleColumn.LOW].min()
            max_high = df[CandleColumn.HIGH].max()
            price_range = max_high - min_low
            return price_range
        except (KeyError, TypeError):
            return None
    
    @staticmethod
    def calculate_conditional_window_price_range(
        lookback_window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate price range of conditional window (excluding last/alert candle).
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window DataFrame
            
        Returns:
            Optional[float]: Price range of conditional window (all except last candle)
        """
        if len(lookback_window_df) <= 1:
            return None
        
        conditional_window_df = lookback_window_df.iloc[:-1]
        return Analyzer.calculate_window_price_range(conditional_window_df)
    
    # ===== COMMON VOLUME CALCULATIONS =====
    
    @staticmethod
    def find_min_volume_candle_up_to_index(
        window_df: pd.DataFrame,
        target_candle: pd.Series
    ) -> Optional[pd.Series]:
        """
        Find candle with minimum volume from start up to (but not including) target candle.

        Searches for the minimum volume candle in the portion of the window
        from the beginning up to (but not including) the target candle's index.
        This is useful for finding min volume before a peak volume candle, ensuring
        a strict ordering relationship.

        Args:
            window_df (pd.DataFrame): Full window with volume column.
            target_candle (pd.Series): Target candle that defines the search boundary.

        Returns:
            Optional[pd.Series]: Candle with min volume up to (but not including)
                target candle index, or None if invalid input or insufficient candles.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 200, 150]}, index=['a', 'b', 'c'])
            >>> target_c = df.loc['b']
            >>> min_c = Analyzer.find_min_volume_candle_up_to_index(df, target_c)
            >>> min_c['volume']
            100
            >>> min_c.name
            'a'

        Note:
            Returns None if window is empty, target_candle not in window,
            or if there are no candles before the target candle.

        Guidelines:
            Useful for ensuring volume progression patterns across approaches.
        """
        if window_df.empty:
            return None

        try:
            target_idx = window_df.index.get_loc(target_candle.name)
            # Slice from start to target index (exclusive)
            slice_df = window_df.iloc[:target_idx]

            if slice_df.empty:
                # No candles before target candle
                return None

            min_idx = slice_df[CandleColumn.VOLUME].idxmin()
            return window_df.loc[min_idx]
        except (KeyError, AttributeError):
            return None

    @staticmethod
    def get_max_volume_in_window(df: pd.DataFrame) -> float:
        """
        Get maximum volume in a DataFrame window.
        
        Args:
            df (pd.DataFrame): DataFrame with 'volume' column
            
        Returns:
            float: Maximum volume, or 0.0 if DataFrame empty/no volume column
        """
        if len(df) == 0 or CandleColumn.VOLUME not in df.columns:
            return 0.0
        
        return df[CandleColumn.VOLUME].max()
    
    @staticmethod
    def get_max_volume_in_conditional_window(
        lookback_window_df: pd.DataFrame
    ) -> float:
        """
        Get maximum volume in conditional window (excluding alert candle).
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window DataFrame
            
        Returns:
            float: Maximum volume in conditional window
        """
        if len(lookback_window_df) <= 1:
            return 0.0
        
        conditional_window_df = lookback_window_df.iloc[:-1]
        return Analyzer.get_max_volume_in_window(conditional_window_df)
    
    # ===== COMMON WINDOW SLICING =====
    
    @staticmethod
    def slice_window(
        window_df: pd.DataFrame,
        start_candle: pd.Series,
        end_candle: pd.Series
    ) -> Optional[pd.DataFrame]:
        """
        Slice window from start candle to end candle (inclusive).

        Extracts the portion of the window between two candles, useful for
        analyzing price movement patterns between key points.

        Args:
            window_df (pd.DataFrame): Full window.
            start_candle (pd.Series): Starting candle (inclusive).
            end_candle (pd.Series): Ending candle (inclusive).

        Returns:
            Optional[pd.DataFrame]: Sliced window from start_candle to end_candle,
                or None if invalid (start > end or candles not in window).

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'close': [100, 102, 101, 103]
            ... }, index=['a', 'b', 'c', 'd'])
            >>> start = df.loc['a']
            >>> end = df.loc['d']
            >>> sliced = Analyzer.slice_window(df, start, end)
            >>> len(sliced)
            4

        Note:
            Returns None if start_index > end_index or candles not found.

        Guidelines:
            Useful for analyzing price action between identified key points
            (e.g., min volume to alert candle, support to resistance, etc).
        """
        try:
            start_idx = window_df.index.get_loc(start_candle.name)
            end_idx = window_df.index.get_loc(end_candle.name)

            if start_idx > end_idx:
                return None

            return window_df.iloc[start_idx:end_idx + 1]
        except (KeyError, AttributeError):
            return None
    
    # ===== SHIFTED CANDLE RETRIEVAL =====
    
    @staticmethod
    def get_shifted_candle(
        scan_index: int,
        df_indexed: pd.DataFrame,
        shift_offset: int
    ) -> Tuple[bool, Optional[pd.Series]]:
        """
        Retrieve a forward-shifted candle from the dataframe for shifted indicators.
        
        Pure static calculation method that retrieves candles at shifted indices,
        commonly used by approaches with forward-shifted technical indicators
        (e.g., Ichimoku's Senkou Cloud, VRA's shifted validation).
        
        Args:
            scan_index (int): Current scanning index in the dataframe
            df_indexed (pd.DataFrame): Indexed dataframe with all candles
            shift_offset (int): Number of periods to shift forward (e.g., senkou_shift_period)
            
        Returns:
            Tuple[bool, Optional[pd.Series]]:
                - bool: True if shift was successful or fallback to last candle applied;
                        False if exception or empty dataframe encountered
                - pd.Series: The shifted candle if within bounds, 
                            the last candle if out of bounds (graceful fallback),
                            None if error occurred or dataframe is empty
            
        Behavior:
            - Within bounds: Returns (True, shifted_candle) - exact shifted candle
            - Out of bounds: Returns (True, last_candle) - graceful fallback to last available candle
            - Exception/Empty: Returns (False, None) - clean failure signal
            
        Example:
            ```python
            success, shifted_candle = Analyzer.get_shifted_candle(i, df_indexed, senkou_shift)
            if success and shifted_candle is not None:
                # Successfully obtained candle for shifted indicator alignment
                alert = create_alert_at_time(shifted_candle.name)
            else:
                # Failed due to error or empty dataframe
                continue
            ```
        
        Guidelines:
            - Executor calls this method and updates its current_window_end_time state
            - This method is pure calculation with no state mutations
            - Handles edge cases (out of bounds, exceptions) with clear return semantics
        """
        if df_indexed is None or df_indexed.empty:
            return False, None
        
        shifted_idx = scan_index + shift_offset
        
        # Safety check: ensure shifted index is within bounds
        if shifted_idx >= len(df_indexed):
            # Return last candle if shifted index is out of bounds (graceful fallback)
            last_candle = df_indexed.iloc[-1]
            return True, last_candle
        
        try:
            shifted_candle = df_indexed.iloc[shifted_idx]
            return True, shifted_candle
        except (IndexError, KeyError) as e:
            # Return False with None on error (clean failure)
            return False, None
    
    # ===== COMMON CANDLE FILTERING =====
    
    @staticmethod
    def get_opposite_color_candles(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series
    ) -> List[pd.Series]:
        """
        Filter and return all candles with opposite color to alert candle.
        
        Compares candle colors using close > open (green) vs close < open (red).
        
        Args:
            lookback_window_df (pd.DataFrame): DataFrame with OHLC data (excluding alert candle)
            alert_candle (pd.Series): The alert candle to compare against
            
        Returns:
            List[pd.Series]: List of candles with opposite color
        """
        alert_is_green = candle_utils.is_green_candle(alert_candle)
        
        opposite_color_candles = []
        for _, row in lookback_window_df.iterrows():
            is_green = candle_utils.is_green_candle(row)
            # Keep only candles with opposite color to alert candle
            if is_green != alert_is_green:
                opposite_color_candles.append(row)
        
        return opposite_color_candles
