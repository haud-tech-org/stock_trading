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
| MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD | 2.0 | Maximum allowed ratio of max to min volume in confirmation window |
| MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD | 2.0 | Minimum price range in confirmation window |
| MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD | 6.0 | Maximum price range in confirmation window |

## Algorithm Steps

### Step 1: Determine Signal from Last Candle Color
- Examine the last candle in the lookback window
- **GREEN candle** → Signal = **BUY**
- **RED candle** → Signal = **SELL**
- If candle is neither clearly green nor red, no alert
- **Validation Tracked**: Signal determination (Step 1, Validation 1)

### Step 2: Find Anchor Candle
- The anchor candle is the **first candle with matching color** found when scanning forward from the extreme open price
- Find the candle with **minimum open price** (for BUY) or **maximum open price** (for SELL)
- Starting from this extreme position, scan **forward** to find the first candle with matching color
- **For BUY signal**: Find the first **GREEN** candle starting from min open position
- **For SELL signal**: Find the first **RED** candle starting from max open position
- Algorithm: Identify extreme open, then scan forward from that position until matching color found
- **Validation Tracked**: Anchor detection (Step 2, Validation 1)

### Step 3: Extract Confirmation Window
- Extract sub-window from **anchor candle to last candle** (inclusive)
- This represents the "momentum period" being validated
- **Validation Tracked**: Window extraction (Step 3, Validation 1)

### Step 4: Validate Volume Consistency
- Find **max volume** (Mx) in the confirmation window
- Find **min volume** (Mn) in the confirmation window
- Validate: **Mx ≤ Mn × MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD**
- Ensures volume is consistent without excessive spikes
- Configuration: MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD (default: 2.0)
- **Validation Tracked**: Volume consistency check (Step 4, Validation 1)

### Step 5: Validate Confirmation Window Price Range
- Calculate the price range as the difference between highest and lowest **close prices** in the confirmation window
- Validate: **MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD ≤ Price Range ≤ MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD**
- **Minimum threshold (2.0)**: Ensures sufficient price movement in the confirmation window (avoids weak signals)
- **Maximum threshold (6.0)**: Ensures price volatility is controlled (avoids excessive swings)
- Example BUY: Closes [100.5, 100.8, 101.2, 101.5] → Range = 1.0 ❌ FAIL (below minimum 2.0)
- Example BUY: Closes [100.0, 101.5, 102.0, 103.0] → Range = 3.0 ✅ PASS (within 2.0-6.0)
- Example SELL: Closes [101.0, 100.5, 100.2, 99.8] → Range = 1.2 ❌ FAIL (below minimum 2.0)
- Example SELL: Closes [101.5, 100.8, 100.2, 99.0] → Range = 2.5 ✅ PASS (within 2.0-6.0)
- **Validation Tracked**: Price range minimum check (Step 5, Validation 1) and maximum check (Step 5, Validation 2)

### Step 6: Validate Color Consistency
- Verify all candles in confirmation window have matching color
- **For BUY signal**: All candles must be **GREEN**
- **For SELL signal**: All candles must be **RED**
- Any candle breaking the color pattern fails validation
- **Validation Tracked**: Color consistency check (Step 6, Validation 1)

### Step 7: Validate Open Price Direction
- Ensure open prices follow the signal direction throughout the confirmation window
- **For BUY signal**: Open prices must strictly increase (open[i] > open[i-1], no equal values allowed)
- **For SELL signal**: Open prices must strictly decrease (open[i] < open[i-1], no equal values allowed)
- This validates that price movement is consistent with the signal direction
- Equal open prices between consecutive candles will fail validation
- Example BUY: opens [100.0, 100.5, 101.0, 101.5] ✅ PASS (strictly increasing)
- Example BUY: opens [100.0, 100.0, 101.0] ❌ FAIL (has equal values)
- Example SELL: opens [100.5, 100.3, 100.1, 99.9] ✅ PASS (strictly decreasing)
- Example SELL: opens [100.5, 100.5, 100.1] ❌ FAIL (has equal values)
- **Validation Tracked**: Open price direction check (Step 7, Validation 1)

### Step 8: Validate Minimum Consistent Candles
- Count consecutive candles with matching color in confirmation window
- Verify count **≥ MIN_CONSISTENT_CANDLES** (3)
- Ensures the momentum is not just a brief spike but sustained
- **Validation Tracked**: Min candle count (Step 8, Validation 1)

### Step 9: Cooldown Check
- Compare current alert time with last accepted alert of same signal
- If time since last alert < COOLDOWN_WINDOW (3 minutes) AND signal matches
- Skip alert to avoid alert spam
- **Validation Tracked**: Cooldown validation (Step 9, Validation 1)

### Step 10: Alert Creation
- Create AlertData with:
  - **Signal**: BUY or SELL (from Step 1)
  - **Magnitude**: MAGNITUDE_THRESHOLD (4.5)
  - **Alert Candle**: Last candle of lookback window
  - **Details**: Anchor index, consistency count, signal type
- Return alert and update LATEST_ALERT for cooldown tracking

## Validation Tracking

The approach tracks **11 validations** across the steps:

| Validation # | Step | Name | Config Variable | Purpose |
|--------------|------|------|-----------------|---------|
| 1 | 1 | Signal determination | N/A | Verify last candle has clear color |
| 2 | 2 | Anchor detection | N/A | Find extreme open price candle |
| 3 | 3 | Window extraction | N/A | Extract confirmation window |
| 4 | 4 | Volume consistency | MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD | Max volume ≤ min volume × threshold |
| 5 | 5 | Price range minimum | MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD | Price range ≥ minimum threshold |
| 6 | 5 | Price range maximum | MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD | Price range ≤ maximum threshold |
| 7 | 6 | Color consistency | N/A | All candles match signal color |
| 8 | 7 | Open price direction | N/A | Opens increase (BUY) or decrease (SELL) |
| 9 | 8 | Min consistent candles | MIN_CONSISTENT_CANDLES | Count ≥ threshold |
| 10 | 9 | Cooldown check | COOLDOWN_WINDOW | Time between same-signal alerts |
| 11 | 10 | Alert creation | MAGNITUDE_THRESHOLD | Final alert generation |

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
  ├─ [Step 2] Find Anchor Candle (From Extreme Open)
  │   ├─ Find Min Open (BUY) or Max Open (SELL)
  │   └─ Scan forward from extreme position:
  │      ├─ BUY: First GREEN candle at or after min open
  │      └─ SELL: First RED candle at or after max open
  │
  ├─ [Step 3] Extract Confirmation Window (anchor → last)
  │
  ├─ [Step 4] Validate Volume Consistency
  │   └─ Max volume ≤ min volume × MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD
  │
  ├─ [Step 5] Validate Confirmation Window Price Range
  │   ├─ MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD ≤ Price Range
  │   └─ Price Range ≤ MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD
  │
  ├─ [Step 6] Validate Color Consistency
  │   └─ All candles match signal color
  │
  ├─ [Step 7] Validate Open Price Direction
  │   ├─ BUY: Opens must increase (non-decreasing)
  │   └─ SELL: Opens must decrease (non-increasing)
  │
  ├─ [Step 8] Validate Min Consistent Candles
  │   └─ Count ≥ MIN_CONSISTENT_CANDLES (3)
  │
  ├─ [Step 9] Cooldown Check
  │   └─ Enough time since last same-signal alert
  │
  ├─ [Step 10] Create & Return Alert
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

