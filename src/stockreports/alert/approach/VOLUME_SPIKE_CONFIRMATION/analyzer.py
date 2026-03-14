# src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/analyzer.py
"""
VOLUME_SPIKE_CONFIRMATION (VSC) Analyzer - Pure calculation functions.

This module contains all pure calculation and analysis functions for the
VOLUME_SPIKE_CONFIRMATION approach. These functions have no side effects
and can be tested independently.

Inherits common calculation methods from the base Analyzer class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.utils import candle_utils, window_utils


class VolumeSpikeConfirmationAnalyzer(Analyzer):
    """
    Analyzer for VOLUME_SPIKE_CONFIRMATION approach.

    Inherits common calculation functions from base Analyzer:
    - Body ratio and size calculations
    - Window size and trend determination
    - Candle color classification
    - Candle filtering operations
    - Window and volume calculations

    This class extends the base Analyzer with VSC-specific calculation
    methods.
    """

    @staticmethod
    def extract_trend_window(
        window_df: pd.DataFrame
    ) -> Optional[pd.DataFrame]:
        """
        Extract consecutive same-color candles from end of window.

        Identifies the trend window by starting from the last candle
        and working backwards, including all consecutive candles with
        the same color as the last candle.

        Args:
            window_df (pd.DataFrame): Full window with OHLC data.

        Returns:
            Optional[pd.DataFrame]: DataFrame containing consecutive
                same-color candles from end, or None if last candle is
                neutral (doji).

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102, 103, 104],
            ...     'close': [102, 103, 104, 105, 106]
            ... })
            >>> trend_win = (
            ...     VolumeSpikeConfirmationAnalyzer.extract_trend_window(
            ...     df
            ... )
            >>> len(trend_win)
            5

        Note:
            Returns None if last candle is doji (close == open).
            Works backwards from end, stops at first color change.

        Guidelines:
            Used to identify consecutive bullish or bearish candles.
            Requires at least 1 candle to form trend window.
        """
        if window_df.empty:
            return None

        last_candle = window_df.iloc[-1]

        # Determine trend color from last candle
        if candle_utils.is_green_candle(last_candle):
            is_trend_candle = candle_utils.is_green_candle
        elif candle_utils.is_red_candle(last_candle):
            is_trend_candle = candle_utils.is_red_candle
        else:
            # Last candle is neutral (doji), no trend window
            return None

        # Collect indices of consecutive candles matching trend color
        # Starting from the end
        trend_indices = [window_df.index[-1]]
        for idx in range(len(window_df) - 2, -1, -1):
            candle = window_df.iloc[idx]
            if is_trend_candle(candle):
                trend_indices.append(window_df.index[idx])
            else:
                break

        # Return sorted in ascending order
        trend_indices = sorted(trend_indices)
        return window_df.loc[trend_indices]

    @staticmethod
    def find_max_volume_candle(
        window_df: pd.DataFrame
    ) -> Optional[pd.Series]:
        """
        Find candle with maximum volume in window.

        Returns the Series representing the candle with the highest
        volume in the given window.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[pd.Series]: Candle with max volume, or None if
                window empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 200, 150]
            ... })
            >>> max_candle = (
            ...     VolumeSpikeConfirmationAnalyzer.find_max_volume_candle(
            ...     df
            ... )
            >>> max_candle['volume']
            200

        Note:
            Returns None if window empty. Returns first occurrence if
            multiple candles have same max volume.

        Guidelines:
            Used to find the candle with volume spike. Paired with
            min_volume_candle for ratio validation.
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
        volume in the given window.

        Args:
            window_df (pd.DataFrame): Window with volume column.

        Returns:
            Optional[pd.Series]: Candle with min volume, or None if
                window empty.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 200, 150]
            ... })
            >>> min_candle = (
            ...     VolumeSpikeConfirmationAnalyzer.find_min_volume_candle(
            ...     df
            ... )
            >>> min_candle['volume']
            100

        Note:
            Returns None if window empty. Returns first occurrence if
            multiple candles have same min volume.

        Guidelines:
            Used as baseline for volume spike calculation. Min must
            occur before max in trend window.
        """
        if window_df.empty:
            return None

        min_idx = window_df['volume'].idxmin()
        return window_df.loc[min_idx]

    @staticmethod
    def calculate_volume_spike_ratio(
        max_volume: float,
        min_volume: float
    ) -> Optional[float]:
        """
        Calculate volume spike ratio between max and min volumes.

        Computes max_volume / min_volume to determine spike magnitude.
        Used to validate that volume spike is significant enough.

        Args:
            max_volume (float): Maximum volume value.
            min_volume (float): Minimum volume value.

        Returns:
            Optional[float]: Volume ratio (max / min), or None if min
                is <= 0.

        Example:
            >>> ratio = (
            ...     VolumeSpikeConfirmationAnalyzer.
            ...     calculate_volume_spike_ratio(200, 100)
            >>> ratio
            2.0

        Note:
            Returns None if min_volume <= 0 (invalid state). Ratio
            must be >= multiplier threshold for spike.

        Guidelines:
            Ratio > 1 indicates spike. Higher ratio = stronger spike.
            Used to validate spike magnitude.
        """
        if min_volume <= 0:
            return None

        return max_volume / min_volume

    @staticmethod
    def calculate_window_price_range(
        window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate price range of trend window.

        Computes the difference between highest and lowest prices in
        the window using standard high-low methodology.

        Args:
            window_df (pd.DataFrame): Window with high and low
                columns.

        Returns:
            Optional[float]: Absolute price range, or None if empty or
                invalid.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100]
            ... })
            >>> price_range = (
            ...     VolumeSpikeConfirmationAnalyzer.
            ...     calculate_window_price_range(df)
            >>> price_range
            5.0

        Note:
            Uses get_window_size_and_trend utility. Returns None if
            window empty.

        Guidelines:
            Represents total volatility in trend window. Used to
            validate window size threshold.
        """
        if window_df.empty:
            return None

        window_size, _ = window_utils.get_window_size_and_trend(
            window_df
        )
        return abs(window_size) if window_size is not None else None

    @staticmethod
    def get_trend_candle_count(
        window_df: pd.DataFrame
    ) -> int:
        """
        Get count of candles in trend window.

        Simply returns the number of rows in the window DataFrame.

        Args:
            window_df (pd.DataFrame): Trend window.

        Returns:
            int: Number of candles in window.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [101, 102, 103]
            ... })
            >>> count = (
            ...     VolumeSpikeConfirmationAnalyzer.get_trend_candle_count(
            ...     df
            ... )
            >>> count
            3

        Note:
            Empty window returns 0.

        Guidelines:
            Used to validate minimum candle requirements for trend.
        """
        return len(window_df)
