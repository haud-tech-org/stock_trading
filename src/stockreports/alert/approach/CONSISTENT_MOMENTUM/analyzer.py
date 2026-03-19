# src/stockreports/alert/approach/CONSISTENT_MOMENTUM/analyzer.py
"""
CONSISTENT_MOMENTUM Analyzer - Pure calculation functions.

This module contains all pure calculation and analysis functions for the
CONSISTENT_MOMENTUM approach. These functions have no side effects and can be
tested independently.

Inherits common calculation methods from the base Analyzer class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.alert.common.constants import CandleColumn
from src.stockreports.utils import window_utils


class ConsistentMomentumAnalyzer(Analyzer):
    """
    Analyzer for CONSISTENT_MOMENTUM approach.

    Inherits common calculation functions from base Analyzer:
    - Body ratio and size calculations
    - Window size and trend determination
    - Candle color classification
    - Candle filtering operations
    - Window and volume calculations

    This class extends the base Analyzer with specific calculation methods
    for the CONSISTENT_MOMENTUM approach.
    """

    @staticmethod
    def calculate_max_body_positions(
        confirmation_window_df: pd.DataFrame
    ) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        """
        Calculate the first and second maximum body candles in window.

        Analyzes the confirmation window to find the positions of the
        two candles with the largest body sizes (close - open).

        Args:
            confirmation_window_df (pd.DataFrame): Confirmation window
                data with open and close prices.

        Returns:
            Tuple[Optional[int], Optional[int], Optional[float]]:
                (first_max_pos, second_max_pos, max_body_value) or
                (None, None, None) if window has fewer than 2 candles.
                Positions are relative to window start (0-indexed).

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [101, 105, 103]
            ... })
            >>> pos1, pos2, max_val = (
            ...     ConsistentMomentumAnalyzer.
            ...     calculate_max_body_positions(df)
            ... )
            >>> pos1, pos2, max_val
            (1, 0, 4.0)

        Note:
            Body size = |close - open|. Returns positions in ascending
            order (first_max_pos <= second_max_pos).

        Guidelines:
            Assumes window has at least 2 candles. Returns None if
            precondition not met.
        """
        if len(confirmation_window_df) < 2:
            return (None, None, None)

        # Calculate body for each candle
        confirmation_copy = confirmation_window_df.copy()
        confirmation_copy['body'] = abs(
            confirmation_copy[CandleColumn.CLOSE] - confirmation_copy[CandleColumn.OPEN]
        )

        # Get top 2 by body size
        sorted_by_body = confirmation_copy.nlargest(2, 'body')
        max_body_value = sorted_by_body.iloc[0]['body']

        # Get positions
        max_positions = sorted([
            confirmation_copy.index.get_loc(idx)
            for idx in sorted_by_body.index
        ])

        return (max_positions[0], max_positions[1], max_body_value)

    @staticmethod
    def calculate_window_price_range(
        window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate the price range of a window using close extremes.

        Computes the difference between highest and lowest close prices
        in the given window using the close price extremes method.

        Args:
            window_df (pd.DataFrame): Price window with close column.

        Returns:
            Optional[float]: Absolute difference between max and min
                close prices, or None if calculation fails.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'close': [100, 102, 101, 103]})
            >>> price_range = (
            ...     ConsistentMomentumAnalyzer.calculate_window_price_range(
            ...     df
            ... )
            >>> price_range
            3.0

        Note:
            Uses close-based extremes rather than high/low. Requires
            non-empty DataFrame with 'close' column.

        Guidelines:
            Returns None if window is empty or missing 'close' column.
        """
        if window_df.empty or 'close' not in window_df.columns:
            return None

        window_size_val, _ = (
            window_utils.get_window_size_and_trend_by_close_extremes(
                window_df
            )
        )
        return window_size_val

    @staticmethod
    def calculate_volume_stats(
        window_df: pd.DataFrame
    ) -> Optional[Tuple[float, float, float]]:
        """
        Calculate volume statistics for a window.

        Computes minimum, maximum, and ratio of volumes in the given
        price window.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[Tuple[float, float, float]]: (min_vol, max_vol,
                ratio) or None if window is empty. Ratio is max/min.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 200, 150]})
            >>> min_v, max_v, ratio = (
            ...     ConsistentMomentumAnalyzer.calculate_volume_stats(
            ...     df
            ... )
            >>> min_v, max_v, ratio
            (100, 200, 2.0)

        Note:
            Ratio = max_volume / min_volume. Returns (None, None, None)
            if window is empty or min volume is 0.

        Guidelines:
            Used for volume consistency validation. Handles edge case
            where min volume is 0 or negative.
        """
        if window_df.empty or 'volume' not in window_df.columns:
            return None

        min_vol = window_df['volume'].min()
        max_vol = window_df['volume'].max()

        if min_vol <= 0:
            return None

        ratio = max_vol / min_vol
        return (min_vol, max_vol, ratio)

    @staticmethod
    def calculate_gaps_between_candles(
        window_df: pd.DataFrame
    ) -> list[float]:
        """
        Calculate gaps between consecutive candles.

        Computes the absolute difference between the close price of one
        candle and the open price of the next candle for all consecutive
        pairs in the window.

        Args:
            window_df (pd.DataFrame): Window with open and close
                columns, ordered chronologically.

        Returns:
            list[float]: List of gap values. Empty list if fewer than
                2 candles.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'close': [100, 101, 102],
            ...     'open': [100.5, 101.5, 102.5]
            ... })
            >>> gaps = (
            ...     ConsistentMomentumAnalyzer.calculate_gaps_between_candles(
            ...     df
            ... )
            >>> gaps
            [0.5, 0.5]

        Note:
            Gap = |close[i] - open[i+1]|. A gap of 0 means no gap
            between consecutive candles.

        Guidelines:
            Window must be ordered chronologically. Returns empty list
            if window has fewer than 2 candles.
        """
        if len(window_df) < 2:
            return []

        gaps = []
        for i in range(len(window_df) - 1):
            close_current = window_df.iloc[i]['close']
            open_next = window_df.iloc[i + 1]['open']
            gap = abs(close_current - open_next)
            gaps.append(gap)

        return gaps

    @staticmethod
    def get_body_sizes(
        window_df: pd.DataFrame
    ) -> list[float]:
        """
        Get body sizes for all candles in window.

        Calculates the body size (|close - open|) for each candle in
        the window and returns as a list.

        Args:
            window_df (pd.DataFrame): Window with open and close
                columns.

        Returns:
            list[float]: List of body sizes in order. Empty list if
                window is empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [102, 103, 101]
            ... })
            >>> bodies = (
            ...     ConsistentMomentumAnalyzer.get_body_sizes(df)
            ... )
            >>> bodies
            [2.0, 2.0, 1.0]

        Note:
            Body size = |close - open|. Always positive.

        Guidelines:
            Returns empty list for empty window. Used to assess candle
            strength throughout the window.
        """
        if window_df.empty:
            return []

        bodies = [
            abs(row['close'] - row['open'])
            for _, row in window_df.iterrows()
        ]
        return bodies
