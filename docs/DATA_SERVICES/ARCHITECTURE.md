# Data Services Architecture (v2.0) - POST MIGRATION

## Overview

The Data Services system provides a **complete data pipeline** from request to final result. It integrates multiple data sources (Vietstock, Binance API, Binance CCXT) with intelligent caching, data processing, and standardization. This is the production-ready v2.0 after the Data Provider Migration.

## High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                    Application / User Code                           │
│               (Approaches, Executors, Strategies)                    │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                    [1] REQUEST DATA
                    (symbol, time range, resolution)
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│          HistoricalDataManager (Cache & Intelligent Fetching)        │
│  - Check cache for data                                              │
│  - If missing: fetch from Coordinator                                │
│  - Process & cache result                                            │
│  - Return standardized data                                          │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                    [2] FETCH DATA VIA COORDINATOR
                    (Auto-detect provider, fetch OHLCV)
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│      DataProviderCoordinator (Provider Selection & Routing)          │
│  - Auto-detect provider from symbol config                           │
│  - Route to appropriate provider                                     │
│  - Standardize output format (time as index)                         │
│  - Validate type compatibility                                       │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
         ┌────────────┐   ┌────────────┐   ┌────────────┐
         │ Vietstock  │   │  Binance   │   │ Binance    │
         │ Provider   │   │  API       │   │ CCXT       │
         │            │   │  Provider  │   │ Provider   │
         └────┬───────┘   └────┬───────┘   └────┬───────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                [3] EXTERNAL API CALLS
                               │
         ┌─────────────────────┴──────────────────────┐
         │                                            │
         ▼                                            ▼
    ┌─────────────┐                         ┌─────────────┐
    │ Vietstock   │                         │  Binance    │
    │ APIs        │                         │  APIs       │
    └─────────────┘                         └─────────────┘
                                 │
                    [4] RAW DATA PROCESSING
                    (Timezone + Price Adjustments)
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│        DataProcessor (Data Transformation Pipeline)                  │
│  - Convert timezone to market timezone (if enabled)                  │
│  - Adjust prices by symbol (if enabled)                              │
│  - Return processed data                                             │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                    [5] CACHE & RETURN RESULT
                                 │
┌────────────────────────────────▼─────────────────────────────────────┐
│          HistoricalDataManager (Final Result)                        │
│  - Cache processed data                                              │
│  - Return to application                                             │
└────────────────────────────────┬─────────────────────────────────────┘
                                 │
                    [6] DOWNSTREAM PROCESSING
                                 │
                ┌────────────────┼────────────────┐
                │                │                │
                ▼                ▼                ▼
        ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
        │  Approaches  │ │  Executors   │ │  Strategies  │
        │  (Analysis)  │ │  (Trading)   │ │  (Logic)     │
        └──────────────┘ └──────────────┘ └──────────────┘
                                 │
                         [7] FINAL RESULT
                                 │
                         Application Output
```

## Key Components

- **HistoricalDataManager**: Cache management, intelligent fetching
- **DataProviderCoordinator**: Provider selection and routing
- **Providers**: Vietstock, Binance API, Binance CCXT
- **DataProcessor**: Timezone conversion, price adjustments
- **Configuration**: Single source of truth in data_provider_settings.py

## Core Components Concepts

### 1. HistoricalDataManager
**Concept:** In-memory cache hub with intelligent fetching
- Manages cache with key: `(symbol, resolution)`
- Decides cache HIT vs MISS automatically
- Fetches missing data segments from Coordinator
- Merges new data with existing cache
- Returns sliced data to application

### 2. DataProviderCoordinator
**Concept:** Provider selection and routing center
- Auto-detects provider from symbol using configuration
- Routes requests to: Vietstock, Binance API, or Binance CCXT
- Standardizes output format (time as index)
- Validates type compatibility

### 3. DataProcessor
**Concept:** Data transformation pipeline
- Applies timezone conversion (UTC → market timezone)
- Applies price adjustments (splits, dividends)
- Both transformations are optional and configurable

### 4. Providers
**Concept:** Data source interfaces (3 implementations)
- **Vietstock Provider:** Vietnamese stocks (VCB, VN30, etc)
- **Binance API Provider:** Crypto pairs (BTCUSDT, ETHUSDT, etc)
- **Binance CCXT Provider:** Crypto pairs via CCXT (BTC/USDT, etc)
- All support resolutions: 1, 5, 15, 30, 60, 240, 1440 minutes

### 5. Configuration System
**Concept:** Single source of truth for settings
- `ENABLED_DATA_PROVIDERS`: List of active providers
- `PROVIDER_SYMBOLS_CONFIG`: Symbol to provider mapping
- `DATA_PROVIDER_CONFIG`: Provider-specific settings

---

## Directory Structure

```
src/stockreports/data_services/
├── _internal/
│   ├── fetching/
│   │   └── _manager.py                  # HistoricalDataManager
│   ├── providing/
│   │   ├── _coordinator.py              # DataProviderCoordinator
│   │   ├── _provider_factory.py         # Provider creation
│   │   ├── _registry.py                 # Provider registration
│   │   ├── _base_provider.py            # Abstract base
│   │   ├── _providers.py                # Provider enum
│   │   └── [provider_implementations]/
│   └── processing/
│       ├── _processor.py                # DataProcessor
│       └── _settings.py                 # Processing config
└── [public_api]/

