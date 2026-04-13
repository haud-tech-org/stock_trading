# Timezone Consistency Guide for Data Providers

**Date:** April 11, 2026  
**Status:** Critical Implementation Guide  
**Audience:** Data provider developers, anyone extending the data layer  
**Priority:** ⚠️ CRITICAL - Failure to follow causes cascading TypeErrors

---

## 📌 Summary

All data providers in the system MUST convert timestamps to **market timezone** (Asia/Ho_Chi_Minh), NOT UTC. This ensures consistent data structures across all providers and prevents cascading TypeErrors downstream.

**The Problem:** When one provider uses UTC and another uses market timezone, downstream code expecting uniform data structures will fail with cryptic errors like: "int() argument must be a string, a bytes-like object or a real number, not 'Timestamp'"

---

## ✅ The Correct Pattern

### In Normalizer's `normalize()` Method

```python
import pandas as pd
import pytz
from src.stockreports.utils.time_utils import get_market_timezone_str

class YourProviderNormalizer:
    def __init__(self):
        """Initialize normalizer with market timezone."""
        self.market_tz = pytz.timezone(get_market_timezone_str())
    
    def normalize(self, raw_data, symbol):
        """
        Normalize raw data to standard OHLCV format.
        
        CRITICAL: Convert to market timezone, NOT UTC
        """
        # Extract timestamps from API response
        timestamps_sec = [...]  # Unix timestamps in seconds
        
        # Step 1: Localize to UTC
        datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
        
        # Step 2: Convert to MARKET TIMEZONE
        datetimes = datetimes.tz_convert(self.market_tz)  # ← CRITICAL LINE
        
        # Step 3: Create DataFrame with market-timezone index
        df = pd.DataFrame({
            'time': datetimes,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        # Step 4: Set time as index
        df.set_index('time', inplace=True)
        
        # Step 5: Validate
        self.validate_ohlcv(df)
        
        return df
```

### In Normalizer's `validate_ohlcv()` Method

```python
def validate_ohlcv(self, df: pd.DataFrame) -> bool:
    """
    Validate that DataFrame meets OHLCV requirements.
    
    CRITICAL: Check timezone matches market timezone, not just existence
    """
    # Check required columns
    required_columns = ['open', 'high', 'low', 'close', 'volume']
    missing_cols = [c for c in required_columns if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Check index is DatetimeIndex
    if not isinstance(df.index, pd.DatetimeIndex):
        raise ValueError("Index must be DatetimeIndex")
    
    # CRITICAL: Check timezone matches market timezone
    market_tz_str = get_market_timezone_str()
    if str(df.index.tz) != market_tz_str:
        raise ValueError(
            f"Index timezone must be {market_tz_str}, got {df.index.tz}"
        )
    
    # Check no NaN values
    if df[required_columns].isnull().any().any():
        nan_info = df[required_columns].isnull().sum()
        raise ValueError(f"Found NaN values: {nan_info[nan_info > 0].to_dict()}")
    
    return True
```

---

## ❌ Common Mistakes

### Mistake 1: Forgetting `tz_convert()`

```python
# ❌ WRONG - Stops at UTC
timestamps_sec = [...]
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
df = pd.DataFrame({'time': datetimes, ...})
# Index has UTC timezone, not market timezone!
# Downstream code will fail with TypeErrors

# ✅ CORRECT - Converts to market timezone
timestamps_sec = [...]
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)  # Convert!
df = pd.DataFrame({'time': datetimes, ...})
# Index has market timezone, consistent with other providers
```

### Mistake 2: Not Localizing Before Converting

```python
# ❌ WRONG - Missing localize step
timestamps_ms = [...]
timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
datetimes = pd.to_datetime(timestamps_sec, unit='s')
# No timezone info yet - will fail if you try to convert

# ✅ CORRECT - Localize to UTC first, then convert
timestamps_ms = [...]
timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)  # UTC first
datetimes = datetimes.tz_convert(self.market_tz)  # Then convert
```

### Mistake 3: Only Checking Timezone Exists

```python
# ❌ WRONG - Only checks existence
if df.index.tz is None:
    raise ValueError("Must have timezone")
# But doesn't check if it's the CORRECT timezone!
# Could still be UTC instead of market timezone

# ✅ CORRECT - Checks it's the correct timezone
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(
        f"Index timezone must be {market_tz_str}, got {df.index.tz}"
    )
```

### Mistake 4: Mixing UTC and Market Timezone Between Providers

```python
# ❌ WRONG - Provider 1 uses UTC, Provider 2 uses market timezone
# Provider1Normalizer:
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)  # UTC only
# Missing: datetimes.tz_convert(self.market_tz)

# Provider2Normalizer:
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)  # Market timezone
# Result: Inconsistent data structures cause downstream TypeErrors

# ✅ CORRECT - All providers use same pattern
# Both Provider1Normalizer and Provider2Normalizer:
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)  # ALL providers do this
# Result: Consistent data structures across entire system
```

---

## 📍 Real-World Example: The Binance Bug

This guide was created after discovering that the Binance normalizer was missing the `tz_convert()` call:

**Before Fix (Buggy Code):**
```python
# In BinanceNormalizer.normalize() - lines 80-82 (BEFORE FIX)
timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
# Missing: datetimes = datetimes.tz_convert(self.market_tz)

# This created UTC-indexed DataFrames instead of market-timezone-indexed
# Result in downstream executor: TypeError
# "int() argument must be a string, a bytes-like object or a real number, not 'Timestamp'"
```

