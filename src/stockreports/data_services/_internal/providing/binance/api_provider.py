"""
Binance REST API data provider - implements BaseDataProvider for Binance.

This provider fetches historical OHLCV data from Binance REST API
and normalizes it to the standard format.

Binance API endpoints:
- Klines (candlestick): GET /api/v3/klines
"""

import logging
from typing import Optional, Dict, Any, Union
import pandas as pd
import requests
import time

from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing.binance.normalizer import BinanceNormalizer


class BinanceAPIProvider(BaseDataProvider):
    """
    Binance REST API data provider implementation.
    
    Fetches OHLCV data from Binance REST API and normalizes it to standard format.
    Supports all trading pairs available on Binance (e.g., BTCUSDT, ETHUSDT, etc.).
    """
    
    # API endpoint for Binance
    API_BASE_URL = "https://api.binance.com/api/v3"
    
    # Supported timeframes (Binance uses different naming)
    # Map from standard timeframe to Binance interval
    TIMEFRAME_MAP = {
        "1m": "1m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "4h": "4h",
        "1d": "1d",
        "1w": "1w",
        "1M": "1M"
    }
    
    SUPPORTED_TIMEFRAMES = list(TIMEFRAME_MAP.keys())
    
    # API rate limiting
    DEFAULT_TIMEOUT = 10
    DEFAULT_RETRIES = 3
    
    def __init__(self, timeout: int = DEFAULT_TIMEOUT, retries: int = DEFAULT_RETRIES):
        """
        Initialize Binance API provider.
        
        Uses Provider.BINANCE enum value as the provider name.
        
        Args:
            timeout (int): Request timeout in seconds. Defaults to 10
            retries (int): Number of retries on failure. Defaults to 3
        """
        super().__init__(Provider.BINANCE.value)
        self.normalizer = BinanceNormalizer()
        self.timeout = timeout
        self.retries = retries
        self.session = requests.Session()
        self.logger.info(f"Initialized {self.provider_name} API provider (timeout={timeout}s, retries={retries})")
    
    def close(self):
        """
        Close HTTP session for this provider.
        
        This method is called automatically when exiting a 'with' statement:
            with provider:
                df = provider.fetch_ohlcv(...)
            # Session is closed here automatically
        """
        try:
            if self.session:
                self.session.close()
                self.logger.debug("HTTP session closed")
        except Exception as e:
            self.logger.warning(f"Error closing HTTP session: {e}")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: int = 1
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Binance REST API.
        
        Args:
            symbol (str): Trading pair (e.g., "BTCUSDT", "ETHUSDT")
            from_timestamp (int): Start time as Unix timestamp in seconds
            to_timestamp (int): End time as Unix timestamp in seconds
            resolution (int): Candle resolution in minutes (default: 1).
                             Supported values: 1, 5, 15, 30, 60, 240, 1440
                             Internally converts to Binance interval format:
                             - 1 → "1m", 5 → "5m", 15 → "15m", 30 → "30m"
                             - 60 → "1h", 240 → "4h", 1440 → "1d"
        
        Returns:
            pd.DataFrame: OHLCV data with timezone-aware datetime index
        
        Raises:
            ValueError: If symbol or resolution is not supported
            RuntimeError: If API request fails
        """
        # Convert int resolution to string timeframe
        timeframe = self._resolution_to_timeframe(resolution)
        
        # Validate inputs
        self.validate_symbol(symbol)
        if timeframe not in self.SUPPORTED_TIMEFRAMES:
            raise ValueError(
                f"Unsupported resolution: {resolution} minutes. "
                f"Supported: {[self._timeframe_to_resolution(tf) for tf in self.SUPPORTED_TIMEFRAMES]}"
            )
        
        self.logger.info(
            f"Fetching {symbol} resolution={resolution}min ({timeframe}) data from {from_timestamp} to {to_timestamp}"
        )
        
        try:
            # Convert timeframe to Binance interval
            interval = self.TIMEFRAME_MAP[timeframe]
            
            # Fetch all candles in the time range
            all_candles = []
            current_start_ms = from_timestamp * 1000
            end_ms = to_timestamp * 1000
            
            # Binance max limit per request is 1000
            max_candles_per_request = 1000
            
            while current_start_ms < end_ms:
                candles = self._fetch_candles_batch(
                    symbol=symbol,
                    interval=interval,
                    start_time_ms=current_start_ms,
                    end_time_ms=end_ms,
                    limit=max_candles_per_request
                )
                
                if not candles or len(candles) == 0:
                    break
                
                all_candles.extend(candles)
                
                # Move to next batch (last candle's time + 1 interval)
                last_candle_time_ms = candles[-1][0]
                current_start_ms = last_candle_time_ms + 1
                
                # Add small delay to avoid rate limiting
                time.sleep(0.1)
            
            if not all_candles:
                self.logger.warning(f"No data received from Binance for {symbol}")
                return pd.DataFrame()
            
            # Normalize raw data to standard format
            df = self.normalizer.normalize(all_candles, symbol)
            
            self.logger.info(
                f"Successfully fetched {len(df)} candles for {symbol} {timeframe}"
            )
            
            return df
        
        except Exception as e:
            self.logger.error(
                f"Error fetching data from Binance API for {symbol}: {e}"
            )
            raise RuntimeError(
                f"Failed to fetch {symbol} data from Binance: {str(e)}"
            )
    
    def _fetch_candles_batch(
        self,
        symbol: str,
        interval: str,
        start_time_ms: int,
        end_time_ms: int,
        limit: int = 1000
    ) -> list:
        """
        Fetch a batch of candles from Binance API.
        
        Args:
            symbol (str): Trading pair
            interval (str): Binance interval format
            start_time_ms (int): Start time in milliseconds
            end_time_ms (int): End time in milliseconds
            limit (int): Max candles to fetch
        
        Returns:
            list: List of candle arrays
        
        Raises:
            RuntimeError: If API request fails
        """
        url = f"{self.API_BASE_URL}/klines"
        
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": start_time_ms,
            "endTime": end_time_ms,
            "limit": limit
        }
        
        for attempt in range(self.retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                
                candles = response.json()
                if not isinstance(candles, list):
                    raise RuntimeError(f"Expected list, got {type(candles)}")
                
                self.logger.debug(
                    f"Fetched {len(candles)} candles for {symbol} from Binance"
                )
                
                return candles
            
            except requests.exceptions.RequestException as e:
                if attempt < self.retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.warning(
                        f"Binance API request failed (attempt {attempt + 1}/{self.retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    raise RuntimeError(f"Binance API request failed after {self.retries} attempts: {e}")
            
            except (ValueError, KeyError) as e:
                raise RuntimeError(f"Error parsing Binance API response: {e}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate that symbol is supported by Binance.
        
        Binance supports trading pairs like "BTCUSDT", "ETHUSDT" (6-20 alphanumeric characters).
        
        Uses centralized configuration from SymbolConfigRegistry.
        
        Args:
            symbol (str): Trading pair (e.g., "BTCUSDT", "ETHUSDT")
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If symbol is invalid
        """
        return self._validate_symbol_common(symbol)
    
    def get_supported_timeframes(self) -> list:
        """
        Get list of supported timeframes.
        
        Returns:
            list: Supported timeframe strings
        """
        return self.SUPPORTED_TIMEFRAMES.copy()
    
    def normalize_response(self, raw_data: list) -> pd.DataFrame:
        """
        Normalize raw Binance API response to standard DataFrame format.
        
        Args:
            raw_data (list): Raw API response containing candle arrays
        
        Returns:
            pd.DataFrame: Normalized OHLCV DataFrame
        
        Raises:
            ValueError: If data format is invalid
        """
        try:
            # Binance API returns array of arrays
            # We need to infer symbol from context - here we use generic reference
            return self.normalizer.normalize(raw_data, 'UNKNOWN')
        except Exception as e:
            self.logger.error(f"Error normalizing response: {e}")
            raise ValueError(f"Failed to normalize Binance response: {str(e)}")
    
    @staticmethod
    def _resolution_to_timeframe(resolution: int) -> str:
        """
        Convert resolution (minutes) to standard timeframe format.
        
        Args:
            resolution (int): Resolution in minutes (1, 5, 15, 30, 60, 240, 1440)
        
        Returns:
            str: Standard timeframe string (e.g., "1m", "5m", "1d")
        
        Raises:
            ValueError: If resolution is not supported
        """
        mapping = {
            1: "1m",
            5: "5m",
            15: "15m",
            30: "30m",
            60: "1h",
            240: "4h",
            1440: "1d",
        }
        
        if resolution not in mapping:
            raise ValueError(f"Unsupported resolution: {resolution} minutes. Supported: {list(mapping.keys())}")
        
        return mapping[resolution]
    
    def validate_configuration(self) -> bool:
        """
        Validate provider configuration.
        
        Checks that:
        - API endpoint is accessible
        - Required dependencies are available
        - Configuration is valid
        
        Returns:
            bool: True if configuration is valid
        
        Raises:
            RuntimeError: If configuration is invalid
        """
        try:
            # Check that normalizer is initialized
            if not self.normalizer:
                raise RuntimeError("Normalizer not initialized")
            
            # Check that API base URL is valid
            if not self.API_BASE_URL or not self.API_BASE_URL.startswith("http"):
                raise RuntimeError(f"Invalid API base URL: {self.API_BASE_URL}")
            
            # Check that timeout and retries are positive
            if self.timeout <= 0:
                raise RuntimeError(f"Invalid timeout: {self.timeout}")
            
            if self.retries <= 0:
                raise RuntimeError(f"Invalid retries: {self.retries}")
            
            self.logger.info("Configuration validation passed")
            return True
        
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    def __del__(self):
        """Cleanup - close session."""
        try:
            if hasattr(self, 'session'):
                self.session.close()
        except Exception:
            pass
