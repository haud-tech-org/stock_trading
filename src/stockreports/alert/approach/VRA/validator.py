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
from src.stockreports.alert.common.constants import Trend, CandleColumn, CandleColor


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

    @staticmethod
    def validate_confirmation_window_size(
        confirmation_window_df: pd.DataFrame,
        min_candle_count: int = 3
    ) -> bool:
        """
        Validate confirmation window has minimum required candle count.

        Checks that the confirmation window (from max volume candle to end)
        has at least min_candle_count candles for meaningful trend analysis.

        Args:
            confirmation_window_df (pd.DataFrame): Confirmation window to validate.
            min_candle_count (int): Minimum candles required (default: 2).

        Returns:
            bool: True if len(confirmation_window_df) >= min_candle_count.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'high': [100, 102, 101]})
            >>> valid = VraValidator.validate_confirmation_window_size(
            ...     df, min_candle_count=2
            ... )
            >>> valid
            True

        Note:
            Returns False if window is None or empty.

        Guidelines:
            Require sufficient candles in confirmation window for reversal consistency.
        """
        if confirmation_window_df is None or confirmation_window_df.empty:
            return False

        return len(confirmation_window_df) >= min_candle_count

    @staticmethod
    def validate_anchor_candle_found(
        anchor_candle: Optional[pd.Series]
    ) -> bool:
        """
        Validate that anchor candle was successfully identified.

        Args:
            anchor_candle (Optional[pd.Series]): The anchor candle to validate.

        Returns:
            bool: True if anchor_candle is not None, False otherwise.

        Example:
            >>> import pandas as pd
            >>> candle = pd.Series({'high': 110, 'low': 100})
            >>> valid = VraValidator.validate_anchor_candle_found(candle)
            >>> valid
            True

        Note:
            Simple validation to check if anchor candle identification succeeded.

        Guidelines:
            Used as a prerequisite check before reversal trend consistency validation.
        """
        return anchor_candle is not None

    @staticmethod
    def validate_max_volume_vs_alert_candle(
        max_volume: float,
        alert_volume: float,
        multiplier_threshold: float
    ) -> bool:
        """
        Validate that max volume candle volume is sufficient relative to alert candle volume.

        Checks that max_volume >= alert_volume * multiplier_threshold to ensure
        the volume spike at max volume candle is proportional to the alert candle volume.

        Args:
            max_volume (float): Volume of the maximum volume candle.
            alert_volume (float): Volume of the alert candle (usually last candle).
            multiplier_threshold (float): Multiplier threshold (e.g., 1.5).

        Returns:
            bool: True if max_volume >= alert_volume * multiplier_threshold.

        Example:
            >>> valid = VraValidator.validate_max_volume_vs_alert_candle(
            ...     max_volume=1000.0,
            ...     alert_volume=500.0,
            ...     multiplier_threshold=1.5
            ... )
            >>> valid
            True

        Note:
            Returns False if either volume is None or negative.

        Guidelines:
            Ensures the peak volume is meaningfully higher than current volume,
            not just a marginal spike.
        """
        if max_volume is None or alert_volume is None:
            return False

        if max_volume < 0 or alert_volume < 0:
            return False

        # Handle zero volume edge case
        if alert_volume == 0:
            return max_volume > 0

        required_volume = alert_volume * multiplier_threshold
        return max_volume >= required_volume

    @staticmethod
    def validate_trend_consistency(
        window_slice: pd.DataFrame,
        window_trend: Trend
    ) -> bool:
        """
        Validate that all candles in window maintain consistent trend color.

        Checks that all candles in the window slice have consistent color
        matching the trend direction:
        - For UPTREND: All candles must be GREEN (close > open)
        - For DOWNTREND: All candles must be RED (close < open)

        Args:
            window_slice (pd.DataFrame): Window slice with OHLC data.
            window_trend (Trend): Expected trend direction (UPTREND or DOWNTREND).

        Returns:
            bool: True if all candles maintain consistent color for the trend.

        Example:
            >>> import pandas as pd
            >>> from src.stockreports.alert.common.constants import Trend, CandleColumn
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [102, 103, 104],
            ... })
            >>> valid = VraValidator.validate_trend_consistency(
            ...     df, Trend.UPTREND
            ... )
            >>> valid
            True

        Note:
            Returns False if window is None, empty, or trend is NEUTRAL.
            Uses base Analyzer.get_candle_color() for color determination.

        Guidelines:
            Ensures reversal momentum is consistent throughout the confirmation phase.
            Filters out weak or mixed-signal candles from the confirmation window.
        """
        if window_slice is None or window_slice.empty:
            return False

        if window_trend is None or window_trend == Trend.NEUTRAL:
            return False

        # Import here to avoid circular imports
        from src.stockreports.alert.analyzer import Analyzer

        try:
            if window_trend == Trend.UPTREND:
                # All candles must be GREEN (close > open)
                for _, candle in window_slice.iterrows():
                    candle_color = Analyzer.get_candle_color(candle)
                    if candle_color != CandleColor.GREEN:
                        return False
            elif window_trend == Trend.DOWNTREND:
                # All candles must be RED (close < open)
                for _, candle in window_slice.iterrows():
                    candle_color = Analyzer.get_candle_color(candle)
                    if candle_color != CandleColor.RED:
                        return False
            else:
                return False

            return True
        except (KeyError, AttributeError):
            return False
