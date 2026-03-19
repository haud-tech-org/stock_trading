# src/stockreports/alert/approach/CONSISTENT_VOLUME_ANCHOR/analyzer.py
"""
CONSISTENT_VOLUME_ANCHOR (CVA) Analyzer - Pure calculation functions.

This module contains all pure calculation and analysis functions for the
CONSISTENT_VOLUME_ANCHOR approach. These functions have no side effects and
can be tested independently.

Inherits common calculation methods from the base Analyzer class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.alert.common.constants import CandleColumn
from src.stockreports.utils import candle_utils, window_utils


class ConsistentVolumeAnchorAnalyzer(Analyzer):
    """
    Analyzer for CONSISTENT_VOLUME_ANCHOR approach.

    Inherits common calculation functions from base Analyzer:
    - Body ratio and size calculations
    - Window size and trend determination
    - Candle color classification
    - Candle filtering operations
    - Window and volume calculations

    This class extends the base Analyzer with CVA-specific calculation
    methods.
    """

    @staticmethod
    def find_anchor_candle(
        lookback_window_df: pd.DataFrame
    ) -> Optional[int]:
        """
        Find anchor candle with strictly decreasing volumes.

        Identifies the first candle where volumes from start to this
        candle are strictly decreasing. This represents the point where
        volume momentum shifts.

        Args:
            lookback_window_df (pd.DataFrame): Window with volume
                column.

        Returns:
            Optional[int]: Index position of anchor candle (relative to
                window), or None if not found.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 90, 80, 70, 85]
            ... })
            >>> idx = (
            ...     ConsistentVolumeAnchorAnalyzer.find_anchor_candle(
            ...     df
            ... )
            >>> idx
            3

        Note:
            Requires strictly decreasing volumes from start. Returns
            first position where this pattern holds. Returns None if
            pattern never occurs.

        Guidelines:
            Anchor marks the turning point in volume trend. Checked
            sequentially from position 1 onwards.
        """
        volumes = lookback_window_df[CandleColumn.VOLUME].values

        for i in range(1, len(volumes)):
            # Check if volumes from 0 to i are strictly decreasing
            is_decreasing = all(
                volumes[j] > volumes[j + 1] for j in range(i)
            )
            if is_decreasing:
                return i

        return None

    @staticmethod
    def extract_consistent_window(
        lookback_window_df: pd.DataFrame,
        anchor_index: int
    ) -> Optional[pd.DataFrame]:
        """
        Extract window from anchor candle to penultimate candle.

        Creates a window starting at the anchor candle and ending at
        the second-to-last candle (excluding the alert/last candle).
        This window contains candles showing consistent patterns before
        the final alert candle.

        Args:
            lookback_window_df (pd.DataFrame): Full lookback window.
            anchor_index (int): Index of anchor candle.

        Returns:
            Optional[pd.DataFrame]: Window from anchor to penultimate
                candle, or None if anchor too close to end.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102, 103, 104],
            ...     'close': [101, 102, 103, 104, 105]
            ... })
            >>> window = (
            ...     ConsistentVolumeAnchorAnalyzer.extract_consistent_window(
            ...     df, 1
            ... )
            >>> len(window)
            3

        Note:
            Returns window from anchor_index to (len - 1) inclusive.
            Returns None if anchor_index >= (len - 1).

        Guidelines:
            Window must have space for alert candle after it. Used to
            validate consistent patterns before final signal.
        """
        end_index = len(lookback_window_df) - 1

        if anchor_index >= end_index:
            return None

        return lookback_window_df.iloc[anchor_index:end_index]

    @staticmethod
    def filter_window_by_volume_and_body(
        window_df: pd.DataFrame,
        median_volume: float,
        max_volume_multiplier: float,
        max_body_size: float
    ) -> pd.DataFrame:
        """
        Filter window by volume consistency and body size.

        Applies two sequential filters:
        1. Volume filter: volume * max_multiplier <= median_volume
        2. Body size filter: |close - open| <= max_body_size

        Returns only candles passing both conditions.

        Args:
            window_df (pd.DataFrame): Window to filter.
            median_volume (float): Median volume threshold.
            max_volume_multiplier (float): Volume multiplier factor.
            max_body_size (float): Maximum body size threshold.

        Returns:
            pd.DataFrame: Filtered window (may be empty if no candles
                match).

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [80, 100, 90],
            ...     'open': [100, 101, 102],
            ...     'close': [101, 102, 103]
            ... })
            >>> filtered = (
            ...     ConsistentVolumeAnchorAnalyzer.
            ...     filter_window_by_volume_and_body(
            ...     df, 100, 1.1, 1.5
            ... )
            >>> len(filtered)
            2

        Note:
            Filters applied sequentially: volume first, then body size.
            Returns empty DataFrame if no candles match.

        Guidelines:
            Used to identify "consistent" candles that show stable
            patterns before the alert candle.
        """
        # Filter by volume condition
        volume_mask = (
            window_df[CandleColumn.VOLUME] * max_volume_multiplier
        ) <= median_volume
        volume_filtered = window_df[volume_mask]

        # Filter by body size condition
        bodies = (
            volume_filtered[CandleColumn.CLOSE] -
            volume_filtered[CandleColumn.OPEN]
        ).abs()
        body_mask = bodies <= max_body_size
        filtered_result = volume_filtered[body_mask]

        return filtered_result

    @staticmethod
    def calculate_window_price_range(
        window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate price range of window using high/low extremes.

        Computes the difference between highest and lowest prices in
        the window using standard high-low methodology.

        Args:
            window_df (pd.DataFrame): Window with high and low columns.

        Returns:
            Optional[float]: Absolute difference between max high and
                min low, or None if empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100]
            ... })
            >>> price_range = (
            ...     ConsistentVolumeAnchorAnalyzer.
            ...     calculate_window_price_range(df)
            ... )
            >>> price_range
            5.0

        Note:
            Returns None if window is empty. Uses high-low extremes,
            not close extremes.

        Guidelines:
            Represents total price volatility range in window. Used to
            validate window size thresholds.
        """
        if window_df.empty:
            return None

        window_size, _ = window_utils.get_window_size_and_trend(
            window_df
        )
        return abs(window_size)

    @staticmethod
    def calculate_alert_body_ratio(
        alert_candle: pd.Series
    ) -> Optional[float]:
        """
        Calculate body ratio for alert candle.

        Computes the ratio of body size to range:
        body_ratio = |close - open| / (high - low)

        Args:
            alert_candle (pd.Series): Candle with OHLC data.

        Returns:
            Optional[float]: Body ratio (0-1 range), or None if range
                is invalid.

        Example:
            >>> import pandas as pd
            >>> candle = pd.Series({
            ...     'open': 100,
            ...     'close': 104,
            ...     'high': 105,
            ...     'low': 99
            ... })
            >>> ratio = (
            ...     ConsistentVolumeAnchorAnalyzer.
            ...     calculate_alert_body_ratio(candle)
            ... )
            >>> ratio
            0.6666666666666666

        Note:
            Returns None if high <= low (invalid range). Ratio is
            between 0 and 1.

        Guidelines:
            Higher ratio means more of range is body (strong candle).
            Used to validate alert candle strength.
        """
        body = abs(alert_candle[CandleColumn.CLOSE] - alert_candle[CandleColumn.OPEN])
        candle_range = alert_candle[CandleColumn.HIGH] - alert_candle[CandleColumn.LOW]

        if candle_range <= 0:
            return None

        return body / candle_range

    @staticmethod
    def get_max_and_min_volumes(
        window_df: pd.DataFrame
    ) -> Optional[Tuple[float, float]]:
        """
        Get max and min volumes from window.

        Extracts the maximum and minimum volume values from the given
        window.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[Tuple[float, float]]: (max_volume, min_volume),
                or None if window empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 200, 150]})
            >>> max_vol, min_vol = (
            ...     ConsistentVolumeAnchorAnalyzer.get_max_and_min_volumes(
            ...     df
            ... )
            >>> max_vol, min_vol
            (200, 100)

        Note:
            Simple extremes query. Returns None if window empty.

        Guidelines:
            Used to compare alert candle volume against window ranges.
        """
        if window_df.empty:
            return None

        max_vol = window_df[CandleColumn.VOLUME].max()
        min_vol = window_df[CandleColumn.VOLUME].min()

        return (max_vol, min_vol)

    @staticmethod
    def get_max_body_in_window(
        window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Get maximum body size in window.

        Calculates |close - open| for each candle and returns the
        maximum.

        Args:
            window_df (pd.DataFrame): Window with open and close
                columns.

        Returns:
            Optional[float]: Maximum body size, or None if window
                empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [102, 105, 103]
            ... })
            >>> max_body = (
            ...     ConsistentVolumeAnchorAnalyzer.get_max_body_in_window(
            ...     df
            ... )
            >>> max_body
            4.0

        Note:
            Returns None if window empty. Computes absolute difference.

        Guidelines:
            Used to verify alert candle has largest body in full
            lookback window.
        """
        if window_df.empty:
            return None

        bodies = (
            window_df[CandleColumn.CLOSE] - window_df[CandleColumn.OPEN]
        ).abs()
        return bodies.max()
