# src/stockreports/alert/approach/CONSISTENT_MOMENTUM/validator.py
"""
CONSISTENT_MOMENTUM Validator - Pure validation functions.

This module contains all pure validation functions for the
CONSISTENT_MOMENTUM approach. These functions return validation results
without side effects and can be tested independently.

Inherits common validation methods from the base Validator class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.validator import Validator
from src.stockreports.alert.common.constants import Signal
from src.stockreports.utils import candle_utils
from .analyzer import ConsistentMomentumAnalyzer


class ConsistentMomentumValidator(Validator):
    """
    Validator for CONSISTENT_MOMENTUM approach.

    Inherits common validation functions from base Validator:
    - Candle color consistency validation
    - Opposite color candle existence checks
    - Price and ratio threshold validation
    - Volume threshold and multiplier validation
    - DataFrame validation utilities

    Contains CONSISTENT_MOMENTUM specific validations:
    - Maximum body momentum at boundaries
    - Volume consistency across window
    - Price range within thresholds
    - Gaps between consecutive candles
    - Color consistency
    - Price direction (open and close)
    - Minimum candle count
    """

    @staticmethod
    def validate_max_body_at_boundaries(
        confirmation_window_df: pd.DataFrame,
        signal: Signal
    ) -> bool:
        """
        Validate momentum strength at window boundaries.

        Checks two conditions (OR logic):
        1. First and last candles are among the top 2 max body candles
        2. Last candle is the maximum body candle

        This ensures momentum is strongest at the end (ideally also at
        the beginning) of the confirmation window, indicating sustained
        and powerful price movement.

        Args:
            confirmation_window_df (pd.DataFrame): Confirmation window
                with open and close prices.
            signal (Signal): BUY or SELL signal (currently unused but
                kept for consistency with step pattern).

        Returns:
            bool: True if either condition is satisfied, False
                otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [102, 105, 103]
            ... })
            >>> result = (
            ...     ConsistentMomentumValidator.validate_max_body_at_boundaries(
            ...     df, Signal.BUY
            ... )
            >>> result
            True

        Note:
            Signal parameter is included for API consistency but not
            used in validation. Requires at least 2 candles.

        Guidelines:
            Returns False if window has fewer than 2 candles. OR logic
            means either condition satisfies validation.
        """
        if len(confirmation_window_df) < 2:
            return False

        first_pos = 0
        last_pos = len(confirmation_window_df) - 1

        # Calculate max body positions
        max_pos1, max_pos2, _ = (
            ConsistentMomentumAnalyzer.calculate_max_body_positions(
                confirmation_window_df
            )
        )

        if max_pos1 is None or max_pos2 is None:
            return False

        # Condition 1: First and last are among top 2 max bodies
        condition1 = (
            (first_pos in [max_pos1, max_pos2]) and
            (last_pos in [max_pos1, max_pos2])
        )

        # Condition 2: Last candle is max body
        condition2 = (last_pos == max_pos1)

        # Return OR result
        return condition1 or condition2

    @staticmethod
    def validate_volume_consistency(
        window_df: pd.DataFrame,
        max_multiplier: float
    ) -> bool:
        """
        Validate that volume is consistent within threshold.

        Checks that the volume ratio between max and min does not
        exceed the specified multiplier. Formula:
        max_volume <= min_volume * max_multiplier

        Args:
            window_df (pd.DataFrame): Window with volume column.
            max_multiplier (float): Maximum allowed volume multiplier.

        Returns:
            bool: True if max_volume <= min_volume * max_multiplier,
                False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'volume': [100, 150, 200]})
            >>> result = (
            ...     ConsistentMomentumValidator.validate_volume_consistency(
            ...     df, 2.5
            ... )
            >>> result
            True

        Note:
            Requires window with at least 1 candle. If min_volume <= 0,
            returns False (invalid state).

        Guidelines:
            Used to ensure volume doesn't spike excessively, indicating
            sustained momentum rather than brief spikes.
        """
        if window_df.empty or 'volume' not in window_df.columns:
            return False

        min_vol = window_df['volume'].min()
        max_vol = window_df['volume'].max()

        if min_vol <= 0:
            return False

        return max_vol <= min_vol * max_multiplier

    @staticmethod
    def validate_price_range(
        window_df: pd.DataFrame,
        min_threshold: float,
        max_threshold: float
    ) -> bool:
        """
        Validate that window price range is within min/max bounds.

        Checks that the price range (difference between highest and
        lowest close prices) is:
        - >= min_threshold (sufficient price movement)
        - <= max_threshold (not excessive volatility)

        Args:
            window_df (pd.DataFrame): Window with close prices.
            min_threshold (float): Minimum required price range.
            max_threshold (float): Maximum allowed price range.

        Returns:
            bool: True if min_threshold <= range <= max_threshold,
                False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({'close': [100, 102, 101, 103]})
            >>> result = (
            ...     ConsistentMomentumValidator.validate_price_range(
            ...     df, 2.0, 5.0
            ... )
            >>> result
            True

        Note:
            Returns False if window is empty or price range cannot be
            calculated.

        Guidelines:
            Ensures window has both meaningful and bounded price
            movement. Used for confirmation window validation.
        """
        window_size = (
            ConsistentMomentumAnalyzer.calculate_window_price_range(
                window_df
            )
        )

        if window_size is None:
            return False

        return min_threshold <= window_size <= max_threshold

    @staticmethod
    def validate_gaps_between_candles(
        window_df: pd.DataFrame,
        max_gap_threshold: float
    ) -> bool:
        """
        Validate that gaps between consecutive candles are acceptable.

        Checks that no gap (|close[i] - open[i+1]|) exceeds the
        specified threshold. This prevents gaps indicating no volume
        continuity between candles.

        Args:
            window_df (pd.DataFrame): Window with open and close
                prices, ordered chronologically.
            max_gap_threshold (float): Maximum allowed gap size.

        Returns:
            bool: True if all gaps <= max_gap_threshold, False if any
                gap exceeds threshold.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'close': [100, 101, 102],
            ...     'open': [100.5, 101.5, 102.5]
            ... })
            >>> result = (
            ...     ConsistentMomentumValidator.validate_gaps_between_candles(
            ...     df, 1.0
            ... )
            >>> result
            True

        Note:
            Returns True for windows with fewer than 2 candles (no gaps
            to validate). Requires window ordered chronologically.

        Guidelines:
            A gap of 0 means no gap. Large gaps indicate potential
            slippage or gaps in market data.
        """
        if len(window_df) < 2:
            # Single candle, no gap to validate
            return True

        gaps = (
            ConsistentMomentumAnalyzer.calculate_gaps_between_candles(
                window_df
            )
        )

        for gap in gaps:
            if gap > max_gap_threshold:
                return False

        return True

    @staticmethod
    def validate_color_consistency(
        window_df: pd.DataFrame,
        signal: Signal
    ) -> bool:
        """
        Validate that all candles have consistent color with signal.

        Checks that every candle in the window matches the expected
        color: green for BUY, red for SELL.

        Args:
            window_df (pd.DataFrame): Window with open and close
                prices.
            signal (Signal): Expected signal (BUY or SELL).

        Returns:
            bool: True if all candles match signal color, False if any
                candle doesn't match.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101],
            ...     'close': [102, 103]
            ... })
            >>> result = (
            ...     ConsistentMomentumValidator.validate_color_consistency(
            ...     df, Signal.BUY
            ... )
            >>> result
            True

        Note:
            Requires window with at least 1 candle. Uses candle_utils
            is_green_candle/is_red_candle for color detection.

        Guidelines:
            Green = close > open, Red = close < open. Doji candles
            (close == open) don't match either color.
        """
        if window_df.empty:
            return False

        for _, candle in window_df.iterrows():
            if signal == Signal.BUY:
                if not candle_utils.is_green_candle(candle):
                    return False
            else:  # SELL
                if not candle_utils.is_red_candle(candle):
                    return False

        return True

    @staticmethod
    def validate_open_close_price_direction(
        window_df: pd.DataFrame,
        signal: Signal
    ) -> bool:
        """
        Validate that open and close prices follow signal direction.

        For BUY: Both open and close must strictly increase
        (each > previous). For SELL: Both must strictly decrease
        (each < previous).

        Args:
            window_df (pd.DataFrame): Window with open and close
                prices, ordered chronologically.
            signal (Signal): BUY or SELL signal.

        Returns:
            bool: True if all open and close prices follow direction,
                False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [101, 102, 103]
            ... })
            >>> result = (
            ...     ConsistentMomentumValidator.
            ...     validate_open_close_price_direction(df, Signal.BUY)
            ... )
            >>> result
            True

        Note:
            Returns True for windows with fewer than 2 candles (no
            direction to validate). Requires strict inequality (not
            equal).

        Guidelines:
            BUY: prices increase. SELL: prices decrease. Used to
            confirm sustained directional momentum.
        """
        if len(window_df) < 2:
            return True

        opens = window_df['open'].values
        closes = window_df['close'].values

        if signal == Signal.BUY:
            # Check strictly increasing
            for i in range(1, len(opens)):
                if opens[i] <= opens[i - 1]:
                    return False
            for i in range(1, len(closes)):
                if closes[i] <= closes[i - 1]:
                    return False
        else:  # SELL
            # Check strictly decreasing
            for i in range(1, len(opens)):
                if opens[i] >= opens[i - 1]:
                    return False
            for i in range(1, len(closes)):
                if closes[i] >= closes[i - 1]:
                    return False

        return True

    @staticmethod
    def validate_min_consistent_candles(
        window_df: pd.DataFrame,
        min_count: int
    ) -> bool:
        """
        Validate that window has minimum number of consistent candles.

        Checks that the window contains at least the specified minimum
        number of candles.

        Args:
            window_df (pd.DataFrame): Window to validate.
            min_count (int): Minimum required candle count.

        Returns:
            bool: True if len(window) >= min_count, False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'open': [100, 101, 102],
            ...     'close': [101, 102, 103]
            ... })
            >>> result = (
            ...     ConsistentMomentumValidator.validate_min_consistent_candles(
            ...     df, 2
            ... )
            >>> result
            True

        Note:
            Simple count check. Returns True for empty window if
            min_count is 0 or less.

        Guidelines:
            Used to ensure sufficient data for confirming momentum.
            Should typically be >= 2.
        """
        return len(window_df) >= min_count
