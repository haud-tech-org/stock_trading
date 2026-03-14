# Approach Refactoring TODO List

## Overview
Refactor 4 approaches to follow the Executor → Analyzer → Validator pattern using the STRONG_CANDLE approach as a reference.

**Reference Implementation**: `src/stockreports/alert/approach/STRONG_CANDLE/`

---

## 1. CONSISTENT_MOMENTUM

### Business Logic Summary
- **What it detects**: Consistent color candles with an anchor point (min/max open) followed by same-color confirmation candles
- **Key Rules**:
  1. Determine signal from last candle color (green=BUY, red=SELL)
  2. Find anchor candle (first matching color at/after min/max open)
  3. Extract confirmation window from anchor to last candle
  4. Validate first & last candles have maximum body momentum (1st & 2nd max OR last is max)
  5. Validate volume consistency in confirmation window
  6. Validate confirmation window price range is within thresholds
  7. Validate gap between candles in confirmation window
  8. Validate all candles have same color
  9. Validate open/close direction consistency
  10. Validate minimum consistent candles count
  11. Cooldown check
  12. Create alert

### Files to Create
- [ ] **analyzer.py** - Pure calculation methods
  - [ ] `calculate_body_ratio()` - inherited from base
  - [ ] `calculate_body_size()` - inherited from base
  - [ ] `get_window_size_and_trend()` - inherited from base
  - [ ] Extract 1st & 2nd max body candles logic
  - [ ] Calculate volume stats
  - [ ] Calculate price range
  - [ ] Calculate gap between candles
  
- [ ] **validator.py** - Pure validation methods
  - [ ] `validate_alert_candle_body()` - body ratio and size
  - [ ] `validate_volume_consistency()` - volume in confirmation window
  - [ ] `validate_price_range()` - window price range thresholds
  - [ ] `validate_gap_between_candles()` - gap validation
  - [ ] `validate_color_consistency()` - all same color
  - [ ] `validate_open_close_direction()` - price direction
  - [ ] `validate_min_consistent_candles()` - minimum count
  
- [ ] **executor.py** - Refactor existing code
  - [ ] Remove inline calculations, use analyzer methods
  - [ ] Remove inline validations, use validator methods
  - [ ] Keep orchestration logic in `_find_alerts()`
  - [ ] Keep step methods but call validator/analyzer methods
  
- [ ] **__init__.py** - Exports
  - [ ] Add imports for Analyzer and Validator
  - [ ] Add to __all__

---

## 2. CONSISTENT_VOLUME_ANCHOR

### Business Logic Summary
- **What it detects**: Anchor candles with consistent volume patterns, confirmed by alert candles with volume spikes
- **Key Rules**:
  1. Find anchor candle
  2. Extract consistent volume window
  3. Validate volume consistency in window
  4. Validate consistent window body sizes
  5. Validate consistent window gap between candles
  6. Validate alert candle characteristics
  7. Validate alert candle body size and ratio
  8. Validate alert volume against window
  9. Cooldown check
  10. Create alert

### Files to Create
- [ ] **analyzer.py** - Pure calculation methods
  - [ ] `find_anchor_candle()` - find anchor in window
  - [ ] `extract_consistent_volume_window()` - extract window from anchor
  - [ ] `calculate_volume_stats()` - min/max/median volume
  - [ ] `calculate_body_statistics()` - body sizes
  - [ ] `calculate_gaps()` - gaps between candles
  - [ ] `calculate_window_size_and_trend()` - window metrics
  
- [ ] **validator.py** - Pure validation methods
  - [ ] `validate_anchor_candle()` - anchor validation
  - [ ] `validate_volume_consistency()` - volume in window
  - [ ] `validate_body_sizes()` - body size thresholds
  - [ ] `validate_gaps()` - gap constraints
  - [ ] `validate_alert_candle()` - alert candle checks
  - [ ] `validate_alert_body()` - body ratio/size
  - [ ] `validate_alert_volume()` - volume spike
  
- [ ] **executor.py** - Refactor existing code
  - [ ] Remove calculations, use analyzer methods
  - [ ] Remove validations, use validator methods
  - [ ] Keep orchestration in `_find_alerts()`
  
- [ ] **__init__.py** - Exports

---

## 3. VOLUME_SPIKE_CONFIRMATION

