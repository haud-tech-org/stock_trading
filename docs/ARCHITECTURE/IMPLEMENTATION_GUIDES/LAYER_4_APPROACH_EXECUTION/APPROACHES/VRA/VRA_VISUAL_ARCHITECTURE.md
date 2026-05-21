# VRA Validation - Visual Architecture Guide (Current Implementation - v3)

## 🏗️ Actual Current Architecture (v3)

```
┌─────────────────────────────────────────────────────────────┐
│                    VRA EXECUTOR                              │
│                 _find_alerts() method                         │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
    STEP 1          STEP 2          STEP 3
  Volume Val      Trend Val        Confirmation Val
        │                 │                  │
        ▼                 ▼                  ▼
    ┌────────┐      ┌────────────┐  ┌──────────────────┐
    │ANALYZER│      │ANALYZER    │  │ ANALYZER         │
    │        │      │            │  │                  │
    │Max Vol │      │Trend       │  │ Extract window   │
    │Min Vol │      │Magnitude   │  │ from max_vol→end │
    │        │      │Open Pos    │  │                  │
    └────────┘      │Extremes    │  │ Peak/Trough      │
        │           └────────────┘  │ Prominence calc  │
        ▼                │           │                  │
    ┌────────┐      ┌────────────┐  └──────────────────┘
    │VALIDATOR       │VALIDATOR   │          │
    │        │      │            │          ▼
    │Vol Ratio       │Magnitude   │  ┌──────────────────┐
    │Check  │      │Threshold   │  │ VALIDATOR        │
    │        │      │            │  │                  │
    │Max vs  │      │Open Price  │  │Window Size Check │
    │Alert  │      │Position    │  │                  │
    │        │      │Validation  │  │Prominence Range  │
    └────────┘      └────────────┘  │ [min, max]       │
        │                │           │                  │
        ▼                ▼           └──────────────────┘
    RETURN            RETURN               │
    (Pass: tuple)     (Pass: tuple)        ▼
    max_vol,          window_trend,  RETURN bool
    min_vol           magnitude
```

---

## 📍 Algorithm Flow: Step 1 - Volume Validation

```
START: _step_volume_validation()
    │
    ├─ VALIDATION 1: Find max volume candle in entire window
    │   │
    │   ├─ Analyzer: find_max_volume_candle()
    │   ├─ Returns: Series with highest volume
    │   └─ Result: max_vol_candle ✓
    │
    ├─ VALIDATION 2: Find min volume candle UP TO max volume position
    │   │
    │   ├─ Analyzer: find_min_volume_candle_up_to_index(window, max_vol_candle)
    │   ├─ Ensures: min_vol occurs before max_vol in sequence
    │   └─ Result: min_vol_candle (or None if not found) ✓
    │
    ├─ VALIDATION 3: Check volume ratio (max/min)
    │   │
    │   ├─ Analyzer: calculate_volume_ratio(max_vol, min_vol)
    │   ├─ Validator: validate_volume_ratio(ratio, VOLUME_MULTIPLIER)
    │   ├─ Check: ratio >= VOLUME_MULTIPLIER (default: 4.5)
    │   └─ Result: True/False ✓
    │
    ├─ VALIDATION 4: Check max volume vs alert candle volume
    │   │
    │   ├─ Validator: validate_max_volume_vs_alert_candle()
    │   ├─ Check: max_vol >= alert_vol × VOLUME_MULTIPLIER_BY_REVERSAL_TREND
    │   ├─ Default threshold: 2.0
    │   └─ Result: True/False ✓
    │
    └─ RETURN: (max_vol_candle, min_vol_candle) or None
         └─ On ANY failure → return None (skip window)
```

### Key Points
- **Validation 2 is CRITICAL**: Min volume must occur chronologically BEFORE max volume
- **Two-tier volume check**: Ratio check (Validation 3) + absolute threshold check (Validation 4)
- **Early exit**: Any failure causes immediate return of None

---