src/stockreports/data_provider/
├── validation/
│   ├── __init__.py
│   └── symbol_validator.py              # SymbolValidator class
├── vietstock/
│   ├── __init__.py
│   ├── provider.py                      # VietstockProvider
│   └── normalizer.py                    # Vietstock normalization
├── binance/
│   ├── __init__.py
│   ├── api_provider.py                  # BinanceAPIProvider
│   ├── ccxt_provider.py                 # BinanceCCXTProvider
│   └── normalizer.py                    # Binance normalization
└── SYMBOL_VALIDATION_GUIDE.md

src/stockreports/config/
├── data_provider_settings.py            # Provider config & symbols
├── settings.py                          # Main settings
└── loader.py                            # Config loader
```

## Core Components - Detailed Specification

### 1. HistoricalDataManager
**Location:** `src/stockreports/data_services/_internal/fetching/_manager.py`  
**Purpose:** Central cache hub and intelligent data fetching

**Key Methods:**

#### `get(symbol, start_time, end_time) → Optional[pd.DataFrame]`
- Default resolution (None)
- Delegates to `get_with_resolution` with resolution=None

#### `get_with_resolution(symbol, start_time, end_time, resolution) → Optional[pd.DataFrame]`
- **Input:**
  - `symbol`: Stock symbol string
  - `start_time`: pd.Timestamp with timezone
  - `end_time`: pd.Timestamp with timezone
  - `resolution`: Optional int (1, 5, 15, 60, etc)
## Directory Structure

```
src/stockreports/data_services/
├── _internal/
│   ├── fetching/
│   │   └── _manager.py                  # HistoricalDataManager
│   ├── providing/
│   │   ├── _coordinator.py              # DataProviderCoordinator
│   │   ├── _provider_factory.py         # Provider creation
│   │   ├── _registry.py                 # Provider registration
│   │   ├── _base_provider.py            # Abstract base
│   │   ├── _providers.py                # Provider enum
│   │   └── [provider_implementations]/
│   └── processing/
│       ├── _processor.py                # DataProcessor
│       └── _settings.py                 # Processing config

src/stockreports/data_provider/
├── validation/
│   └── symbol_validator.py              # SymbolValidator class
├── vietstock/
│   ├── provider.py                      # VietstockProvider
│   └── normalizer.py                    # Vietstock normalization
├── binance/
│   ├── api_provider.py                  # BinanceAPIProvider
│   ├── ccxt_provider.py                 # BinanceCCXTProvider
│   └── normalizer.py                    # Binance normalization

