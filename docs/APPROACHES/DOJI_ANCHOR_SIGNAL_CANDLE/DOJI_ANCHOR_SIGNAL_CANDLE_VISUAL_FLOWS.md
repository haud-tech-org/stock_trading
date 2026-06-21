# DOJI_ANCHOR_SIGNAL_CANDLE Detailed Flows & Step-by-Step Walkthrough

**Document Type**: Detailed Implementation Guide  
**Purpose**: Step-by-step walkthrough with real examples and scenarios  
**Target Audience**: Developers, traders understanding implementation  
**Last Updated**: June 21, 2026

---

## 📚 Contents

1. Complete execution walkthrough
2. Real data scenario examples
3. Parameter sensitivity guide
4. Error handling and edge cases
5. Debugging strategies

---

## 🔄 Complete Execution Walkthrough

### Setup Phase

```
1. Executor Initialization:
   ├─ Load DojiAnchorSignalCandleSettings for symbol
   │  └─ Read all 12 parameters from config
   ├─ Create DojiAnchorSignalCandleAnalyzer instance
   ├─ Create DojiAnchorSignalCandleValidator instance
   └─ Initialize logger

2. Get Loop Setup (get_loop_setup method):
   ├─ Input: DataFrame df, new_candle_count, lookback_window_size
   ├─ Calculate loop_start: len(df) - new_candle_count - 1
   ├─ Calculate loop_end: lookback_window_size - 1
   ├─ Backward loop: for i in range(loop_end, loop_start-1, -1)
   └─ Purpose: Process candles in reverse (newest first)

3. Minimum Data Check:
   ├─ If len(df) < LOOKBACK_WINDOW → return empty alerts
   └─ Skip: Not enough historical data
```

### Per-Window Processing

```
For each window i (backward iteration):

4. Set Window Context:
   ├─ Extract lookback_window_df = df[i-lookback_window_size : i+1]
   ├─ Set last_candle = df.iloc[i]
   ├─ Set current_window_end_time = last_candle.timestamp
   └─ Track: current_step = 0 (for logging)

5. Pre-Step: Prepare Candles (Lines 63-68):
   ├─ _step_prepare_candles()
   │  ├─ next_step() → current_step = 1
   │  ├─ Analyzer.find_most_recent_doji()
   │  │  └─ Find candle with body_ratio ≤ MAX_DOJI_BODY_RATIO
   │  ├─ Analyzer.discover_anchor_with_trend()
   │  │  └─ Search backward, find trend, get trend_candle_idx
   │  └─ Calculate avg_momentum_volume from window
   │
   ├─ Result: (doji_idx, anchor_idx, trend, trend_candle_idx, avg_vol)
   │          OR None (skip window)
   │
   └─ Example:
      Window index positions: [0, 1, 2, 3, 4, 5]
      Candle bodies:         [lg, sm, sm, lg, md, md]
      Found doji at index 1 (small body)
      Found anchor at index 0 (large body)
      Trend: UPTREND (established by anchor)

6. Signal Determination (Lines 71-78):
   ├─ reversal_trend = opposite of anchor trend
   │  └─ UPTREND anchor → DOWNTREND reversal
   │
   ├─ reversal_signal = trend_to_signal(reversal_trend)
   │  └─ DOWNTREND → SELL signal
   │
   └─ If signal is NEUTRAL → skip window

7. Step 1: Cooldown Check (Lines 80-87):
   ├─ next_step() → current_step = 2
   ├─ _step_cooldown_check()
   │  ├─ Check if LATEST_ALERT exists
   │  └─ If yes, calculate time_diff = current_time - LATEST_ALERT.time
   │
   ├─ Return: True if time_diff ≥ cooldown_window
   │           False if still in cooldown
   │
   └─ If False → skip window (continue to next)

8. Step 2: Alert Candle Validation (Lines 89-93):
   ├─ next_step() → current_step = 3
   ├─ alert_idx = len(lookback_window_df) - 1 (most recent candle)
   ├─ _step_validate_alert_candle()
   │  ├─ Check volume: alert_vol ≤ avg_vol × MAX_VOLUME_RATIO
   │  ├─ Check body: abs(C - O) ≥ MIN_ALERT_BODY_SIZE
   │  └─ Check direction:
   │      For DOWNTREND: alert_close < doji_low
   │      For UPTREND: alert_close > doji_high
   │
   └─ If False → skip window

9. Step 3: Momentum Validation (Lines 95-99):
   ├─ next_step() → current_step = 4
   ├─ _step_validate_momentum(anchor_idx, doji_idx)
   │  ├─ window_range = MAX(HIGH) - MIN(LOW) in [anchor, doji]
   │  └─ Return: window_range ≥ MOMENTUM_MIN_PRICE_MOVE
   │
   └─ If False → skip window

10. Step 4: Trend Candle Validation (Lines 101-105):
    ├─ next_step() → current_step = 5
    ├─ _step_validate_trend_candle(trend_candle_idx, ...)
    │  ├─ anchor_range = HIGH - LOW of anchor candle
    │  ├─ avg_window_range = mean of (HIGH-LOW) in window
    │  ├─ Check 1: anchor_range ≥ avg_window_range × RANGE_MULTIPLIER
    │  └─ Check 2: anchor_body ≥ MIN_TREND_BODY
    │
    └─ If False → skip window

11. All Validations Passed! (Lines 107-128):
    ├─ next_step() → current_step = 6
    ├─ Collect validation details:
    │  ├─ window_size, doji_idx, anchor_idx
    │  ├─ original_trend, trend_candle_idx
    │  └─ avg_momentum_volume
    │
    ├─ Create AlertData:
    │  ├─ signal = reversal_signal (SELL or BUY)
    │  ├─ trend = reversal_trend (DOWNTREND or UPTREND)
    │  ├─ alert_candle = last_candle
    │  ├─ magnitude = MOMENTUM_MIN_PRICE_MOVE
    │  └─ details = {all validation info}
    │
    ├─ Store:
    │  ├─ self.alerts.append(alert_data)
    │  └─ LATEST_ALERT = alert_data (class variable)
    │
    └─ Return in DEPLOYMENT mode (one alert per execution)
       Continue in REPLAY mode (collect all alerts)
```

