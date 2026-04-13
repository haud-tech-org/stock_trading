# Anchor-Signal-Candle (ASC) - Complete Validation Logic Reference

**Purpose**: Clean, definitive reference for all validation logic  
**Date**: April 10, 2026

---

## 🎯 Validation 1: Window Size & Trend

### Input Parameters
```python
lookback_window_df: pd.DataFrame  # Full window of N candles
min_size_price_window: float      # Config: minimum window range (e.g., 0.5)
```

### Calculation Steps
```python
# Step 1: Calculate window size
window_high = lookback_window_df[CandleColumn.HIGH].max()
window_low = lookback_window_df[CandleColumn.LOW].min()
window_size = window_high - window_low

# Step 2: Check minimum threshold
if window_size < min_size_price_window:
    RETURN (None, None)  # FAIL

# Step 3: Determine trend from close prices
first_close = lookback_window_df[CandleColumn.CLOSE].iloc[0]
last_close = lookback_window_df[CandleColumn.CLOSE].iloc[-1]

if last_close > first_close:
    window_trend = Trend.UPTREND
elif last_close < first_close:
    window_trend = Trend.DOWNTREND
else:
    RETURN (None, None)  # FAIL: Cannot determine trend

# Step 4: Return results
RETURN (window_size, window_trend)
```

### Success Condition
```
window_size >= min_size_price_window
AND
(last_close > first_close OR last_close < first_close)
```

### Output
```python
Tuple[float, Trend]  # (window_size, window_trend)
```

---

## 🎯 Validation 2: Anchor Candle Identification

### Input Parameters
```python
lookback_window_df: pd.DataFrame      # Full window of N candles
min_size_candle: float                # Config: minimum body size (e.g., 0.01)
multiplier_size: float                # Config: multiplier vs avg (e.g., 1.5)
```

### Calculation Steps
```python
# Step 1: Calculate average candle body size (HIGH - LOW)
all_body_sizes = []
for index, candle in lookback_window_df.iterrows():
    body_size = candle[CandleColumn.HIGH] - candle[CandleColumn.LOW]
    all_body_sizes.append(body_size)

average_body_size = sum(all_body_sizes) / len(all_body_sizes)

# Step 2: Find candle with maximum body size
max_body_size = 0.0
anchor_candle = None

for index, candle in lookback_window_df.iterrows():
    body_size = candle[CandleColumn.HIGH] - candle[CandleColumn.LOW]
    if body_size > max_body_size:
        max_body_size = body_size
        anchor_candle = candle

if anchor_candle is None:
    RETURN None  # FAIL: No candles in window

# Step 3: Validate absolute minimum
if max_body_size < min_size_candle:
    RETURN None  # FAIL: Body too small

# Step 4: Validate relative to average
multiplier_threshold = multiplier_size * average_body_size
if max_body_size < multiplier_threshold:
    RETURN None  # FAIL: Not large enough vs average

# Step 5: Return anchor candle
RETURN anchor_candle
```

### Success Conditions
```
max_body_size >= min_size_candle
AND
max_body_size >= (multiplier_size * average_body_size)
```

### Output
```python
pd.Series  # Anchor candle row
```

---

## 🎯 Validation 3: Signal Candle Identification

### Input Parameters
```python
lookback_window_df: pd.DataFrame      # Full window of N candles
anchor_candle: pd.Series              # Anchor candle (from Validation 2)
min_volume: float                     # Config: minimum volume (e.g., 100000)
multiplier_volume: float              # Config: multiplier vs avg (e.g., 1.2)
```

### Calculation Steps
```python
# Step 1: Calculate average volume in FULL window
all_volumes = []
for index, candle in lookback_window_df.iterrows():
    all_volumes.append(candle[CandleColumn.VOLUME])

average_volume = sum(all_volumes) / len(all_volumes)

# Step 2: Find maximum volume candle in ENTIRE window
max_volume = 0.0
signal_candle = None

for index, candle in lookback_window_df.iterrows():
    volume = candle[CandleColumn.VOLUME]
    if volume > max_volume:
        max_volume = volume
        signal_candle = candle

if signal_candle is None:
    RETURN None  # FAIL: No candles in window

# Step 3: Validate absolute minimum volume
if max_volume < min_volume:
    RETURN None  # FAIL: Volume too low

# Step 4: Validate relative to average
multiplier_threshold = multiplier_volume * average_volume
if max_volume < multiplier_threshold:
    RETURN None  # FAIL: Not high enough vs average

# Step 5: Verify signal is at or after anchor (INDEX CHECK)
anchor_index = get_candle_index(lookback_window_df, anchor_candle)
signal_index = get_candle_index(lookback_window_df, signal_candle)

if signal_index < anchor_index:
    RETURN None  # FAIL: Signal before anchor

# Step 6: Return signal candle
RETURN signal_candle
```

### Success Conditions
```
max_volume >= min_volume
AND
max_volume >= (multiplier_volume * average_volume)
AND
signal_index >= anchor_index
```

### Output
```python
pd.Series  # Signal candle row
```

---

## 🎯 Validation 4: Alert Candle Confirmation

