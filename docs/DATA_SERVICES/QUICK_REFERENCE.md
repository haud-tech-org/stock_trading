# Quick Reference - Data Services API

## Public API Methods

### HistoricalDataManager

```python
from src.stockreports.data_services._internal.fetching._manager import HistoricalDataManager

manager = HistoricalDataManager()
```

#### `get(symbol, start_time, end_time) → Optional[pd.DataFrame]`
Fetch data with default resolution (None)

```python
df = manager.get(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-07', tz='UTC')
)
```

#### `get_with_resolution(symbol, start_time, end_time, resolution) → Optional[pd.DataFrame]`
Fetch data with specific resolution

```python
df = manager.get_with_resolution(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-07', tz='UTC'),
    resolution=1  # 1-minute candles
)
# Supported resolutions: 1, 5, 15, 30, 60, 240, 1440 minutes
```

**Returns:** `pd.DataFrame` with:
- **Index:** `pd.DatetimeIndex` named 'time' (with timezone)
- **Columns:** open, high, low, close, volume (float64)
- **Returns None:** if no data available

---

## Cache Key Format

```python
(symbol, resolution)  # Tuple identifying unique dataset

# Examples:
('VCB', None)        # VCB with default resolution
('VCB', 1)           # VCB with 1-minute candles
('BTC/USDT', 5)      # BTC/USDT with 5-minute candles
('VN30F1M', 1)       # VN30F1M with 1-minute candles
```

---

## Common Patterns

### Get data for analysis
```python
df = manager.get_with_resolution('VCB', start, end, resolution=5)
if df is not None and not df.empty:
    for idx, row in df.iterrows():
        time = idx  # pd.Timestamp
        o, h, l, c, v = row['open'], row['high'], row['low'], row['close'], row['volume']
        # Analysis logic
```

### Get data for charting
```python
df = manager.get_with_resolution('BTC/USDT', start, end, resolution=1)
# df.index is time, suitable for plotting
```

### Check what providers are enabled
```python
from src.stockreports.config.data_provider_settings import ENABLED_DATA_PROVIDERS
print(ENABLED_DATA_PROVIDERS)  # ['vietstock', 'binance_ccxt']
```

### View supported symbols
```python
from src.stockreports.config.data_provider_settings import PROVIDER_SYMBOLS_CONFIG
print(PROVIDER_SYMBOLS_CONFIG['vietstock']['supported_symbols'])
print(PROVIDER_SYMBOLS_CONFIG['binance_ccxt']['supported_symbols'])
```

---

## Data Format

**DataFrame Structure:**
```
Index: time (pd.DatetimeIndex with timezone)
Columns:
  - open:   float64 (opening price)
  - high:   float64 (highest price)
  - low:    float64 (lowest price)
  - close:  float64 (closing price)
  - volume: float64 (trading volume)

Example:
                          open    high     low   close  volume
time                                                           
2026-04-01 09:30:00+07:00 100.5  101.0   100.0  100.8   1000.0
2026-04-01 09:31:00+07:00 100.8  101.2   100.5  101.0   1500.0
```

---

## Error Handling

**Always check for None/empty:**
```python
df = manager.get_with_resolution(symbol, start, end, resolution)
if df is None:
    print("No data available")
elif df.empty:
    print("Empty result")
else:
    # Process data
    pass
```

---

## Configuration

**Enable/Disable Providers:**
Edit `src/stockreports/config/data_provider_settings.py`

```python
ENABLED_DATA_PROVIDERS = ["vietstock", "binance_ccxt"]  # Remove "binance" to disable
```

No code changes needed - Coordinator auto-adjusts.

---

## Performance

| Operation | Time |
|-----------|------|
| Cache lookup | <1ms |
| Provider detection | ~5ms |
| Single API fetch | 200-500ms |
| Timezone conversion | ~50ms per 1000 rows |
| Price adjustment | ~30ms per 1000 rows |

---

## For More Details

- **Architecture:** [ARCHITECTURE.md](./ARCHITECTURE.md)
- **Overview:** [README.md](./README.md)