src/stockreports/config/
├── data_provider_settings.py            # Provider config & symbols
└── loader.py                            # Config loader
```
- **Input:** Raw OHLCV DataFrame from provider
- **Process:**
  1. Check if timezone conversion enabled
  2. If yes: convert to market timezone
  3. Check if price adjustment enabled
  4. If yes: adjust prices by symbol
  5. Return processed data

- **Output:** Transformed DataFrame
- **Handling:** Returns None if any transformation fails

#### `_convert_timezone(df) → pd.DataFrame`
- **Purpose:** Convert UTC to market timezone
- **Method:** Calls `convert_dataframe_to_market_timezone(df)`
- **Configuration:** `settings.is_enabled_timezone_conversion()`
- **Example:**
  - Input: 2026-04-07 13:00:00+00:00 (UTC)
  - Output: 2026-04-07 20:00:00+07:00 (GMT+7)

#### `_adjust_prices(df) → pd.DataFrame`
- **Purpose:** Apply symbol-specific adjustments (splits, dividends)
- **Method:** Calls `adjust_prices_by_symbol(df, symbol)`
- **Configuration:** `settings.is_enabled_price_adjustment()`
- **Example:**
  - Input: Raw OHLCV with stock split
  - Output: Adjusted OHLCV after split factorization

**Settings Structure:**
```python
# In _settings.py
class DataProcessorSettings:
    def is_enabled_timezone_conversion() → bool
    def is_enabled_price_adjustment() → bool
    def get_market_timezone(symbol) → str  # 'UTC+7' for Vietnam
    def get_adjustment_rules(symbol) → Dict