### Input Parameters
```python
lookback_window_df: pd.DataFrame      # Full window of N candles
signal_candle: pd.Series              # Signal candle (from Validation 3)
window_trend: Trend                   # From Validation 1 (UPTREND or DOWNTREND)
min_percentage: float                 # Config: min wick % of body (e.g., 0.2)
max_percentage: float                 # Config: max wick % of body (e.g., 0.6)
```

### Calculation Steps

#### Common Steps (Apply to Both Trends)
```python
# Step 1: Extract alert candle (always last in window)
alert_candle = lookback_window_df.iloc[-1]
alert_index = len(lookback_window_df) - 1

# Step 2: Get signal candle index
signal_index = get_candle_index(lookback_window_df, signal_candle)

# Step 3: Verify alert is at or after signal
if alert_index < signal_index:
    RETURN None  # FAIL: Alert before signal

# Step 4: Check if candle has body (reject doji)
candle_body_size = ABS(alert_candle[CandleColumn.CLOSE] - 
                       alert_candle[CandleColumn.OPEN])
if candle_body_size <= 0:
    RETURN None  # FAIL: Doji candle (no body)

# Step 5: Get all extremes from window
all_highs = []
all_closes = []
all_lows = []

for index, candle in lookback_window_df.iterrows():
    all_highs.append(candle[CandleColumn.HIGH])
    all_closes.append(candle[CandleColumn.CLOSE])
    all_lows.append(candle[CandleColumn.LOW])

max_high = max(all_highs)
max_close = max(all_closes)
min_low = min(all_lows)
min_close = min(all_closes)
```

#### IF UPTREND (last_close > first_close)
```python
# Step 6a: Check price extremes for UPTREND
if alert_candle[CandleColumn.HIGH] != max_high:
    RETURN None  # FAIL: Alert doesn't have highest HIGH

if alert_candle[CandleColumn.CLOSE] != max_close:
    RETURN None  # FAIL: Alert doesn't have highest CLOSE

# Step 7a: Calculate upper wick percentage
upper_wick_size = alert_candle[CandleColumn.HIGH] - 
                  alert_candle[CandleColumn.CLOSE]
wick_percentage = upper_wick_size / candle_body_size

# Step 8a: Validate upper wick percentage
if wick_percentage < min_percentage:
    RETURN None  # FAIL: Upper wick too small

if wick_percentage > max_percentage:
    RETURN None  # FAIL: Upper wick too large

# Step 9a: Return success for UPTREND
RETURN True
```

#### ELSE IF DOWNTREND (last_close < first_close)
```python
# Step 6b: Check price extremes for DOWNTREND
if alert_candle[CandleColumn.LOW] != min_low:
    RETURN None  # FAIL: Alert doesn't have lowest LOW

if alert_candle[CandleColumn.CLOSE] != min_close:
    RETURN None  # FAIL: Alert doesn't have lowest CLOSE

# Step 7b: Calculate lower wick percentage
lower_wick_size = alert_candle[CandleColumn.CLOSE] - 
                  alert_candle[CandleColumn.LOW]
wick_percentage = lower_wick_size / candle_body_size

# Step 8b: Validate lower wick percentage
if wick_percentage < min_percentage:
    RETURN None  # FAIL: Lower wick too small

if wick_percentage > max_percentage:
    RETURN None  # FAIL: Lower wick too large

# Step 9b: Return success for DOWNTREND
RETURN True
```

### Success Conditions - UPTREND
```
alert_index >= signal_index
AND
candle_body_size > 0 (not doji)
AND
alert.HIGH == max_high (highest in window)
AND
alert.CLOSE == max_close (highest in window)
AND
(HIGH - CLOSE) / body_size in [min_percentage, max_percentage]
```

### Success Conditions - DOWNTREND
```
alert_index >= signal_index
AND
candle_body_size > 0 (not doji)
AND
alert.LOW == min_low (lowest in window)
AND
alert.CLOSE == min_close (lowest in window)
AND
(CLOSE - LOW) / body_size in [min_percentage, max_percentage]
```

### Output
```python
bool  # True if all validations pass
```

---

## 🔄 Complete Execution Flow

### Loop Structure
```python
for scan_index in range(loop_end, loop_start - 1, -1):
    # Extract lookback_window_df from scan_index
    
    # VALIDATION 1: Window Analysis
    (window_size, window_trend) = validate_window(lookback_window_df)
    if (window_size, window_trend) == (None, None):
        continue  # Skip this window
    
    # VALIDATION 2: Anchor Candle
    anchor_candle = validate_anchor(lookback_window_df)
    if anchor_candle is None:
        continue  # Skip this window
    
    # VALIDATION 3: Signal Candle
    signal_candle = validate_signal(lookback_window_df, anchor_candle)
    if signal_candle is None:
        continue  # Skip this window
    
    # VALIDATION 4: Alert Candle
    is_alert_valid = validate_alert(lookback_window_df, signal_candle, window_trend)
    if is_alert_valid is None:
        continue  # Skip this window
    
    # VALIDATION 5: Cooldown Check
    is_not_in_cooldown = check_cooldown(latest_alert, current_time, cooldown_window)
    if not is_not_in_cooldown:
        continue  # Skip this window
    
    # VALIDATION 6: Determine Reversal
    if window_trend == UPTREND:
        reversal_trend = DOWNTREND
        reversal_signal = SELL
    else:  # DOWNTREND
        reversal_trend = UPTREND
        reversal_signal = BUY
    
    # CREATE ALERT
    alert = create_alert(
        signal=reversal_signal,
        trend=reversal_trend,
        magnitude=window_size,
        details={...}
    )
    
    alerts.append(alert)
    LATEST_ALERT = alert
    
    # Stop after first alert in production mode
    if not is_development_mode:
        break

# Return alerts in forward order
return reverse(alerts)
```

