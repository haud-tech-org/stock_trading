# src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/validator.py
"""
VOLUME_SPIKE_CONFIRMATION (VSC) Validator - Pure validation functions.

This module contains all pure validation functions for the
VOLUME_SPIKE_CONFIRMATION approach. These functions return validation
results without side effects and can be tested independently.

Inherits common validation methods from the base Validator class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.validator import Validator
from src.stockreports.alert.common.constants import Trend, CandleColumn
from .analyzer import VolumeSpikeConfirmationAnalyzer


class VolumeSpikeConfirmationValidator(Validator):
    """
    Validator for VOLUME_SPIKE_CONFIRMATION approach.

    Inherits common validation functions from base Validator:
    - Candle color consistency validation
    - Opposite color candle existence checks
    - Price and ratio threshold validation
    - Volume threshold and multiplier validation
    - DataFrame validation utilities

    Contains VSC-specific validations:
    - Trend window size and candle count
    - Price range validation
    - Volume spike ratio validation
    - Min/max volume candle ordering
    """

    @staticmethod
    def validate_trend_window(
        trend_window_df: pd.DataFrame,
        min_candle_count: int,
        min_price_range: float
    ) -> bool:
        """
        Validate trend window has minimum candles and price range.

        Checks two conditions:
        1. Candle count >= min_candle_count
        2. Price range >= min_price_range

        Args:
            trend_window_df (pd.DataFrame): Trend window.
            min_candle_count (int): Minimum required candles.
            min_price_range (float): Minimum required price range.

        Returns:
            bool: True if both conditions met, False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100],
            ...     'open': [100, 101, 102],
            ...     'close': [103, 102, 104]
            ... })
            >>> result = (
            ...     VolumeSpikeConfirmationValidator.validate_trend_window(
            ...     df, 2, 4.0
            ... )
            >>> result
            True

        Note:
            Returns False if window empty. Both conditions must be
            true.

        Guidelines:
            Ensures sufficient data for trend confirmation. Validates
            both size and movement.
        """
        if trend_window_df.empty:
            return False

        # Check candle count
        candle_count = (
            VolumeSpikeConfirmationAnalyzer.get_trend_candle_count(
                trend_window_df
            )
        )
        if candle_count < min_candle_count:
            return False

        # Check price range
        price_range = (
            VolumeSpikeConfirmationAnalyzer.calculate_window_price_range(
                trend_window_df
            )
        )
        if price_range is None or price_range < min_price_range:
            return False

        return True

    @staticmethod
    def validate_volume_spike(
        max_vol_candle: pd.Series,
        min_vol_candle: pd.Series,
        volume_multiplier: float
    ) -> bool:
        """
        Validate volume spike ratio meets threshold.

        Checks that max_volume / min_volume >= multiplier threshold.

        Args:
            max_vol_candle (pd.Series): Candle with max volume.
            min_vol_candle (pd.Series): Candle with min volume.
            volume_multiplier (float): Required multiplier threshold.

        Returns:
            bool: True if ratio >= multiplier, False otherwise.

        Example:
            >>> import pandas as pd
            >>> max_c = pd.Series({'volume': 200})
            >>> min_c = pd.Series({'volume': 100})
            >>> result = (
            ...     VolumeSpikeConfirmationValidator.validate_volume_spike(
            ...     max_c, min_c, 1.5
            ... )
            >>> result
            True

        Note:
            Returns False if ratio cannot be calculated (min <= 0).

        Guidelines:
            Ensures significant volume spike before max candle. Used
            to filter for meaningful volume confirmation.
        """
        max_vol = max_vol_candle[CandleColumn.VOLUME]
        min_vol = min_vol_candle[CandleColumn.VOLUME]

        ratio = (
            VolumeSpikeConfirmationAnalyzer.calculate_volume_spike_ratio(
                max_vol,
                min_vol
            )
        )

        if ratio is None:
            return False

        return ratio >= volume_multiplier

    @staticmethod
    def validate_volume_candle_order(
        min_vol_candle: pd.Series,
        max_vol_candle: pd.Series,
        trend_window_df: pd.DataFrame
    ) -> bool:
        """
        Validate that min volume candle occurs before max volume.

        Checks temporal ordering: min volume candle must come before
        max volume candle in the trend window.

        Args:
            min_vol_candle (pd.Series): Candle with min volume.
            max_vol_candle (pd.Series): Candle with max volume.
            trend_window_df (pd.DataFrame): Trend window for index
                lookup.

        Returns:
            bool: True if min occurs before max, False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 200, 150]
            ... }, index=['a', 'b', 'c'])
            >>> min_c = df.loc['a']
            >>> max_c = df.loc['b']
            >>> result = (
            ...     VolumeSpikeConfirmationValidator.
            ...     validate_volume_candle_order(
            ...     min_c, max_c, df
            ... )
            >>> result
            True

        Note:
            Returns False if candles are in wrong order or not in
            window.

        Guidelines:
            Ensures volume trend: low → high → trend end. Prevents
            false spikes where max comes before min.
        """
        try:
            min_idx = trend_window_df.index.get_loc(min_vol_candle.name)
            max_idx = trend_window_df.index.get_loc(max_vol_candle.name)
            return min_idx < max_idx
        except (KeyError, AttributeError):
            return False

    @staticmethod
    def validate_trend_window_size(
        window_df: pd.DataFrame,
        min_size: float
    ) -> bool:
        """
        Validate that trend window price range meets minimum.

        Checks that price range (highest - lowest) >= min_size.

        Args:
            window_df (pd.DataFrame): Window with high/low prices.
            min_size (float): Minimum required price range.

        Returns:
            bool: True if range >= min_size, False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100]
            ... })
            >>> result = (
            ...     VolumeSpikeConfirmationValidator.validate_trend_window_size(
            ...     df, 4.0
            ... )
            >>> result
            True

        Note:
            Returns False if window empty or price range cannot be
            calculated.

        Guidelines:
            Ensures sufficient price movement in trend window. Filters
            out small, insignificant moves.
        """
        if window_df.empty:
            return False

        price_range = (
            VolumeSpikeConfirmationAnalyzer.calculate_window_price_range(
                window_df
            )
        )

        if price_range is None:
            return False

        return price_range >= min_size