```

---

### 4. Providers (Vietstock, Binance API, Binance CCXT)
**Location:** `src/stockreports/data_provider/*/provider.py`  
**Purpose:** Fetch raw data from external APIs

**Interface (BaseDataProvider):**

#### `fetch_ohlcv(symbol, from_timestamp, to_timestamp, resolution) → pd.DataFrame`
- **Input:**
  - `symbol`: Provider-specific symbol format
  - `from_timestamp`: Unix timestamp (seconds)
  - `to_timestamp`: Unix timestamp (seconds)
  - `resolution`: Candle minutes (1, 5, 15, 60, etc)
  
- **Process:**
  1. Convert resolution to provider's format (if needed)
  2. Make HTTP/API call to external service
  3. Normalize response with provider's Normalizer
  4. Return OHLCV DataFrame

- **Output:** pd.DataFrame with 'time' as index

#### `validate_symbol(symbol) → bool`
- Centralized via SymbolValidator

**Normalizers:**
Each provider has a Normalizer class that converts raw API response to standard OHLCV format:
- `vietstock/normalizer.py` - Vietstock JSON → OHLCV
- `binance/normalizer.py` - Binance API/CCXT → OHLCV

**Supported Symbols by Provider:**

| Provider | Symbols | Count |
|----------|---------|-------|
| Vietstock | VCB, ACB, VN30, VN30F1M, ... | 50+ |
| Binance API | BTCUSDT, ETHUSDT, BNBUSDT, ... | 100+ |
| Binance CCXT | BTC/USDT, ETH/USDT, BNB/USDT, ... | 100+ |

---

### 5. Configuration System
**Location:** `src/stockreports/config/data_provider_settings.py`  
**Purpose:** Single source of truth for provider settings

**Key Configuration:**

#### `ENABLED_DATA_PROVIDERS: List[str]`
- Only place to enable/disable providers
- Example: `["vietstock", "binance_ccxt"]`
- Updates all internal provider configs automatically

#### `PROVIDER_SYMBOLS_CONFIG: Dict`
```python
{
    "vietstock": {
        "name": "vietstock",
        "supported_symbols": ["VCB", "ACB", "VN30", ...],
        "description": "Vietnamese stock market"
    },
    "binance": {
        "name": "binance",
        "supported_symbols": ["BTCUSDT", "ETHUSDT", ...],
        "description": "Binance Spot Trading"
    },
    "binance_ccxt": {
        "name": "binance_ccxt",
        "supported_symbols": ["BTC/USDT", "ETH/USDT", ...],
        "description": "Binance via CCXT"
    }
}
```

#### `DATA_PROVIDER_CONFIG: Dict`
```python
{
    "vietstock": {
        "enabled": True,          # Auto-synced with ENABLED_DATA_PROVIDERS
        "timeout": 15,            # Seconds
        "retries": 3,             # Max attempts
        "cache_ttl": 300,         # Seconds
        "base_url": "...",
        "headers": {...}
    },
    # Similar for binance, binance_ccxt
}
```
## Design Patterns

The architecture uses five core design patterns: **Factory+Registry** (provider instantiation), **Strategy** (provider-specific normalization), **Coordinator** (central orchestration), **Configuration-Driven** (single source of truth), and **Pipeline** (sequential transformations).

## Data Type Compatibility

All data uses a standardized format: `pd.DataFrame` with `pd.DatetimeIndex` named 'time' (with timezone), and OHLCV columns (open, high, low, close, volume as float64). Type validation occurs at the coordinator level before returning data.

## Error Handling Strategy

Errors are handled at four levels: **Provider** (API failures logged with context), **Coordinator** (type validation with detailed messages), **Manager** (fetch failures return None), and **DataProcessor** (transformation failures return None with graceful degradation).

## Cache Management Strategy

Cache uses symbol+resolution tuples as keys and tracks hit/miss patterns to detect when fetches are needed. Full range coverage allows returning cached data; missing segments trigger fetches that are merged with existing cache.

## Integration Points

Applications interact with the system via `HistoricalDataManager.get()` or `get_with_resolution()`. Approaches/Executors iterate over returned data (which has 'time' index and OHLCV columns). Configuration changes only require editing `ENABLED_DATA_PROVIDERS` list.

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Cache lookup | <1ms | Dict key access O(1) |
| Provider detection | ~5ms | Config search O(n providers) |
| Provider instantiation | ~50ms | First time only, then cached |
| Single data fetch | 200-500ms | Depends on external API |
| Multi-provider fetch | 400-1500ms | Sequential execution |
| Timezone conversion | ~50ms | Per 1000 rows |
| Price adjustment | ~30ms | Per 1000 rows |
| Data slicing | <1ms | Index-based, O(1) |

## Version 2.0 Characteristics

Post-Migration Production-Ready Features:
- ✅ Complete data pipeline (request → result)
- ✅ Intelligent caching with miss detection
- ✅ Multi-provider support (3 providers active)
- ✅ Format standardization (time as index)
- ✅ Type compatibility validation
- ✅ Data processing pipeline (timezone + price adjustment)
- ✅ Configuration-driven provider management
- ✅ Graceful error handling with detailed messages
- ✅ Performance optimization (singleton providers, cached instances)
- ✅ Full test coverage (27+ integration tests)
- ✅ Production deployment ready

## Best Practices

### For Using HistoricalDataManager
1. **Always use get_with_resolution() for explicit control**
   ```python
   df = manager.get_with_resolution('VCB', start, end, resolution=1)
   ```

2. **Cache is automatic** - No need to manually manage
   - First request fetches from API
   - Subsequent requests return cached data (if in range)
   - Cache automatically detects missing segments

3. **Timezone handling**
   - Pass timestamps with timezone info
   - Manager and processor handle conversion automatically

### For Coordinator Usage
1. **Always let coordinator auto-detect provider**
   ```python
   coordinator.fetch_ohlcv('VCB', ts1, ts2)  # Auto-detects
   # Not: coordinator.fetch_ohlcv('VCB', ts1, ts2, provider=Provider.VIETSTOCK)
   ```

2. **Check returned data has correct format**
   - Coordinator validates, but verify in code if needed
   - Expected: 'time' index, OHLCV columns, float types

### For Configuration
1. **Only edit ENABLED_DATA_PROVIDERS to enable/disable**
   - Never manually edit 'enabled' fields
   - Let system auto-sync configuration

2. **Provider-specific settings**
   - Timeout, retries, cache_ttl in DATA_PROVIDER_CONFIG
   - Symbols in PROVIDER_SYMBOLS_CONFIG

### For Error Handling
1. **Check for None/empty DataFrame**
   ```python
   df = manager.get_with_resolution(...)
   if df is None or df.empty:
       # Handle missing data
   ```

2. **Type errors are provider bugs**
   - Coordinator raises ValueError if types wrong
   - Should not happen in production
   - If occurs: check provider implementation

## Summary

The Data Services Architecture provides:

1. **Complete Pipeline** - Request → Cache Check → Fetch → Process → Return
2. **Intelligent Caching** - Automatic miss detection and partial fetching
3. **Multi-Provider Support** - Route to appropriate provider automatically
4. **Format Standardization** - Consistent DataFrame format across providers
5. **Data Processing** - Timezone conversion and price adjustments
6. **Configuration Management** - Single source of truth
7. **Error Handling** - Detailed error messages and graceful degradation
8. **Performance** - Singleton providers, cached instances, efficient caching
9. **Extensibility** - Easy to add new providers or processing steps
10. **Production Ready** - Full test coverage, type validation, detailed logging
