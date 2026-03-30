# VRA Refactoring - Visual Flow Diagrams (Current v3 Implementation)

**Date**: March 30, 2026  
**Purpose**: Accurate visual representation of v3 implementation  
**Status**: ✅ Current implementation documented

---

## 1. Volume Validation Zone (Step 1)

### What It Means

```
LOOKBACK WINDOW: [C1, C2, C3, C4, C5_alert]
Volume:          [50, 40, 60, 45, 70]
                       ▲         ▲
                      min       max

VOLUME ZONE = [C2 (min=40) ... C5 (max=70)]

VALIDATION 1: max_volume candle exists ✓
VALIDATION 2: min_volume candle BEFORE max_volume ✓
VALIDATION 3: max/min ratio validation
            70 / 40 = 1.75 >= 4.5? ❌ Would FAIL

VALIDATION 4: max_volume vs alert_volume
            70 / 70 = 1.0 >= 2.0? ❌ Would FAIL
```

### Critical Point: Min Volume Chronology

```
┌─────────────────────────────────────┐
│  Min Volume Must Occur FIRST        │
│                                     │
│  Valid: [C1=50, C2=40, C3=50, C5=70]│
│         └─min  └─────────────┬─max  │
│         C2 position < C5 position ✓ │
│                                     │
│  Invalid: [C1=50, C5=40, C3=50, C2=70] │
│          ┌─min ─────────────┬─max   │
│          But C5 comes BEFORE C2!    │
│          Cannot satisfy requirement ❌
│                                     │
└─────────────────────────────────────┘

KEY: find_min_volume_candle_up_to_index() ensures this
```

---

## 2. Trend & Magnitude Measurement (Step 2)

### Window Extraction

```
LOOKBACK WINDOW: [C1, C2, C3, C4, C5_alert]

AFTER STEP 1:
├─ min_vol_candle = C2
├─ max_vol_candle = C5
└─ Both validations passed

STEP 2 INPUT: Slice from C2 to C5
┌─────────────────────────────┐
│ TREND WINDOW:               │
│ [C2, C3, C4, C5]            │
│ └─────────┬─────────┘       │
│   This slice only            │
│   for magnitude check        │
│                             │
│ Price movement:             │
│ Start (C2): 100             │
│ End (C5):   108             │
│ Magnitude: |108 - 100| = 8  │
└─────────────────────────────┘

VALIDATION 1: Window size
└─ Check: len(trend_window) >= 3 ✓ (4 candles)

VALIDATION 2: Magnitude threshold
└─ Check: 8 >= MIN_TREND_MAGNITUDE (6.5) ✓

VALIDATION 3: Open price extremes
└─ Analyze positions of L (lowest) and H (highest) opens
```

### Open Price Extremes Validation

```
UPTREND Pattern:
─────────────────

Trend Window: [C2=100, C3=102, C4=101, C5=108]
Opens:        [  100,   102,   101,   108]
              
L = 100 (C2 position: 0)
H = 108 (C5 position: 3)

CHECKS (with TREND_WINDOW_EDGE_SLICE = 3):
├─ L before H? 0 < 3 ✓
├─ L near start? 0 - 0 = 0 <= 3 ✓
└─ H near end? (4-1) - 3 = 0 <= 3 ✓

Result: UPTREND ✓


DOWNTREND Pattern:
──────────────────

Trend Window: [C2=108, C3=106, C4=107, C5=100]
Opens:        [  108,   106,   107,   100]

H = 108 (C2 position: 0)
L = 100 (C5 position: 3)

CHECKS (with TREND_WINDOW_EDGE_SLICE = 3):
├─ H before L? 0 < 3 ✓
├─ H near start? 0 - 0 = 0 <= 3 ✓
└─ L near end? (4-1) - 3 = 0 <= 3 ✓

Result: DOWNTREND ✓
```

### Why Open Price Extremes Matter

```
This validation FILTERS OUT:
├─ Consolidation patterns (mixed high/low positions)
├─ Zigzag patterns (extremes not at edges)
├─ Weak trends (not clearly directional)
└─ Noise (natural trend should have clean structure)

EXAMPLE: This would FAIL for UPTREND
┌─────────────────────────────┐
│ Zigzag: [100, 102, 99, 108] │
│ Opens:  [100, 102, 99, 108] │
│                             │
│ L = 99 (position 2)        │
│ H = 108 (position 3)       │
│                             │
│ L near start? 2 <= 3 ✓ but │
│ L NOT in first 3! Pos=2   │
│ Actually close, maybe OK   │
│                             │
│ If stricter: Fails validation
└─────────────────────────────┘
```

---