## 📍 Algorithm Flow: Step 2 - Trend & Magnitude Validation

```
START: _step_trend_and_magnitude_validation()
    │
    ├─ STEP 1: Create trend slice from min_vol_candle → alert_candle
    │   │
    │   ├─ Analyzer: slice_window(window, min_vol_candle, alert_candle)
    │   ├─ Result: trend_slice DataFrame
    │   └─ Return None if slice creation fails
    │
    ├─ VALIDATION 1: Check trend window size
    │   │
    │   ├─ Validator: validate_trend_window_size(trend_slice, min_count=3)
    │   ├─ Check: len(trend_slice) >= 3
    │   └─ Return (None, None) if fails
    │
    ├─ VALIDATION 2: Calculate magnitude and trend
    │   │
    │   ├─ Analyzer: window_utils.get_window_size_and_trend(trend_slice)
    │   ├─ Returns: (magnitude_value, trend_direction)
    │   │   - magnitude_value: abs(price_change)
    │   │   - trend_direction: UPTREND or DOWNTREND
    │   │
    │   ├─ Validator: validate_trend_magnitude(magnitude, MIN_TREND_MAGNITUDE)
    │   ├─ Check: magnitude >= MIN_TREND_MAGNITUDE (default: 6.5)
    │   └─ Return (None, None) if fails
    │
    ├─ VALIDATION 3: Verify open price extremes positions
    │   │
    │   ├─ Find: L (lowest open) and H (highest open) positions
    │   │
    │   ├─ FOR UPTREND:
    │   │   ├─ L must be before H: L_pos < H_pos
    │   │   ├─ L near start: L_pos <= TREND_WINDOW_EDGE_SLICE (default: 3)
    │   │   └─ H near end: (len(trend_slice) - 1 - H_pos) <= TREND_WINDOW_EDGE_SLICE
    │   │
    │   ├─ FOR DOWNTREND:
    │   │   ├─ H must be before L: H_pos < L_pos
    │   │   ├─ H near start: H_pos <= TREND_WINDOW_EDGE_SLICE
    │   │   └─ L near end: (len(trend_slice) - 1 - L_pos) <= TREND_WINDOW_EDGE_SLICE
    │   │
    │   └─ Return (None, None) if ANY check fails
    │
    └─ RETURN: (window_trend, window_size_val)
         └─ On SUCCESS → Continue to Step 3
         └─ On FAILURE → return None (skip window)
```

### Key Points
- **Step 2 validates the INTEGRITY of the trend**: It's not just about magnitude, but that the trend is structured properly
- **Open extremes validation ensures**: The trend has a clear START (low) and END (high) pattern
- **This acts as an anti-noise filter**: Prevents zigzag or consolidation patterns from triggering alerts

---

## 📍 Algorithm Flow: Step 3 - Confirmation Window Validation

```
START: _step_confirmation_window_validation()
    │
    ├─ VALIDATION 1: Extract confirmation window
    │   │
    │   ├─ Analyzer: slice_window(window, max_vol_candle, window.iloc[-1])
    │   ├─ Range: From max volume candle to END of lookback window
    │   ├─ Result: confirmation_window DataFrame
    │   └─ Return None if extraction fails
    │
    ├─ VALIDATION 2: Check confirmation window size
    │   │
    │   ├─ Validator: validate_confirmation_window_size(confirmation_window)
    │   ├─ Check: len(confirmation_window) >= MIN_CONFIRMATION_WINDOW_CANDLES
    │   ├─ Default: >= 3 candles
    │   └─ Return None if fails
    │
    ├─ VALIDATION 3: Validate peak/trough prominence
    │   │
    │   ├─ FOR UPTREND:
    │   │   ├─ Analyzer: window_utils.get_highest_peak(confirmation_window)
    │   │   ├─ Returns: (peak_candle, prominence_value)
    │   │   │
    │   │   ├─ PROMINENCE calculation:
    │   │   │   └─ Measures strength of peak relative to neighbors
    │   │   │   └─ Values too low = weak reversal
    │   │   │   └─ Values too high = overextended move
    │   │   │
    │   │   └─ Validator: validate range
    │   │       └─ Check: MIN_PEAK_TROUGH_PROMINENCE <= prominence <= MAX_PEAK_TROUGH_PROMINENCE
    │   │       └─ Default: 1.5 <= prominence <= 3.0
    │   │
    │   ├─ FOR DOWNTREND:
    │   │   ├─ Analyzer: window_utils.get_lowest_trough(confirmation_window)
    │   │   ├─ Returns: (trough_candle, prominence_value)
    │   │   └─ Same range validation as uptrend
    │   │
    │   └─ Return None if prominence check fails
    │
    └─ RETURN: True (validation passed)
         └─ On SUCCESS → Continue to Step 4
         └─ On FAILURE → return None (skip window)
```

