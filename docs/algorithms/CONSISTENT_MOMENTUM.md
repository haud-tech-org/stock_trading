# CONSISTENT_MOMENTUM Approach

## Objective

The **CONSISTENT_MOMENTUM** approach identifies significant price movements where a sequence of consecutive candles all move in the same direction with consistent color. The approach determines a trading signal based on the color of the last candle in the lookback window, then validates that preceding candles form a consistent momentum pattern anchored at the candle with the most extreme open price in that direction.

**Key Characteristics**:
- Detects directional consistency across multiple consecutive candles
- Uses the last candle's color to determine signal (GREEN=BUY, RED=SELL)
- Anchors to the candle with minimum open (BUY) or maximum open (SELL)
- Validates consecutive candles maintain direction from anchor to end
- Fixed magnitude threshold for consistent alert strength

## Key Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| LOOKBACK_WINDOW | 6 | Number of consecutive candles analyzed for consistency pattern |
| MIN_CONSISTENT_CANDLES | 3 | Minimum number of consecutive candles required with same color |
| MAGNITUDE_THRESHOLD | 4.5 | Fixed alert magnitude for all signals |
| COOLDOWN_WINDOW | 3 | Minutes required between consecutive alerts of the same signal |

## Algorithm Steps

### Step 1: Determine Signal from Last Candle Color
- Examine the last candle in the lookback window
- **GREEN candle** → Signal = **BUY**
- **RED candle** → Signal = **SELL**
- If candle is neither clearly green nor red, no alert
- **Validation Tracked**: Signal determination (Step 1, Validation 1)

### Step 2: Find Anchor Candle
- Scan all candles in lookback window for the anchor point
- **For BUY signal**: Find candle with **MINIMUM open price**
  - Represents the lowest entry point before momentum upward
- **For SELL signal**: Find candle with **MAXIMUM open price**
  - Represents the highest entry point before momentum downward
- **Validation Tracked**: Anchor detection (Step 2, Validation 1)

### Step 3: Extract Confirmation Window
- Extract sub-window from **anchor candle to last candle** (inclusive)
- This represents the "momentum period" being validated
- **Validation Tracked**: Window extraction (Step 3, Validation 1)

### Step 4: Validate Color Consistency
- Verify all candles in confirmation window have matching color
- **For BUY signal**: All candles must be **GREEN**
- **For SELL signal**: All candles must be **RED**
- Any candle breaking the color pattern fails validation
- **Validation Tracked**: Color consistency check (Step 4, Validation 1)

### Step 5: Validate Minimum Consistent Candles
- Count consecutive candles with matching color in confirmation window
- Verify count **≥ MIN_CONSISTENT_CANDLES** (3)
- Ensures the momentum is not just a brief spike but sustained
- **Validation Tracked**: Min candle count (Step 5, Validation 1)

### Step 6: Cooldown Check
- Compare current alert time with last accepted alert of same signal
- If time since last alert < COOLDOWN_WINDOW (3 minutes) AND signal matches
- Skip alert to avoid alert spam
- **Validation Tracked**: Cooldown validation (Step 6, Validation 1)

### Step 7: Alert Creation
- Create AlertData with:
  - **Signal**: BUY or SELL (from Step 1)
  - **Magnitude**: MAGNITUDE_THRESHOLD (4.5)
  - **Alert Candle**: Last candle of lookback window
  - **Details**: Anchor index, consistency count, signal type
- Return alert and update LATEST_ALERT for cooldown tracking

## Validation Tracking

The approach tracks **7 validations** across the steps:

| Validation # | Step | Name | Config Variable | Purpose |
|--------------|------|------|-----------------|---------|
| 1 | 1 | Signal determination | N/A | Verify last candle has clear color |
| 2 | 2 | Anchor detection | N/A | Find extreme open price candle |
| 3 | 3 | Window extraction | N/A | Extract confirmation window |
| 4 | 4 | Color consistency | N/A | All candles match signal color |
| 5 | 5 | Min consistent candles | MIN_CONSISTENT_CANDLES | Count ≥ threshold |
| 6 | 6 | Cooldown check | COOLDOWN_WINDOW | Time between same-signal alerts |
| 7 | 7 | Alert creation | MAGNITUDE_THRESHOLD | Final alert generation |

## Flow Diagram

```
Start: Reverse Loop on DataFrame
  │
  ├─ Extract Lookback Window (LOOKBACK_WINDOW candles)
  │
  ├─ [Step 1] Determine Signal from Last Candle Color
  │   ├─ GREEN → BUY
  │   ├─ RED → SELL
  │   └─ Neither → Continue Loop
  │
  ├─ [Step 2] Find Anchor Candle
  │   ├─ BUY: Min open price
  │   └─ SELL: Max open price
  │
  ├─ [Step 3] Extract Confirmation Window (anchor → last)
  │
  ├─ [Step 4] Validate Color Consistency
  │   └─ All candles match signal color
  │
  ├─ [Step 5] Validate Min Consistent Candles
  │   └─ Count ≥ MIN_CONSISTENT_CANDLES (3)
  │
  ├─ [Step 6] Cooldown Check
  │   └─ Enough time since last same-signal alert
  │
  ├─ [Step 7] Create & Return Alert
  │   └─ AlertData with magnitude=MAGNITUDE_THRESHOLD
  │
  └─ End: Continue Loop or Return First Alert (non-development mode)
```