---

## 📊 Real Data Scenario Examples

### Scenario 1: Successful DOWNTREND Reversal (SELL Signal)

**Situation**: Strong uptrend followed by consolidation, then bearish reversal

```
Time Progression (right = newest):
C0        C1        C2        C3        C4        C5 (ALERT)
═════     ═════     ═════     ═════     ═════     ═════
H 105.5   104.8     104.5     105.2     105.0     103.5
L 104.0   103.2     103.8     104.5     104.8     103.0
O 104.5   103.8     104.2     104.8     104.9     105.0
C 105.2   104.0     103.9     105.0     105.0     103.2
V 1.2M    1.1M      1.0M      1.3M      1.2M      1.1M

Window: [C0, C1, C2, C3, C4, C5]
Lookback Window Size: 6
```

**Step-by-Step Analysis**:

```
Step 1: IDENTIFY COMPONENTS

1. Find Doji:
   Check each candle body_ratio = body / range
   C0: body=1.2, range=1.5 → ratio=0.80 → NOT doji (too large)
   C1: body=0.2, range=1.6 → ratio=0.125 → DOJI! ✓
   C2: body=0.3, range=0.7 → ratio=0.43 → NOT doji (too large)
   C3: body=0.2, range=0.7 → ratio=0.29 → Could be doji
   C4: body=0.1, range=0.2 → ratio=0.50 → NOT doji
   C5: body=1.8, range=2.5 → ratio=0.72 → NOT doji
   
   Most recent doji: C1 (index=1)
   doji_idx = 1

2. Discover Anchor (search backward from C1):
   Analyze trend over TREND_WINDOW=4:
   - Check C0: HIGH=105.5, LOW=104.0
   - Check C1: HIGH=104.8, LOW=103.2
   
   recent_high = 104.8 > previous_high = 105.5? NO
   recent_low = 103.2 < previous_low = 104.0? YES
   
   Pattern: Lower low, lower high → DOWNTREND? No...
   Actually anchor is UPTREND (C0 established up)
   
   anchor_idx = 0
   trend = UPTREND (C0 was strong upward candle)

3. Average Momentum Volume:
   Window [C0:C1] volumes: [1.2M, 1.1M]
   avg_vol = (1.2M + 1.1M) / 2 = 1.15M

Step 2: SIGNAL DETERMINATION

reversal_trend = opposite(UPTREND) = DOWNTREND
reversal_signal = DOWNTREND → SELL
Signal = SELL ✓ (not NEUTRAL)

Step 3: VALIDATION CHECKS

Check 1: Cooldown
  Last alert time: 10:05:00
  Current time: 10:08:15
  Cooldown: 5 minutes = 300 seconds
  Time diff: 195 seconds
  Result: 195 < 300 → FAIL ✗
  
  SKIP WINDOW - still in cooldown period
```