## 3. Confirmation Window Validation (Step 3)

### Window Extraction

```
LOOKBACK WINDOW: [C1, C2, C3, C4, C5_alert]

AFTER STEP 2:
├─ window_trend = UPTREND
├─ min_vol_candle = C2
└─ max_vol_candle = C5

STEP 3 INPUT: Slice from C5 (max_vol) to end of window
┌─────────────────────────────┐
│ CONFIRMATION WINDOW:        │
│ [C5]                        │
│ └──┘                        │
│ Just 1 candle in this case │
│                             │
│ But in larger windows:      │
│ [C5, C6, C7, ...C15]       │
│ └────────────────┘         │
│ Can be many candles        │
└─────────────────────────────┘

VALIDATION 1: Window extraction
└─ Check: extraction successful ✓

VALIDATION 2: Window size
└─ Check: len(confirmation_window) >= 3
   └─ 1 candle < 3? ❌ WOULD FAIL in this case

VALIDATION 3: Peak/Trough prominence (if size >= 3)
└─ Not applicable if window too small
```

### Peak/Trough Prominence

```
FOR UPTREND (expecting peak):
─────────────────────────────

Confirmation Window: [C5, C6, C7, C8, C9]
Highs:               [110, 115, 120, 118, 112]
Lows:                [105, 112, 115, 114, 108]

Peak = C7 (highest high: 120)

PROMINENCE calculation for C7:
└─ Measures strength relative to neighbors
   ├─ High: 120
   ├─ Left neighbor (C6) high: 115
   ├─ Right neighbor (C8) high: 118
   └─ Prominence ≈ 120 - max(115, 118) = 2

Check: 1.5 <= 2 <= 3.0? ✓ PASS


FOR DOWNTREND (expecting trough):
──────────────────────────────────

Confirmation Window: [C5, C6, C7, C8, C9]
Highs:               [110, 105, 100, 102, 108]
Lows:                [105, 100,  95,  98, 104]

Trough = C7 (lowest low: 95)

PROMINENCE calculation for C7:
└─ Measures strength relative to neighbors
   ├─ Low: 95
   ├─ Left neighbor (C6) low: 100
   ├─ Right neighbor (C8) low: 98
   └─ Prominence ≈ max(100, 98) - 95 = 3

Check: 1.5 <= 3 <= 3.0? ✓ PASS (barely!)
```

### What Prominence Range Prevents

```
TOO LOW (< 1.5): Weak reversal
├─ Peak/trough is barely distinct from neighbors
├─ Indicates potential noise or consolidation
└─ Example: Peak within 0.5 points of neighbors

TOO HIGH (> 3.0): Overextended move
├─ Extreme spike or crash
├─ May indicate exhaustion
├─ Market might gap back through
└─ Example: Peak 5+ points above neighbors

OPTIMAL (1.5-3.0): High-quality reversal
├─ Clear peak/trough with good definition
├─ Not extreme, not weak
├─ Likely to sustain initial reversal
└─ Sweet spot for trading signal
```

---

## 4. Cooldown Check (Step 4)

### Mechanism

```
AFTER STEP 3: Confirmation passed
├─ window_trend = UPTREND
├─ reversal_trend = DOWNTREND (opposite)
└─ reversal_signal = SELL (derived from trend)

STEP 4 LOGIC:
┌──────────────────────────────────┐
│ Prevent Signal Spam              │
│                                  │
│ Check: LATEST_ALERT class var   │
│        └─ Last alert generated  │
│                                  │
│ If LATEST_ALERT exists:         │
│ ├─ Symbol match? (same stock)   │
│ ├─ Signal match? (SELL = SELL?)  │
│ └─ Time check: within cooldown? │
│    └─ COOLDOWN_WINDOW = 3       │
│    └─ Current candle - Alert    │
│        candle <= 3?             │
│                                  │
│ If ALL match → Skip (in cooldown)│
│ Otherwise → Continue to Step 5  │
└──────────────────────────────────┘

Example Cooldown:
├─ LATEST_ALERT created at C10 with SELL
├─ Current window analyzing: C12
├─ Distance: 12 - 10 = 2 <= 3 ✓ IN COOLDOWN → SKIP
│
├─ Current window analyzing: C13
├─ Distance: 13 - 10 = 3 <= 3 ✓ IN COOLDOWN → SKIP
│
├─ Current window analyzing: C14
├─ Distance: 14 - 10 = 4 > 3 ❌ NOT IN COOLDOWN → CONTINUE
```

---

## 5. Alert Creation (Step 5)

### What Gets Created