## Example Scenarios

### Scenario 1: BUY Alert (5 Consecutive Green Candles)

```
Time    Open    Close   Color   Step
----    ----    -----   -----   ----
T-5     100.5   100.3   RED     ✓ Not in lookback
T-4     100.2   100.5   GREEN   Part of window
T-3     100.0   100.8   GREEN   ← Anchor (Min Open)
T-2     100.1   100.9   GREEN   
T-1     100.3   100.7   GREEN   
T0      100.4   101.0   GREEN   ← Last Candle (Signal=BUY)

Steps:
1. Last candle (T0) is GREEN → Signal=BUY ✓
2. Find anchor: Min open = T-3 (100.0) ✓
3. Confirmation window: T-3 to T0 (4 candles) ✓
4. Color consistency: All 4 candles GREEN ✓
5. Min candles: 4 ≥ 3 ✓
6. Cooldown: Last BUY was > 3 minutes ago ✓
7. Create ALERT: BUY with magnitude=4.5
```

### Scenario 2: SELL Alert (3 Red Candles with Anchor)

```
Time    Open    Close   Color   Step
----    ----    -----   -----   ----
T-2     100.8   100.5   RED     
T-1     100.9   100.4   RED     ← Anchor (Max Open)
T0      100.7   100.2   RED     ← Last Candle (Signal=SELL)

Steps:
1. Last candle (T0) is RED → Signal=SELL ✓
2. Find anchor: Max open = T-1 (100.9) ✓
3. Confirmation window: T-1 to T0 (2 candles) ✓
4. Color consistency: Both RED ✓
5. Min candles: 2 < 3 ✗ FAILED - Not enough consistency
   Result: NO ALERT (needs at least 3 consistent candles)
```

### Scenario 3: Failed Color Consistency

```
Time    Open    Close   Color   Step
----    ----    -----   -----   ----
T-3     100.2   100.5   GREEN   Part of window
T-2     100.0   100.6   GREEN   ← Anchor (Min Open)
T-1     100.1   100.7   GREEN   
T0      100.4   99.9    RED     ← Last Candle (Signal=RED)

Steps:
1. Last candle (T0) is RED → Signal=RED ✓
2. Find anchor: Max open = T0 (100.4) ✓
3. Confirmation window: T0 to T0 (1 candle) ✓
4. Color consistency: Only 1 RED candle ✓ (trivially consistent)
5. Min candles: 1 < 3 ✗ FAILED
   Result: NO ALERT (only 1 candle in confirmation window)
```

## Configuration Integration

All parameters are centralized in `src/stockreports/config/signal_settings.py`:

```python
"CONSISTENT_MOMENTUM": {
    "LOOKBACK_WINDOW": 6,
    "MIN_CONSISTENT_CANDLES": 3,
    "MAGNITUDE_THRESHOLD": 4.5,
    "COOLDOWN_WINDOW": 3
}
```

Parameters are loaded into `ConsistentMomentumSettings` class via `BaseSettings` inheritance.

## Implementation Details

### File Structure
- **Executor**: `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py`
- **Settings**: `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/settings.py`
- **Configuration**: `src/stockreports/config/signal_settings.py`

### Class Hierarchy
```
Executor (base class)
  └─ ConsistentMomentumExecutor
       └─ Uses ConsistentMomentumSettings(BaseSettings)
```

### Key Methods in ConsistentMomentumExecutor

| Method | Purpose |
|--------|---------|
| `_find_alerts()` | Main orchestrator, reverse loop through candles |
| `_step_determine_signal_from_color()` | Determine BUY/SELL from last candle |
| `_step_find_anchor_candle()` | Find min/max open based on signal |
| `_step_extract_confirmation_window()` | Extract anchor-to-last subwindow |
| `_step_validate_color_consistency()` | Check all candles match signal color |
| `_step_validate_min_consistent_candles()` | Verify count threshold met |

## Performance Characteristics

- **Lookback Requirement**: 6 candles minimum
- **Confirmation Time**: Fast (no forward windows)
- **Alert Frequency**: Controlled by cooldown (3 minutes min between same signal)
- **Magnitude**: Fixed at 4.5 for consistent signal strength
- **Development Mode**: Returns first alert and stops
- **Deployment Mode**: Scans entire available history respecting new candle count

## Related Approaches

- **STRONG_CANDLE**: Detects strong single candles with opposite-color context
- **SESSION_EXTREME_VOLUME_REVERSAL**: Uses volume spikes with reversal patterns
- **CVA**: Complex validation approach with extended confirmation windows