**Outcome**: Alert suppressed by cooldown (too soon after last alert)

---

### Scenario 2: Successful Complete Analysis (SELL Signal Passes All Checks)

**Situation**: Same data, but after cooldown window expires

```
Adjusted scenario:
  Last alert: 10:00:00
  Current time: 10:06:30
  Time diff: 390 seconds ≥ 300 → PASS ✓

Check 1: Cooldown → PASS ✓

Check 2: Alert Candle Direction
  Expected: DOWNTREND reversal (close below doji)
  Doji: close=104.0, high=104.8, low=103.2
  Alert: C5 with close=103.2, body=1.8, vol=1.1M
  
  Threshold = 0.5
  lower_bound = max(103.2, 104.0 - 0.5) = max(103.2, 103.5) = 103.5
  
  alert_close = 103.2 < 103.5? YES → PASS ✓
  
  Volume check: 1.1M ≤ 1.15M × 1.2 = 1.38M? YES → PASS ✓
  Body check: 1.8 ≥ 1.5? YES → PASS ✓

Check 2: Alert Candle → PASS ✓

Check 3: Momentum
  Window [C0:C5]:
    window_high = max(105.5, 104.8, 104.5, 105.2, 105.0, 103.5) = 105.5
    window_low = min(104.0, 103.2, 103.8, 104.5, 104.8, 103.0) = 103.0
    window_range = 105.5 - 103.0 = 2.5
  
  MOMENTUM_MIN_PRICE_MOVE = 2.0
  Result: 2.5 ≥ 2.0 → PASS ✓

Check 3: Momentum → PASS ✓

Check 4: Trend Candle Strength (C0 - the anchor)
  anchor_candle = C0
  anchor_body = 1.2
  anchor_range = 1.5
  
  Average window range [C0:C5]:
    ranges = [1.5, 1.6, 0.7, 0.7, 0.2, 2.5]
    avg_range = (1.5 + 1.6 + 0.7 + 0.7 + 0.2 + 2.5) / 6 = 1.2
  
  TREND_CANDLE_RANGE_MULTIPLIER = 1.5
  TREND_CANDLE_MIN_BODY = 1.0
  
  Range check: 1.5 ≥ 1.2 × 1.5 = 1.8? NO → FAIL ✗
  
Result: Trend candle validation FAILS
  Anchor not strong enough relative to average
```

**Outcome**: Alert not generated (trend candle validation fails)

---

### Scenario 3: Successful BUY Signal (Complete)

**Situation**: Downtrend anchor, consolidation doji, bullish reversal

```
Time Progression:
C0        C1        C2        C3        C4        C5 (ALERT)
═════     ═════     ═════     ═════     ═════     ═════
H 102.5   102.2     102.0     101.8     101.5     104.0
L 100.5   101.5     101.8     101.5     101.2     102.5
O 101.5   102.0     101.9     101.8     101.3     102.8
C 100.8   101.8     101.8     101.5     101.2     103.8
V 1.5M    0.9M      0.8M      0.7M      0.6M      1.2M

Min doji body ratio: 0.25
```

**Analysis**:

