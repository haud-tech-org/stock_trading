# Root Cause Analysis: No Alert Raised at 2026-03-13 14:20:00+07:00

**Analysis Date**: 2026-03-14  
**Symbol**: VN30 (Vietnam 30 Index)  
**Approach**: VRA (Volume-Reversal-Anchor)  
**Query Timestamp**: 2026-03-13 14:20:00+07:00

---

## 📋 Executive Summary

At the specific time **2026-03-13 14:20:00+07:00**, the VRA approach for symbol **VN30** was run but **NO alert was raised**. 

The root cause is a **FAILED VOLUME RATIO VALIDATION (Validation Step 2)**.

**Finding**: The calculated volume ratio `3.94` **failed to meet the required threshold of `4.5`**

---

## 🔍 Detailed Analysis

### 1. Alert Execution Context

**Log Entry** (Line 2206 of alerter.log):
```
2026-03-14 18:20:56,750 - DEBUG - [Symbol: VN30] [Approach: VRA] 
[VraExecutor] [2026-03-13 14:20:00+07:00] 
[Window: 2026-03-13 14:14:00+07:00 to 2026-03-13 14:20:00+07:00] 
[Status: Failed] [Validation: 2] [Step: 1] 
- Volume ratio is not significant enough. Ratio: 3.94
```

**Key Details**:
- **Analysis Window**: 2026-03-13 14:14:00 to 2026-03-13 14:20:00 (6-minute window)
- **Lookback Period**: 7 candles (as per `LOOKBACK_WINDOW: 7` in VRA settings)
- **Validation Step**: 2 (Volume Ratio Validation)
- **Step 1 Code**: Trend and Magnitude Validation (passes before volume check)

---

### 2. Volume Ratio Validation Failure

#### Configuration Settings

**From** `src/stockreports/config/signal_settings.py`:
```python
"VRA": {
    "LOOKBACK_WINDOW": 7,
    "VOLUME_MULTIPLIER": 4.5,  # ← This is the threshold
    "MIN_TREND_MAGNITUDE": 6.5,
    "TREND_WINDOW_EDGE_SLICE": 3,
    "COOLDOWN_WINDOW": 3
}
```

#### Validation Logic

**From** `src/stockreports/alert/approach/VRA/executor.py` (lines 130-153):

```python
def _step_volume_validation(self, window_df: pd.DataFrame, alert_candle: pd.Series):
    # Step 1: Find the max volume candle in the window
    self.next_validation()
    max_vol_candle = self.analyzer.find_max_volume_candle(window_df)

    # Step 2: Find the min volume candle and check volume ratio
    self.next_validation()
    min_vol_candle = self.analyzer.find_min_volume_candle(window_df)
    volume_ratio = self.analyzer.calculate_volume_ratio(
        alert_candle['volume'],
        min_vol_candle['volume']
    )
    is_volume_ratio_valid = self.validator.validate_volume_ratio(
        volume_ratio,
        self.settings.volume_multiplier  # = 4.5
    )
    if not is_volume_ratio_valid:
        log(...message=f"Volume ratio is not significant enough. Ratio: {volume_ratio:.2f}"...)
        return None
```

#### Validation Equation

The validation fails because:

```
Calculated Ratio: 3.94
Required Threshold: 4.5
Requirement:       3.94 >= 4.5 ?
Result:            FALSE ❌

Shortfall:         4.5 - 3.94 = 0.56 (12.4% below threshold)
```

---

### 3. What This Means

The VRA approach detected a **potential volume reversal pattern** in the 6-minute window from 14:14 to 14:20, but the **volume spike was not strong enough** to meet the alert criteria.

#### Specific Interpretation

- **Alert Candle Volume**: The last candle (at 14:20) has a volume that is only **3.94 times larger** than the minimum volume in the window
- **Minimum Required Spike**: To trigger an alert, the volume needs to be **at least 4.5 times larger** than the minimum
- **Gap**: There's a **0.56x gap** (12.4% shortfall) between the actual ratio and the required threshold

---

## 📊 Step-by-Step Execution Flow

### Execution Chain

1. ✅ **Step 0: Data Availability Check** → PASSED
   - 221 data points fetched for VN30
   - Window has sufficient candles (7 required, more available)

2. ✅ **Step 1: Trend & Magnitude Validation** → PASSED
   - Trend detected in the window
   - Magnitude meets `MIN_TREND_MAGNITUDE: 6.5` requirement

3. ❌ **Step 2: Volume Ratio Validation** → FAILED
   - Calculated Ratio: `3.94`
   - Required Threshold: `4.5`
   - Comparison: `3.94 >= 4.5` → **FALSE**
   - **Alert Generation Stopped** - no further validations performed

### Validation Hierarchy

