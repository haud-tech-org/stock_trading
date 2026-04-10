# Data Layer Architecture (v2.0) - Complete Data Services Pipeline

**Location:** `docs/ARCHITECTURE/TECHNICAL_REFERENCE/`  
**Purpose:** Understanding the complete data pipeline as foundational system layer  
**Audience:** All developers (data layer is prerequisite for understanding system)  
**Status:** Production Ready ✅

---

## 📊 Overview

The **Data Layer** is the foundational subsystem providing a complete data pipeline from API request to processed OHLCV output. It integrates three data sources (Vietstock, Binance API, Binance CCXT) with intelligent caching, format standardization, and optional data processing.

**Key Responsibility:** Supply standardized OHLCV data to all other system components (alert system, executors, strategies).

---

## 🔄 7-Step Data Flow Diagram

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

---

## 🏗️ Core Components

### Component 1: HistoricalDataManager
**Purpose:** Central cache hub with intelligent data fetching  
**Location:** `src/stockreports/data_services/_internal/fetching/_manager.py`

**Responsibilities:**
- Manages in-memory cache with key: `(symbol, resolution)`
- Detects cache hits vs misses automatically
- Fetches missing data segments from Coordinator
- Merges new data with existing cache
- Processes and returns sliced data to application

**Key Methods:**
```python
# Get data with default resolution
get(symbol, start_time, end_time) → Optional[pd.DataFrame]

# Get data with specific resolution  
get_with_resolution(symbol, start_time, end_time, resolution) → Optional[pd.DataFrame]
```

**Cache Strategy:**
- Cache key: `(symbol, resolution)` tuple
- Full range coverage detection: checks if cached range covers requested range
- Partial fetch: if missing segments detected, fetches only missing parts
- Automatic merge: combines new and cached data
- Returns: sliced data for requested time range

---

### Component 2: DataProviderCoordinator
**Purpose:** Provider selection and routing center  
**Location:** `src/stockreports/data_services/_internal/providing/_coordinator.py`

**Responsibilities:**
- Auto-detects provider from symbol using configuration
- Routes requests to: Vietstock, Binance API, or Binance CCXT
- Standardizes output format (time as DatetimeIndex)
- Validates type compatibility (correct columns, dtypes)
- Returns standardized OHLCV data

**Provider Routing Logic:**
```
Input: symbol (e.g., 'VCB', 'BTCUSDT')
  ↓
Lookup in PROVIDER_SYMBOLS_CONFIG
  ├─ If symbol in vietstock list → VietstockProvider
  ├─ If symbol in binance list → BinanceAPIProvider
  └─ If symbol in binance_ccxt list → BinanceCCXTProvider
  ↓
Provider fetches and normalizes data
  ↓
Coordinator validates format
  ├─ Index must be DatetimeIndex named 'time'
  ├─ Columns must be [open, high, low, close, volume]
  ├─ All values must be float64
  └─ Return or raise ValueError if invalid
```

---

### Component 3: DataProcessor
**Purpose:** Data transformation pipeline  
**Location:** `src/stockreports/data_services/_internal/processing/_processor.py`

**Responsibilities:**
- Applies timezone conversion (UTC → market timezone)
- Applies price adjustments (stock splits, dividends)
- Both transformations are optional and configurable
- Returns None if any transformation fails

**Processing Pipeline:**
1. **Timezone Conversion** (if enabled)
   - Convert from UTC to market timezone
   - Example: 2026-04-07 13:00:00+00:00 UTC → 2026-04-07 20:00:00+07:00 (Vietnam)

2. **Price Adjustment** (if enabled)
   - Apply symbol-specific adjustments
   - Example: Adjust for 2:1 stock split

**Configuration:**
```python
# Enable/disable transformations
is_enabled_timezone_conversion() → bool
is_enabled_price_adjustment() → bool

# Market timezone for symbol
get_market_timezone(symbol) → str  # 'UTC+7' for Vietnam
```

---

### Component 4: Data Providers (3 Implementations)
**Purpose:** Fetch raw OHLCV data from external APIs

**Provider 1: VietstockProvider**
- **Data Source:** Vietstock API (Vietnam Stock Exchange)
- **Symbols:** Vietnamese stocks (VCB, ACB, VN30, VN30F1M, etc.)
- **Count:** 50+ symbols
- **Resolutions:** 1, 5, 15, 30, 60, 240, 1440 minutes
- **Location:** `src/stockreports/data_provider/vietstock/provider.py`

**Provider 2: BinanceAPIProvider**
- **Data Source:** Binance REST API
- **Symbols:** Cryptocurrency pairs (BTCUSDT, ETHUSDT, etc.)
- **Count:** 100+ symbols
- **Resolutions:** 1, 5, 15, 30, 60, 240, 1440 minutes
- **Location:** `src/stockreports/data_provider/binance/api_provider.py`