### Key Points
- **Confirmation window starts at max volume candle**, NOT at the beginning
- **Prominence is NOT price range**, it's a relative strength metric
- **Range limits prevent false signals**: Weak peaks/troughs are filtered out, as are overextended moves

---

## 🎯 Complete Data Flow: Full Execution Path

```
                    LOOKBACK WINDOW (15 candles)
                  [C1, C2, C3, ... C14, C15_alert]
                        │
        ┌───────────────┼───────────────────┐
        │               │                   │
        │         STEP 1: VOLUME             │
        │         Identify volume spike      │
        │                                   │
        ├─ Find max_vol_candle (e.g., C7)  │
        ├─ Find min_vol_candle (e.g., C2)  │
        ├─ Check ratio: C7_vol/C2_vol       │
        ├─ Check C7_vol vs C15_vol          │
        │                                   │
        ▼ (PASS)                            │
    [C2_min, C7_max identified]            │
        │                                   │
        ├───────────────────────────────────┘
        │
        │         STEP 2: TREND & MAGNITUDE
        │         Verify trend structure
        │
        ├─ Slice: [C2 → C15]  (trend window)
        ├─ Size check: len >= 3 ✓
        ├─ Magnitude: |price_change| >= 6.5 ✓
        ├─ Open extremes:
        │   ├─ If UPTREND:
        │   │   ├─ Lowest open in first 3 candles ✓
        │   │   └─ Highest open in last 3 candles ✓
        │   └─ Else DOWNTREND: opposite pattern
        │
        ▼ (PASS)
    [Window_trend: UPTREND, Magnitude: 8.5]
        │
        │         STEP 3: CONFIRMATION
        │         Validate reversal zone
        │
        ├─ Slice: [C7 → C15]  (confirmation window)
        ├─ Size check: len >= 3 ✓
        ├─ Peak/Trough prominence:
        │   ├─ Find highest peak in [C7→C15]
        │   ├─ Prominence = 2.1
        │   ├─ Check: 1.5 <= 2.1 <= 3.0 ✓
        │
        ▼ (PASS)
    [Confirmation validated]
        │
        │         STEP 4: COOLDOWN CHECK
        │         Prevent spam alerts
        │
        ├─ Current signal: SELL (opposite of UPTREND)
        ├─ Check LATEST_ALERT history
        ├─ Last alert for symbol: SELL at C12
        ├─ Cooldown window: 3 candles
        ├─ Distance: C15 - C12 = 3 candles
        ├─ Not in cooldown ✓
        │
        ▼ (PASS)
    [Cooldown OK]
        │
        │         STEP 5: ALERT CREATION
        │         Generate AlertData
        │
        ├─ Signal: SELL
        ├─ Trend: DOWNTREND (reversal of UPTREND)
        ├─ Candle: C15
        ├─ Magnitude: 8.5
        ├─ Timestamp: C15 timestamp
        │
        ▼
    [AlertData object created]
        │
        └─ Update LATEST_ALERT
        └─ Add to alerts list
        └─ Deployment mode: Return, else continue loop
```

---

## 🔄 Reversal Signal Logic (from Step 1 to Step 5)