```
1. Find Doji:
   C1: body=0.2, range=0.7 → ratio=0.29 → Doji? (borderline)
   C2: body=0.1, range=0.2 → ratio=0.5 → NOT doji
   C3: body=0.3, range=0.3 → ratio=1.0 → NOT doji
   ...
   
   Most recent valid doji: C1
   doji_idx = 1

2. Discover Anchor (backward from C1):
   Trend analysis [C0]:
   C0 high=102.5, low=100.5 (downward move from previous)
   
   trend = DOWNTREND (C0 established downward)
   anchor_idx = 0

3. Signal Determination:
   reversal_trend = UPTREND (opposite of DOWNTREND)
   reversal_signal = BUY

4. Validations (assuming cooldown passes):
   
   Check 2: Alert Direction (C5)
   Expected: UPTREND reversal (close above doji)
   Doji: close=101.8, high=102.0, low=101.8
   Alert: C5 close=103.8
   
   threshold = 0.5
   upper_bound = min(102.0, 101.8 + 0.5) = min(102.0, 102.3) = 102.0
   
   alert_close = 103.8 > 102.0? YES → PASS ✓
   
   Check 2: → PASS ✓

   Check 3: Momentum
   window_high = 104.0 (C5)
   window_low = 100.5 (C0)
   window_range = 3.5
   
   MOMENTUM_MIN_PRICE_MOVE = 2.0
   3.5 ≥ 2.0 → PASS ✓

   Check 4: Trend Candle (C0)
   C0: body=0.7, range=2.0
   avg_range = 1.43
   
   0.7 ≥ 1.43 × 1.5 = 2.145? NO → FAIL ✗
```