**Provider 3: BinanceCCXTProvider**
- **Data Source:** Binance via CCXT library (unified crypto interface)
- **Symbols:** Cryptocurrency pairs (BTC/USDT, ETH/USDT, etc.)
- **Count:** 100+ symbols (same assets as API provider, different format)
- **Resolutions:** Same as API provider
- **Location:** `src/stockreports/data_provider/binance/ccxt_provider.py`

**Provider Interface (BaseDataProvider):**
```python
fetch_ohlcv(symbol, from_timestamp, to_timestamp, resolution) → pd.DataFrame
validate_symbol(symbol) → bool
```

**Normalizers:**
Each provider includes a normalizer to convert raw API response to standard OHLCV format:
- `vietstock/normalizer.py` - Vietstock JSON → OHLCV DataFrame
- `binance/normalizer.py` - Binance API/CCXT → OHLCV DataFrame

---

### Component 5: Configuration System
**Purpose:** Single source of truth for provider settings  
**Location:** `src/stockreports/config/data_provider_settings.py`

**Key Configuration:**

**ENABLED_DATA_PROVIDERS**
```python
ENABLED_DATA_PROVIDERS = ["vietstock", "binance_ccxt"]
# Only edit this to enable/disable providers
# All internal configs auto-sync from this list
```

**PROVIDER_SYMBOLS_CONFIG**
```python
{
    "vietstock": {
        "name": "vietstock",
        "supported_symbols": ["VCB", "ACB", "VN30", ...],  # 50+ symbols
        "description": "Vietnamese stock market"
    },
    "binance": {
        "name": "binance",
        "supported_symbols": ["BTCUSDT", "ETHUSDT", ...],  # 100+ symbols
        "description": "Binance Spot Trading"
    },
    "binance_ccxt": {
        "name": "binance_ccxt",
        "supported_symbols": ["BTC/USDT", "ETH/USDT", ...],  # 100+ symbols
        "description": "Binance via CCXT"
    }
}
```

**DATA_PROVIDER_CONFIG**
```python
{
    "vietstock": {
        "enabled": True,          # Auto-synced with ENABLED_DATA_PROVIDERS
        "timeout": 15,            # Seconds
        "retries": 3,             # Max attempts
        "cache_ttl": 300,         # Seconds
        "base_url": "https://api.vietstock.vn/...",
        "headers": {...}
    },
    # Similar configs for binance, binance_ccxt
}
```

---

## 🎯 Design Patterns Used

### Pattern 1: Factory + Registry
**Purpose:** Create and manage provider instances  
**Implementation:**
- `_provider_factory.py` - Creates provider instances
- `_registry.py` - Maintains singleton instances
- `_providers.py` - Provider enum with all types

**Benefit:** New providers can be added without changing coordinator

### Pattern 2: Strategy Pattern
**Purpose:** Normalize data from different providers  
**Implementation:** Each provider has normalizer (VietstockNormalizer, BinanceNormalizer)  
**Benefit:** Provider-specific logic isolated, easy to maintain

### Pattern 3: Coordinator Pattern
**Purpose:** Central orchestration of multiple providers  
**Implementation:** DataProviderCoordinator routes to appropriate provider  
**Benefit:** Simple public interface, provider selection logic centralized

### Pattern 4: Configuration-Driven Design
**Purpose:** Control behavior via settings, not code  
**Implementation:** ENABLED_DATA_PROVIDERS list controls which providers are active  
**Benefit:** Enable/disable providers without code changes

### Pattern 5: Pipeline Pattern
**Purpose:** Sequential data transformations  
**Implementation:** HistoricalDataManager → Coordinator → Provider → Processor → Application  
**Benefit:** Clear separation of concerns, each step is independent

---

## 📊 Data Format Specification

### Standard OHLCV DataFrame Format

**Required Structure:**
```python
pd.DataFrame with:
  Index:     pd.DatetimeIndex named 'time' (with timezone)
  Columns:   ['open', 'high', 'low', 'close', 'volume']
  Dtypes:    open/high/low/close/volume = float64
  Timezone:  UTC or market-specific timezone
```

**Example:**
```python
                              open    high     low   close    volume
time                                                                 
2026-04-07 09:00:00+07:00  1768.49 1768.85 1768.30 1768.65  1000000
2026-04-07 09:01:00+07:00  1768.65 1769.20 1768.40 1768.99  1200000
2026-04-07 09:02:00+07:00  1768.99 1769.50 1768.80 1769.20   900000
```

