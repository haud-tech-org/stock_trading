# Anchor-Signal-Candle (ASC) Approach - Visual Reference Guide

**Purpose**: Visual representation of the ASC approach validations and flow  
**Date**: April 10, 2026

---

## 📊 Validation 1: Window Analysis

### Window Trend Identification

```
UPTREND Example:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    High ──────────────── ← Window Peak (HIGH prices)
    |                    /
    |        ╱╲ ╱╲     ╱
    |      ╱    ╲  ╲   ╱  ← Price Action
    |    ╱        ╲  ╲╱
    |  ╱            ╲
    Low ─────────────── ← Window Trough (LOW prices)
    
    First Close (start)  →  Last Close (end) 
    [Lower value] ──────→ [Higher value]
    
    ✓ Trend = UPTREND
    ✓ Window Size = High - Low
    ✓ Must pass: Window Size >= min_size_price_window


DOWNTREND Example:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    High ──────────────── ← Window Peak (HIGH prices)
    |  ╲            ╱
    |    ╲  ╱╲    ╱
    |      ╲╱  ╲╱ ╱╲  ← Price Action
    |           ╲╱  ╲╱
    |                ╲
    Low ─────────────── ← Window Trough (LOW prices)
    
    First Close (start)  →  Last Close (end)
    [Higher value] ────→ [Lower value]
    
    ✓ Trend = DOWNTREND
    ✓ Window Size = High - Low
    ✓ Must pass: Window Size >= min_size_price_window
```

---

## 📊 Validation 2: Anchor Candle Identification

### Large Body Detection

```
ANCHOR CANDLE (Largest HIGH-LOW Range in Window):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Window of N candles with body sizes: [S1, S2, S3, S4, ... Sn]
Body Size = HIGH - LOW (full range for each candle)

Example:
Candle 1: ╭─ High
         │ ├─ Close
         │ ├─ Open      (body = small)
         ╰─ Low

Candle 2: ╭─ High
         │ │            (LARGEST RANGE ★)
         │ ├─ Close
         │ ├─ Open
         │ │
         ╰─ Low

Candle 3: ╭─ High
         │ ├─ Close     (body = small)
         │ ├─ Open
         ╰─ Low

VALIDATION LOGIC:
1. Find: candle with MAX(HIGH - LOW) in window
2. Calculate: average_body = SUM(all HIGH-LOW) / N candles
3. Checks (BOTH must pass):
   ✓ Anchor Body >= min_size_candle (absolute threshold)
   ✓ Anchor Body >= (multiplier_size × average_body)

Example with multiplier_size = 1.5:
  Average = 0.5, Anchor = 0.8
  0.8 >= 0.01 (min_size_candle) ✓
  0.8 >= 1.5 × 0.5 = 0.75 ✓ BOTH PASS

  Average = 0.5, Anchor = 0.7
  0.7 >= 0.01 (min_size_candle) ✓
  0.7 >= 1.5 × 0.5 = 0.75 ✗ FAILS MULTIPLIER CHECK
```

---

## 📊 Validation 3: Signal Candle Identification

### High Volume Detection After Anchor

```
SIGNAL CANDLE (Maximum Volume in Logical Window):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Full Window:
[C1] [C2] [ANCHOR★] [C4] [C5] [C6] [C7] [SIGNAL★] [C9]

LOGICAL WINDOW:
                 ↓ Start here     ↓ End here
                 └─────────────────────────┘
                 [ANCHOR★] [C4] [C5] [C6] [C7] [SIGNAL★] [C9]

Volume Analysis:
Candle:  C1    C2    ANCHOR  C4    C5    C6    C7   SIGNAL   C9
Volume: 1000  2000   5000   1500  1200  2500  3000  8000★   1500
                     (starting point for search)

VALIDATION LOGIC:
1. Average Volume = Sum of all volumes in FULL window / N candles
2. Signal Volume = Maximum volume in logical_window
3. Checks:
   ✓ Signal Volume >= min_volume (absolute threshold)
   ✓ Signal Volume >= (multiplier_volume × average_volume)

Example with multiplier_volume = 1.2:
  Average = 3000, Signal = 8000
  8000 >= 1.2 × 3000 = 3600 ✓ PASS
  8000 >= 100000 (min_volume) ✓ PASS

  Average = 3000, Signal = 3000
  3000 >= 1.2 × 3000 = 3600 ✗ FAIL (not sufficiently large)
```

---

## 📊 Validation 4: Alert Candle Confirmation

### Final Candle Validation (Doji Check, Close-to-Extreme & Wick Validation)

