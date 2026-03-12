# src/stockreports/alert/approach/STRONG_CANDLE/validator.py
"""
STRONG_CANDLE Validator - Pure validation functions.

This module contains all pure validation functions for the STRONG_CANDLE approach.
These functions return validation results without side effects and can be tested
independently.

Inherits common validation methods from the base Validator class.
"""

import pandas as pd
from typing import Optional, Tuple
from src.stockreports.alert.common.constants import Signal, Trend
from src.stockreports.utils import candle_utils
from src.stockreports.alert.validator import Validator
from .analyzer import StrongCandleAnalyzer


class StrongCandleValidator(Validator):
    """
    Validator for STRONG_CANDLE approach.
    
    Inherits common validation functions from base Validator:
    - Candle color consistency validation
    - Opposite color candle existence checks
    - Price and ratio threshold validation
    - Volume threshold and multiplier validation
    - DataFrame validation utilities
    
    Contains STRONG_CANDLE specific validations:
    - Alert candle body validation (ratio and size)
    - Alert candle volume validation
    - Window color consistency validation
    - Window price range validation
    - Opposite color candles body validation
    """
    
    @staticmethod
    def validate_alert_candle_body(
        alert_candle: pd.Series,
        min_body_ratio: float,
        min_body_size: float
    ) -> Optional[float]:
        """
        Validate that alert candle has a strong body (both ratio and size).
        
        Checks two conditions:
        1. Body ratio >= min_body_ratio
        2. Body size >= min_body_size
        
        Args:
            alert_candle (pd.Series): Candle to validate
            min_body_ratio (float): Minimum body ratio threshold
            min_body_size (float): Minimum body size threshold
            
        Returns:
            Optional[float]: Body size if validation passes, None otherwise
        """
        # Check body ratio
        body_ratio = StrongCandleAnalyzer.calculate_body_ratio(alert_candle)
        if body_ratio < min_body_ratio:
            return None
        
        # Check body size
        body_size = StrongCandleAnalyzer.calculate_body_size(alert_candle)
        if body_size < min_body_size:
            return None
        
        return body_size
    
    @staticmethod
    def validate_alert_candle_volume(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series,
        max_volume_multiplier: float
    ) -> bool:
        """
        Validate alert candle volume against conditional window.
        
        The conditional window is the lookback window excluding the alert candle.
        
        Condition: alert_candle_volume <= max_conditional_window_volume * max_volume_multiplier
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window
            alert_candle (pd.Series): Alert candle to validate
            max_volume_multiplier (float): Multiplier for max conditional window volume
            
        Returns:
            bool: True if volume validation passes, False otherwise
        """
        max_conditional_volume = StrongCandleAnalyzer.get_max_volume_in_conditional_window(
            lookback_window_df
        )
        max_allowed_volume = max_conditional_volume * max_volume_multiplier
        
        return alert_candle['volume'] <= max_allowed_volume
    
    @staticmethod
    def validate_window_color_consistency(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series,
        min_window_size_threshold: float,
        max_window_size_threshold: float
    ) -> Tuple[Optional[Signal], Optional[Trend]]:
        """
        Validate window color consistency and price range thresholds.
        
        Checks three conditions:
        1. Window trend can be determined
        2. Window size >= min_window_size_threshold
        3. Window size <= max_window_size_threshold
        4. Alert candle color matches window trend (green for uptrend, red for downtrend)
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window
            alert_candle (pd.Series): Alert candle to validate
            min_window_size_threshold (float): Minimum window price range
            max_window_size_threshold (float): Maximum window price range
            
        Returns:
            Tuple[Optional[Signal], Optional[Trend]]: (signal, trend) if valid, (None, None) otherwise
                - signal: Signal.BUY (green in uptrend) or Signal.SELL (red in downtrend)
                - trend: UPTREND or DOWNTREND
        """
        # Determine window size and trend
        window_size_val, window_trend = StrongCandleAnalyzer.get_window_size_and_trend(
            lookback_window_df
        )
        
        if window_trend is None:
            return (None, None)
        
        # Validate window size is within minimum threshold
        if window_size_val < min_window_size_threshold:
            return (None, None)
        
        # Validate window size is within maximum threshold
        if window_size_val > max_window_size_threshold:
            return (None, None)
        
        # Determine if candle color matches trend
        signal = None
        is_consistent = False
        
        if window_trend == Trend.UPTREND:
            is_green = candle_utils.is_green_candle(alert_candle)
            if is_green:
                is_consistent = True
                signal = Signal.BUY
        elif window_trend == Trend.DOWNTREND:
            is_red = candle_utils.is_red_candle(alert_candle)
            if is_red:
                is_consistent = True
                signal = Signal.SELL
        
        if not is_consistent:
            return (None, None)
        
        return (signal, window_trend)
    
    @staticmethod
    def validate_window_price_range(
        lookback_window_df: pd.DataFrame,
        max_window_size_threshold: float
    ) -> bool:
        """
        Validate that conditional window price range is within threshold.
        
        Conditional window = full lookback window excluding alert candle
        
        Condition: conditional_window_price_range <= max_window_size_threshold
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window
            max_window_size_threshold (float): Maximum allowed price range
            
        Returns:
            bool: True if window price range valid, False otherwise
        """
        window_size_val = StrongCandleAnalyzer.calculate_conditional_window_price_range(
            lookback_window_df
        )
        
        if window_size_val is None:
            return False
        
        return window_size_val <= max_window_size_threshold
    
    @staticmethod
    def validate_opposite_color_candles_bodies(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series,
        max_opposite_color_candle_body_size: float
    ) -> bool:
        """
        Validate that all opposite-color candles have body sizes within threshold.
        
        Conditional window = lookback window excluding alert candle
        Opposite color candles = candles with different color than alert candle
        
        Condition: All opposite-color candles must have body_size <= max_opposite_color_candle_body_size
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window
            alert_candle (pd.Series): Alert candle (determines color to compare against)
            max_opposite_color_candle_body_size (float): Maximum body size for opposite-color candles
            
        Returns:
            bool: True if all opposite-color candles valid, False otherwise
        """
        conditional_window_df = lookback_window_df.iloc[:-1]
        
        opposite_color_candles = StrongCandleAnalyzer.get_opposite_color_candles(
            conditional_window_df,
            alert_candle
        )
        
        # If no opposite color candles, validation passes
        if len(opposite_color_candles) == 0:
            return True
        
        # Check all opposite-color candles have small bodies
        for candle in opposite_color_candles:
            if not candle_utils.is_body_smaller_than_max(candle, max_opposite_color_candle_body_size):
                return False
        
        return True