### Cache Key Format
```python
(symbol: str, resolution: Optional[int]) → tuple

Examples:
  ('VCB', None)           # VCB with default resolution
  ('VCB', 1)              # VCB with 1-minute candles
  ('BTCUSDT', 5)          # BTC/USDT with 5-minute candles
  ('BTC/USDT', 60)        # BTC/USDT with 1-hour candles
```

---

## ⚙️ Error Handling Strategy

### Level 1: Provider Errors
- API call failures
- Network timeouts
- Invalid response format
- **Action:** Log with context, raise exception

### Level 2: Coordinator Errors
- Type validation failures
- Provider not found
- Format mismatch
- **Action:** Raise ValueError with detailed message

### Level 3: Manager Errors
- Cache miss and fetch fails
- Processor returns None
- **Action:** Return None to caller

### Level 4: DataProcessor Errors
- Timezone conversion fails
- Price adjustment fails
- **Action:** Return None (graceful degradation)

---

## 📈 Performance Characteristics

| Operation | Time | Complexity | Notes |
|-----------|------|-----------|-------|
| **Cache lookup** | <1ms | O(1) | Dict key access |
| **Provider detection** | ~5ms | O(n providers) | Config search |
| **Provider creation** | ~50ms | O(1) | First time only, then cached |
| **Single API fetch** | 200-500ms | O(1) | Depends on external API |
| **Multi-provider fetch** | 400-1500ms | O(n providers) | Sequential execution |
| **Timezone conversion** | ~50ms | O(rows) | Per 1000 rows |
| **Price adjustment** | ~30ms | O(rows) | Per 1000 rows |
| **Data slicing** | <1ms | O(1) | Index-based |

---

## ✅ Integration with Alert System

### Data Flow to Alert System
```
HistoricalDataManager (Data Layer)
  ↓
Returns: pd.DataFrame with OHLCV data
  ↓
SymbolAlerter (Alert System)
  ├─ ResolutionCoordinator maps approach → resolution
  ├─ Selects data for specific resolution
  ├─ Passes to executors
  └─ Executors analyze data
```

### Key Integration Points
1. **Data Provider:** Executors call `manager.get_with_resolution()` for OHLCV
2. **Format Contract:** Always get `pd.DataFrame` with `time` index + OHLCV columns
3. **Multi-resolution:** Each executor can request different resolution
4. **Caching Benefit:** Shared cache across all executors for same symbol

---

## 🚀 Production Ready Features

- ✅ Complete data pipeline (7 steps: request → cache → fetch → process → return)
- ✅ Intelligent caching with miss detection
- ✅ Multi-provider support (3 providers: Vietstock, Binance API, Binance CCXT)
- ✅ Format standardization (time as DatetimeIndex, OHLCV columns)
- ✅ Type compatibility validation (coordinator validates dtypes)
- ✅ Data processing pipeline (timezone conversion, price adjustments)
- ✅ Configuration-driven provider management (single source of truth)
- ✅ Graceful error handling with detailed messages (returns None on failure)
- ✅ Performance optimization (singleton providers, cached instances)
- ✅ Full test coverage (27+ integration tests, validated)

---

## 📋 Configuration Quick Start

**Enable/Disable Providers:**
```python
# Edit: src/stockreports/config/data_provider_settings.py
ENABLED_DATA_PROVIDERS = ["vietstock", "binance_ccxt"]  # Your choices
```

**Add New Symbols:**
```python
# Edit: PROVIDER_SYMBOLS_CONFIG in data_provider_settings.py
"vietstock": {
    "supported_symbols": ["VCB", "ACB", "NEW_SYMBOL", ...],
}
```

**Enable/Disable Data Processing:**
```python
# Timezone conversion
is_enabled_timezone_conversion() → bool  # Edit in settings

# Price adjustments
is_enabled_price_adjustment() → bool     # Edit in settings
```

---

## 🔗 Related Documentation

**See Also:**
- 👉 [TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md](./DEEP_DIVE_FINDINGS.md) - Complete system architecture (9 components)
- 👉 [IMPLEMENTATION_GUIDES/DATA_PROVIDER_EXTENSION_GUIDE.md](../IMPLEMENTATION_GUIDES/DATA_PROVIDER_EXTENSION_GUIDE.md) - How to add new provider
- 👉 [IMPLEMENTATION_GUIDES/DATA_SERVICES_QUICK_REFERENCE.md](../IMPLEMENTATION_GUIDES/DATA_SERVICES_QUICK_REFERENCE.md) - API quick reference

---

**Version:** 2.0 (Post-Migration)  
**Status:** ✅ Production Ready  
**Last Updated:** April 10, 2026
