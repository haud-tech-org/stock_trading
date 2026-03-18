# src/stockreports/alert/approach/STRONG_CANDLE/analyzer.py
"""
STRONG_CANDLE Analyzer - Pure calculation functions.

This module contains all pure calculation and analysis functions for the
STRONG_CANDLE approach. These functions have no side effects and can be
tested independently.

Inherits common calculation methods from the base Analyzer class.
"""

from src.stockreports.alert.analyzer import Analyzer


class StrongCandleAnalyzer(Analyzer):
    """
    Analyzer for STRONG_CANDLE approach.
    
    Inherits common calculation functions from base Analyzer:
    - Body ratio and size calculations
    - Window size and trend determination
    - Candle color classification
    - Candle filtering operations
    - Window and volume calculations
    
    All calculations are inherited from the base Analyzer class.
    This class is kept for approach-specific extensions if needed in the future.
    """
    pass


