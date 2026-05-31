# Anchor-Signal-Candle (ASC) Approach - Analysis & Design Document

**Purpose**: Define and clarify all validations for the new Anchor-Signal-Candle approach  
**Status**: 🔄 AWAITING REVIEW AND CLARIFICATION  
**Date**: April 10, 2026

---

## 📋 Executive Summary

This document describes a new trading approach that detects alerts by identifying three sequential price events:
1. **Anchor Candle**: A candle with abnormally large body size relative to the window average
2. **Signal Candle**: A high-volume candle occurring at or after the anchor candle
3. **Alert Candle**: The final candle meeting specific price and wick requirements

The approach works exclusively within a lookback window and analyzes price action in response to significant volume and volatility events.

---

## 🎯 What This Approach Detects

**Market Condition**: Reversal signals following high-volume price expansion events.

**Key Trading Rules**:
1. Window must show significant price movement (high - low) >= min_size_price_window
2. Identify the **anchor candle** (highest body size in window), which represents abnormal volatility
3. Identify the **signal candle** (highest volume at or after anchor), which confirms institutional interest
4. Confirm with **alert candle** (last candle in window) that shows specific extremes and wick characteristics

**What Makes This Different**:
- Uses three distinct candle roles (anchor → signal → alert) rather than one-candle detection
- Combines volatility (anchor body) + volume (signal) + price extremes (alert) in sequence
- Requires alert candle to be final candle in window (unlike VRA which can be anywhere)
- Analyzes wick size/position on alert candle to confirm reversal potential

---

## 🔍 Detailed Validation Flow

All validations operate on a **lookback_window_df** (a slice of price data with fixed lookback_window size).

### **Validation 1: Window Size & Trend Determination**

**Name**: `Window Price Range & Trend Analysis`

**Purpose**: Ensure the lookback window has meaningful price movement to analyze.

**Input**: 
- `lookback_window_df`: Full lookback window DataFrame
- `min_size_price_window`: Minimum price range (config)

**Logic**:
```
window_high = maximum HIGH price in lookback_window
window_low = minimum LOW price in lookback_window
window_size = window_high - window_low

IF window_size < min_size_price_window:
    FAIL: "Window price range insufficient"
    RETURN None

Determine trend:
    - first_close = lookback_window.close[0]
    - last_close = lookback_window.close[-1]
    IF last_close > first_close:
        trend = UPTREND
    ELSE IF last_close < first_close:
        trend = DOWNTREND
    ELSE:
        FAIL: "Cannot determine trend (first close == last close)"
        RETURN None

PASS: (window_size, trend)
```

**Configuration Parameters**:
- `min_size_price_window`: float (minimum price range for valid window, e.g., 0.5)

**Returns**: 
- `Tuple[Optional[float], Optional[Trend]]`: (window_size, trend) or (None, None) on failure

**Key Points**:
- Window size uses HIGH/LOW extremes (not close)
- Trend determined by first vs. last CLOSE prices
- Must establish clear trend direction before proceeding

---

### **Validation 2: Anchor Candle Identification**

**Name**: `Anchor Candle Validation`

**Purpose**: Identify the candle with abnormally large body size as the "anchor" of price movement.

**Input**:
- `lookback_window_df`: Full lookback window DataFrame
- `min_size_candle`: Minimum body size threshold (config, e.g., 0.01)
- `multiplier_size`: Multiplier for average body size (config, e.g., 1.5)

**Logic**:
```
Step 1: Calculate average candle body size in window
    total_body_size = SUM of (HIGH - LOW) for all candles in window
    average_candle_size = total_body_size / number_of_candles

Step 2: Find candle with largest body size
    max_body_candle = candle in window with MAX(body_size)
    max_body_size = max_body_candle.HIGH - max_body_candle.LOW

Step 3: Validate anchor candle meets BOTH thresholds
    IF max_body_size < min_size_candle:
        FAIL: "Largest candle body too small"
        RETURN None
    
    IF max_body_size < (multiplier_size * average_candle_size):
        FAIL: "Largest candle not significantly larger than average"
        RETURN None

PASS: max_body_candle
```

