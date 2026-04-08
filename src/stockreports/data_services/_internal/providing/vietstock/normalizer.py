"""
Vietstock data normalizer - converts raw API responses to standard format.

Vietstock API returns OHLCV data in the format:
{
    "s": "VN30",           # symbol
    "t": [timestamps],     # array of Unix timestamps (seconds)
    "o": [opens],          # array of opening prices
    "h": [highs],          # array of high prices
    "l": [lows],           # array of low prices
    "c": [closes],         # array of closing prices
    "v": [volumes]         # array of volumes
}

This normalizer converts this format to a standard timezone-aware pandas DataFrame.

IMPORTANT DATA CONTRACT:
- Output format: pd.DataFrame with 'time' set as index (pandas best practice for time-series)
- The DataProviderCoordinator.fetch_ohlcv() is responsible for standardizing this to a column
  before returning to consumers (HistoricalDataManager, Executors, etc.)
- This ensures consistent 'time' format throughout the application.

Columns: [open, high, low, close, volume]
Index: time (datetime64[ns] with market timezone)
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional
import pytz
from datetime import datetime
from src.stockreports.utils.time_utils import get_market_timezone_str


class VietstockNormalizer:
    """
    Normalizes Vietstock API responses to standard OHLCV DataFrame format.
    
    The normalizer ensures all timestamps are converted to the market timezone
    and data is properly indexed and typed.
    """
    
    def __init__(self):
        """Initialize the Vietstock normalizer."""
        self.logger = logging.getLogger("VietstockNormalizer")
        self.market_tz = pytz.timezone(get_market_timezone_str())
    
    def normalize(self, raw_data: Dict[str, Any], symbol: str) -> pd.DataFrame:
        """
        Normalize raw Vietstock API response to standard DataFrame format.
        
        Args:
            raw_data (Dict): Raw response from Vietstock API containing:
                - 's': Symbol string
                - 't': List of Unix timestamps (seconds)
                - 'o': List of opening prices
                - 'h': List of high prices
                - 'l': List of low prices
                - 'c': List of closing prices
                - 'v': List of volumes
            symbol (str): Expected symbol for validation
        
        Returns:
            pd.DataFrame: Normalized OHLCV data with columns:
                [time, open, high, low, close, volume]
                Index: timezone-aware datetime in Asia/Ho_Chi_Minh
        
        Raises:
            ValueError: If raw_data format is invalid or incomplete
            KeyError: If required fields are missing
        """
        try:
            # Validate input
            self._validate_raw_data(raw_data, symbol)
            
            # Extract data arrays
            timestamps = raw_data['t']
            opens = raw_data['o']
            highs = raw_data['h']
            lows = raw_data['l']
            closes = raw_data['c']
            volumes = raw_data['v']
            
            # Verify all arrays have same length
            arrays_info = {
                'timestamps': len(timestamps),
                'opens': len(opens),
                'highs': len(highs),
                'lows': len(lows),
                'closes': len(closes),
                'volumes': len(volumes)
            }
            
            if len(set(arrays_info.values())) != 1:
                raise ValueError(
                    f"Array length mismatch in Vietstock response: {arrays_info}"
                )
            
            # Convert timestamps from seconds to datetime
            datetimes = pd.to_datetime(timestamps, unit='s', utc=True)
            # Localize to market timezone
            datetimes = datetimes.tz_convert(self.market_tz)
            
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
        
        except KeyError as e:
            self.logger.error(f"Missing required field in Vietstock response: {e}")
            raise ValueError(f"Invalid Vietstock response format: missing {e}")
        except Exception as e:
            self.logger.error(
                f"Error normalizing Vietstock data for {symbol}: {e}"
            )
            raise
    
    def _validate_raw_data(self, raw_data: Dict[str, Any], symbol: str) -> None:
        """
        Validate raw Vietstock API response structure.
        
        Args:
            raw_data (Dict): Raw data to validate
            symbol (str): Expected symbol
        
        Raises:
            ValueError: If data structure is invalid
            KeyError: If required fields are missing
        """
        # Check type
        if not isinstance(raw_data, dict):
            raise ValueError(
                f"Expected dict, got {type(raw_data).__name__}"
            )
        
        # Check required fields
        required_fields = ['s', 't', 'o', 'h', 'l', 'c', 'v']
        missing_fields = [f for f in required_fields if f not in raw_data]
        if missing_fields:
            raise KeyError(f"Missing required fields: {missing_fields}")
        
        # Validate symbol matches
        returned_symbol = raw_data.get('s')
        if returned_symbol != symbol:
            self.logger.warning(
                f"Symbol mismatch: expected {symbol}, got {returned_symbol}. "
                f"Continuing with returned symbol."
            )
        
        # Validate arrays are iterable
        for field in ['t', 'o', 'h', 'l', 'c', 'v']:
            try:
                iter(raw_data[field])
            except TypeError:
                raise ValueError(
                    f"Field '{field}' is not iterable: {type(raw_data[field])}"
                )
        
        # Validate non-empty
        if len(raw_data['t']) == 0:
            raise ValueError("Response contains no data (empty array)")
    
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
        
        # Check timezone matches market timezone
        market_tz_str = get_market_timezone_str()
        if str(df.index.tz) != market_tz_str:
            raise ValueError(
                f"Index timezone must be {market_tz_str}, "
                f"got {df.index.tz}"
            )
        
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