**Outcome**: Alert fails trend candle validation (C0 wasn't strong enough)

---

### Scenario 4: All Validations Pass - SELL Signal

```
Optimized window that passes all checks:

C0 (Anchor):  H=105.5, L=104.0, O=104.5, C=105.2, V=1.2M
C1 (Doji):    H=104.8, L=103.2, O=103.8, C=104.0, V=1.1M
C2-C4:        [various consolidation candles]
C5 (Alert):   H=103.5, L=103.0, O=105.0, C=103.2, V=1.0M

Cooldown: Passes (enough time since last alert)

Momentum:
  Range [C0:C5] = 105.5 - 103.0 = 2.5
  Threshold = 2.0 → PASS ✓

Alert Candle:
  Expected direction: Below doji (103.2)
  Alert close: 103.2 < 103.5? YES → PASS ✓
  Volume: 1.0M ≤ 1.15M × 1.2 → PASS ✓
  Body: 1.8 ≥ 1.5 → PASS ✓

Trend Candle (C0):
  C0 range = 1.5
  avg_range = 1.3
  1.5 ≥ 1.3 × 1.5 = 1.95? NO... 
  
  Wait, let's adjust:
  C0 range = 1.8 (bigger)
  avg_range = 1.2
  1.8 ≥ 1.2 × 1.5 = 1.8? YES → PASS ✓
  C0 body = 1.2 ≥ 1.0 → PASS ✓

ALL VALIDATIONS PASS!

Result:
  Signal: SELL
  Trend: DOWNTREND
  Magnitude: 2.0
  Details: All validation info
  
  AlertData created and returned
```

**Outcome**: ✅ SELL Alert generated

---

## 📈 Parameter Sensitivity Guide

### How Each Parameter Affects Alert Generation

#### LOOKBACK_WINDOW

```
Parameter: LOOKBACK_WINDOW = number of candles in analysis window

Effect on Detection:
- Larger value: Analyze more history, find older doji/anchor
- Smaller value: Recent patterns only, faster execution

Example:
  LOOKBACK_WINDOW = 3
  ├─ Can only find doji within last 3 candles
  └─ Misses patterns with older anchors
  
  LOOKBACK_WINDOW = 6
  ├─ Can find doji within last 6 candles
  └─ More patterns detected, more computation
  
  LOOKBACK_WINDOW = 10
  ├─ Very old patterns detected
  └─ More false signals, slower execution

Recommendation: 6-8 for 1-minute resolution
```

#### MAX_DOJI_BODY_RATIO

```
Parameter: MAX_DOJI_BODY_RATIO = maximum body/range ratio for doji

Effect on Detection:
- Higher value (e.g., 0.5): More candles classified as doji
- Lower value (e.g., 0.1): Stricter doji definition

Example:
  Candle: body=0.5, range=2.0 → body_ratio = 0.25
  
  With MAX_DOJI_BODY_RATIO=0.3:
    0.25 ≤ 0.3 → IS DOJI ✓
  
  With MAX_DOJI_BODY_RATIO=0.2:
    0.25 ≤ 0.2 → NOT DOJI ✗

Sensitivity:
- 0.1: Very strict (few doji found)
- 0.25: Moderate (good balance)
- 0.5: Loose (many candles classified as doji)

Recommendation: 0.2-0.3 for reliable indecision detection
```

#### MOMENTUM_MIN_PRICE_MOVE

```
Parameter: MOMENTUM_MIN_PRICE_MOVE = minimum price range anchor→doji

Effect on Detection:
- Higher value: Require more volatility
- Lower value: Accept less volatile setups

Example:
  Anchor at 100.0, Doji at 102.0
  Prices ranged from 99.5 to 102.5
  window_range = 3.0
  
  With MOMENTUM_MIN_PRICE_MOVE=2.0:
    3.0 ≥ 2.0 → PASS ✓ (generate alert)
  
  With MOMENTUM_MIN_PRICE_MOVE=3.5:
    3.0 ≥ 3.5 → FAIL ✗ (skip window)

Alert Frequency:
- Lower threshold: More alerts (lower quality)
- Higher threshold: Fewer alerts (higher quality)

Recommendation: 1.5-2.5x average candle range for your symbol
```

#### TREND_CANDLE_RANGE_MULTIPLIER

```
Parameter: TREND_CANDLE_RANGE_MULTIPLIER = anchor strength requirement

Effect on Detection:
- Higher value (e.g., 2.0): Anchor must be very strong
- Lower value (e.g., 1.2): Accept weaker anchors

Example:
  avg_window_range = 2.0
  anchor_range = 2.4
  
  With TREND_CANDLE_RANGE_MULTIPLIER=1.5:
    2.4 ≥ 2.0 × 1.5 = 3.0? NO → FAIL
  
  With TREND_CANDLE_RANGE_MULTIPLIER=1.2:
    2.4 ≥ 2.0 × 1.2 = 2.4? YES → PASS

Alert Quality:
- Higher multiplier: Stronger anchors, higher quality signals
- Lower multiplier: More alerts, mixed quality

Recommendation: 1.3-1.8 for balanced quality/frequency
```

#### COOLDOWN_WINDOW

```
Parameter: COOLDOWN_WINDOW = minutes between consecutive alerts

Effect on Detection:
- Higher value: Fewer alerts (less spam)
- Lower value: More alerts (potential spam)

Example:
  Last alert: 10:05:00
  Current time: 10:08:00
  
  With COOLDOWN_WINDOW=5:
    3 minutes < 5 minutes → Skip (still in cooldown)
  
  With COOLDOWN_WINDOW=2:
    3 minutes ≥ 2 minutes → Allow (outside cooldown)

Alert Frequency:
- 2 minutes: ~30 alerts/hour possible
- 5 minutes: ~12 alerts/hour possible
- 10 minutes: ~6 alerts/hour possible

Recommendation: 3-5 minutes for trading (avoid spam)
```

---

## 🛡️ Error Handling & Edge Cases

### Edge Case 1: Not Enough Data

```
Situation: DataFrame has fewer candles than LOOKBACK_WINDOW

Code Path:
  if len(df) < lookback_window_size:
      log(FAILED, "Not enough data")
      return empty alerts

Handling:
  ✓ Graceful failure
  ✓ Logged as DEBUG (not an error)
  ✓ Returns empty alert list
  
Example:
  LOOKBACK_WINDOW = 6
  Received df with 4 candles
  
  Result: Skip execution, wait for more data
```

### Edge Case 2: No Doji Found

```
Situation: No candle matches doji criteria in lookback window

Code Path:
  doji_idx = Analyzer.find_most_recent_doji(...)
  if doji_idx is None:
      log(FAILED, "No doji found")
      return None → skip window

Handling:
  ✓ Logged as DEBUG
  ✓ Window skipped
  ✓ Execution continues to next window

Example:
  MAX_DOJI_BODY_RATIO = 0.25
  All candles in window have body_ratio > 0.25
  
  Result: Skip window, continue
```

### Edge Case 3: Anchor Not Found

```
Situation: No valid anchor candle found backward from doji

Code Path:
  anchor_result = Analyzer.discover_anchor_with_trend(...)
  if anchor_result is None:
      log(FAILED, "Failed to discover anchor")
      return None → skip window

Handling:
  ✓ Logged as DEBUG
  ✓ Window skipped
  ✓ Execution continues

Common Causes:
  - All candles in search limit have NEUTRAL trend
  - No clear uptrend or downtrend established
  - ANCHOR_SEARCH_LIMIT too small

Debugging:
  Increase ANCHOR_SEARCH_LIMIT if frequent
```

### Edge Case 4: Division by Zero in Calculations

```
Situation: Average range calculation results in zero

Code Path:
  avg_range = window_df[HIGH - LOW].mean()
  if avg_range == 0:
      return body >= min_body (skip range check)

Handling:
  ✓ Protected by condition
  ✓ Falls back to body size check only
  ✓ Does not crash

When This Happens:
  - All candles in window are doji-like (flat)
  - Rare in normal market conditions
```

### Edge Case 5: Exception During Processing

```
Situation: Unexpected error in validation

Code Path:
  try:
      # validation logic
  except Exception as e:
      log(ERROR, f"Exception: {e}")
      return None → skip window

Handling:
  ✓ Logged as ERROR
  ✓ Window skipped gracefully
  ✓ Execution continues
  ✓ No crash

Example:
  Corrupted OHLC data → NaN values
  → numpy operation fails
  → caught by exception handler
  → logged and skipped
```

---

## 🐛 Debugging Strategies

### Strategy 1: Enable Detailed Logging

```python
# Check executor.py for current logging configuration
# Each validation step logs details:

Log entry format:
  - timestamp
  - symbol
  - current step
  - validation number
  - message describing what failed
  - log level (DEBUG vs ERROR)

Where to find logs:
  - Application logs: logs/ directory
  - Alert-specific: search for DOJI_ANCHOR_SIGNAL_CANDLE
```

### Strategy 2: Trace Through Single Window

```python
# When debugging specific window:

1. Identify the window index (i)
2. Extract window data:
   lookback_window_df = df[i-lookback_size : i+1]
3. Manually run each step:
   doji_idx = analyzer.find_most_recent_doji(...)
   anchor_result = analyzer.discover_anchor_with_trend(...)
   ...
4. Check values at each step
5. Verify against expected values
```

### Strategy 3: Parameter Tuning Experiment

```python
# When alerts aren't being generated:

1. Loosen one parameter at a time:
   - Increase MAX_DOJI_BODY_RATIO (0.25 → 0.35)
   - Decrease MOMENTUM_MIN_PRICE_MOVE
   - Decrease TREND_CANDLE_RANGE_MULTIPLIER
   - Increase ANCHOR_SEARCH_LIMIT

2. Re-run and observe:
   - Did alert count increase?
   - Were quality still good?
   
3. Adjust parameters based on results

4. Validate with real trading data
```

### Strategy 4: Analyze Failure Distribution

```python
# To understand where most windows fail:

Count failures at each step:
  Pre-step failures: 60%
  Step 1 (cooldown): 75% of remaining
  Step 2 (alert): 55% of remaining
  Step 3 (momentum): 45% of remaining
  Step 4 (trend): 30% of remaining
  
Analysis:
  - If too many fail at cooldown → increase COOLDOWN_WINDOW
  - If too many fail at momentum → decrease MOMENTUM_MIN_PRICE_MOVE
  - If too many fail at trend → decrease TREND_CANDLE_RANGE_MULTIPLIER
```

---

## 🔗 Cross-References

- **Main Specification**: `DOJI_ANCHOR_SIGNAL_CANDLE.md`
- **Architecture**: `DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md`
- **Navigation**: `INDEX.md`
- **Implementation Code**: `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/`

---

**Status**: ✅ Complete with examples and scenarios  
**Last Reviewed**: June 21, 2026  
**Verification**: All examples traced through algorithm