```
PRE-CHECK: Alert Candle is NOT a Doji
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DOJI Definition:
Body Size / Candle Range < 0.05 (body is less than 5% of total range)

Example:
Scenario 1: Regular Candle (NOT Doji) ✓
╭─ High
│ ├─ Upper Wick
│ ├─ Close    ← Body = |CLOSE - OPEN| = 0.3
│ ├─ Open
│ ├─ Lower Wick
╰─ Low
  Candle Range (HIGH - LOW) = 1.0
  Body Ratio = 0.3 / 1.0 = 0.30 (30%)
  0.30 >= 0.05 ✓ NOT DOJI → PASS CHECK

Scenario 2: Doji Candle (FAIL) ✗
╭─ High
│ │
│ ├─ Close ─┐
│ ├─ Open  ─┤─→ Body = |CLOSE - OPEN| = 0.02
│ │       ─┘
│ │
╰─ Low
  Candle Range (HIGH - LOW) = 1.0
  Body Ratio = 0.02 / 1.0 = 0.02 (2%)
  0.02 < 0.05 ✗ IS DOJI → FAIL CHECK

If Alert Candle is Doji: STOP, skip to next window


UPTREND ALERT CANDLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Window view:
[Candle 1] [Candle 2] ... [SIGNAL] ... [ALERT★] ← Must be LAST candle

Price grid showing window extremes:

         HIGH (window max)
         
         [ALERT CANDLE]
         
         Body = CLOSE - OPEN (green/positive)
         Upper Wick = HIGH - CLOSE ← Validation target
         Candle Range = HIGH - LOW
         
         CLOSE-TO-EXTREME THRESHOLD (NEW):
         ─────────────────────────────
         For UPTREND: (window_max_high - CLOSE) <= close_to_extreme_threshold
         For DOWNTREND: (CLOSE - window_min_low) <= close_to_extreme_threshold
         (Alert candle close must be as close as possible to the window extreme in the direction of the trend, within a configurable price threshold. For uptrend, close just below the high; for downtrend, close just above the low.)
         
         Wick Percentage Validation:
         ─────────────────────────────
         upper_wick_size = HIGH - CLOSE
         wick_percentage = upper_wick_size / candle_range
         
         Must satisfy: min_percentage <= wick_percentage <= max_percentage
         
         Example (min=0.2, max=0.6):
         
         Scenario 1: Wick too small (0.1)
         ╭─ HIGH
         │ ├─ Small Upper Wick (0.1 × body)  ✗ FAIL (0.1 < 0.2)
         │ ├─ CLOSE
         │ ├─ OPEN
         ╰─ LOW
         
         Scenario 2: Wick perfect (0.4)
         ╭─ HIGH
         │ ├─ Good Upper Wick (0.4 × body)  ✓ PASS (0.2 ≤ 0.4 ≤ 0.6)
         │ ├─ CLOSE
         │ ├─ OPEN
         ╰─ LOW
         
         Scenario 3: Wick too large (0.8)
         ╭─ HIGH
         │ │
         │ ├─ Excessive Upper Wick (0.8 × body)  ✗ FAIL (0.8 > 0.6)
         │ ├─ CLOSE
         │ ├─ OPEN
         ╰─ LOW


DOWNTREND ALERT CANDLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Window view:
[Candle 1] [Candle 2] ... [SIGNAL] ... [ALERT★] ← Must be LAST candle

Price grid showing window extremes:

         HIGH
           ▲
           │
         CLOSE (window min)
         LOW (window min)
                        ╱ │ ╲
                      ╱   │   ╲
         
         [ALERT CANDLE]
         
         Body = OPEN - CLOSE (red/negative)
         Lower Wick = CLOSE - LOW ← Validation target
         Candle Range = HIGH - LOW
         
         CLOSE-TO-EXTREME THRESHOLD (NEW):
         ─────────────────────────────
         For DOWNTREND: (CLOSE - window_min_low) <= close_to_extreme_threshold
         (Alert candle close must be as close as possible to the window low, within a configurable price threshold. For downtrend, close just above the low.)
         
         Wick Percentage Validation:
         ─────────────────────────────
         lower_wick_size = CLOSE - LOW
         wick_percentage = lower_wick_size / candle_range
         
         Must satisfy: min_percentage <= wick_percentage <= max_percentage
```

---

## 🔄 Complete Validation Sequence