```
IF ALL STEPS PASS:
┌────────────────────────────────┐
│ AlertData object created       │
├────────────────────────────────┤
│ symbol: "AAPL"                 │
│ signal: SELL (reversal_signal) │
│ trend: DOWNTREND (reversal_trend)
│ candle: C15 (the alert candle) │
│ magnitude: 8.5 (window_size)   │
│ timestamp: C15 time            │
│ details: (window_trend, vols)  │
└────────────────────────────────┘

CLASS VARIABLE UPDATE:
├─ VraExecutor.LATEST_ALERT = new AlertData
└─ Used by future iterations for cooldown

EXECUTION MODE CHECK:
├─ Development: Continue loop
└─ Production: Return immediately (one alert per run)
```

---

## 6. Complete Step Comparison

### All 5 Steps at a Glance

```
┌─ STEP 1: VOLUME ──────────────────────────────┐
│ Purpose: Identify volume spike                 │
│ Input: Full lookback window                    │
│ Output: max_vol_candle, min_vol_candle        │
│ Validations: 4                                 │
│  ├─ Max volume exists                          │
│  ├─ Min volume found (before max)             │
│  ├─ Ratio >= 4.5                              │
│  └─ Max >= Alert × 2.0                        │
└────────────────────────────────────────────────┘

┌─ STEP 2: TREND ───────────────────────────────┐
│ Purpose: Validate trend structure              │
│ Input: Slice from min_vol to alert             │
│ Output: window_trend, window_magnitude        │
│ Validations: 3 groups                          │
│  ├─ Window size >= 3                          │
│  ├─ Magnitude >= 6.5                          │
│  └─ Open extremes in correct positions        │
│     ├─ For UPTREND: Low early, High late      │
│     └─ For DOWNTREND: High early, Low late    │
└────────────────────────────────────────────────┘

┌─ STEP 3: CONFIRMATION ────────────────────────┐
│ Purpose: Validate reversal zone quality        │
│ Input: Slice from max_vol to end               │
│ Output: Confirmation status (bool)             │
│ Validations: 3                                 │
│  ├─ Window extraction successful              │
│  ├─ Window size >= 3                          │
│  └─ Peak/Trough prominence in [1.5, 3.0]    │
│     ├─ UPTREND: Find highest peak prominence  │
│     └─ DOWNTREND: Find lowest trough          │
└────────────────────────────────────────────────┘

┌─ STEP 4: COOLDOWN ────────────────────────────┐
│ Purpose: Prevent alert spam                    │
│ Input: Current signal, last alert info         │
│ Output: Can proceed (bool)                     │
│ Validation: 1 check                            │
│  └─ Not in cooldown window (3 candles)       │
└────────────────────────────────────────────────┘

┌─ STEP 5: CREATION ────────────────────────────┐
│ Purpose: Generate alert object                 │
│ Input: All passed validations                  │
│ Output: AlertData object                       │
│ Action: 2 operations                           │
│  ├─ Create AlertData                           │
│  └─ Update LATEST_ALERT                        │
└────────────────────────────────────────────────┘
```

---

## 7. Configuration Parameters Reference

### Current v3 Settings (9 parameters)

```
PARAMETER                           DEFAULT    STEP USED
──────────────────────────────────────────────────────────
LOOKBACK_WINDOW                     15         All steps
VOLUME_MULTIPLIER                   4.5        Step 1
MIN_TREND_MAGNITUDE                 6.5        Step 2
TREND_WINDOW_EDGE_SLICE             3          Step 2
MIN_CONFIRMATION_WINDOW_CANDLES     3          Step 3
VOLUME_MULTIPLIER_BY_REVERSAL_TREND 2.0        Step 1
MIN_PEAK_TROUGH_PROMINENCE          1.5        Step 3
MAX_PEAK_TROUGH_PROMINENCE          3.0        Step 3
COOLDOWN_WINDOW                     3          Step 4
```

### Sensitivity Adjustment Guide

```
TO INCREASE ALERT FREQUENCY:
├─ Reduce VOLUME_MULTIPLIER (4.5 → 3.5)
├─ Reduce MIN_TREND_MAGNITUDE (6.5 → 5.0)
├─ Reduce TREND_WINDOW_EDGE_SLICE (3 → 2)
├─ Reduce MIN_PEAK_TROUGH_PROMINENCE (1.5 → 1.0)
└─ Reduce COOLDOWN_WINDOW (3 → 1)

TO DECREASE ALERT FREQUENCY:
├─ Increase VOLUME_MULTIPLIER (4.5 → 6.0)
├─ Increase MIN_TREND_MAGNITUDE (6.5 → 8.0)
├─ Increase TREND_WINDOW_EDGE_SLICE (3 → 5)
├─ Increase MAX_PEAK_TROUGH_PROMINENCE (3.0 → 4.0)
└─ Increase COOLDOWN_WINDOW (3 → 5)

SIGNAL QUALITY vs FREQUENCY TRADEOFF:
├─ Tight parameters (strict): Fewer, higher-quality alerts
├─ Loose parameters (relaxed): More alerts, potentially lower quality
└─ Sweet spot: Validated through backtesting
```

