"""Validation methods for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.

Pure validation methods with no state. All validations return boolean results.
"""

from typing import Optional
import pandas as pd
from src.stockreports.alert.common.constants import CandleColumn, Trend


class ReversalAnchorSignalCandleValidator:
    """Validator for REVERSAL_ANCHOR_SIGNAL_CANDLE approach.
    
    Provides static methods for validating each stage of the approach:
    - Window size and trend analysis
    - Anchor candle identification
    - Signal candle confirmation
    - Alert candle extremes and wick characteristics
    """

    @staticmethod
    def validate_window_size(
        window_size: float,
        min_size: float,
    ) -> bool:
        """Validate window has sufficient price range.
        
        Validation 1: Window price range must meet minimum threshold.
        
        Args:
            window_size: HIGH - LOW for entire window
            min_size: Minimum required window size
            
        Returns:
            bool: True if window_size >= min_size
            
        Raises:
            ValueError: If inputs are invalid
        """
        if window_size < 0:
            raise ValueError(f"Window size cannot be negative: {window_size}")
        if min_size < 0:
            raise ValueError(f"Min size cannot be negative: {min_size}")

        return window_size >= min_size

    @staticmethod
    def validate_anchor_candle(
        anchor_body: float,
        average_body: float,
        min_body_size: float,
        multiplier: float,
    ) -> bool:
        """Validate anchor candle meets size requirements.
        
        Validation 2: Anchor body must be:
        - At least min_body_size
        - At least multiplier * average body in window
        
        Args:
            anchor_body: Body size of anchor candle (HIGH - LOW)
            average_body: Average body size in window
            min_body_size: Minimum absolute body size
            multiplier: Multiplier for average body comparison
            
        Returns:
            bool: True if anchor meets both size criteria
            
        Raises:
            ValueError: If inputs are invalid
        """
        if anchor_body < 0:
            raise ValueError(f"Anchor body cannot be negative: {anchor_body}")
        if average_body < 0:
            raise ValueError(f"Average body cannot be negative: {average_body}")
        if min_body_size < 0:
            raise ValueError(f"Min body size cannot be negative: {min_body_size}")
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be positive: {multiplier}")

        # Check both criteria
        meets_absolute: bool = anchor_body >= min_body_size
        meets_relative: bool = anchor_body >= multiplier * average_body

        return meets_absolute and meets_relative

    @staticmethod
    def validate_signal_candle(
        signal_volume: float,
        average_volume: float,
        min_volume: float,
        multiplier: float,
    ) -> bool:
        """Validate signal candle meets volume requirements.
        
        Validation 3: Signal volume must be:
        - At least min_volume
        - At least multiplier * average volume in window
        
        Args:
            signal_volume: Volume of signal candle
            average_volume: Average volume in window
            min_volume: Minimum absolute volume
            multiplier: Multiplier for average volume comparison
            
        Returns:
            bool: True if signal meets both volume criteria
            
        Raises:
            ValueError: If inputs are invalid
        """
        if signal_volume < 0:
            raise ValueError(f"Signal volume cannot be negative: {signal_volume}")
        if average_volume < 0:
            raise ValueError(f"Average volume cannot be negative: {average_volume}")
        if min_volume < 0:
            raise ValueError(f"Min volume cannot be negative: {min_volume}")
        if multiplier <= 0:
            raise ValueError(f"Multiplier must be positive: {multiplier}")

        # Check both criteria
        meets_absolute: bool = signal_volume >= min_volume
        meets_relative: bool = signal_volume >= multiplier * average_volume

        return meets_absolute and meets_relative

    @staticmethod
    def validate_alert_candle_is_doji(
        alert_candle: pd.Series,
    ) -> bool:
        """Check if alert candle is a Doji (negligible body).
        
        Doji: |CLOSE - OPEN| / (HIGH - LOW) < 0.05 (5% threshold)
        
        Args:
            alert_candle: The final candle in window
            
        Returns:
            bool: True if alert candle IS a Doji (FAIL condition)
            
        Raises:
            ValueError: If candle missing required columns
        """
        if CandleColumn.CLOSE not in alert_candle.index:
            raise ValueError("Alert candle missing CLOSE column")

        high: float = alert_candle[CandleColumn.HIGH]
        low: float = alert_candle[CandleColumn.LOW]
        close: float = alert_candle[CandleColumn.CLOSE]
        open_price: float = alert_candle[CandleColumn.OPEN]

        candle_range: float = high - low
        
        if candle_range == 0:
            # Zero range = Doji
            return True

        body_ratio: float = abs(close - open_price) / candle_range
        is_doji: bool = body_ratio < 0.05

        return is_doji


    @staticmethod
    def validate_alert_candle_wick(
        wick_percentage: float,
        min_percentage: float,
        max_percentage: float,
    ) -> bool:
        """Validate alert candle wick is within acceptable range.
        
        Validation 4b: Wick percentage must be:
        - At least min_percentage (has meaningful wick)
        - At most max_percentage (not excessive wick)
        
        Args:
            wick_percentage: Calculated wick percentage (0.0 to 1.0)
            min_percentage: Minimum wick percentage
            max_percentage: Maximum wick percentage
            
        Returns:
            bool: True if wick is within acceptable range
            
        Raises:
            ValueError: If inputs are invalid
        """
        if wick_percentage < 0 or wick_percentage > 1:
            raise ValueError(
                f"Wick percentage must be 0-1, got {wick_percentage}"
            )
        if min_percentage < 0 or min_percentage > 1:
            raise ValueError(
                f"Min percentage must be 0-1, got {min_percentage}"
            )
        if max_percentage < 0 or max_percentage > 1:
            raise ValueError(
                f"Max percentage must be 0-1, got {max_percentage}"
            )
        if min_percentage > max_percentage:
            raise ValueError(
                f"Min ({min_percentage}) cannot exceed max ({max_percentage})"
            )

        is_valid: bool = (
            wick_percentage >= min_percentage
            and wick_percentage <= max_percentage
        )
        return is_valid
    
    @staticmethod
    def validate_alert_candle_close_to_extreme(
        alert_candle: pd.Series,
        trend: Trend,
        window_df: pd.DataFrame,
        threshold: float,
    ) -> bool:
        """Validate alert candle's close is within a fixed price threshold of the window extreme.

        Validation: Close-to-extreme threshold (configurable, absolute price)
        - For uptrend: close must be within `threshold` price units of window high
        - For downtrend: close must be within `threshold` price units of window low

        Args:
            alert_candle: The final candle in window
            trend: Trend instance (UPTREND or DOWNTREND)
            window_df: Full window DataFrame
            threshold: Absolute price threshold (e.g., 10.0 means within $10)
        Returns:
            bool: True if close is within threshold of extreme
        Raises:
            ValueError: If invalid trend or data
        """
        if trend not in (Trend.UPTREND, Trend.DOWNTREND):
            raise ValueError(f"Invalid trend: {trend}")
        if window_df.empty:
            raise ValueError("Window cannot be empty")
        close = alert_candle[CandleColumn.CLOSE]
        if trend == Trend.UPTREND:
            window_max_high = window_df[CandleColumn.HIGH].max()
            distance = window_max_high - close
        else:
            window_min_low = window_df[CandleColumn.LOW].min()
            distance = close - window_min_low
        return distance <= threshold

    @staticmethod
    def validate_not_in_cooldown(
        last_alert_time: Optional[pd.Timestamp],
        current_time: pd.Timestamp,
        cooldown_minutes: int,
    ) -> bool:
        """Validate current time is outside cooldown window.
        
        Prevents duplicate alerts within cooldown period.
        
        Args:
            last_alert_time: Timestamp of last alert (None if first alert)
            current_time: Current candle timestamp
            cooldown_minutes: Cooldown period in minutes
            
        Returns:
            bool: True if not in cooldown (can send alert)
            
        Raises:
            ValueError: If cooldown_minutes is invalid
        """
        if cooldown_minutes <= 0:
            raise ValueError(f"Cooldown must be positive: {cooldown_minutes}")

        if last_alert_time is None:
            # No previous alert, not in cooldown
            return True

        time_diff: pd.Timedelta = current_time - last_alert_time
        minutes_elapsed: float = time_diff.total_seconds() / 60

        return minutes_elapsed >= cooldown_minutes

