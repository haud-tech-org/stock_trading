"""
Binance data normalizer - converts raw API responses to standard format.

Binance API returns OHLCV data in array format:
[
    [timestamp_ms, open, high, low, close, volume, close_time, quote_asset_volume, trades, taker_buy_base, taker_buy_quote, ignored],
    ...
]

This normalizer converts this format to a standard timezone-aware pandas DataFrame
with columns: [time, open, high, low, close, volume]
"""

import pandas as pd
import logging
from typing import List, Dict, Any, Optional
import pytz
from datetime import datetime
from src.stockreports.utils.time_utils import get_market_timezone_str


class BinanceNormalizer:
    """
    Normalizes Binance API responses to standard OHLCV DataFrame format.
    
    The normalizer handles both REST API array format and converts timestamps
    from milliseconds to seconds with proper timezone handling.
    """
    
    def __init__(self):
        """Initialize the Binance normalizer."""
        self.logger = logging.getLogger("BinanceNormalizer")
        self.market_tz = pytz.timezone(get_market_timezone_str())
    
    def normalize(self, raw_data: List[List[Any]], symbol: str) -> pd.DataFrame:
        """
        Normalize raw Binance API response to standard DataFrame format.
        
        Args:
            raw_data (List[List]): Raw response from Binance API containing:
                - Each element is a candle: [timestamp_ms, open, high, low, close, volume, ...]
            symbol (str): Trading symbol for reference/validation
        
        Returns:
            pd.DataFrame: Normalized OHLCV data with columns:
                [time, open, high, low, close, volume]
                Index: timezone-aware datetime in UTC
        
        Raises:
            ValueError: If raw_data format is invalid or incomplete
            TypeError: If data types are incorrect
        """
        try:
            # Validate input
            self._validate_raw_data(raw_data, symbol)
            
            if len(raw_data) == 0:
                raise ValueError("Response contains no data (empty array)")
            
            # Extract OHLCV data from each candle
            timestamps_ms = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            for candle in raw_data:
                if len(candle) < 6:
                    raise ValueError(
                        f"Candle data incomplete. Expected at least 6 fields, got {len(candle)}"
                    )
                
                try:
                    timestamps_ms.append(int(candle[0]))
                    opens.append(float(candle[1]))
                    highs.append(float(candle[2]))
                    lows.append(float(candle[3]))
                    closes.append(float(candle[4]))
                    volumes.append(float(candle[5]))
                except (TypeError, ValueError) as e:
                    raise ValueError(f"Error converting candle data types: {e}")
            
            # Convert timestamps from milliseconds to seconds, then to datetime
            timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
            datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
            
            # Create DataFrame
            df = pd.DataFrame({
                'time': datetimes,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            # Set time as index
            df.set_index('time', inplace=True)
            
            # Convert numeric columns to float
            numeric_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in numeric_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Check for NaN values (from coercion failures)
            nan_count = df.isnull().sum().sum()
            if nan_count > 0:
                self.logger.warning(
                    f"Found {nan_count} NaN values after type coercion. "
                    f"Data may contain invalid numeric values."
                )
            
            # Sort by timestamp (should already be sorted)
            df.sort_index(inplace=True)
            
            self.logger.debug(
                f"Normalized {len(df)} candles for {symbol}. "
                f"Period: {df.index[0]} to {df.index[-1]}"
            )
            
            return df
        
        except Exception as e:
            self.logger.error(f"Error normalizing Binance data for {symbol}: {e}")
            raise
    
    def _validate_raw_data(self, raw_data: List[List[Any]], symbol: str) -> None:
        """
        Validate raw Binance API response structure.
        
        Args:
            raw_data (List[List]): Raw data to validate
            symbol (str): Expected symbol for reference
        
        Raises:
            ValueError: If data structure is invalid
            TypeError: If data type is incorrect
        """
        # Check type
        if not isinstance(raw_data, list):
            raise TypeError(
                f"Expected list, got {type(raw_data).__name__}"
            )
        
        # Check if empty (handled separately in normalize)
        if len(raw_data) == 0:
            self.logger.debug(f"Empty response for {symbol}")
            return
        
        # Check first element structure
        first_candle = raw_data[0]
        if not isinstance(first_candle, (list, tuple)):
            raise TypeError(
                f"Expected candle to be list/tuple, got {type(first_candle).__name__}"
            )
        
        if len(first_candle) < 6:
            raise ValueError(
                f"Candle data incomplete. Expected at least 6 fields, got {len(first_candle)}"
            )
        
        # Validate timestamp is numeric
        try:
            ts_ms = int(first_candle[0])
            if ts_ms <= 0:
                raise ValueError(f"Invalid timestamp: {ts_ms}")
        except (TypeError, ValueError):
            raise ValueError(f"First element must be numeric timestamp, got {first_candle[0]}")
    
    def validate_ohlcv(self, df: pd.DataFrame) -> bool:
        """
        Validate that normalized DataFrame meets OHLCV requirements.
        
        Args:
            df (pd.DataFrame): DataFrame to validate
        
        Returns:
            bool: True if valid, raises exception otherwise
        
        Raises:
            ValueError: If DataFrame doesn't meet requirements
        """
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_cols = [c for c in required_columns if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Check index is datetime with timezone
        if not isinstance(df.index, pd.DatetimeIndex):
            raise ValueError("Index must be DatetimeIndex")
        if df.index.tz is None:
            raise ValueError("Index must be timezone-aware")
        
        # Check no NaN values in critical columns
        if df[required_columns].isnull().any().any():
            nan_info = df[required_columns].isnull().sum()
            raise ValueError(f"Found NaN values: {nan_info[nan_info > 0].to_dict()}")
        
        # Check OHLC relationship (high >= low, high >= open/close, etc)
        invalid_rows = df[
            (df['high'] < df['low']) |
            (df['high'] < df['open']) |
            (df['high'] < df['close']) |
            (df['low'] > df['open']) |
            (df['low'] > df['close'])
        ]
        
        if len(invalid_rows) > 0:
            self.logger.warning(
                f"Found {len(invalid_rows)} rows with invalid OHLC relationships"
            )
        
        # Check volume is non-negative
        if (df['volume'] < 0).any():
            raise ValueError("Volume values must be non-negative")
        
        return True
