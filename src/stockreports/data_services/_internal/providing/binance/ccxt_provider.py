"""
Binance CCXT data provider - implements BaseDataProvider using CCXT library.

CCXT (CryptoCurrency eXchange Trading) is a unified library for interfacing
with crypto exchange APIs. This provider wraps Binance through CCXT.

Benefits:
- Unified interface across exchanges
- Built-in error handling and rate limiting
- Automatic reconnection
- Consistent data format
"""

import logging
from typing import Optional, Union
import pandas as pd

try:
    import ccxt  # type: ignore
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False

from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing.binance.normalizer import BinanceNormalizer


class BinanceCCXTProvider(BaseDataProvider):
    """
    Binance data provider using CCXT unified library.
    
    Fetches OHLCV data from Binance through CCXT and normalizes to standard format.
    Supports all trading pairs available on Binance.
    """
    
    # CCXT exchange name
    EXCHANGE_NAME = "binance"
    
    # Supported timeframes (CCXT format)
    SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w", "1M"]
    
    # CCXT rate limiting
    DEFAULT_ENABLE_RATELIMIT = True
    DEFAULT_REQUEST_TIMEOUT = 10000  # milliseconds
    
    def __init__(
        self,
        enable_ratelimit: bool = DEFAULT_ENABLE_RATELIMIT,
        request_timeout: int = DEFAULT_REQUEST_TIMEOUT
    ):
        """
        Initialize Binance CCXT provider.
        
        Uses Provider.BINANCE_CCXT enum value as the provider name.
        
        Args:
            enable_ratelimit (bool): Enable CCXT rate limiting. Defaults to True
            request_timeout (int): Request timeout in milliseconds. Defaults to 10000
        
        Raises:
            RuntimeError: If CCXT library is not installed
        """
        if not CCXT_AVAILABLE:
            raise RuntimeError(
                "CCXT library is not installed. "
                "Install it with: pip install ccxt"
            )
        
        super().__init__(Provider.BINANCE_CCXT.value)
        self.normalizer = BinanceNormalizer()
        self.enable_ratelimit = enable_ratelimit
        self.request_timeout = request_timeout
        
        # Initialize CCXT exchange
        try:
            exchange_class = getattr(ccxt, self.EXCHANGE_NAME)
            self.exchange = exchange_class({
                'enableRateLimit': enable_ratelimit,
                'timeout': request_timeout
            })
            self.logger.info(
                f"Initialized {self.provider_name} provider via CCXT "
                f"(ratelimit={enable_ratelimit}, timeout={request_timeout}ms)"
            )
        except AttributeError:
            raise RuntimeError(f"CCXT exchange '{self.EXCHANGE_NAME}' not found")
        except Exception as e:
            raise RuntimeError(f"Failed to initialize CCXT exchange: {e}")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: int = 1
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data from Binance through CCXT.
        
        Args:
            symbol (str): Trading pair (e.g., "BTCUSDT", "ETH/USDT")
                         Note: CCXT uses "/" separator format
            from_timestamp (int): Start time as Unix timestamp in seconds
            to_timestamp (int): End time as Unix timestamp in seconds
            resolution (int): Candle resolution in minutes (default: 1).
                             Supported values: 1, 5, 15, 30, 60, 240, 1440
                             Internally converts to CCXT timeframe format:
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
        
        # Convert symbol format if needed (add "/" if not present)
        ccxt_symbol = self._normalize_symbol_format(symbol)
        
        self.logger.info(
            f"Fetching {ccxt_symbol} {timeframe} data from {from_timestamp} to {to_timestamp}"
        )
        
        try:
            # Fetch all candles in the time range
            all_candles = []
            current_start_ms = from_timestamp * 1000
            end_ms = to_timestamp * 1000
            
            # CCXT limit per request is 1000 for most exchanges
            max_candles_per_request = 1000
            
            while current_start_ms < end_ms:
                candles = self.exchange.fetch_ohlcv(
                    ccxt_symbol,
                    timeframe=timeframe,
                    since=current_start_ms,
                    limit=max_candles_per_request
                )
                
                if not candles or len(candles) == 0:
                    break
                
                all_candles.extend(candles)
                
                # Move to next batch
                # Note: CCXT returns timestamps in milliseconds
                last_candle_time_ms = candles[-1][0]
                current_start_ms = last_candle_time_ms + 1
                
                # Check if we've reached the end
                if len(candles) < max_candles_per_request:
                    break
            
            if not all_candles:
                self.logger.warning(f"No data received from CCXT for {ccxt_symbol}")
                return pd.DataFrame()
            
            # Normalize raw data to standard format
            # Remove trailing columns that CCXT includes (we only need OHLCV)
            normalized_candles = [c[:6] for c in all_candles]  # Keep only [time, o, h, l, c, v]
            df = self.normalizer.normalize(normalized_candles, ccxt_symbol)
            
            self.logger.info(
                f"Successfully fetched {len(df)} candles for {ccxt_symbol} {timeframe}"
            )
            
            return df
        
        except Exception as e:
            # Handle CCXT-specific exceptions if available
            exc_name = type(e).__name__
            if exc_name in ['ExchangeError', 'NetworkError']:
                self.logger.error(f"CCXT {exc_name} for {ccxt_symbol}: {e}")
                raise RuntimeError(f"Binance CCXT error ({exc_name}): {str(e)}")
            
            self.logger.error(f"Error fetching data via CCXT for {ccxt_symbol}: {e}")
            raise RuntimeError(f"Failed to fetch {ccxt_symbol} via CCXT: {str(e)}")
    
    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate that symbol is supported by Binance CCXT.
        
        Binance CCXT supports trading pairs with "/" separator (e.g., "BTCUSDT", "ETH/USDT")
        or standard format (e.g., "BTCUSDT", "ETHUSDT").
        
        Uses centralized configuration from SymbolConfigRegistry with custom "/" handling.
        
        Args:
            symbol (str): Trading pair (e.g., "BTCUSDT", "BTCUSDT", "ETH/USDT")
                         Accepts both Binance format and CCXT "/" format
        
        Returns:
            bool: True if valid
        
        Raises:
            ValueError: If symbol is invalid
        """
        # Basic type/empty check
        if not symbol or not isinstance(symbol, str):
            raise ValueError(f"Symbol must be a non-empty string, got: {symbol}")
        
        # Normalize to uppercase for consistency
        symbol = symbol.upper().strip()
        
        # Use base validation on the symbol (CCXT config supports "/" format)
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
        Normalize raw CCXT response to standard DataFrame format.
        
        Args:
            raw_data (list): Raw CCXT OHLCV response
        
        Returns:
            pd.DataFrame: Normalized OHLCV DataFrame
        
        Raises:
            ValueError: If data format is invalid
        """
        try:
            # Keep only first 6 columns [time, o, h, l, c, v]
            normalized = [c[:6] for c in raw_data]
            return self.normalizer.normalize(normalized, 'UNKNOWN')
        except Exception as e:
            self.logger.error(f"Error normalizing CCXT response: {e}")
            raise ValueError(f"Failed to normalize CCXT response: {str(e)}")
    
    def validate_configuration(self) -> bool:
        """
        Validate provider configuration.
        
        Checks that:
        - CCXT exchange is initialized
        - Required dependencies are available
        - Configuration is valid
        
        Returns:
            bool: True if configuration is valid
        """
        try:
            # Check that normalizer is initialized
            if not self.normalizer:
                raise RuntimeError("Normalizer not initialized")
            
            # Check that exchange is initialized
            if not self.exchange:
                raise RuntimeError("CCXT exchange not initialized")
            
            # Check that exchange supports the required methods
            if not hasattr(self.exchange, 'fetch_ohlcv'):
                raise RuntimeError("Exchange does not support fetch_ohlcv")
            
            # Check timeout and ratelimit settings
            if self.request_timeout <= 0:
                raise RuntimeError(f"Invalid request timeout: {self.request_timeout}")
            
            self.logger.info("Configuration validation passed")
            return True
        
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False
    
    @staticmethod
    def _normalize_symbol_format(symbol: str) -> str:
        """
        Normalize symbol format to CCXT format with "/" separator.
        
        Examples:
            "BTCUSDT" -> "BTCUSDT"
            "BTCUSDT" -> "BTCUSDT"
            "ETHBUSD" -> "ETH/BUSD"
        
        Args:
            symbol (str): Symbol in either format
        
        Returns:
            str: Symbol in CCXT format (with "/")
        """
        symbol = symbol.upper()
        
        # Already in CCXT format
        if '/' in symbol:
            return symbol
        
        # Try common base assets to determine split point
        # Order matters - check longer bases first
        common_bases = ['USDT', 'BUSD', 'USDC', 'USDT', 'BNB', 'ETH', 'BTC', 'USDA']
        
        for base in common_bases:
            if symbol.endswith(base):
                quote = base
                asset = symbol[:-len(base)]
                if asset:  # Make sure we have something before the base
                    return f"{asset}/{quote}"
        
        # Fallback: assume first 3 chars are asset, rest is base
        if len(symbol) > 3:
            return f"{symbol[:-4]}/{symbol[-4:]}"
        
        # Can't determine - return as-is (will fail validation later)
        return symbol
    
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
    
    def close(self):
        """Close the exchange connection."""
        try:
            if hasattr(self, 'exchange') and self.exchange:
                # Not all CCXT exchange instances have a close() method
                if hasattr(self.exchange, 'close') and callable(getattr(self.exchange, 'close')):
                    self.exchange.close()
                    self.logger.debug("CCXT exchange connection closed")
                else:
                    self.logger.debug("CCXT exchange does not have close() method, skipping")
        except Exception as e:
            self.logger.warning(f"Error closing exchange: {e}")
    
    def __del__(self):
        """Cleanup - close connection on deletion."""
        self.close()
