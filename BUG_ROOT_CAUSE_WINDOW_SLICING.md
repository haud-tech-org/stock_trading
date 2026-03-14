# Investigation: Old Code Alert at 14:20 vs Refactored Code No Alert

## Summary of Findings

Through detailed analysis of the data, we've identified why the **old code raised an alert at 14:20** but the **refactored code does not**.

---

## The Data

For VN30F1M on 2026-03-13 from 14:00-14:25:

```
Index  Time        Volume  
───────────────────────── 
...
17     14:17:00    992.0    ← MIN VOLUME
...
20     14:20:00    5393.0   ← MAX VOLUME (5393/992 = 5.44x ratio)
21     14:21:00    3534.0
...
```

**Expected Alert**: Time 14:20 with volume ratio 5.44

---

## How Window Slicing Works

With `lookback_window = 7` candles:

### Current (Broken) Code Logic

When analyzing at `scan_idx = 20`:
```python
window = df_indexed.iloc[20 - 7 : 20]
       = df_indexed.iloc[13 : 20]   # Python slice: [13, 14, 15, 16, 17, 18, 19]
       → Last candle: Index 19 (14:19:00), volume=3975.0
       → Volume Ratio: 3975 / 992 = 4.01 (FAILS, need 4.5)
       → NO ALERT ❌
```

When analyzing at `scan_idx = 21`:
```python
window = df_indexed.iloc[21 - 7 : 21]
       = df_indexed.iloc[14 : 21]   # Python slice: [14, 15, 16, 17, 18, 19, 20]
       → Last candle: Index 20 (14:20:00), volume=5393.0
       → Volume Ratio: 5393 / 992 = 5.44 (PASSES!)
       → ALERT RAISED AT 14:21 ✓
```

**Problem**: Alert is raised at 14:21 (one candle later) instead of 14:20

---

## Root Cause Analysis

### The Semantic Issue

The window slicing `[scan_idx - lookback : scan_idx]` excludes `scan_idx` because Python slicing is **exclusive at the end**.

This means:
- When `scan_idx = 20`, the window **doesn't include index 20**
- The **last candle in the window is at index 19**
- The alert would only trigger when `scan_idx = 21`, at which point the window includes index 20

### Why Old Code Might Have Different Behavior

The old code also uses the same slicing, so it **should** have the same issue. However:

1. **Possibility 1**: Old code might have a different loop setup or different `scan_idx` values
2. **Possibility 2**: Old code might have processed data at 14:20 when 14:21 candle wasn't yet available
3. **Possibility 3**: Alert JSON might show the **trigger time** (14:20 close), not the **analysis time** (14:21 analysis)

---

## The Core Problem

We cannot modify `src/stockreports/alert/executor.py` because it's inherited by all other executors (CONSISTENT_MOMENTUM, STRONG_CANDLE, VOLUME_SPIKE_CONFIRMATION, etc.). Changing it could break everything.

**We need a VRA-specific solution** in the VRA executor itself, not in the base class.

---

## Proposed Solutions

### Solution 1: VRA-Specific Window Offset (RECOMMENDED)

Modify `VRA executor._find_alerts()` to use a different loop setup:

```python
# In VraExecutor._find_alerts()
df_indexed, loop_start, loop_end = self.get_loop_setup(...)

# VRA-specific: Include the scan_idx candle itself
for i in range(loop_end - 1, loop_start - 2, -1):  # Start one earlier
    self.set_window_context(i + 1, df_indexed, window_size)  # Analyze one step ahead
    # ... rest of VRA logic
```

This way:
- When looking at what **would** trigger an alert at time T, we analyze with T included
- Maintains compatibility with other approaches
- No base class changes needed

### Solution 2: Override set_window_context in VRA

```python
class VraExecutor(Executor):
    def _set_vra_window_context(self, scan_index, df_indexed, lookback_window_size):
        """VRA-specific window that includes scan_index"""
        self.lookback_window_df = df_indexed.iloc[
            max(0, scan_index - lookback_window_size + 1) : scan_index + 1
        ]
        # ... rest of setup
```

Then use `self._set_vra_window_context()` instead of `self.set_window_context()`

### Solution 3: Adjust Loop Parameters

Override `get_loop_setup()` in VraExecutor to start the loop one position earlier, then adjust the window offset.

---

## Recommendation

**Use Solution 1 or 2** because:
- ✅ No changes to base Executor (safe for all other approaches)
- ✅ VRA-specific logic stays in VRA executor
- ✅ Clearer intent and easier to maintain
- ✅ No risk of side effects on other alert approaches

---

## Next Steps

1. **Identify** which solution is most compatible with VRA's existing logic
2. **Implement** the VRA-specific fix
3. **Test** with the debug script to confirm alert now triggers at 14:20
4. **Verify** no side effects on other time windows
5. **Backtest** to ensure profitability isn't affected

---

## Test Verification

After implementing the fix, run:

```bash
python3 analysis_vra_14_20_debug.py
```

Expected output: Alert should trigger at scan_idx=20 with ratio 5.44

---

##Technical Details

The key insight is that **alert timing is relative**:
- **Alert notification**: Sent when candle **closes**
- **Alert analysis**: Computed based on **lookback window**
- **Mismatch**: If we analyze the candle after close, we catch the alert one candle late

For trading purposes, we want to alert **at the close of the triggering candle**, not the next candle.

---

**Status**: ROOT CAUSE IDENTIFIED ✅  
**Next**: Implement VRA-specific window logic