```
START: Extract lookback_window_df (50 candles, for example)
│
├─► VALIDATION 1: Window Analysis
│   ├─ Calculate: window_size = MAX(HIGH) - MIN(LOW)
│   ├─ Determine: trend from first_close vs. last_close
│   ├─ Check: window_size >= min_size_price_window
│   └─ Output: (window_size, trend) or FAIL → SKIP THIS WINDOW
│
├─► VALIDATION 2: Anchor Candle
│   ├─ Find: candle with MAX(HIGH - LOW) in window
│   ├─ Calculate: average_body = SUM(HIGH-LOW) / N
│   ├─ Check: anchor_body >= min_size_candle
│   ├─ Check: anchor_body >= (multiplier_size × average_body)
│   └─ Output: anchor_candle or FAIL → SKIP THIS WINDOW
│
├─► VALIDATION 3: Signal Candle
│   ├─ Define: logical_window from anchor onwards
│   ├─ Calculate: average_volume = MEAN(all volumes) in window
│   ├─ Find: candle with MAX(volume) in logical_window
│   ├─ Check: signal_volume >= min_volume
│   ├─ Check: signal_volume >= (multiplier_volume × average_volume)
│   └─ Output: signal_candle or FAIL → SKIP THIS WINDOW
│
├─► VALIDATION 4: Alert Candle
│   ├─ Extract: alert_candle = window[-1] (always last)
│   ├─ Check: alert_index >= signal_index
│   │
│   ├─► 4a: Doji Check
│   │   ├─ Check: |CLOSE - OPEN| / (HIGH - LOW) < 0.05
│   │   └─ If IS DOJI → FAIL → SKIP THIS WINDOW
│   │
│   ├─► 4b: Close-to-Extreme Threshold (NEW)
│   │   ├─ For UPTREND: |alert_candle.CLOSE - window_max_high| <= close_to_extreme_threshold
│   │   └─ For DOWNTREND: |alert_candle.CLOSE - window_min_low| <= close_to_extreme_threshold
│   │   (Alert candle close must be within a configurable price threshold of the window extreme)
│   │
│   │   ├─ Calculate: upper_wick_percentage = (HIGH - CLOSE) / candle_range (uptrend)
│   │   └─ Calculate: lower_wick_percentage = (CLOSE - LOW) / candle_range (downtrend)
│   │   └─ Check: min_pct <= wick_pct <= max_pct
│   │
│   └─ Output: True or FAIL → SKIP THIS WINDOW
│
├─► DETERMINE REVERSAL SIGNAL
│   ├─ If original_trend == UPTREND → reversal = DOWNTREND → Signal = SELL
│   ├─ If original_trend == DOWNTREND → reversal = UPTREND → Signal = BUY
│   └─ Note: Alert is for the REVERSAL trend, not the window trend
│
├─► COOLDOWN CHECK
│   ├─ Check: time since last alert >= cooldown_window (minutes)
│   └─ Output: Pass or FAIL → SKIP THIS WINDOW
│
└─► CREATE ALERT
    ├─ Signal: BUY (if reversal=UPTREND) or SELL (if reversal=DOWNTREND)
    ├─ Trend: Reversal trend
    ├─ Alert Price: alert_candle.CLOSE
    ├─ Magnitude: window_size from Validation 1
    ├─ Details: Include anchor/signal/alert info
    └─ Return: AlertData object
```

---

## 🎯 Summary Table: Validation Requirements

| Validation | Primary Input | Checks | Key Metric | Pass Condition |
|---|---|---|---|---|
| **1. Window** | lookback_window | Size & Trend | window_high - window_low | >= min_size_price_window |
| **2. Anchor** | lookback_window | Body Size | anchor_body / avg_body | >= multiplier_size |
| **3. Signal** | anchor_candle onwards | Volume Rank | signal_vol / avg_vol | >= multiplier_volume |
| **4a. Doji** | alert_candle (last) | Body Ratio | body / candle_range | < 0.05 to FAIL |
| **4b. Extremes** | alert_candle (last) | Trend-based | HIGH or LOW extremes | Must be window extreme |
| **4c. Wick** | alert_candle (last) | Wick Range | wick_size / body_size | in [min%, max%] |

---

## ⚠️ CRITICAL: Signal Generation Logic

**This approach detects REVERSAL patterns, not continuation patterns:**

```
Window Trend Analysis    →    Reversal Detection    →    Alert Signal
───────────────────────      ────────────────────       ─────────────

UPTREND in window        →    Uptrend is reversing  →    SELL alert
(prices rising)                (bearish reversal)       (BUY calls would be late)

DOWNTREND in window      →    Downtrend is reversing →    BUY alert  
(prices falling)              (bullish reversal)       (SELL calls would be late)
```