---

## 8. Key Implementation Characteristics (v3)

| Characteristic | Value | Notes |
|---|---|---|
| **Loop direction** | Reverse (newest first) | `range(loop_end, loop_start - 1, -1)` |
| **Window extraction** | Slice method | `analyzer.slice_window()` |
| **Volume checks** | Dual-validation | Ratio + absolute threshold |
| **Trend validation** | Multi-part | Size, magnitude, structure |
| **Peak/Trough calc** | prominence-based | Not just price range |
| **Confirmation window** | Starts at max_vol | Isolates reversal zone |
| **Cooldown tracking** | Class variable | `VraExecutor.LATEST_ALERT` |
| **Return pattern** | Single/multiple | Depends on deployment mode |
| **Validation depth** | 15+ checks | Comprehensive quality control |

---

## 9. Error Paths and Recovery

```
Each step can fail independently:

┌─ STEP 1 FAILS (Volume check) ────────┐
│ Action: Continue to next candle      │
│ No penalty, just try next window     │
└─────────────────────────────────────┘

┌─ STEP 2 FAILS (Trend structure) ────┐
│ Action: Continue to next candle      │
│ Window trend not clear enough        │
│ Next candle might have better trend  │
└─────────────────────────────────────┘

┌─ STEP 3 FAILS (Confirmation) ───────┐
│ Action: Continue to next candle      │
│ Reversal zone not high-quality       │
│ Wait for better setup                │
└─────────────────────────────────────┘

┌─ STEP 4 FAILS (Cooldown) ──────────┐
│ Action: Continue to next candle      │
│ Signal would spam, skip this window  │
│ LATEST_ALERT will eventually age out │
└─────────────────────────────────────┘

COMPLETE FAILURE: No alerts found
└─ Return empty alerts list
└─ Executor continues monitoring
```

---

## 10. Visual Timeline of Alert Generation

```
TIME →

Candles: [C1, C2, C3, C4, C5, C6, C7, C8, C9, C10]
Analysis: Loop from C10 backwards

Window 1: [C1-C10] analyze...
  ├─ STEP 1: ❌ Volume fails (not enough spike)
  └─ Skip

Window 2: [C2-C11] - doesn't exist, end loop

Actually, assume 15-candle window:
Window 1: [C1-C15] analyze...
  ├─ STEP 1: ✓ Volume OK
  ├─ STEP 2: ✓ Trend OK  
  ├─ STEP 3: ✓ Confirmation OK
  ├─ STEP 4: ✓ Cooldown OK
  └─ STEP 5: ✓ ALERT CREATED! (at C15)
     └─ LATEST_ALERT = Alert(C15, SELL)

Window 2: [C2-C16] analyze...
  ├─ STEP 1: ✓ Volume OK
  ├─ STEP 2: ✓ Trend OK
  ├─ STEP 3: ✓ Confirmation OK
  ├─ STEP 4: ❌ Cooldown FAIL
  │  └─ Distance: C16 - C15 = 1 <= 3 → IN COOLDOWN
  └─ Skip (no alert generated)

Window 3: [C3-C17] analyze...
  ├─ STEP 1: ✓ Volume OK
  ├─ STEP 2: ✓ Trend OK
  ├─ STEP 3: ✓ Confirmation OK
  ├─ STEP 4: ❌ Cooldown FAIL
  │  └─ Distance: C17 - C15 = 2 <= 3 → IN COOLDOWN
  └─ Skip (no alert generated)

Window 4: [C4-C18] analyze...
  ├─ STEP 1: ✓ Volume OK
  ├─ STEP 2: ✓ Trend OK
  ├─ STEP 3: ✓ Confirmation OK
  ├─ STEP 4: ✓ Cooldown OK!
  │  └─ Distance: C18 - C15 = 3 <= 3 → BORDERLINE, passes
  └─ Continue or STEP 5?
     └─ Actually: 3 == 3, so typically IN cooldown still
     
Wait until Window 5: [C5-C19] 
  ├─ Distance: C19 - C15 = 4 > 3 → NOT IN COOLDOWN ✓
  ├─ STEP 5: ✓ ALERT CREATED! (at C19)
  └─ LATEST_ALERT = Alert(C19, SELL or BUY?)
```

