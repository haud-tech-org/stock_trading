# Quick Reference - Data Services API

**Location:** `docs/ARCHITECTURE/IMPLEMENTATION_GUIDES/`  
**Purpose:** Quick API reference for data layer developers and users  
**Audience:** Developers using data layer APIs, executors, approaches  
**Status:** Quick Reference ✅

---

## 🚀 Quick Start

### Get OHLCV Data (Most Common)

```python
from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager
import pandas as pd

manager = HistoricalDataManager()

# Fetch 5-minute candles for VCB
df = manager.get_with_resolution(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-07', tz='UTC'),
    resolution=5  # 5-minute candles
)

# Check result
if df is not None and not df.empty:
    print(df)  # Ready to use!
```

---

## 📚 Public API Methods

### HistoricalDataManager

**Import:**
```python
from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager
```

#### Method 1: `get(symbol, start_time, end_time)` → Optional[pd.DataFrame]

**Purpose:** Fetch data with default resolution

**Parameters:**
- `symbol` (str): Symbol to fetch (e.g., 'VCB', 'BTCUSDT', 'BTCUSDT')
- `start_time` (pd.Timestamp): Start of time range
- `end_time` (pd.Timestamp): End of time range

**Returns:** DataFrame or None if not available

**Example:**
```python
df = manager.get(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-07', tz='UTC')
)
```

---

#### Method 2: `get_with_resolution(symbol, start_time, end_time, resolution)` → Optional[pd.DataFrame]

**Purpose:** Fetch data with specific candle resolution

**Parameters:**
- `symbol` (str): Symbol to fetch
- `start_time` (pd.Timestamp): Start of time range
- `end_time` (pd.Timestamp): End of time range
- `resolution` (int): Candle size in minutes

**Supported Resolutions:**
```
1       # 1-minute candles
5       # 5-minute candles
15      # 15-minute candles
30      # 30-minute candles
60      # 1-hour candles
240     # 4-hour candles
1440    # 1-day candles
```

**Returns:** DataFrame or None if not available

**Example:**
```python
# 1-minute candles
df_1m = manager.get_with_resolution('VCB', start, end, 1)

# 5-minute candles
df_5m = manager.get_with_resolution('VCB', start, end, 5)

# 1-hour candles
df_1h = manager.get_with_resolution('BTCUSDT', start, end, 60)
```

---

## 📊 DataFrame Format

**Standardized Output Structure:**

```python
Index:   pd.DatetimeIndex named 'time' (with market timezone)
Columns: ['open', 'high', 'low', 'close', 'volume']
Dtype:   All numeric columns are float64
Timezone: Market timezone (Asia/Ho_Chi_Minh, NOT UTC)
```

**⚠️ IMPORTANT - Timezone:**
- All data returned uses **market timezone** (Asia/Ho_Chi_Minh, +07:00 in Vietnam)
- NOT UTC - this is by design to ensure consistency across all providers
- This is enforced in normalizers with strict validation

**Example Output:**
```
                              open    high     low   close       volume
time                                                                    
2026-04-01 09:00:00+07:00  1768.49 1768.85 1768.30 1768.65  1000000.00
2026-04-01 09:01:00+07:00  1768.65 1769.20 1768.40 1768.99  1200000.00
2026-04-01 09:02:00+07:00  1768.99 1769.50 1768.80 1769.20   900000.00
2026-04-01 09:03:00+07:00  1769.20 1769.80 1769.00 1769.50  1100000.00

# Note: All timestamps have +07:00 timezone (market timezone)
```

**Access Data:**
```python
# By time index
close_price = df.loc['2026-04-01 09:01:00', 'close']

# By row number
first_row = df.iloc[0]
open_price = first_row['open']
high_price = first_row['high']
volume = first_row['volume']

# Iterate
for timestamp, row in df.iterrows():
    time = timestamp
    o = row['open']
    h = row['high']
    l = row['low']
    c = row['close']
    v = row['volume']
```

---

## 🔑 Cache Key Format

The data layer uses cache keys to identify unique datasets:

```python
(symbol, resolution)  # Tuple: (str, Optional[int])
```

**Examples:**
```python
('VCB', None)         # VCB with default resolution
('VCB', 1)            # VCB with 1-minute candles
('VCB', 5)            # VCB with 5-minute candles
('BTCUSDT', 1)        # BTCUSDT (Binance API format) with 1-min
('BTCUSDT', 1)       # BTCUSDT (CCXT format) with 1-min
('VN30F1M', 60)       # VN30F1M (Vietnam index) with 1-hour
```

**For Developers:** Cache keys are used internally by HistoricalDataManager for intelligent miss detection and partial data fetching.

---

## ✅ Common Usage Patterns

### Pattern 1: Analysis Loop (Most Common)

