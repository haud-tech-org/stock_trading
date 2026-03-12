"""
Abstract base class for Analyzer implementations across all approaches.

This module provides the base Analyzer class with common static methods for
pure calculations that are shared across multiple trading approaches.
Subclasses implement approach-specific analysis logic while inheriting
common calculation utilities.
"""

from abc import ABC
import pandas as pd
from typing import List, Optional, Tuple
from src.stockreports.alert.common.constants import Trend, CandleColor, CandleColumn
from src.stockreports.utils import window_utils, candle_utils


class Analyzer(ABC):
    """
    Abstract base class for approach-specific Analyzers.
    
    Provides common static calculation methods that are reusable across
    different trading approaches. These are pure functions with no state
    mutations or side effects.
    
    Each approach subclasses this to inherit common calculations while
    adding approach-specific analysis methods.
    
    Color Constants:
        All candle color returns use CandleColor constants:
        - CandleColor.GREEN - Bullish candle (close > open)
        - CandleColor.RED - Bearish candle (close < open)
        - CandleColor.NEUTRAL - No change (close == open)
    
    Examples:
        - StrongCandleAnalyzer(Analyzer)
        - IchimokuAnalyzer(Analyzer) - purely approach-specific, no inheritance used
        - VRAAnalyzer(Analyzer)
    """
    
    # ===== COMMON CANDLE CALCULATIONS =====
    
    @staticmethod
    def calculate_body_ratio(candle: pd.Series) -> float:
        """
        Calculate the body ratio of a candle.
        
        Body ratio = body size / full candle range (high - low)
        
        Ratio of 1.0 = full range is body (no wicks)
        Ratio of 0.0 = no body (doji/cross)
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close', 'high', 'low'
            
        Returns:
            float: Body ratio (0.0 to 1.0)
        """
        high = candle[CandleColumn.HIGH]
        low = candle[CandleColumn.LOW]
        open_price = candle[CandleColumn.OPEN]
        close = candle[CandleColumn.CLOSE]
        
        full_range = high - low
        if full_range == 0:
            return 0.0
        
        body_size = abs(close - open_price)
        body_ratio = body_size / full_range
        
        return body_ratio
    
    @staticmethod
    def calculate_body_size(candle: pd.Series) -> float:
        """
        Calculate the absolute body size of a candle.
        
        Body size = absolute difference between close and open
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close'
            
        Returns:
            float: Absolute body size in price units
        """
        body_size = abs(candle[CandleColumn.CLOSE] - candle[CandleColumn.OPEN])
        return body_size
    
    @staticmethod
    def get_candle_color(candle: pd.Series) -> CandleColor:
        """
        Determine the color of a candle.
        
        Args:
            candle (pd.Series): Candle data with 'open', 'close'
            
        Returns:
            CandleColor: One of the following:
                - CandleColor.GREEN if close > open (bullish)
                - CandleColor.RED if close < open (bearish)
                - CandleColor.NEUTRAL if close == open (no change)
        """
        if candle[CandleColumn.CLOSE] > candle[CandleColumn.OPEN]:
            return CandleColor.GREEN
        elif candle[CandleColumn.CLOSE] < candle[CandleColumn.OPEN]:
            return CandleColor.RED
        else:
            return CandleColor.NEUTRAL
    
    # ===== COMMON WINDOW CALCULATIONS =====
    
    @staticmethod
    def get_window_size_and_trend(
        lookback_window_df: pd.DataFrame
    ) -> Tuple[float, Optional[Trend]]:
        """
        Calculate window size and trend from close price extremes.
        
        Uses the minimum and maximum close prices in the window to determine:
        - Window size: max close - min close
        - Trend: UPTREND if close is rising, DOWNTREND if falling
        
        Args:
            lookback_window_df (pd.DataFrame): DataFrame with 'close' column
            
        Returns:
            Tuple[float, Optional[Trend]]: (window_size, trend)
                - window_size: Price range between min and max close
                - trend: UPTREND if first close < last close, DOWNTREND otherwise
                - trend: None if cannot determine
        """
        if len(lookback_window_df) == 0:
            return 0.0, None
        
        window_size_val, window_trend = window_utils.get_window_size_and_trend_by_close_extremes(
            lookback_window_df
        )
        
        return window_size_val, window_trend
    
    @staticmethod
    def calculate_window_price_range(df: pd.DataFrame) -> Optional[float]:
        """
        Calculate the price range of a window using high/low extremes.
        
        Args:
            df (pd.DataFrame): DataFrame with 'high', 'low' columns
            
        Returns:
            Optional[float]: Price range (max high - min low) or None if calculation fails
        """
        if len(df) == 0:
            return None
        
        try:
            min_low = df[CandleColumn.LOW].min()
            max_high = df[CandleColumn.HIGH].max()
            price_range = max_high - min_low
            return price_range
        except (KeyError, TypeError):
            return None
    
    @staticmethod
    def calculate_conditional_window_price_range(
        lookback_window_df: pd.DataFrame
    ) -> Optional[float]:
        """
        Calculate price range of conditional window (excluding last/alert candle).
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window DataFrame
            
        Returns:
            Optional[float]: Price range of conditional window (all except last candle)
        """
        if len(lookback_window_df) <= 1:
            return None
        
        conditional_window_df = lookback_window_df.iloc[:-1]
        return Analyzer.calculate_window_price_range(conditional_window_df)
    
    # ===== COMMON VOLUME CALCULATIONS =====
    
    @staticmethod
    def get_max_volume_in_window(df: pd.DataFrame) -> float:
        """
        Get maximum volume in a DataFrame window.
        
        Args:
            df (pd.DataFrame): DataFrame with 'volume' column
            
        Returns:
            float: Maximum volume, or 0.0 if DataFrame empty/no volume column
        """
        if len(df) == 0 or CandleColumn.VOLUME not in df.columns:
            return 0.0
        
        return df[CandleColumn.VOLUME].max()
    
    @staticmethod
    def get_max_volume_in_conditional_window(
        lookback_window_df: pd.DataFrame
    ) -> float:
        """
        Get maximum volume in conditional window (excluding alert candle).
        
        Args:
            lookback_window_df (pd.DataFrame): Full lookback window DataFrame
            
        Returns:
            float: Maximum volume in conditional window
        """
        if len(lookback_window_df) <= 1:
            return 0.0
        
        conditional_window_df = lookback_window_df.iloc[:-1]
        return Analyzer.get_max_volume_in_window(conditional_window_df)
    
    # ===== COMMON CANDLE FILTERING =====
    
    @staticmethod
    def get_opposite_color_candles(
        lookback_window_df: pd.DataFrame,
        alert_candle: pd.Series
    ) -> List[pd.Series]:
        """
        Filter and return all candles with opposite color to alert candle.
        
        Compares candle colors using close > open (green) vs close < open (red).
        
        Args:
            lookback_window_df (pd.DataFrame): DataFrame with OHLC data (excluding alert candle)
            alert_candle (pd.Series): The alert candle to compare against
            
        Returns:
            List[pd.Series]: List of candles with opposite color
        """
        alert_is_green = candle_utils.is_green_candle(alert_candle)
        
        opposite_color_candles = []
        for _, row in lookback_window_df.iterrows():
            is_green = candle_utils.is_green_candle(row)
            # Keep only candles with opposite color to alert candle
            if is_green != alert_is_green:
                opposite_color_candles.append(row)
        
        return opposite_color_candles
