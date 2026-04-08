# Data Services Documentation (v2.0 - Post-Migration)

**Status:** Production Ready ✅  
**Last Updated:** April 7, 2026

---

## 🔗 Related Code

- **Manager:** `src/stockreports/data_services/_internal/fetching/_manager.py`
- **Coordinator:** `src/stockreports/data_services/_internal/providing/_coordinator.py`
- **Processor:** `src/stockreports/data_services/_internal/processing/_processor.py`
- **Providers:** `src/stockreports/data_provider/*/provider.py`
- **Configuration:** `src/stockreports/config/data_provider_settings.py`
- **Tests:** `tests/data_provider/` and `tests/data_services/`s is the essential documentation for the Data Services layer - a complete data pipeline from request to result, integrating multiple data sources (Vietstock, Binance API, Binance CCXT) with intelligent caching and data processing.

## 📚 Documentation Files

| Document | Purpose |
|----------|---------|
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | System overview, components, design patterns, data flow diagram |
| **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)** | API methods, usage examples, common patterns |
| **[README.md](./README.md)** | This file - quick start and navigation |

---

## 🎯 Quick Start by Task

### "I need to use HistoricalDataManager to get data"
```python
from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager
import pandas as pd

manager = HistoricalDataManager()
df = manager.get_with_resolution(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-07', tz='UTC'),
    resolution=1  # 1-minute candles
)
# Returns: DataFrame with 'time' index and OHLCV columns
```

### "I want to understand the architecture"
→ See [ARCHITECTURE.md](./ARCHITECTURE.md) - High-Level Data Flow section with complete system diagram

### "I need API reference and examples"
→ See [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - All methods and patterns

### "I need to configure providers"
→ Edit `src/stockreports/config/data_provider_settings.py`:
```python
ENABLED_DATA_PROVIDERS = ["vietstock", "binance_ccxt"]  # Enable/disable providers
```

---

## 🏗️ System Overview

The system provides a 7-step data pipeline:

1. **Request Data** - Application requests OHLCV data
2. **Cache Check** - HistoricalDataManager checks if data exists
3. **Provider Routing** - DataProviderCoordinator auto-detects provider
4. **External API Call** - Provider fetches from Vietstock/Binance
5. **Processing** - DataProcessor applies timezone conversion and price adjustments
6. **Cache Storage** - HistoricalDataManager caches result
7. **Return to Application** - Final standardized DataFrame returned

**See:** [ARCHITECTURE.md](./ARCHITECTURE.md) for complete diagram

---

## 🔑 Key Concepts

**Cache Key:** `(symbol, resolution)` tuple identifying unique dataset  
**Data Format:** `pd.DataFrame` with `pd.DatetimeIndex` named 'time' and OHLCV columns  
**Providers:** 3 implementations (Vietstock, Binance API, Binance CCXT)  
**Processing:** Optional timezone conversion and price adjustments  
**Configuration:** Single source of truth in `data_provider_settings.py`

---

## 📖 Documentation Details

### [ARCHITECTURE.md](./ARCHITECTURE.md)
- High-level data flow diagram with all 7 steps
- Core components (HistoricalDataManager, Coordinator, Processor, Providers)
- Design patterns used (Factory+Registry, Strategy, Coordinator, etc)
- Data type format and validation
- Error handling strategy
- Cache management approach
- Integration points
- Performance characteristics

### [QUICK_REFERENCE.md](./QUICK_REFERENCE.md)
- All public API methods
- Cache key format
- Common usage patterns
- Quick lookup reference

---

## ✅ Production Ready Features

- ✅ Complete data pipeline (request → result)
- ✅ Intelligent caching with miss detection
- ✅ Multi-provider support (Vietstock, Binance API, Binance CCXT)
- ✅ Format standardization (time as index, OHLCV columns)
- ✅ Type compatibility validation
- ✅ Data processing (timezone conversion, price adjustments)
- ✅ Configuration-driven provider management
- ✅ Graceful error handling
- ✅ Performance optimization (singleton providers, cached instances)
- ✅ Full test coverage (27+ integration tests)

---

## 📊 System Stats

| Item | Value |
|------|-------|
| Providers | 3 (Vietstock, Binance API, Binance CCXT) |
| Supported Symbols | 150+ |
| Cache Key | (symbol, resolution) tuple |
| Pipeline Steps | 7 (request → cache check → fetch → process → return) |
| Data Format | pd.DataFrame with DatetimeIndex |
| Processing Steps | 2 (timezone, price adjustment) |
| Test Coverage | 27+ integration tests |

---

## � Related Code
