# src/stockreports/alert/approach/CONSISTENT_VOLUME_ANCHOR/validator.py
"""
CONSISTENT_VOLUME_ANCHOR (CVA) Validator - Pure validation functions.

This module contains all pure validation functions for the
CONSISTENT_VOLUME_ANCHOR approach. These functions return validation
results without side effects and can be tested independently.

Inherits common validation methods from the base Validator class.
"""

from typing import Optional, Tuple
import pandas as pd
from src.stockreports.alert.validator import Validator
from src.stockreports.alert.common.constants import Signal
from src.stockreports.utils import candle_utils
from .analyzer import ConsistentVolumeAnchorAnalyzer


class ConsistentVolumeAnchorValidator(Validator):
    """
    Validator for CONSISTENT_VOLUME_ANCHOR approach.

    Inherits common validation functions from base Validator:
    - Candle color consistency validation
    - Opposite color candle existence checks
    - Price and ratio threshold validation
    - Volume threshold and multiplier validation
    - DataFrame validation utilities

    Contains CVA-specific validations:
    - Window filtering by volume and body size
    - Consistent candle percentage
    - Window price range
    - Alert volume against window volumes
    - Alert body size and ratio
    - Alert body as largest in window
    - Alert price direction relative to window
    """

    @staticmethod
    def validate_volume_and_body_consistency(
        window_df: pd.DataFrame,
        median_volume: float,
        max_volume_multiplier: float,
        max_body_size: float,
        min_percentage: float
    ) -> Optional[Tuple[pd.DataFrame, float, float]]:
        """
        Validate and filter window by volume/body, return filtered data.

        Filters the window by:
        1. Volume: volume * multiplier <= median_volume
        2. Body size: |close - open| <= max_body_size

        Then checks that filtered candles meet minimum percentage of
        original window size.

        Args:
            window_df (pd.DataFrame): Window to filter and validate.
            median_volume (float): Median volume threshold.
            max_volume_multiplier (float): Volume multiplier factor.
            max_body_size (float): Maximum body size threshold.
            min_percentage (float): Minimum percentage of original
                window (0.0-1.0) that must pass filters.

        Returns:
            Optional[Tuple[pd.DataFrame, float, float]]: (filtered_df,
                min_volume, max_volume) if valid, None otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'volume': [80, 100, 90],
            ...     'open': [100, 101, 102],
            ...     'close': [101, 102, 103]
            ... })
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.
            ...     validate_volume_and_body_consistency(
            ...     df, 100, 1.1, 1.5, 0.5
            ... )
            >>> result is not None
            True

        Note:
            Returns None if percentage doesn't meet minimum. Includes
            min/max volumes from filtered data.

        Guidelines:
            Used to identify stable "consistent" candles before alert.
            Percentage ensures sufficient consistency signal.
        """
        filtered = (
            ConsistentVolumeAnchorAnalyzer.filter_window_by_volume_and_body(
                window_df,
                median_volume,
                max_volume_multiplier,
                max_body_size
            )
        )

        filtered_count = len(filtered)
        original_count = len(window_df)
        percentage = filtered_count / original_count if original_count > 0 else 0

        if percentage < min_percentage:
            return None

        max_vol, min_vol = (
            ConsistentVolumeAnchorAnalyzer.get_max_and_min_volumes(
                filtered
            ) or (None, None)
        )

        if max_vol is None or min_vol is None:
            return None

        return (filtered, min_vol, max_vol)

    @staticmethod
    def validate_window_price_range(
        window_df: pd.DataFrame,
        max_threshold: float
    ) -> bool:
        """
        Validate that window price range is within maximum threshold.

        Checks that the price range (high - low spread) does not
        exceed the specified maximum, ensuring volatility is bounded.

        Args:
            window_df (pd.DataFrame): Window with high/low columns.
            max_threshold (float): Maximum allowed price range.

        Returns:
            bool: True if range <= max_threshold, False otherwise.

        Example:
            >>> import pandas as pd
            >>> df = pd.DataFrame({
            ...     'high': [105, 103, 104],
            ...     'low': [100, 101, 100]
            ... })
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.validate_window_price_range(
            ...     df, 6.0
            ... )
            >>> result
            True

        Note:
            Returns False if window empty or range cannot be
            calculated.

        Guidelines:
            Ensures window doesn't have excessive volatility. Bounds
            the price movement span.
        """
        price_range = (
            ConsistentVolumeAnchorAnalyzer.calculate_window_price_range(
                window_df
            )
        )

        if price_range is None:
            return False

        return price_range <= max_threshold

    @staticmethod
    def validate_alert_volume(
        alert_candle: pd.Series,
        max_window_volume: float,
        min_window_volume: float,
        volume_multiplier: float
    ) -> bool:
        """
        Validate alert candle volume against window volumes.

        Checks two conditions:
        1. alert_volume >= max_window_volume
        2. alert_volume >= min_window_volume * multiplier

        Both must be true.

        Args:
            alert_candle (pd.Series): Alert candle with volume.
            max_window_volume (float): Maximum volume in window.
            min_window_volume (float): Minimum volume in window.
            volume_multiplier (float): Multiplier for min volume
                threshold.

        Returns:
            bool: True if both conditions met, False otherwise.

        Example:
            >>> import pandas as pd
            >>> candle = pd.Series({'volume': 150})
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.validate_alert_volume(
            ...     candle, 120, 100, 1.2
            ... )
            >>> result
            True

        Note:
            Alert must "spike" above both absolute max and relative
            minimum thresholds.

        Guidelines:
            Ensures alert candle shows significant volume spike
            compared to consistent window. Both conditions required.
        """
        alert_vol = alert_candle['volume']

        # Check against max volume
        if alert_vol < max_window_volume:
            return False

        # Check against multiplier threshold
        threshold = min_window_volume * volume_multiplier
        if alert_vol < threshold:
            return False

        return True

    @staticmethod
    def validate_alert_body_size(
        alert_candle: pd.Series,
        min_body_size: float
    ) -> bool:
        """
        Validate that alert candle body meets minimum size.

        Checks that |close - open| >= min_body_size.

        Args:
            alert_candle (pd.Series): Alert candle with open/close.
            min_body_size (float): Minimum required body size.

        Returns:
            bool: True if body >= min_body_size, False otherwise.

        Example:
            >>> import pandas as pd
            >>> candle = pd.Series({'open': 100, 'close': 104})
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.validate_alert_body_size(
            ...     candle, 3.0
            ... )
            >>> result
            True

        Note:
            Simple body size check. Returns False if body too small.

        Guidelines:
            Ensures alert candle has sufficient strength/size to
            confirm signal.
        """
        body = abs(alert_candle['close'] - alert_candle['open'])
        return body >= min_body_size

    @staticmethod
    def validate_alert_largest_body_with_ratio(
        alert_candle: pd.Series,
        lookback_window_df: pd.DataFrame,
        min_body_ratio: float
    ) -> bool:
        """
        Validate alert has largest body in window and meets ratio.

        Checks two conditions:
        1. Alert body size is maximum in lookback window
        2. Alert body ratio (body / range) >= min_ratio

        Args:
            alert_candle (pd.Series): Alert candle with OHLC.
            lookback_window_df (pd.DataFrame): Full lookback window.
            min_body_ratio (float): Minimum body ratio threshold
                (0.0-1.0).

        Returns:
            bool: True if both conditions met, False otherwise.

        Example:
            >>> import pandas as pd
            >>> alert = pd.Series({
            ...     'open': 100,
            ...     'close': 104,
            ...     'high': 105,
            ...     'low': 99
            ... })
            >>> window = pd.DataFrame({
            ...     'open': [100, 101, 102, 100],
            ...     'close': [101, 102, 103, 104],
            ...     'high': [105, 103, 104, 105],
            ...     'low': [100, 101, 100, 99]
            ... })
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.
            ...     validate_alert_largest_body_with_ratio(
            ...     alert, window, 0.6
            ... )
            >>> result
            True

        Note:
            Alert must have both largest body AND sufficient ratio.
            Range must be positive.

        Guidelines:
            Ensures alert candle stands out as strongest and contains
            sufficient body relative to range.
        """
        # Check if alert has largest body
        alert_body = abs(
            alert_candle['close'] - alert_candle['open']
        )
        max_body = (
            ConsistentVolumeAnchorAnalyzer.get_max_body_in_window(
                lookback_window_df
            )
        )

        if max_body is None or alert_body < max_body:
            return False

        # Check body ratio
        ratio = (
            ConsistentVolumeAnchorAnalyzer.calculate_alert_body_ratio(
                alert_candle
            )
        )

        if ratio is None or ratio < min_body_ratio:
            return False

        return True

    @staticmethod
    def validate_alert_price_direction(
        alert_candle: pd.Series,
        signal: Signal,
        consistent_window_df: pd.DataFrame
    ) -> bool:
        """
        Validate alert price is in correct direction vs window.

        For BUY: alert close > max(window open/close)
        For SELL: alert close < min(window open/close)

        Args:
            alert_candle (pd.Series): Alert candle with close.
            signal (Signal): BUY or SELL signal.
            consistent_window_df (pd.DataFrame): Window with
                open/close.

        Returns:
            bool: True if alert price in correct direction, False
                otherwise.

        Example:
            >>> import pandas as pd
            >>> alert = pd.Series({'close': 110})
            >>> window = pd.DataFrame({
            ...     'open': [100, 101],
            ...     'close': [101, 102]
            ... })
            >>> result = (
            ...     ConsistentVolumeAnchorValidator.
            ...     validate_alert_price_direction(
            ...     alert, Signal.BUY, window
            ... )
            >>> result
            True

        Note:
            For BUY: alert must be above window. For SELL: alert must
            be below window.

        Guidelines:
            Ensures alert confirms directional continuation beyond
            consistent window bounds.
        """
        alert_close = alert_candle['close']
        window_opens = consistent_window_df['open']
        window_closes = consistent_window_df['close']
        prices = pd.concat([window_opens, window_closes])

        if signal == Signal.BUY:
            # Alert must be above window
            return alert_close > prices.max()
        elif signal == Signal.SELL:
            # Alert must be below window
            return alert_close < prices.min()

        return False
