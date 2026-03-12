import pandas as pd
import numpy as np

from .settings import IchimokuSettings


class IchimokuAnalyzer:
    """
    Calculate all Ichimoku indicator components.
    Pure calculation functions - no state, no logging.
    """
    
    @staticmethod
    def calculate_tenkan_sen(df: pd.DataFrame, period: int = 9) -> pd.Series:
        """
        Calculate Tenkan-sen (Conversion Line).
        
        Formula: (N-period high + N-period low) / 2
        Represents short-term momentum (9-period standard).
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            period (int): Period for calculation (default: 9)
            
        Returns:
            pd.Series: Tenkan-sen values
        """
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        return (high_max + low_min) / 2
    
    @staticmethod
    def calculate_kijun_sen(df: pd.DataFrame, period: int = 26) -> pd.Series:
        """
        Calculate Kijun-sen (Base Line).
        
        Formula: (N-period high + N-period low) / 2
        Represents medium-term support/resistance (26-period standard).
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            period (int): Period for calculation (default: 26)
            
        Returns:
            pd.Series: Kijun-sen values
        """
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        return (high_max + low_min) / 2
    
    @staticmethod
    def calculate_senkou_span_a(tenkan: pd.Series, kijun: pd.Series, shift: int = 26) -> pd.Series:
        """
        Calculate Senkou Span A (Leading Span A, Upper cloud boundary).
        
        Formula: (Tenkan + Kijun) / 2, shifted forward 26 periods
        Faster-moving cloud boundary that reacts to recent price action.
        
        Args:
            tenkan (pd.Series): Tenkan-sen values
            kijun (pd.Series): Kijun-sen values
            shift (int): Forward shift periods (default: 26)
            
        Returns:
            pd.Series: Senkou Span A values
        """
        senkou_a = (tenkan + kijun) / 2
        return senkou_a.shift(shift)
    
    @staticmethod
    def calculate_senkou_span_b(df: pd.DataFrame, period: int = 52, shift: int = 26) -> pd.Series:
        """
        Calculate Senkou Span B (Leading Span B, Lower cloud boundary).
        
        Formula: (N-period high + N-period low) / 2, shifted forward 26 periods
        Slower-moving cloud boundary, longer-term support/resistance (52-period standard).
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            period (int): Period for calculation (default: 52)
            shift (int): Forward shift periods (default: 26)
            
        Returns:
            pd.Series: Senkou Span B values
        """
        high_max = df['high'].rolling(window=period).max()
        low_min = df['low'].rolling(window=period).min()
        senkou_b = (high_max + low_min) / 2
        return senkou_b.shift(shift)
    
    @staticmethod
    def calculate_chikou_span(df: pd.DataFrame, period: int = 26) -> pd.Series:
        """
        Calculate Chikou Span (Lagging Line, Lagging Span).
        
        Formula: Current close shifted backward N periods
        Unique indicator that plots current price on past chart.
        Used to confirm trend strength by comparing current price to historical price.
        
        Args:
            df (pd.DataFrame): OHLCV dataframe
            period (int): Lag periods (default: 26)
            
        Returns:
            pd.Series: Chikou span values
        """
        return df['close'].shift(-period)
    
    @staticmethod
    def calculate_all_components(df: pd.DataFrame, settings: IchimokuSettings) -> pd.DataFrame:
        """
        Calculate all 5 Ichimoku components at once.
        
        Adds the following columns to the dataframe:
        - tenkan_sen: Conversion line (9-period)
        - kijun_sen: Base line (26-period)
        - senkou_a: Upper cloud boundary
        - senkou_b: Lower cloud boundary
        - chikou_span: Lagging confirmation line
        
        Args:
            df (pd.DataFrame): OHLCV dataframe with 'high', 'low', 'close'
            settings (IchimokuSettings): IchimokuSettings instance with period configurations
            
        Returns:
            pd.DataFrame: Original dataframe with indicator columns added, or None on failure
        """
        try:
            result_df = df.copy()
            
            # Calculate each component using settings periods
            result_df['tenkan_sen'] = IchimokuAnalyzer.calculate_tenkan_sen(
                result_df, settings.tenkan_period
            )
            result_df['kijun_sen'] = IchimokuAnalyzer.calculate_kijun_sen(
                result_df, settings.kijun_period
            )
            result_df['senkou_a'] = IchimokuAnalyzer.calculate_senkou_span_a(
                result_df['tenkan_sen'], result_df['kijun_sen'], settings.senkou_shift_period
            )
            result_df['senkou_b'] = IchimokuAnalyzer.calculate_senkou_span_b(
                result_df, settings.senkou_b_period, settings.senkou_shift_period
            )
            result_df['chikou_span'] = IchimokuAnalyzer.calculate_chikou_span(
                result_df, settings.chikou_period
            )
            
            return result_df
            
        except Exception as e:
            return None
