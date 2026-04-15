# Data Provider Timezone Consistency - Implementation Reference

**Date:** April 11, 2026  
**Status:** Critical Implementation Reference  
**Audience:** All developers working with data providers  
**Location:** Core reference document for data layer  

---

## 📌 Executive Summary

**One-Line Rule:** All data providers MUST return market-timezone-indexed DataFrames (Asia/Ho_Chi_Minh), NOT UTC.

**Why:** Inconsistent timezone handling between providers causes cascading TypeErrors downstream.

**Status:** All current providers comply. This document prevents future regressions.

---

## ✅ The Standard Pattern

Every normalizer MUST follow this exact pattern:

```python
import pandas as pd
import pytz
from src.stockreports.utils.time_utils import get_market_timezone_str

class YourNormalizer:
    def __init__(self):
        # 1. Initialize market timezone
        self.market_tz = pytz.timezone(get_market_timezone_str())
    
    def normalize(self, raw_data, symbol):
        # 2a. Convert timestamps to seconds (if needed)
        timestamps_sec = [ts_ms / 1000.0 for ts_ms in timestamps_ms]
        
        # 2b. Create UTC-aware DatetimeIndex
        datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
        
        # 2c. CRITICAL: Convert to market timezone
        datetimes = datetimes.tz_convert(self.market_tz)
        
        # 3. Create DataFrame
        df = pd.DataFrame({
            'time': datetimes,
            'open': opens,
            'high': highs,
            'low': lows,
            'close': closes,
            'volume': volumes
        })
        
        # 4. Set time as index
        df.set_index('time', inplace=True)
        
        # 5. Validate
        self.validate_ohlcv(df)
        
        return df
    
    def validate_ohlcv(self, df):
        # Check timezone is correct (not just present)
        market_tz_str = get_market_timezone_str()
        if str(df.index.tz) != market_tz_str:
            raise ValueError(
                f"Index timezone must be {market_tz_str}, got {df.index.tz}"
            )
        
        # ... other validations ...
        return True
```

---

## 🔍 Live Implementation Examples

### Vietstock (✅ Correct)
**File:** `src/stockreports/data_services/_internal/providing/vietstock/normalizer.py`

**Line 104-106 (normalize method):**
```python
datetimes = pd.to_datetime(timestamps, unit='s', utc=True)
# ✅ Converts to market timezone
datetimes = datetimes.tz_convert(self.market_tz)
```

**Line 224-230 (validate_ohlcv method):**
```python
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(
        f"Index timezone must be {market_tz_str}, "
        f"got {df.index.tz}"
    )
```

### Binance (✅ Fixed)
**File:** `src/stockreports/data_services/_internal/providing/binance/normalizer.py`

**Line 83-84 (normalize method):**
```python
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
# ✅ CRITICAL FIX: Converts to market timezone (was missing before)
datetimes = datetimes.tz_convert(self.market_tz)
```

**Line 205-209 (validate_ohlcv method):**
```python
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(
        f"Index timezone must be {market_tz_str}, "
        f"got {df.index.tz}"
    )
```

---

## ❌ Common Mistakes

### Mistake 1: Missing `tz_convert()`
```python
# ❌ WRONG
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
# Stops here with UTC index - causes TypeErrors downstream

# ✅ CORRECT
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)  # Convert!
```

### Mistake 2: Missing `utc=True`
```python
# ❌ WRONG
datetimes = pd.to_datetime(timestamps_sec, unit='s')
# Naive (no timezone) - tz_convert() will fail

# ✅ CORRECT
datetimes = pd.to_datetime(timestamps_sec, unit='s', utc=True)
```

### Mistake 3: Weak Validation
```python
# ❌ WRONG
if df.index.tz is None:
    raise ValueError("Must have timezone")
# Only checks existence, not correctness

# ✅ CORRECT
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(f"Index timezone must be {market_tz_str}, got {df.index.tz}")
```

### Mistake 4: Mixing Timezones Between Providers
```python
# ❌ WRONG
# Provider A: UTC only
datetimes = pd.to_datetime(timestamps, unit='s', utc=True)

# Provider B: Market timezone
datetimes = pd.to_datetime(timestamps, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)

# Result: Inconsistent data structures → TypeErrors

# ✅ CORRECT: ALL providers follow same pattern
# Provider A and B both do:
datetimes = pd.to_datetime(timestamps, unit='s', utc=True)
datetimes = datetimes.tz_convert(self.market_tz)
```

---

## 🐛 The Bug Story

### What Happened
Binance provider's normalizer was missing the `tz_convert()` call, causing it to return UTC-indexed DataFrames instead of market-timezone-indexed DataFrames.