---

## 📊 Parameter Defaults

```python
LOOKBACK_WINDOW = 50              # Candles
MIN_SIZE_PRICE_WINDOW = 0.5       # Price units
MIN_SIZE_CANDLE = 0.01            # Price units
MULTIPLIER_SIZE = 1.5             # X times average
MIN_VOLUME = 100000               # Volume units
MULTIPLIER_VOLUME = 1.2           # X times average
MIN_PERCENTAGE = 0.2              # 20% of body
MAX_PERCENTAGE = 0.6              # 60% of body
COOLDOWN_WINDOW = 60              # Minutes
```

---

## ✅ Edge Cases & Error Handling

### Edge Case 1: Empty Window
**Condition**: len(lookback_window_df) == 0  
**Action**: FAIL - Return None  
**Message**: "Not enough data for analysis"

### Edge Case 2: Single Candle
**Condition**: len(lookback_window_df) == 1  
**Action**: FAIL - Cannot determine trend  
**Message**: "Cannot compare first vs last close with single candle"

### Edge Case 3: Doji Alert Candle
**Condition**: CLOSE == OPEN (body_size == 0)  
**Action**: FAIL - Cannot calculate wick percentage  
**Message**: "Alert candle is doji (no body) - cannot validate wick"

### Edge Case 4: No Variation in Window
**Condition**: High == Low for all candles  
**Action**: FAIL - No price range  
**Message**: "Window has no price variation"

### Edge Case 5: Flat Close Line
**Condition**: first_close == last_close  
**Action**: FAIL - Cannot determine trend  
**Message**: "First close equals last close - trend indeterminate"

### Edge Case 6: Alert Before Signal
**Condition**: Alert candle index < Signal candle index  
**Action**: FAIL - Violates sequence  
**Message**: "Alert candle occurs before signal candle"

### Edge Case 7: Signal Before Anchor
**Condition**: Signal candle index < Anchor candle index  
**Action**: FAIL - Violates sequence  
**Message**: "Signal candle occurs before anchor candle"

### Edge Case 8: Division by Zero
**Condition**: Wick validation with doji (body = 0)  
**Action**: FAIL - Caught in Step 4 above  
**Message**: "Cannot validate wick for zero-body candle"

---

## 🎯 Configuration Tuning Guide

### To Detect More Alerts
```
✓ Decrease min_size_price_window (lower threshold for window size)
✓ Decrease min_size_candle (easier to find anchor)
✓ Decrease multiplier_size (anchor doesn't need to be as large)
✓ Decrease min_volume (easier to find signal)
✓ Decrease multiplier_volume (signal doesn't need as high volume)
✓ Increase min_percentage (wick can be smaller)
✓ Increase max_percentage (wick can be larger)
✓ Decrease cooldown_window (allow more frequent alerts)
```

### To Detect Fewer, Higher-Quality Alerts
```
✓ Increase min_size_price_window (require larger window)
✓ Increase min_size_candle (require larger anchor)
✓ Increase multiplier_size (anchor must be much larger than average)
✓ Increase min_volume (require higher volume signal)
✓ Increase multiplier_volume (signal must be much higher than average)
✓ Decrease min_percentage (wick must be larger)
✓ Decrease max_percentage (wick can't be too large)
✓ Increase cooldown_window (restrict alert frequency)
```

---

## 📝 Implementation Notes

### Data Types
- All prices: `float`
- All volumes: `float` (handled as-is from exchange)
- All indices: `int` (0-based position in window)
- All percentages: `float` (0.0 to 1.0 range)
- All series: `pd.Series` (from DataFrame rows)
- All dataframes: `pd.DataFrame` (indexed by time)

### Naming Conventions
- `_df`: DataFrame variables
- `_size`: Size/magnitude values
- `_body`: Body-related calculations
- `_wick`: Wick-related calculations
- `_volume`: Volume-related values
- `_high/low/close/open`: Specific OHLC columns
- `_index`: Position in DataFrame
- `_percentage`: Ratio expressed as decimal (0.0-1.0)

### Logging Level
- **DEBUG**: All validation failures (expected)
- **DEBUG**: All validation passes with details
- **WARNING**: Alert creation
- **INFO**: Approach started/completed
- **ERROR**: Exceptions and unexpected failures

---

**READY FOR IMPLEMENTATION** ✅

This document provides complete, definitive validation logic for code generation.