```python
import pandas as pd
from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager

manager = HistoricalDataManager()

# Fetch data
df = manager.get_with_resolution(
    'VCB',
    pd.Timestamp('2026-04-01', tz='UTC'),
    pd.Timestamp('2026-04-07', tz='UTC'),
    resolution=5
)

# Always check for None/empty
if df is None or df.empty:
    print("No data available")
else:
    # Process each candle
    for time_idx, candle in df.iterrows():
        time = time_idx
        open_price = candle['open']
        high_price = candle['high']
        low_price = candle['low']
        close_price = candle['close']
        volume = candle['volume']
        
        # Your analysis logic here
        if close_price > high_price * 0.99:  # Example
            print(f"Alert at {time}: Close near high")
```

### Pattern 2: Multi-Resolution (Different Resolutions)

```python
# Approach might need different resolutions
df_1m = manager.get_with_resolution(symbol, start, end, 1)    # For quick detection
df_5m = manager.get_with_resolution(symbol, start, end, 5)    # For confirmation
df_1h = manager.get_with_resolution(symbol, start, end, 60)   # For trend

# Analyze each resolution
if all([df_1m, df_5m, df_1h]):
    # All resolutions available
    current_1m = df_1m.iloc[-1]    # Last 1-minute candle
    current_5m = df_5m.iloc[-1]    # Last 5-minute candle
    current_1h = df_1h.iloc[-1]    # Last 1-hour candle
```

### Pattern 3: Time Range Slicing

```python
# Get data for specific time range
df = manager.get_with_resolution('VCB', start, end, 1)

# Slice to specific period
specific_time_range = df['2026-04-05 10:00:00':'2026-04-05 15:00:00']

# Get last N candles
last_10_candles = df.tail(10)
last_5_candles = df.tail(5)
```

### Pattern 4: Data Validation

```python
df = manager.get_with_resolution(symbol, start, end, resolution)

# Validate result
if df is None:
    print("ERROR: No data available")
elif df.empty:
    print("ERROR: Empty result")
elif not all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume']):
    print("ERROR: Missing required columns")
elif df[['open', 'high', 'low', 'close', 'volume']].dtype != 'float64':
    print("WARNING: Unexpected data type")
else:
    print("✓ Data is valid and ready to use")
    # Process data
```

---

## 🔍 Supported Symbols

### Vietnam Stock Exchange (Vietstock Provider)

**Sample Symbols:** VCB, ACB, VN30, VN30F1M, VNI, HNX, UPCOM, etc.

**Check All Symbols:**
```python
from src.stockreports.config.data_provider_settings import PROVIDER_SYMBOLS_CONFIG

vietstock_symbols = PROVIDER_SYMBOLS_CONFIG['vietstock']['supported_symbols']
print(vietstock_symbols)  # List of 50+ symbols
```

### Cryptocurrency - Binance API Provider

**Sample Symbols:** BTCUSDT, ETHUSDT, BNBUSDT, etc.

**Check All Symbols:**
```python
from src.stockreports.config.data_provider_settings import PROVIDER_SYMBOLS_CONFIG

binance_symbols = PROVIDER_SYMBOLS_CONFIG['binance']['supported_symbols']
print(binance_symbols)  # List of 100+ symbols
```

### Cryptocurrency - Binance CCXT Provider

**Sample Symbols:** BTCUSDT, ETH/USDT, BNB/USDT, etc.

**Check All Symbols:**
```python
from src.stockreports.config.data_provider_settings import PROVIDER_SYMBOLS_CONFIG

ccxt_symbols = PROVIDER_SYMBOLS_CONFIG['binance_ccxt']['supported_symbols']
print(ccxt_symbols)  # List of 100+ symbols (same assets as API, different format)
```

---

## ⚙️ Configuration

### Check Which Providers Are Enabled

```python
from src.stockreports.config.data_provider_settings import ENABLED_DATA_PROVIDERS

print(ENABLED_DATA_PROVIDERS)
# Output: ['vietstock', 'binance_ccxt']
```

### Enable/Disable Providers

**File:** `src/stockreports/config/data_provider_settings.py`

```python
# Edit this line to enable/disable providers
ENABLED_DATA_PROVIDERS = ["vietstock", "binance_ccxt"]

# To disable Binance CCXT:
ENABLED_DATA_PROVIDERS = ["vietstock"]

# To enable only Binance CCXT:
ENABLED_DATA_PROVIDERS = ["binance_ccxt"]
```

**Effect:** Changes take effect immediately on next manager instantiation (no code restart needed if using singletons).

### Provider Configuration Details

**File:** `src/stockreports/config/data_provider_settings.py`

```python
# Provider-specific settings
DATA_PROVIDER_CONFIG = {
    "vietstock": {
        "enabled": True,           # Auto-synced with ENABLED_DATA_PROVIDERS
        "timeout": 15,             # Seconds to wait for API response
        "retries": 3,              # Max retry attempts on failure
        "cache_ttl": 300,          # Cache valid for 300 seconds
    },
    "binance": {
        "enabled": False,          # Binance API (less common, see binance_ccxt)
        "timeout": 10,
        "retries": 3,
    },
    "binance_ccxt": {
        "enabled": True,           # Recommended Binance provider
        "timeout": 10,
        "retries": 3,
        "cache_ttl": 300,
    }
}
```