**Why the reversal?** The anchor-signal-candle pattern indicates exhaustion of the current trend and potential reversal. The alert is generated for the NEW trend beginning, not the old trend continuing.

**Execution Implementation:**
```python
# From executor.py:
reversal_trend = Trend.DOWNTREND if trend == Trend.UPTREND else Trend.UPTREND
reversal_signal = candle_utils.get_signal_from_trend(reversal_trend)
# Then create alert with reversal_signal and reversal_trend
```

---

## ⚙️ Configuration Example Values

All configuration values are stored in `src/stockreports/config/signal_settings.py` under `APPROACH_CONFIG["REVERSAL_ANCHOR_SIGNAL_CANDLE"]`:

```python
REVERSAL_ANCHOR_SIGNAL_CANDLE = {
  # Lookback window size
  "LOOKBACK_WINDOW": 11,              # Analyze 11 candles per window

  # Validation 1: Window size threshold
  "MIN_SIZE_PRICE_WINDOW": 750,       # Minimum 750 price units range

  # Validation 2: Anchor candle thresholds
  "MIN_SIZE_CANDLE": 150,             # Anchor body must be >= 150 price units
  "MULTIPLIER_SIZE": 1.3,             # Anchor >= 1.3x average body size

  # Validation 3: Signal candle thresholds
  "MIN_VOLUME": 1500,                 # Absolute minimum volume
  "MULTIPLIER_VOLUME": 2.5,           # Signal >= 2.5x average volume

  # Validation 4: Alert candle thresholds
  "MIN_PERCENTAGE": 0.01,             # Minimum wick 1% of body size
  "MAX_PERCENTAGE": 0.4,              # Maximum wick 40% of body size
  "ALERT_CANDLE_CLOSE_TO_EXTREME_THRESHOLD": 150.0, # Close must be within 150 price units of window extreme

  # Cooldown validation
  "COOLDOWN_WINDOW": 3,               # 3 minutes between alerts
}
```

**Note**: These values are loaded from the orchestrator configuration (see `executor_approach_configuration.json`). Access them in code via:
```python
settings = ReversalAnchorSignalCandleSettings(symbol)
settings.lookback_window          # 11
settings.min_size_price_window    # 750
settings.min_size_candle          # 150
settings.multiplier_size          # 1.3
settings.min_volume               # 1500
settings.multiplier_volume        # 2.5
settings.min_percentage           # 0.01
settings.max_percentage           # 0.4
settings.alert_candle_close_to_extreme_threshold  # 150.0
settings.cooldown_window          # 3
```

---

## 🔍 Code Reference Mapping


This visual reference directly corresponds to these codebase components:

**Validation Logic:**
- `src/stockreports/alert/approach/REVERSAL_ANCHOR_SIGNAL_CANDLE/validator.py`
  - `validate_window_size()` - Validation 1
  - `validate_anchor_candle()` - Validation 2
  - `validate_signal_candle()` - Validation 3
  - `validate_alert_candle_is_doji()` - Validation 4a
  - `validate_alert_candle_close_to_extreme()` - Validation 4b (NEW: close-to-extreme threshold)
  - `validate_alert_candle_wick()` - Validation 4c
  - `validate_not_in_cooldown()` - Cooldown check

**Analysis Logic:**
- `src/stockreports/alert/approach/REVERSAL_ANCHOR_SIGNAL_CANDLE/analyzer.py`
  - `analyze_window_trend()` - Step 1
  - `find_anchor_candle()` - Step 2
  - `find_signal_candle()` - Step 3
  - `calculate_wick_percentage()` - Step 4c
  - `calculate_average_body_size()` - Baseline for anchor
  - `calculate_average_volume()` - Baseline for signal

**Execution Logic:**
- `src/stockreports/alert/approach/REVERSAL_ANCHOR_SIGNAL_CANDLE/executor.py`
  - `_find_alerts()` - Main entry point (complete sequence)
  - `_step_analyze_window_trend()` - Step 1 execution
  - `_step_validate_anchor_candle()` - Step 2 execution
  - `_step_validate_signal_candle()` - Step 3 execution
  - `_step_validate_alert_candle()` - Step 4 execution (4a, 4b, 4c)

**Configuration:**
- `src/stockreports/alert/approach/REVERSAL_ANCHOR_SIGNAL_CANDLE/settings.py`
  - Loads all parameters from the orchestrator configuration (`executor_approach_configuration.json`)

---

**END OF VISUAL REFERENCE**

Use this guide alongside approach documentation for complete understanding of reversal detection.

