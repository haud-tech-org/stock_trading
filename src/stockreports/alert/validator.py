"""
Abstract base class for Validator implementations across all approaches.

This module provides the base Validator class with common static methods for
pure validations that are shared across multiple trading approaches.
Subclasses implement approach-specific validation logic while inheriting
common validation utilities.
"""

from abc import ABC
import pandas as pd
from typing import Optional
from src.stockreports.alert.common.constants import CandleColor, Comparison, CandleColumn
from src.stockreports.utils import candle_utils


class Validator(ABC):
    """
    Abstract base class for approach-specific Validators.
    
    Provides common static validation methods that are reusable across
    different trading approaches. These are pure functions with no state
    mutations or side effects.
    
    Each approach subclasses this to inherit common validations while
    adding approach-specific validation methods.
    
    Color Constants:
        All methods that reference candle colors should use CandleColor constants:
        - CandleColor.GREEN - Bullish candle (close > open)
        - CandleColor.RED - Bearish candle (close < open)
        - CandleColor.NEUTRAL - No change (close == open)
    
    Comparison Constants:
        All methods that perform comparisons should use Comparison constants:
        - Comparison.GREATER - price > threshold
        - Comparison.LESS - price < threshold
        - Comparison.EQUAL - price == threshold
        - Comparison.GREATER_EQUAL - price >= threshold
        - Comparison.LESS_EQUAL - price <= threshold
    
    Examples:
        - StrongCandleValidator(Validator)
        - IchimokuValidator(Validator) - purely approach-specific, no inheritance used
        - VRAValidator(Validator)
    """
    
    # ===== COMMON CANDLE VALIDATIONS =====
    
    @staticmethod
    def validate_candle_color_consistency(
        df: pd.DataFrame,
        target_color: CandleColor
    ) -> bool:
        """
        Check if all candles in DataFrame match a target color.
        
        Useful for validating that a sequence of candles are all the same color.
        
        Args:
            df (pd.DataFrame): DataFrame with OHLC data
            target_color (CandleColor): Expected color - CandleColor.GREEN, CandleColor.RED, 
                                       or CandleColor.NEUTRAL
            
        Returns:
            bool: True if all candles match target color, False otherwise
        """
        if len(df) == 0:
            return False
        
        for _, candle in df.iterrows():
            if candle[CandleColumn.CLOSE] > candle[CandleColumn.OPEN]:
                candle_color = CandleColor.GREEN
            elif candle[CandleColumn.CLOSE] < candle[CandleColumn.OPEN]:
                candle_color = CandleColor.RED
            else:
                candle_color = CandleColor.NEUTRAL
            
            if candle_color != target_color:
                return False
        
        return True
    
    @staticmethod
    def validate_opposite_color_exists(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series
    ) -> bool:
        """
        Check if opposite color candles exist in the window.
        
        Args:
            lookback_window_df (pd.DataFrame): DataFrame with OHLC data
            alert_candle (pd.Series): The alert candle to compare against
            
        Returns:
            bool: True if at least one opposite color candle exists, False otherwise
        """
        if len(lookback_window_df) == 0:
            return False
        
        alert_is_green = candle_utils.is_green_candle(alert_candle)
        
        for _, row in lookback_window_df.iterrows():
            is_green = candle_utils.is_green_candle(row)
            if is_green != alert_is_green:
                return True
        
        return False
    
    @staticmethod
    def validate_price_threshold(
        price: float,
        threshold: float,
        comparison: Comparison
    ) -> bool:
        """
        Validate a price against a threshold with flexible comparison.
        
        Args:
            price (float): Price to validate
            threshold (float): Threshold value
            comparison (Comparison): Comparison operator - must be explicitly specified:
                                    Comparison.GREATER, Comparison.LESS, Comparison.EQUAL,
                                    Comparison.GREATER_EQUAL, or Comparison.LESS_EQUAL
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        if comparison == Comparison.GREATER:
            return price > threshold
        elif comparison == Comparison.LESS:
            return price < threshold
        elif comparison == Comparison.EQUAL:
            return price == threshold
        elif comparison == Comparison.GREATER_EQUAL:
            return price >= threshold
        elif comparison == Comparison.LESS_EQUAL:
            return price <= threshold
        else:
            return False
    
    @staticmethod
    def validate_ratio_threshold(
        ratio: float,
        min_threshold: Optional[float] = None,
        max_threshold: Optional[float] = None
    ) -> bool:
        """
        Validate a ratio is within acceptable bounds.
        
        Common for body ratio, volume ratio, etc.
        
        Args:
            ratio (float): Ratio to validate (typically 0.0 to 1.0)
            min_threshold (float, optional): Minimum acceptable value
            max_threshold (float, optional): Maximum acceptable value
            
        Returns:
            bool: True if ratio is within bounds, False otherwise
        """
        if min_threshold is not None and ratio < min_threshold:
            return False
        
        if max_threshold is not None and ratio > max_threshold:
            return False
        
        return True
    
    # ===== COMMON VOLUME VALIDATIONS =====
    
    @staticmethod
    def validate_volume_threshold(
        volume: float,
        threshold: float,
        comparison: Comparison
    ) -> bool:
        """
        Validate volume against a threshold.
        
        Args:
            volume (float): Volume to validate
            threshold (float): Threshold value
            comparison (Comparison): Comparison operator - must be explicitly specified:
                                    Comparison.GREATER, Comparison.LESS, Comparison.EQUAL,
                                    Comparison.GREATER_EQUAL, or Comparison.LESS_EQUAL
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        if comparison == Comparison.GREATER:
            return volume > threshold
        elif comparison == Comparison.LESS:
            return volume < threshold
        elif comparison == Comparison.EQUAL:
            return volume == threshold
        elif comparison == Comparison.GREATER_EQUAL:
            return volume >= threshold
        elif comparison == Comparison.LESS_EQUAL:
            return volume <= threshold
        else:
            return False
    
    @staticmethod
    def validate_volume_multiplier(
        current_volume: float,
        reference_volume: float,
        multiplier: float
    ) -> bool:
        """
        Validate current volume is at least a multiplier of reference volume.
        
        Common for spike detection: current_volume >= reference_volume * multiplier
        
        Args:
            current_volume (float): Volume to validate
            reference_volume (float): Reference/baseline volume
            multiplier (float): Multiplier threshold (e.g., 1.5 for 1.5x)
            
        Returns:
            bool: True if current_volume >= reference_volume * multiplier, False otherwise
        """
        if reference_volume == 0:
            return False
        
        return current_volume >= reference_volume * multiplier
    
    # ===== COMMON DATAFRAME VALIDATIONS =====
    
    @staticmethod
    def validate_dataframe_not_empty(df: pd.DataFrame) -> bool:
        """
        Check if DataFrame has at least one row.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
            
        Returns:
            bool: True if DataFrame has rows, False if empty
        """
        return len(df) > 0
    
    @staticmethod
    def validate_required_columns(
        df: pd.DataFrame,
        required_cols: list
    ) -> bool:
        """
        Check if DataFrame has all required columns.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
            required_cols (list): List of required column names
            
        Returns:
            bool: True if all columns exist, False otherwise
        """
        return all(col in df.columns for col in required_cols)
    
    @staticmethod
    def validate_window_size(
        df: pd.DataFrame,
        min_size: int,
        max_size: Optional[int] = None
    ) -> bool:
        """
        Validate DataFrame has appropriate window size.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
            min_size (int): Minimum required rows
            max_size (int, optional): Maximum allowed rows
            
        Returns:
            bool: True if size is within bounds, False otherwise
        """
        size = len(df)
        
        if size < min_size:
            return False
        
        if max_size is not None and size > max_size:
            return False
        
        return True