---

## ⚡ Performance Tips

| Scenario | Time | Notes |
|----------|------|-------|
| **Cache hit** | <1ms | Data already in memory |
| **Provider detection** | ~5ms | Configuration lookup |
| **First API fetch** | 200-500ms | Depends on external API |
| **Timezone conversion** | ~50ms/1000 rows | If enabled |
| **Price adjustment** | ~30ms/1000 rows | If enabled |
| **Multi-resolution** | 200-1500ms | Fetches for multiple resolutions |

**Optimization Tips:**
1. **Reuse Manager Instance:** Create once, use multiple times
2. **Batch Similar Symbols:** Symbols using same provider together
3. **Avoid Overlapping Ranges:** Request full range once instead of multiple small ranges
4. **Use Caching:** Same symbol + resolution = <1ms on second fetch
5. **Choose Appropriate Resolution:** Don't fetch 1-minute if 5-minute is sufficient

---

## ❌ Error Handling

**Always Check Results:**

```python
df = manager.get_with_resolution(symbol, start, end, resolution)

# Handle None (no data)
if df is None:
    print("ERROR: No data available for this symbol/range")
    # Check:
    # - Symbol is in PROVIDER_SYMBOLS_CONFIG
    # - Provider for symbol is in ENABLED_DATA_PROVIDERS
    # - Date range is valid
    # - API is accessible
    return None

# Handle empty (data exists but range has no candles)
if df.empty:
    print("WARNING: Data exists but no candles in this range")
    # Check:
    # - Time range falls in trading hours
    # - Date range doesn't have holidays
    return None

# Handle successfully
return df
```

**Common Issues:**

1. **"None returned - symbol not found"**
   - Verify symbol in PROVIDER_SYMBOLS_CONFIG
   - Check symbol format (e.g., 'BTCUSDT' vs 'BTCUSDT')

2. **"Empty DataFrame - no data for range"**
   - Check if range is during trading hours
   - Try a known trading date

3. **"Different columns than expected"**
   - Verify OHLCV columns: open, high, low, close, volume
   - Check data type: all should be float64

---

## � Context Manager Usage (For Providers)

All data providers support the context manager pattern for safe resource cleanup:

```python
# Using a provider directly (normally done by coordinator)
from src.stockreports.data_services._internal.providing._provider_factory import get_provider

provider = get_provider('VCB')

# Context manager ensures cleanup
with provider:
    ohlcv = provider.fetch_ohlcv('VCB', from_ts, to_ts, resolution)
# Cleanup called automatically on exit ✅

# Even if error occurs, cleanup still happens
try:
    with provider:
        data = provider.fetch_ohlcv(...)
except Exception as e:
    print(f"Error: {e}")
# Cleanup still called despite exception ✅
```

**Why This Matters:**
- Prevents 1-2 hour connection timeouts
- Guarantees resource cleanup (connections, sessions, etc.)
- Makes monitoring loop reliable for 24+ hours
- Exception-safe (cleanup even on errors)

**For Developers:**
If you're implementing a new provider, see `CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md` for step-by-step instructions on implementing context managers.

---

## �🔗 Related Documentation

**See Also:**
- 👉 [TECHNICAL_REFERENCE/DATA_LAYER_ARCHITECTURE.md](../TECHNICAL_REFERENCE/DATA_LAYER_ARCHITECTURE.md) - Complete 7-step pipeline architecture
- 👉 [IMPLEMENTATION_GUIDES/DATA_PROVIDER_EXTENSION_GUIDE.md](./DATA_PROVIDER_EXTENSION_GUIDE.md) - How to add new providers
- 👉 [TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md](../TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md) - System architecture (Component 1.10 covers data layer)

---

## 📞 Quick Reference Table

| Task | Code |
|------|------|
| **Import** | `from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager` |
| **Create manager** | `manager = HistoricalDataManager()` |
| **Get with resolution** | `df = manager.get_with_resolution(symbol, start, end, resolution)` |
| **Get with default** | `df = manager.get(symbol, start, end)` |
| **Check for data** | `if df is not None and not df.empty:` |
| **Last candle** | `latest = df.iloc[-1]` |
| **Last N candles** | `last_n = df.tail(n)` |
| **Iterate candles** | `for time, row in df.iterrows():` |
| **List providers** | `from src.stockreports.config.data_provider_settings import ENABLED_DATA_PROVIDERS` |
| **List symbols** | `from src.stockreports.config.data_provider_settings import PROVIDER_SYMBOLS_CONFIG` |

---

**Version:** 2.0 (Post-Migration)  
**Status:** ✅ Production Ready  
**Last Updated:** April 10, 2026

