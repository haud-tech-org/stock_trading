# Data Provider Extension Guide - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Codebase Analysis  
**Target Audience:** Developers adding new data sources  
**Prerequisites:** Understanding Technical Reference architecture  

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Understanding Data Provider Architecture](#understanding-data-provider-architecture)
3. [BaseDataProvider Interface](#basedataprovider-interface)
4. [Actual Data Providers](#actual-data-providers)
5. [Provider Registration](#provider-registration)
6. [Creating a New Provider](#creating-a-new-provider)
7. [Integration Points](#integration-points)
8. [Testing](#testing)

---

## Overview

### What is a Data Provider?

A data provider is a class that:
- **Fetches** OHLCV (Open, High, Low, Close, Volume) data from an external source
- **Normalizes** data to standard DataFrame format
- **Returns** timezone-aware data in market timezone
- **Handles** errors gracefully with appropriate logging
- **Implements** the BaseDataProvider interface

### Current Data Providers (3 Total)

Located in `/src/stockreports/data_services/_internal/providing/`:

1. **VietstockProvider** - `vietstock/provider.py` (217 lines)
   - Data source: Vietstock API
   - Symbols: Vietnamese stocks (VN30, VNM, TPB, etc.)
   - Resolution: 1, 5, 15, 30, 60, 240, 1440 minutes
   - URL: https://api.vietstock.vn

2. **BinanceAPIProvider** - `binance/api_provider.py`
   - Data source: Binance REST API
   - Symbols: Cryptocurrency pairs (BTC/USDT, ETH/USDT, etc.)
   - Resolution: 1, 5, 15, 30, 60, 240, 1440 minutes
   - URL: https://api.binance.com

3. **BinanceCCXTProvider** - `binance/ccxt_provider.py`
   - Data source: Binance via CCXT library
   - Symbols: Cryptocurrency pairs (same as API provider)
   - Resolution: Same as API provider
   - Library: ccxt (unified crypto exchange interface)

### Provider Enum

All providers are registered in `_providers.py`:

```python
class Provider(Enum):
    VIETSTOCK = "vietstock"
    BINANCE = "binance"
    BINANCE_CCXT = "binance_ccxt"
```

### When to Create a New Provider

Create a new provider when:
- ✅ You have a new data source to integrate
- ✅ You need different asset class support (stocks, crypto, forex, etc.)
- ✅ You want to add an alternative to existing providers
- ❌ Don't create if you just need different symbols (configure existing provider)
- ❌ Don't create if you just need data processing changes (use normalizer)

---

## Understanding Data Provider Architecture

### Architecture Layers

```
DataServiceOrchestrator (Public API)
    ↓
HistoricalDataManager (Caching & Management)
    ↓
Provider Factory / Registry
    ↓
BaseDataProvider (Abstract Interface)
    ├── VietstockProvider
    ├── BinanceAPIProvider
    └── BinanceCCXTProvider
```

### Data Flow

```
User calls: orchestrator.fetch_and_process(symbol, start_time, end_time, resolution)
    ↓
HistoricalDataManager checks cache
    ↓
Cache miss → Select provider by symbol
    ↓
Provider.fetch_ohlcv(symbol, from_timestamp, to_timestamp, resolution)
    ↓
Provider fetches from API
    ↓
Provider normalizes to standard format
    ↓
HistoricalDataManager merges with cache
    ↓
Returns: pd.DataFrame with [time, open, high, low, close, volume]
```

### Key Concepts

#### Unix Timestamps
- All providers use Unix timestamps (seconds since epoch)
- Input: `from_timestamp`, `to_timestamp` as integers
- Example: 1712592000 = 2024-04-08 00:00:00 UTC

#### Resolution Mapping
- Input: Resolution in minutes (1, 5, 15, 30, 60, 240, 1440)
- Provider maps to its format:
  - Vietstock: "1", "5", "15", "30", "60", "240", "D"
  - Binance: "1m", "5m", "15m", "30m", "1h", "4h", "1d"
  - CCXT: Same as Binance

#### DataFrame Format
```python
DataFrame columns: [time, open, high, low, close, volume]
- time: datetime64[ns] with timezone (Asia/Ho_Chi_Minh)
- open, high, low, close: float64 (prices)
- volume: int64 (trading volume)
- Index: RangeIndex (not time-indexed)
```

---

## BaseDataProvider Interface

### Location
`/src/stockreports/data_services/_internal/providing/_base_provider.py` (196 lines)

### Abstract Method (You Must Implement)

```python
@abstractmethod
def fetch_ohlcv(
    self,
    symbol: str,
    from_timestamp: int,
    to_timestamp: int,
    resolution: int = 1
) -> pd.DataFrame:
    """
    Fetch OHLCV data from the provider.
    
    Args:
        symbol (str): Symbol identifier in provider format
                     Examples: "VN30" (Vietstock), "BTC/USDT" (Binance)
        from_timestamp (int): Start time as Unix timestamp in seconds
        to_timestamp (int): End time as Unix timestamp in seconds
        resolution (int): Candle resolution in minutes (default: 1)
                         Supported: 1, 5, 15, 30, 60, 240, 1440
    
    Returns:
        pd.DataFrame: DataFrame with columns [time, open, high, low, close, volume]
                     - time: timezone-aware datetime
                     - prices: float values
                     - volume: integer values
    
    Raises:
        ValueError: If symbol not supported or resolution invalid
        Exception: If API request fails
    """
    pass
```

### Concrete Methods (Provided by Base Class)

#### `__init__(provider_name: str)`
```python
def __init__(self, provider_name: str):
    """Initialize provider with name and logger."""
    self.provider_name = provider_name
    self.logger = logging.getLogger(f"DataProvider.{provider_name}")
```

#### `get_provider_name() -> str`
```python
def get_provider_name(self) -> str:
    """Get this provider's name."""
    return self.provider_name
```

#### `validate_symbol(symbol: str) -> None`
```python
def validate_symbol(self, symbol: str) -> None:
    """Validate symbol is supported. Raises ValueError if not."""
    # Uses SymbolValidator from validation/ package
```

### Normalizer Pattern

Each provider has a normalizer class:
- `VietstockNormalizer` - Converts Vietstock API format
- `BinanceNormalizer` - Converts Binance API format

```python
# In your provider's __init__:
self.normalizer = YourProviderNormalizer()

# In your fetch_ohlcv:
raw_data = self._fetch_from_api(...)
normalized_df = self.normalizer.normalize(raw_data)
return normalized_df
```

---

## Actual Data Providers

### 1. VietstockProvider

**File:** `/src/stockreports/data_services/_internal/providing/vietstock/provider.py` (217 lines)

**Key Features:**
- Vietnamese stock symbols (VN30, VNM, VCB, TPB, etc.)
- API Base: https://api.vietstock.vn
- Supports all standard resolutions

**Initialization:**
```python
class VietstockProvider(BaseDataProvider):
    API_BASE_URL = "https://api.vietstock.vn"
    
    def __init__(self):
        super().__init__(Provider.VIETSTOCK.value)  # "vietstock"
        self.normalizer = VietstockNormalizer()
        self.market_tz = pytz.timezone(get_market_timezone_str())
        self.logger.info(f"Initialized {self.provider_name} provider")
```

**Implementation Pattern:**
```python
def fetch_ohlcv(
    self,
    symbol: str,
    from_timestamp: int,
    to_timestamp: int,
    resolution: int = 1
) -> pd.DataFrame:
    # 1. Validate symbol
    self.validate_symbol(symbol)
    
    # 2. Convert resolution to provider format
    resolution_str = str(resolution)  # "1", "60", etc.
    
    # 3. Fetch from API
    api_url = f"{self.API_BASE_URL}/..."
    response = execute_api_request(api_url, params={...})
    
    # 4. Normalize data
    normalized_df = self.normalizer.normalize(response)
    
    # 5. Return
    return normalized_df
```

### 2. BinanceAPIProvider

**File:** `/src/stockreports/data_services/_internal/providing/binance/api_provider.py`

**Key Features:**
- Cryptocurrency pairs
- Uses Binance REST API
- Symbols: "BTC/USDT", "ETH/USDT", etc.

**Resolution Mapping:**
- 1 min → "1m"
- 60 min → "1h"
- 1440 min → "1d"

### 3. BinanceCCXTProvider

**File:** `/src/stockreports/data_services/_internal/providing/binance/ccxt_provider.py`

**Key Features:**
- Uses unified CCXT library
- Alternative to API provider
- Same resolution mapping as API provider

---

## Provider Registration

### Provider Enum
Register new providers in `_providers.py`:

```python
class Provider(Enum):
    VIETSTOCK = "vietstock"
    BINANCE = "binance"
    BINANCE_CCXT = "binance_ccxt"
    YOUR_PROVIDER = "your_provider"  # Add this
```

### Provider Factory
The factory in `_provider_factory.py` maps symbols to providers:

```python
# Pseudocode - actual implementation in _provider_factory.py
def get_provider(symbol: str) -> BaseDataProvider:
    if symbol in VIETSTOCK_SYMBOLS:
        return VietstockProvider()
    elif symbol in BINANCE_SYMBOLS:
        return BinanceAPIProvider()
    else:
        raise ValueError(f"No provider for symbol: {symbol}")
```

You need to register your provider in the factory.

---

## Creating a New Provider

### Step 1: Add to Provider Enum

```python
# src/stockreports/data_services/_internal/providing/_providers.py
class Provider(Enum):
    VIETSTOCK = "vietstock"
    BINANCE = "binance"
    BINANCE_CCXT = "binance_ccxt"
    YOUR_PROVIDER = "your_provider"  # Add this
```

### Step 2: Create Provider Directory

```
src/stockreports/data_services/_internal/providing/your_provider/
├── __init__.py
├── provider.py           # Your provider class
└── normalizer.py         # Data normalization
```

### Step 3: Create Normalizer

```python
# src/stockreports/data_services/_internal/providing/your_provider/normalizer.py
import pandas as pd
from typing import Dict, List

class YourProviderNormalizer:
    """Normalizes YOUR_PROVIDER data to standard format."""
    
    def normalize(self, raw_data: Dict) -> pd.DataFrame:
        """
        Convert provider format to standard OHLCV format.
        
        Expected output:
            DataFrame with columns: [time, open, high, low, close, volume]
            - time: datetime64[ns] with Asia/Ho_Chi_Minh timezone
            - prices: float64
            - volume: int64
        """
        # Your normalization logic
        df = pd.DataFrame(...)
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(
            'UTC'
        ).dt.tz_convert('Asia/Ho_Chi_Minh')
        return df
```

### Step 4: Create Provider Class

```python
# src/stockreports/data_services/_internal/providing/your_provider/provider.py
import pandas as pd
import logging
from typing import Optional

from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider
from src.stockreports.data_services._internal.providing._providers import Provider
from .normalizer import YourProviderNormalizer

class YourProviderClass(BaseDataProvider):
    """Data provider for YOUR_PROVIDER."""
    
    API_BASE_URL = "https://api.your-provider.com"
    
    def __init__(self):
        super().__init__(Provider.YOUR_PROVIDER.value)
        self.normalizer = YourProviderNormalizer()
        self.logger.info(f"Initialized {self.provider_name} provider")
    
    def fetch_ohlcv(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: int = 1
    ) -> pd.DataFrame:
        """Fetch OHLCV data from YOUR_PROVIDER API."""
        
        # 1. Validate symbol
        self.validate_symbol(symbol)
        
        # 2. Map resolution to provider format
        resolution_map = {
            1: "1m",
            5: "5m",
            60: "1h",
            1440: "1d"
        }
        resolution_str = resolution_map.get(resolution, "1m")
        
        # 3. Fetch from API
        try:
            raw_data = self._fetch_from_api(
                symbol=symbol,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                resolution=resolution_str
            )
        except Exception as e:
            self.logger.error(f"Failed to fetch {symbol}: {e}")
            raise
        
        # 4. Normalize to standard format
        df = self.normalizer.normalize(raw_data)
        
        # 5. Validate output
        self._validate_dataframe(df)
        
        return df
    
    def _fetch_from_api(
        self,
        symbol: str,
        from_timestamp: int,
        to_timestamp: int,
        resolution: str
    ) -> Dict:
        """Fetch raw data from YOUR_PROVIDER API."""
        # Your API logic
        pass
    
    def _validate_dataframe(self, df: pd.DataFrame) -> None:
        """Validate DataFrame has correct structure."""
        required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"Missing required columns. Got: {df.columns.tolist()}")
        
        if not pd.api.types.is_datetime64_any_dtype(df['time']):
            raise ValueError("'time' column must be datetime64")
```

### Step 5: Register in Factory

```python
# src/stockreports/data_services/_internal/providing/_provider_factory.py
from your_provider.provider import YourProviderClass

# In factory function:
def get_provider(symbol: str) -> BaseDataProvider:
    if symbol in VIETSTOCK_SYMBOLS:
        return VietstockProvider()
    elif symbol in BINANCE_SYMBOLS:
        return BinanceAPIProvider()
    elif symbol in YOUR_SYMBOLS:  # Add this
        return YourProviderClass()
    else:
        raise ValueError(f"No provider for symbol: {symbol}")
```

### Step 6: Configure Symbol Validator

```python
# src/stockreports/data_services/_internal/providing/validation/symbol_validator.py
YOUR_PROVIDER_SYMBOLS = {
    "SYMBOL1",
    "SYMBOL2",
    # ... add your symbols
}

# Add to validator registry
PROVIDER_SYMBOL_MAP = {
    "vietstock": VIETSTOCK_SYMBOLS,
    "binance": BINANCE_SYMBOLS,
    "binance_ccxt": BINANCE_SYMBOLS,
    "your_provider": YOUR_PROVIDER_SYMBOLS,  # Add this
}
```

---

## Integration Points

### DataServiceOrchestrator

The public API that uses providers:

```python
# src/stockreports/data_services/orchestrator.py
class DataServiceOrchestrator:
    def fetch_and_process(
        self,
        symbol: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        resolution: int = 1,
    ) -> Optional[pd.DataFrame]:
        """
        Public API for fetching data.
        
        Parameters:
            symbol: Stock/crypto symbol
            start_time: pd.Timestamp (not Unix timestamp)
            end_time: pd.Timestamp (not Unix timestamp)
            resolution: Candle minutes (default 1)
        
        Returns:
            Processed OHLCV DataFrame or None
        """
        # Converts pd.Timestamp to Unix timestamps
        # Calls HistoricalDataManager
        # Handles caching
```

**Key Point:** User-facing API uses `pd.Timestamp`, not Unix timestamps.

### HistoricalDataManager

Handles caching and provider selection:

```python
# src/stockreports/data_services/_internal/fetching/_manager.py
class HistoricalDataManager:
    def get_with_resolution(
        self,
        symbol: str,
        start_time: pd.Timestamp,
        end_time: pd.Timestamp,
        resolution: int
    ) -> Optional[pd.DataFrame]:
        """
        Main method called by orchestrator.
        - Checks cache
        - Calls provider if needed
        - Merges with cache
        - Returns complete data
        """
```

---

## Testing

### Unit Tests

```python
# tests/test_your_provider.py
import pytest
import pandas as pd
from src.stockreports.data_services._internal.providing.your_provider.provider import YourProviderClass

class TestYourProvider:
    
    def test_initialization(self):
        provider = YourProviderClass()
        assert provider.provider_name == "your_provider"
        assert provider.normalizer is not None
    
    def test_fetch_ohlcv(self):
        provider = YourProviderClass()
        
        # Create sample timestamps
        from_timestamp = 1712592000  # 2024-04-08
        to_timestamp = 1712678400    # 2024-04-09
        
        df = provider.fetch_ohlcv(
            symbol="SYMBOL1",
            from_timestamp=from_timestamp,
            to_timestamp=to_timestamp,
            resolution=1
        )
        
        # Validate structure
        assert isinstance(df, pd.DataFrame)
        assert list(df.columns) == ['time', 'open', 'high', 'low', 'close', 'volume']
        assert pd.api.types.is_datetime64_any_dtype(df['time'])
        assert len(df) > 0
    
    def test_invalid_symbol(self):
        provider = YourProviderClass()
        
        with pytest.raises(ValueError):
            provider.fetch_ohlcv(
                symbol="INVALID",
                from_timestamp=1712592000,
                to_timestamp=1712678400,
                resolution=1
            )
    
    def test_normalizer(self):
        normalizer = YourProviderNormalizer()
        
        # Test with mock data
        raw_data = {
            # Your provider's format
        }
        
        df = normalizer.normalize(raw_data)
        
        assert 'time' in df.columns
        assert df['time'].dtype.name.startswith('datetime64')
```

### Integration Tests

```python
# tests/test_data_service_integration.py
def test_orchestrator_with_your_provider():
    from src.stockreports.data_services.orchestrator import DataServiceOrchestrator
    
    orchestrator = DataServiceOrchestrator()
    
    df = orchestrator.fetch_and_process(
        symbol="SYMBOL1",
        start_time=pd.Timestamp("2024-04-08"),
        end_time=pd.Timestamp("2024-04-09"),
        resolution=1
    )
    
    assert df is not None
    assert len(df) > 0
```

---

## Troubleshooting

### Common Issues

**Issue: "Unknown provider" error**
- **Cause:** Provider not registered in enum
- **Fix:** Add to Provider class in `_providers.py`

**Issue: "No provider for symbol" error**
- **Cause:** Symbol not registered
- **Fix:** Add to symbol validator in `validation/symbol_validator.py`

**Issue: DataFrame columns wrong**
- **Cause:** Normalizer not returning correct format
- **Fix:** Ensure normalizer returns [time, open, high, low, close, volume]

**Issue: Timezone issues**
- **Cause:** Not using market timezone in normalizer
- **Fix:** Use `'Asia/Ho_Chi_Minh'` or `get_market_timezone_str()`

---

## Checklist for New Provider

- [ ] Add provider to Provider enum in `_providers.py`
- [ ] Create provider directory with normalizer
- [ ] Implement BaseDataProvider.fetch_ohlcv()
- [ ] Implement normalizer class
- [ ] Register in provider factory
- [ ] Add symbols to validator
- [ ] Write unit tests
- [ ] Test with DataServiceOrchestrator
- [ ] Test timezone handling
- [ ] Verify DataFrame structure
- [ ] Document configuration requirements
- [ ] Add error handling for API failures

---

**Status:** Corrected based on actual codebase  
**Date:** April 8, 2026  
**Actual Providers:** 3 (Vietstock, BinanceAPI, BinanceCCXT)  
**Ready to Use:** Yes