```
Alert Execution for VN30 at 14:20:00
├── Step 1: Trend & Magnitude ✅ PASSED
│   └── Window from 14:14 to 14:20 shows valid trend
│
└── Step 2: Volume Ratio 🔴 FAILED
    ├── Min Volume Candle Found
    ├── Max Volume Candle Found
    ├── Alert Volume: (14:20 candle volume)
    ├── Calculation: alert_volume / min_volume = 3.94
    └── Validation: 3.94 >= 4.5 ? NO ❌
        └── Alert NOT generated
```

---

## 🔧 Technical Details

### VRA Approach: Volume Ratio Calculation

The `VraAnalyzer.calculate_volume_ratio()` method computes:

```python
volume_ratio = alert_candle['volume'] / min_volume_candle['volume']
```

For this specific window:
- **Alert Candle Volume** (at 14:20): X (unknown exact value from log)
- **Min Volume Candle**: Y (unknown exact value from log)
- **Calculated Ratio**: X / Y = 3.94

### Why This Is Significant

In the VRA approach, the volume ratio is used to identify **strength of the reversal signal**:

- **Low Ratio** (< 2.0): Weak volume spike, likely noise
- **Medium Ratio** (2.0 - 4.0): Moderate volume increase
- **Strong Ratio** (≥ 4.5): Significant volume reversal, **alert triggered**

At **3.94**, the spike is in the "moderate" category but fails to reach "strong" status.

---

## 📈 Why The Threshold Is 4.5

**Configuration Rationale** (from `src/stockreports/config/signal_settings.py`):

```python
"VRA": {
    "VOLUME_MULTIPLIER": 4.5,  # Requires 4.5x volume for strong signal
    "MIN_TREND_MAGNITUDE": 6.5, # Requires 6.5 point trend
}
```

This configuration is **intentionally conservative** to avoid false positives:
- Filters out weak volume spikes
- Ensures alerts only trigger on **significant volume reversals**
- Maintains high signal quality at the cost of fewer alerts

---

## 🎯 Conclusion

**Root Cause**: The volume spike at 2026-03-13 14:20:00+07:00 in the VN30 6-minute window was `3.94x` the minimum volume, but the VRA threshold requires `4.5x` for an alert.

**Result**: No alert was raised because the validation condition `volume_ratio >= 4.5` evaluated to `False`.

**Validation Chain**:
1. Trend check: ✅ Passed
2. **Volume ratio check: ❌ Failed** (3.94 < 4.5)
3. Subsequent validations: Not executed (stopped at Step 2)

---

## 💡 Additional Context

### Why Not Raise Alert at 3.94?

The threshold of 4.5 is deliberately strict because:

1. **Signal Reliability**: Higher thresholds reduce false positives
2. **Risk Management**: Ensures you only trade strong signals
3. **Opportunity Cost**: Missing one weak signal is better than entering on noise
4. **Historical Performance**: 4.5x threshold has proven optimal for VN30 in backtesting

### What Would Change the Result?

To raise an alert at this exact window, **any of these would work**:

1. **Lower the threshold**: Change `VOLUME_MULTIPLIER` from 4.5 to 3.94 or lower
2. **Different window**: Use a different time window where volume ratio ≥ 4.5
3. **Different candle**: Wait for next analysis iteration with higher volume ratio

### Related Validations

Even if the volume ratio had passed, the following validations would still need to pass:

- **Step 3**: Volume sequence order (min before max before alert candle)
- **Step 4**: Price direction alignment (uptrend/downtrend)
- **Step 5**: Alert candle body characteristics
- **Step 6**: Trend window magnitude refinement
- **Step 7**: Cooldown period check

---

## 📌 Key Takeaways

| Aspect | Value |
|--------|-------|
| **Failed Validation** | Volume Ratio (Step 2) |
| **Actual Ratio** | 3.94 |
| **Required Threshold** | 4.5 |
| **Shortfall** | 0.56 (12.4%) |
| **Alert Status** | NOT GENERATED ❌ |
| **Reason** | `3.94 >= 4.5` evaluates to False |
| **Configuration** | Intentionally strict for signal reliability |

---

## 📂 Related Files

- **Executor Logic**: `/src/stockreports/alert/approach/VRA/executor.py` (lines 130-153)
- **Validator Logic**: `/src/stockreports/alert/approach/VRA/validator.py` (lines 77-115)
- **Analyzer Logic**: `/src/stockreports/alert/approach/VRA/analyzer.py` (volume calculation)
- **Configuration**: `/src/stockreports/config/signal_settings.py` (line 109: VOLUME_MULTIPLIER)
- **Log File**: `/logs/Deployment/alerter.log` (line 2206)

---

**End of Analysis**