**Configuration Parameters**:
- `min_size_candle`: float (minimum absolute body size, e.g., 0.01)
- `multiplier_size`: float (size multiplier vs. average, e.g., 1.5x)

**Returns**:
- `Optional[pd.Series]`: Anchor candle row if passes all checks, None otherwise

**Key Points**:
- Body size = HIGH - LOW (not CLOSE - OPEN for this validation)
- Anchor candle must be abnormally large compared to window average
- This ensures we identify unusual volatility events

---

### **Validation 3: Signal Candle Identification**

**Name**: `Signal Candle Validation`

**Purpose**: Identify the highest-volume candle occurring at or after the anchor candle.

**Input**:
- `lookback_window_df`: Full lookback window DataFrame
- `anchor_candle`: pd.Series (identified in Validation 2)
- `min_volume`: Minimum volume threshold (config, e.g., 100000)
- `multiplier_volume`: Multiplier for average volume (config, e.g., 1.2x)

**Logic**:
```
Step 1: Define logical_window (anchor candle onwards)
    anchor_index = position of anchor_candle in lookback_window
    logical_window = lookback_window[anchor_index : end]

Step 2: Calculate average volume in full lookback_window
    average_volume = MEAN of all volumes in lookback_window

Step 3: Find maximum volume candle in logical_window
    max_vol_candle = candle in logical_window with MAX(volume)
    max_volume = max_vol_candle.volume

Step 4: Validate signal candle meets BOTH thresholds
    IF max_volume < min_volume:
        FAIL: "Maximum volume below absolute threshold"
        RETURN None
    
    IF max_volume < (multiplier_volume * average_volume):
        FAIL: "Maximum volume not significantly larger than average"
        RETURN None

PASS: max_vol_candle
```

**Configuration Parameters**:
- `min_volume`: float (minimum absolute volume, e.g., 100000)
- `multiplier_volume`: float (volume multiplier vs. average, e.g., 1.2x)

**Returns**:
- `Optional[pd.Series]`: Signal candle row if passes all checks, None otherwise

**Key Points**:
- Searches from anchor candle onwards (not entire window)
- Volume must exceed both absolute threshold AND average-relative threshold
- This confirms institutional/significant market interest after volatility

---

### **Validation 4: Alert Candle Confirmation**

**Name**: `Alert Candle & Wick Validation`

**Purpose**: Confirm the final candle shows extremes and wick characteristics consistent with reversal.

**Input**:
- `lookback_window_df`: Full lookback window DataFrame
- `signal_candle`: pd.Series (identified in Validation 3)
- `window_trend`: Trend enum (from Validation 1)
- `min_percentage`: float (minimum wick as % of candle size, config, e.g., 0.2 = 20%)
- `max_percentage`: float (maximum wick as % of candle size, config, e.g., 0.6 = 60%)