```
TREND DETECTION (Step 2) → REVERSAL SIGNAL (Step 5)
═══════════════════════════════════════════════════

Window Trend: UPTREND
  ↓
  └─ What it means: Market has been moving UP
     
REVERSAL TREND: DOWNTREND (opposite)
  ↓
  └─ What it means: Signal expects market to move DOWN next

REVERSAL SIGNAL: SELL
  ↓
  └─ Calculated from: get_reversal_trend(UPTREND) → DOWNTREND
  └─ Calculated from: get_signal_from_trend(DOWNTREND) → SELL

────────────────────────────────────────────────────

Window Trend: DOWNTREND
  ↓
  └─ What it means: Market has been moving DOWN

REVERSAL TREND: UPTREND (opposite)
  ↓
  └─ What it means: Signal expects market to move UP next

REVERSAL SIGNAL: BUY
  ↓
  └─ Calculated from: get_reversal_trend(DOWNTREND) → UPTREND
  └─ Calculated from: get_signal_from_trend(UPTREND) → BUY
```

---

## 📊 State Transition Diagram: Window Processing

```
START: Loop through lookback window backwards
    │
    ├─────────────────────────────────┐
    │                                 │
    ▼ Each iteration                  │
                                      │
┌─ STEP 1: VOLUME ─────────────────┐ │
│ ✓ Max volume found               │ │
│ ✓ Min volume found (before max)  │ │
│ ✓ Ratio >= threshold             │ │
│ ✓ Max >= alert × multiplier      │ │
└──────────────────┬────────────────┘ │
                   │                  │
                   ├─ FAIL ──────────┤│
                   │                 ││
┌─ STEP 2: TREND ──┘                 ││
│ ✓ Window size >= 3                 ││
│ ✓ Magnitude >= threshold           ││
│ ✓ Open extremes in correct position││
└──────────────────┬────────────────┐ ││
                   │                │ ││
                   ├─ FAIL ────────┤│ ││
                   │               │ ││
┌─ STEP 3: CONFIRM ┘               │ ││
│ ✓ Window extracted                │ ││
│ ✓ Window size >= 3                │ ││
│ ✓ Peak/Trough prominence in range │ ││
└──────────────────┬────────────────┘ ││
                   │                  ││
                   ├─ FAIL ──────────┤ ││
                   │                 │ ││
┌─ STEP 4: COOLDOWN┘                 │ ││
│ ✓ Not in cooldown period           │ ││
└──────────────────┬────────────────┐ │ ││
                   │                │ │ ││
                   ├─ FAIL ────────┤│ │ ││
                   │               │ │ ││
┌─ STEP 5: ALERT ──┘               │ │ ││
│ ✓ Create AlertData                │ │ ││
│ ✓ Update LATEST_ALERT             │ │ ││
│ ✓ Add to alerts list              │ │ ││
└──────────────────┬────────────────┘ │ ││
                   │                  │ ││
                   ▼                  │ ││
            SUCCESS! ✓                │ ││
      (Return if deployment)         │ ││
      (Continue if development)      │ ││
                   │                 │ ││
                   └─────────────────┼─┼┘
                                     │ │
            FAILED WINDOW:           │ │
            └─ Skip iteration ───────┘ │
                                       │
            Continue to next candle ──┘
```

---

## 📌 Key Algorithm Characteristics (Current v3)

| Aspect | Detail |
|--------|--------|
| **Window type** | Reverse loop (most recent candle first) |
| **Lookback period** | Fixed 15 candles by default |
| **Volume validation** | TWO checks: ratio + absolute threshold |
| **Trend validation** | THREE checks: size, magnitude, structure |
| **Confirmation** | Peak/trough prominence range (not just existence) |
| **Cooldown** | Per-symbol, per-signal history tracking |
| **Alert generation** | Reversal trend is opposite of window trend |
| **Parameters** | 9 configurable settings |
| **Validation steps** | 5 major steps, 15+ individual validations |