**After Fix (Correct Code):**
```python
# In BinanceNormalizer.normalize() - lines 80-87 (AFTER FIX)
timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
# NOW: Converts to market timezone (CRITICAL FIX)
datetimes = datetimes.tz_convert(self.market_tz)

# And validation was also fixed to check correctness:
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(f"Index timezone must be {market_tz_str}, got {df.index.tz}")

# Result: Consistent with Vietstock provider, no TypeErrors
```

---

## 🔍 Implementation Verification

### Verify Your Provider

When implementing a new provider, verify it follows the pattern:

```bash
# Check 1: Normalizer creates market-timezone index
grep -n "tz_convert" your_provider/normalizer.py
# Should find line with: datetimes.tz_convert(self.market_tz)

# Check 2: Validation checks correct timezone
grep -n "market_tz_str" your_provider/normalizer.py
grep -n "str(df.index.tz)" your_provider/normalizer.py
# Should find validation comparing timezone strings

# Check 3: Test output
python3 -c "
from your_provider.normalizer import YourNormalizer
normalizer = YourNormalizer()
df = normalizer.normalize(raw_data, 'TEST')
print(f'Timezone: {df.index.tz}')
print(f'Expected: Asia/Ho_Chi_Minh')
# Should print: Timezone: Asia/Ho_Chi_Minh
"
```

### Unit Test Template

```python
def test_normalizer_timezone_market_not_utc():
    """CRITICAL: Verify normalizer uses market timezone, not UTC."""
    normalizer = YourProviderNormalizer()
    
    # Create sample data
    now_ms = int(datetime.now().timestamp() * 1000)
    raw_data = [[now_ms, "1000", "1001", "999", "1000", "100"]]
    
    # Normalize
    df = normalizer.normalize(raw_data, 'TEST')
    
    # CRITICAL: Check timezone is market timezone, NOT UTC
    assert str(df.index.tz) == 'Asia/Ho_Chi_Minh', \
        f"Expected Asia/Ho_Chi_Minh but got {df.index.tz}"
    assert str(df.index.tz) != 'UTC', \
        "Must use market timezone, not UTC"
```

---

## 📋 Checklist for Provider Implementation

- [ ] Normalizer `__init__()` initializes market timezone:
  ```python
  self.market_tz = pytz.timezone(get_market_timezone_str())
  ```

- [ ] Normalizer `normalize()` method converts to market timezone:
  ```python
  datetimes = datetimes.tz_convert(self.market_tz)
  ```

- [ ] Normalizer `validate_ohlcv()` checks timezone matches market timezone:
  ```python
  market_tz_str = get_market_timezone_str()
  if str(df.index.tz) != market_tz_str:
      raise ValueError(...)
  ```

- [ ] Unit test verifies market timezone (not UTC):
  ```python
  assert str(df.index.tz) == 'Asia/Ho_Chi_Minh'
  ```

- [ ] Integration test verifies consistency with other providers

---

## 🎯 Why This Matters

### Problem Chain
1. Provider A returns UTC-indexed DataFrame
2. Provider B returns market-timezone-indexed DataFrame
3. Downstream code expects all providers to return same structure
4. Code tries to convert index to int: `int(df.index[0])`
5. UTC-indexed DataFrame returns pd.Timestamp, int() fails
6. Market-timezone-indexed DataFrame also returns pd.Timestamp, but type error reveals inconsistency

### Solution
All providers return market-timezone-indexed DataFrames:
- ✅ Code expects pd.Timestamp objects with market timezone
- ✅ Consistent behavior across all providers
- ✅ Time-based filtering and indexing work correctly
- ✅ Errors are caught at validation time, not downstream

---

## 📚 References

**Normalizer Implementation:**
- Vietstock: `src/stockreports/data_services/_internal/providing/vietstock/normalizer.py` (lines 104-106)
- Binance: `src/stockreports/data_services/_internal/providing/binance/normalizer.py` (lines 86-87)

**Validation:**
- Vietstock: `src/stockreports/data_services/_internal/providing/vietstock/normalizer.py` (lines 224-230)
- Binance: `src/stockreports/data_services/_internal/providing/binance/normalizer.py` (lines 205-209)

**Timezone Utilities:**
- `src/stockreports/utils/time_utils.py` (get_market_timezone_str, get_market_timezone)

---

## 🆘 Troubleshooting

### Error: "int() argument must be a string, a bytes-like object or a real number, not 'Timestamp'"

**Diagnosis:** One provider is returning UTC-indexed DataFrame, another is returning market-timezone-indexed

**Fix:** Ensure ALL normalizers follow the pattern:
```python
datetimes = datetimes.tz_convert(self.market_tz)  # Convert to market timezone
```

### Error: "Index timezone must be Asia/Ho_Chi_Minh, got UTC"

**Diagnosis:** Normalizer is not converting to market timezone

**Fix:** Add the missing `tz_convert()` call in `normalize()` method

### Error: "Index timezone must be Asia/Ho_Chi_Minh, got None"

**Diagnosis:** Timestamps are naive (no timezone info)

**Fix:** Ensure you localize to UTC first:
```python
datetimes = pd.to_datetime(timestamps, unit='s', utc=True)  # Add utc=True
```

---

**Version:** 1.0  
**Status:** Production Guide  
**Last Updated:** April 11, 2026