### Where It Failed
Downstream in executor's `_step_validate_anchor_candle()` method, code tried to convert index to int:
```python
int(anchor_candle.name)  # anchor_candle.name is pd.Timestamp
```

### The Error
```
TypeError: int() argument must be a string, a bytes-like object 
or a real number, not 'Timestamp'
```

### Why It Was Cryptic
- Vietstock provider returns market-timezone index (correct)
- Binance provider returns UTC index (incorrect)
- Downstream code expects uniform index type
- When encountering UTF index, type conversion fails

### The Fix
```python
# In BinanceNormalizer.normalize() - Line 83-84
datetimes = datetimes.tz_convert(self.market_tz)  # Added this line

# In BinanceNormalizer.validate_ohlcv() - Lines 205-209
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(...)  # Added strict validation
```

---

## 🧪 Unit Test Template

```python
def test_normalizer_timezone_market_not_utc():
    """CRITICAL: Verify normalizer uses market timezone, not UTC."""
    normalizer = YourNormalizer()
    
    # Create sample data
    now_ms = int(datetime.now().timestamp() * 1000)
    raw_data = [[now_ms, "1000", "1001", "999", "1000", "100"]]
    
    # Normalize
    df = normalizer.normalize(raw_data, 'TEST')
    
    # CRITICAL CHECKS
    assert isinstance(df.index, pd.DatetimeIndex), \
        "Index must be DatetimeIndex"
    
    assert df.index.tz is not None, \
        "Index must be timezone-aware"
    
    assert str(df.index.tz) == 'Asia/Ho_Chi_Minh', \
        f"Expected Asia/Ho_Chi_Minh but got {df.index.tz}"
    
    assert str(df.index.tz) != 'UTC', \
        "CRITICAL: Must use market timezone, not UTC"
```

---

## ✅ Compliance Checklist

When implementing a new provider:

- [ ] Normalizer `__init__()` initializes market timezone
  ```python
  self.market_tz = pytz.timezone(get_market_timezone_str())
  ```

- [ ] Normalizer `normalize()` converts to market timezone
  ```python
  datetimes = datetimes.tz_convert(self.market_tz)
  ```

- [ ] Normalizer `validate_ohlcv()` checks timezone strictly
  ```python
  market_tz_str = get_market_timezone_str()
  if str(df.index.tz) != market_tz_str:
      raise ValueError(...)
  ```

- [ ] Unit test verifies market timezone (not UTC)
  ```python
  assert str(df.index.tz) == 'Asia/Ho_Chi_Minh'
  assert str(df.index.tz) != 'UTC'
  ```

- [ ] Integration test verifies consistency with other providers

- [ ] All required columns present: [open, high, low, close, volume]

- [ ] All numeric columns are float64

- [ ] No NaN values in critical columns

---

## 🔗 Quick Reference

**Get Market Timezone String:**
```python
from src.stockreports.utils.time_utils import get_market_timezone_str
tz_str = get_market_timezone_str()  # Returns: 'Asia/Ho_Chi_Minh'
```

**Get Market Timezone Object:**
```python
from src.stockreports.utils.time_utils import get_market_timezone
tz = get_market_timezone()  # Returns: pytz.timezone('Asia/Ho_Chi_Minh')
```

**Verify Timezone Correct:**
```python
from src.stockreports.utils.time_utils import get_market_timezone_str
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(f"Wrong timezone: {df.index.tz}")
```

---

## 🚀 When to Refer to This Document

1. **Creating a new data provider** - Follow the standard pattern
2. **Reviewing provider code** - Check compliance checklist
3. **Debugging timezone errors** - Review common mistakes and bug story
4. **Testing provider** - Use unit test template
5. **Understanding the requirement** - Read executive summary and why it matters

---

## 📚 Full Documentation

For comprehensive guides, see:
- **How to create new providers:** `DATA_PROVIDER_EXTENSION_GUIDE.md`
- **Deep dive on timezone handling:** `TIMEZONE_CONSISTENCY_GUIDE.md`
- **System architecture:** `DATA_LAYER_ARCHITECTURE.md`
- **Quick API reference:** `DATA_SERVICES_QUICK_REFERENCE.md`

---

## ⚠️ TL;DR

```python
# The ONE critical line that broke Binance provider:
datetimes = datetimes.tz_convert(self.market_tz)  # Must have this!

# The ONE critical validation that prevents regression:
market_tz_str = get_market_timezone_str()
if str(df.index.tz) != market_tz_str:
    raise ValueError(...)  # Strict check!
```

**If you forget these two things, you'll get TypeErrors downstream.**

---

**Version:** 1.0  
**Status:** Production Reference  
**Last Updated:** April 11, 2026