### Business Logic Summary
- **What it detects**: Volume spikes in trend confirmation windows with reversals
- **Key Rules**:
  1. Extract trend window (consecutive same-color candles from end)
  2. Validate trend window has minimum candles
  3. Validate trend window price range
  4. Find max volume and min volume candles
  5. Validate min volume occurs before max volume
  6. Validate volume spike ratio
  7. Determine reversal signal from last candle
  8. Cooldown check
  9. Create alert

### Files to Create
- [ ] **analyzer.py** - Pure calculation methods
  - [ ] `extract_trend_window()` - extract same-color window
  - [ ] `find_max_volume_candle()` - find max
  - [ ] `find_min_volume_candle()` - find min
  - [ ] `calculate_volume_ratio()` - volume spike
  - [ ] `get_window_size_and_trend()` - inherited
  
- [ ] **validator.py** - Pure validation methods
  - [ ] `validate_trend_window()` - size and price range
  - [ ] `validate_volume_spike()` - min/max order and ratio
  - [ ] `validate_reversal_signal()` - signal from candle
  
- [ ] **executor.py** - Refactor existing code
  - [ ] Remove calculations, use analyzer methods
  - [ ] Remove validations, use validator methods
  - [ ] Keep orchestration logic
  
- [ ] **__init__.py** - Exports

---

## 4. VRA (Volume Reversal Analysis)

### Business Logic Summary
- **What it detects**: Volume reversals with trend analysis and magnitude validation
- **Key Rules**:
  1. Find max volume candle in window
  2. Find min volume candle
  3. Validate min occurs before max
  4. Validate volume ratio between alert and min
  5. Ensure min volume candle before alert candle
  6. Slice window from min to alert candle
  7. Validate trend window has minimum candles
  8. Validate trend and magnitude
  9. Get reversal trend and signal
  10. Cooldown check
  11. Create alert

### Files to Create
- [ ] **analyzer.py** - Pure calculation methods
  - [ ] `find_max_volume_candle()` - find max
  - [ ] `find_min_volume_candle()` - find min
  - [ ] `calculate_volume_ratio()` - volume ratio
  - [ ] `slice_trend_window()` - extract window
  - [ ] `get_window_size_and_trend()` - trend and magnitude
  
- [ ] **validator.py** - Pure validation methods
  - [ ] `validate_volume_sequence()` - min before max
  - [ ] `validate_volume_ratio()` - ratio threshold
  - [ ] `validate_trend_window_size()` - minimum candles
  - [ ] `validate_trend_and_magnitude()` - magnitude threshold
  
- [ ] **executor.py** - Refactor existing code
  - [ ] Remove calculations, use analyzer methods
  - [ ] Remove validations, use validator methods
  - [ ] Keep orchestration logic
  
- [ ] **__init__.py** - Exports

---

## Refactoring Checklist (Per Approach)

For each approach, verify:

### Code Quality
- [ ] All methods have complete type hints (no missing types)
- [ ] All categorical values use enums (not strings)
- [ ] All classes/methods have Google-style docstrings (7 sections)
- [ ] All lines ≤ 79 characters (PEP 8)
- [ ] Relative imports only
- [ ] Naming: PascalCase classes, snake_case methods, UPPER_SNAKE_CASE constants

### Architecture
- [ ] Analyzer methods are @staticmethod
- [ ] Validator methods are @staticmethod
- [ ] Analyzer has no side effects
- [ ] Validator has no calculations (only boolean results)
- [ ] Executor uses _find_alerts() hook (not override run())
- [ ] Settings inherit BaseSettings

### File Structure
- [ ] settings.py - Configuration class
- [ ] analyzer.py - Pure calculation functions
- [ ] validator.py - Pure validation functions
- [ ] executor.py - Orchestration & alert creation
- [ ] __init__.py - Exports with __all__

---

## Execution Order

1. **CONSISTENT_MOMENTUM** - Most complex, but well-structured
2. **CONSISTENT_VOLUME_ANCHOR** - Similar structure to CM
3. **VOLUME_SPIKE_CONFIRMATION** - Simpler, fewer steps
4. **VRA** - Simpler, volume-focused

---

## Verification Steps (After Each Approach)

- [ ] Run tests: `pytest tests/` for approach-specific tests
- [ ] Check syntax: No import errors
- [ ] Check imports: All relative imports correct
- [ ] Verify backups: .backup/ directory has original executor.py
- [ ] Code review: Spot check 5-10 methods for quality

---

## Final Validation

After all 4 approaches:
- [ ] All 4 approaches follow STRONG_CANDLE pattern
- [ ] No business logic changes (only refactoring)
- [ ] All tests pass
- [ ] No circular imports
- [ ] Documentation updated (if needed)

