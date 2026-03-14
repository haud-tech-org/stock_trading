# src/stockreports/alert/approach/VRA/validator.py
"""
VRA (Volume Reversal Analysis) Validator - Pure validation functions.

This module contains all pure validation functions for the VRA approach.
These functions evaluate calculated values against thresholds and return
boolean validation results.

Inherits common validation methods from the base Validator class.
"""

from typing import Optional
import pandas as pd
from src.stockreports.alert.validator import Validator


class VraValidator(Validator):
    """
    Validator for VRA (Volume Reversal Analysis) approach.

    Inherits common validation functions from base Validator:
    - Body size and ratio validation
    - Color consistency checks
    - Price range and threshold validation
    - Window size and candle count checks

    This class extends the base Validator with VRA-specific validation
    methods.
    """

    @staticmethod
    def validate_volume_sequence(
        min_vol_candle: pd.Series,
        max_vol_candle: pd.Series,
        alert_candle: pd.Series,
        window_df: pd.DataFrame
    ) -> bool:
        """
        Validate volume progression: min before max before alert.

        Checks that the candles appear in correct order: minimum volume
        before maximum volume before alert candle.

        Args:
            min_vol_candle (pd.Series): Candle with minimum volume.
            max_vol_candle (pd.Series): Candle with maximum volume.
            alert_candle (pd.Series): Alert candle.
            window_df (pd.DataFrame): Full window for index lookup.

        Returns:
            bool: True if min_idx < max_idx < alert_idx.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 200, 150]
            ... }, index=['a', 'b', 'c'])
            >>> min_c = df.loc['a']
            >>> max_c = df.loc['b']
            >>> alert_c = df.loc['c']
            >>> valid = VraValidator.validate_volume_sequence(
            ...     min_c, max_c, alert_c, df
            ... )
            >>> valid
            True

        Note:
            Returns False if candles not in window or order invalid.

        Guidelines:
            Volume reversal must show clear progression from low to
            high to trigger signal.
        """
        try:
            min_idx = window_df.index.get_loc(min_vol_candle.name)
            max_idx = window_df.index.get_loc(max_vol_candle.name)
            alert_idx = window_df.index.get_loc(alert_candle.name)

            # Allow the max volume candle to be the same as the alert candle
            # (original implementation accepted alert == max). Require only
            # that min occurs before max, and max occurs at or before alert.
            return min_idx < max_idx <= alert_idx
        except (KeyError, AttributeError):
            return False

    @staticmethod
    def validate_volume_ratio(
        volume_ratio: float,
        multiplier_threshold: float
    ) -> bool:
        """
        Validate volume spike ratio meets multiplier threshold.

        Checks that volume_ratio >= multiplier_threshold to confirm
        meaningful volume reversal spike.

        Args:
            volume_ratio (float): Alert volume / min volume ratio.
            multiplier_threshold (float): Minimum ratio required.

        Returns:
            bool: True if volume_ratio >= multiplier_threshold.

        Example:
            >>> valid = VraValidator.validate_volume_ratio(
            ...     volume_ratio=2.5,
            ...     multiplier_threshold=2.0
            ... )
            >>> valid
            True

        Note:
            Ratio should be calculated via analyzer method.
            Handles float('inf') and 1.0 for zero-volume edge cases.

        Guidelines:
            Higher multiplier = stronger volume reversal signal.
        """
        if volume_ratio is None:
            return False

        # Handle infinite ratio (when min_volume is 0 but alert_volume > 0)
        if volume_ratio == float('inf'):
            return True

        return volume_ratio >= multiplier_threshold

    @staticmethod
    def validate_trend_window_size(
        window_df: pd.DataFrame,
        min_candle_count: int
    ) -> bool:
        """
        Validate trend window has minimum required candle count.

        Checks that window_df has at least min_candle_count candles
        to establish a valid trend reversal pattern.

        Args:
            window_df (pd.DataFrame): Window to validate.
            min_candle_count (int): Minimum candles required.

        Returns:
            bool: True if len(window_df) >= min_candle_count.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [100, 200, 150]
            ... })
            >>> valid = VraValidator.validate_trend_window_size(
            ...     df, min_candle_count=2
            ... )
            >>> valid
            True

        Note:
            Empty window returns False.

        Guidelines:
            Require sufficient candles to establish reversal pattern.
        """
        if window_df is None or window_df.empty:
            return False

        return len(window_df) >= min_candle_count

    @staticmethod
    def validate_trend_magnitude(
        magnitude: float,
        min_magnitude_threshold: float
    ) -> bool:
        """
        Validate trend window magnitude meets minimum threshold.

        Checks that the absolute price movement in the window is
        meaningful (>= min_magnitude_threshold).

        Args:
            magnitude (float): Window price range magnitude.
            min_magnitude_threshold (float): Minimum magnitude required.

        Returns:
            bool: True if magnitude >= min_magnitude_threshold.

        Example:
            >>> valid = VraValidator.validate_trend_magnitude(
            ...     magnitude=50.0,
            ...     min_magnitude_threshold=25.0
            ... )
            >>> valid
            True

        Note:
            Magnitude should be calculated via analyzer method.

        Guidelines:
            Higher threshold requires stronger price movement signal.
        """
        if magnitude is None or magnitude <= 0:
            return False

        return magnitude >= min_magnitude_threshold