**Logic**:
```
alert_candle = lookback_window[-1]  # Always the last candle in window

Step 1: Verify alert candle is at or after signal candle
    signal_index = position of signal_candle in lookback_window
    alert_index = len(lookback_window) - 1
    
    IF alert_index < signal_index:
        FAIL: "Alert candle occurs before signal candle"
        RETURN None

Step 2: Check price extremes based on trend

    IF window_trend == UPTREND:
        max_high = MAX of all HIGH prices in lookback_window
        max_close = MAX of all CLOSE prices in lookback_window
        
        IF alert_candle.HIGH != max_high:
            FAIL: "Alert candle does not have highest HIGH (uptrend)"
            RETURN None
        
        IF alert_candle.CLOSE != max_close:
            FAIL: "Alert candle does not have highest CLOSE (uptrend)"
            RETURN None
    
    ELSE IF window_trend == DOWNTREND:
        min_low = MIN of all LOW prices in lookback_window
        min_close = MIN of all CLOSE prices in lookback_window
        
        IF alert_candle.LOW != min_low:
            FAIL: "Alert candle does not have lowest LOW (downtrend)"
            RETURN None
        
        IF alert_candle.CLOSE != min_close:
            FAIL: "Alert candle does not have lowest CLOSE (downtrend)"
            RETURN None

Step 3: Validate wick size and position

    candle_body_size = ABS(alert_candle.CLOSE - alert_candle.OPEN)
    
    IF window_trend == UPTREND:
        # Upper wick = HIGH - CLOSE (in uptrend)
        upper_wick_size = alert_candle.HIGH - alert_candle.CLOSE
        wick_percentage = upper_wick_size / candle_body_size
        
        IF wick_percentage < min_percentage OR wick_percentage > max_percentage:
            FAIL: "Upper wick size outside acceptable range"
            RETURN None
    
    ELSE IF window_trend == DOWNTREND:
        # Lower wick = LOW - CLOSE (in downtrend; note: this is negative or very small)
        # Actually: lower wick = CLOSE - LOW (to get positive value)
        lower_wick_size = alert_candle.CLOSE - alert_candle.LOW
        wick_percentage = lower_wick_size / candle_body_size
        
        IF wick_percentage < min_percentage OR wick_percentage > max_percentage:
            FAIL: "Lower wick size outside acceptable range"
            RETURN None

PASS: True
```

**Configuration Parameters**:
- `min_percentage`: float (minimum wick as % of body, e.g., 0.2)
- `max_percentage`: float (maximum wick as % of body, e.g., 0.6)

**Returns**:
- `Optional[bool]`: True if alert candle passes all checks, None otherwise

**Key Points**:
- Alert candle is ALWAYS the last candle in the lookback window
- Must have window extremes (highest/lowest depending on trend)
- Wick validation ensures rejection rejection is not too small or too large
- Wick size is expressed as percentage of candle body size

---

## ⚙️ Summary of Configuration Parameters

| Parameter Name | Type | Purpose | Example |
|---|---|---|---|
| `lookback_window` | int | Size of analysis window in candles | 50 |
| `min_size_price_window` | float | Minimum window price range | 0.5 |
| `min_size_candle` | float | Minimum anchor candle body size | 0.01 |
| `multiplier_size` | float | Anchor size multiplier vs. average | 1.5 |
| `min_volume` | float | Minimum absolute volume | 100000 |
| `multiplier_volume` | float | Signal volume multiplier vs. average | 1.2 |
| `min_percentage` | float | Minimum wick as % of body | 0.2 |
| `max_percentage` | float | Maximum wick as % of body | 0.6 |
| `cooldown_window` | int | Minutes between alerts (approach-wide) | 60 |

---

## 🔄 Validation Execution Flow

```
START with lookback_window_df
    ↓
Validation 1: Window Size & Trend
    ├─ Calculate window price range
    ├─ Determine trend direction
    └─ Returns: (window_size, trend) or FAIL
    ↓
Validation 2: Anchor Candle
    ├─ Find largest body candle
    ├─ Check vs. min_size_candle
    ├─ Check vs. multiplier_size * average
    └─ Returns: anchor_candle or FAIL
    ↓
Validation 3: Signal Candle
    ├─ Define logical_window (anchor onwards)
    ├─ Find maximum volume candle
    ├─ Check vs. min_volume
    ├─ Check vs. multiplier_volume * average
    └─ Returns: signal_candle or FAIL
    ↓
Validation 4: Alert Candle
    ├─ Verify alert is final candle
    ├─ Verify after signal candle
    ├─ Check price extremes (based on trend)
    ├─ Check wick size percentage
    └─ Returns: True or FAIL
    ↓
CREATE ALERT with:
    - Signal: BUY (uptrend) or SELL (downtrend)
    - Trend: from Validation 1
    - Details: anchor/signal/alert candle info
    - Magnitude: window_size from Validation 1
```

