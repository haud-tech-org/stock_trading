from typing import Optional, Tuple
import pandas as pd

from src.stockreports.alert.common.constants import CandleColumn, Trend
from src.stockreports.utils.candle_utils import (
    get_trend_from_candle,
    get_candle_body_size,
    get_candle_high_low_range,
)


class DojiAnchorSignalCandleAnalyzer:
    """Pure calculation functions for DOJI_ANCHOR_SIGNAL_CANDLE."""

    @staticmethod
    def is_doji(row: pd.Series, max_body_ratio: float, min_range: float, eps: float = 1e-9) -> bool:
        body = get_candle_body_size(row)
        rng = get_candle_high_low_range(row)
        
        if rng <= eps:
            return False
        body_ratio = body / (rng + eps)
        return (body_ratio <= max_body_ratio) and (rng >= min_range)

    @staticmethod
    def find_most_recent_doji(df: pd.DataFrame, max_body_ratio: float, min_range: float) -> Optional[int]:
        # prefer most recent (end of df)
        for idx in range(len(df) - 1, -1, -1):
            if DojiAnchorSignalCandleAnalyzer.is_doji(df.iloc[idx], max_body_ratio, min_range):
                return idx
        return None

    @staticmethod
    def discover_anchor_with_trend(df: pd.DataFrame, doji_idx: int, search_limit: int, trend_window: int = 3) -> Optional[Tuple[int, str, int, float]]:
        """Discover anchor candle and determine trend direction for doji candle.
        
        This method performs a complete anchor discovery process:
        1. Find trend candle: candle with longest body in trend_window before doji
        2. Determine trend direction from trend candle (compare OPEN vs CLOSE)
        3. Validate doji candle matches trend direction (doji at extreme of trend)
        4. Find anchor in lookback window (before/at trend candle):
           - Downtrend: candle with highest HIGH
           - Uptrend: candle with lowest LOW
        5. Calculate average volume between anchor and doji
        
        Args:
            df: OHLCV DataFrame
            doji_idx: index of doji candle
            search_limit: max number of candles to search backward
            trend_window: candles used to find trend candle (longest body)
            
        Returns:
            Tuple of (anchor_idx, trend, trend_candle_idx, avg_vol) or None if not found.
            trend: Trend.UPTREND or Trend.DOWNTREND
            trend_candle_idx: index of the trend candle used to determine trend
            avg_vol: average volume between anchor and doji
        """
        if doji_idx <= 0 or search_limit <= 0:
            return None
            
        search_start = max(0, doji_idx - search_limit)
        
        # Step 1: Find trend candle (longest body in trend_window before doji)
        trend_start = max(search_start, doji_idx - trend_window)
        if trend_start >= doji_idx:
            return None
        
        # Use get_candle_body_size utility to calculate bodies
        bodies = [get_candle_body_size(df.iloc[idx]) for idx in range(trend_start, doji_idx)]
        if not bodies:
            return None
        
        trend_candle_rel_idx = bodies.index(max(bodies))
        trend_candle_idx = trend_start + trend_candle_rel_idx
        
        # Step 2: Determine trend direction from trend candle
        # Use get_trend_from_candle to determine trend from the candle's OPEN/CLOSE
        trend_candle = df.iloc[trend_candle_idx]
        trend = get_trend_from_candle(trend_candle)
        is_downtrend = trend == Trend.DOWNTREND
        is_uptrend = trend == Trend.UPTREND
        
        # Step 2.5: Validate doji candle matches trend direction
        # If uptrend: doji's HIGH should be the highest HIGH in [search_start, doji_idx]
        # If downtrend: doji's LOW should be the lowest LOW in [search_start, doji_idx]
        doji_candle = df.iloc[doji_idx]
        doji_high = float(doji_candle[CandleColumn.HIGH])
        doji_low = float(doji_candle[CandleColumn.LOW])
        
        if is_uptrend:
            # For uptrend: verify doji's HIGH is the highest in the window
            window_high = float(df[CandleColumn.HIGH].astype(float).iloc[search_start:doji_idx+1].max())
            if doji_high != window_high:
                # Doji's high is not the highest - invalid uptrend anchor
                return None
        elif is_downtrend:
            # For downtrend: verify doji's LOW is the lowest in the window
            window_low = float(df[CandleColumn.LOW].astype(float).iloc[search_start:doji_idx+1].min())
            if doji_low != window_low:
                # Doji's low is not the lowest - invalid downtrend anchor
                return None
        else:
            # No clear trend (OPEN == CLOSE): return None
            return None
        
        # Step 3: Find anchor in [search_start, trend_candle_idx]
        anchor_search_end = trend_candle_idx + 1
        
        anchor_idx = None
        if is_downtrend:
            # Downtrend: anchor = candle with highest HIGH
            anchor_idx = search_start + int(
                df[CandleColumn.HIGH].astype(float).iloc[search_start:anchor_search_end].values.argmax()
            )
        elif is_uptrend:
            # Uptrend: anchor = candle with lowest LOW
            anchor_idx = search_start + int(
                df[CandleColumn.LOW].astype(float).iloc[search_start:anchor_search_end].values.argmin()
            )
        
        # Step 4: Calculate average volume between anchor and doji
        avg_vol = DojiAnchorSignalCandleAnalyzer.avg_volume(df, anchor_idx, doji_idx)
        
        return (anchor_idx, trend, trend_candle_idx, avg_vol)

    @staticmethod
    def select_trend_candle(df: pd.DataFrame, start_idx: int, end_idx: int) -> Optional[int]:
        # pick candle with largest body in [start_idx, end_idx]
        if start_idx >= end_idx:
            return None
        
        # Use get_candle_body_size utility
        bodies = [get_candle_body_size(df.iloc[idx]) for idx in range(start_idx, end_idx + 1)]
        if not bodies:
            return None
        
        rel_idx = bodies.index(max(bodies))
        return start_idx + rel_idx

    @staticmethod
    def avg_volume(df: pd.DataFrame, start_idx: int, end_idx: int) -> float:
        vol = df[CandleColumn.VOLUME].astype(float).iloc[start_idx:end_idx+1]
        if vol.empty:
            return 0.0
        return float(vol.mean())