---

## 🤔 Questions for Clarification

Before proceeding with implementation, please review and clarify:

### **Question 1: Anchor Candle Body Size Calculation**
Currently defined as: `body_size = HIGH - LOW`

**Alternative interpretation**: Should body size be `ABS(CLOSE - OPEN)` instead?
- **Current choice**: Captures full candle range regardless of open/close position (more inclusive)
- **Alternative**: Only captures actual price movement direction (more restrictive)

**Your preference**: ✅ **CONFIRMED** - Use `body_size = HIGH - LOW` (full candle range)

---

### **Question 2: Signal Candle Search Scope**
Currently: Search from anchor candle onwards for max volume

**Alternative options**:
- A) From anchor candle to end (current)
- B) From signal candle to end (after we identify it - circular dependency)
- C) Entire window with additional check that signal is at/after anchor
- D) Fixed window after anchor (e.g., next 10 candles)

**Your preference**: ✅ **CONFIRMED** - Option C) Entire window with verification that signal_index >= anchor_index

---

### **Question 3: Alert Candle Wick Validation Logic**
Currently: Wick percentage = wick_size / candle_body_size

**Edge case issue**: What if candle_body_size is 0 (doji)?
- Current code: Would cause division by zero
- Proposal: Skip wick validation for doji candles? Or fail?

**Your preference**: ✅ **CONFIRMED** - FAIL validation if body_size is 0 (reject doji alert candles)

---

### **Question 4: Window Trend Determination**
Currently: Compare first close vs. last close in window

**Alternative options**:
- A) First close vs. last close (current)
- B) Compare open/close of entire window
- C) Use slope/regression of close prices
- D) Compare first high/low vs. last high/low

**Your preference**: ✅ **CONFIRMED** - Option A) First close vs. last close

---

### **Question 5: Signal Definition - REVERSAL APPROACH**
Should we define:
- Signal = the direction based on window trend (BUY for uptrend, SELL for downtrend)?
- Or include more context like reversal type?

**Your preference**: ✅ **CONFIRMED** - **REVERSAL DETECTION APPROACH**

**Logic**:
- Determine original_trend from window (UPTREND or DOWNTREND)
- If original_trend = UPTREND → original_signal = BUY
- If original_trend = DOWNTREND → original_signal = SELL
- **If all validations pass → generate REVERSAL alert**:
  - reversal_trend = opposite of original_trend
  - reversal_signal = opposite of original_signal
  - Example: original_trend=UPTREND → reversal_trend=DOWNTREND, reversal_signal=SELL
- **Purpose**: Detect when a trend is likely to reverse based on anchor/signal/alert candle sequence

---

## 📝 Implementation Readiness Checklist

Before code generation, confirm:

- [x] All 4 validations are clearly understood
- [x] Configuration parameters are correct and complete
- [x] Clarification questions answered (ALL 5 CONFIRMED)
- [x] You've reviewed the VRA executor pattern for reference
- [x] Ready to proceed with code generation

**Status**: ✅ **READY FOR IMPLEMENTATION**

---

## 📚 Reference Materials

**Existing Similar Approaches**:
- **VRA (Volume Reversal Analysis)**: Uses window validation + volume analysis (closest match)
- **STRONG_CANDLE**: Simpler validation flow, good reference for alert creation pattern

**Architecture References**:
- Base Executor class: `src/stockreports/alert/executor.py`
- Analyzer pattern: `src/stockreports/alert/analyzer.py`
- Validator pattern: `src/stockreports/alert/validator.py`
- VRA Executor: `src/stockreports/alert/approach/VRA/executor.py` (most similar)

---

**NEXT STEP**: Review all validations above, answer clarification questions, then proceed to code generation phase.

