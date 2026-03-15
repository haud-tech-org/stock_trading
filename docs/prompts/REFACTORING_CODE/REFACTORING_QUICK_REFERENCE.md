# AI Refactoring Quick-Reference Card

**Purpose**: One-page guide for refactoring trading approaches  
**Use Case**: Keep this open while refactoring  
**Reference**: Full details in `docs/REFACTORING_AI_PROMPT.md`

---

## 🎯 The EAV Pattern in 30 Seconds

```
Executor          Analyzer          Validator
(Orchestrate)     (Calculate)       (Validate)
     │                 │                 │
     ├─────Call────────▶                 │
     │                 ├────Return───────▶
     │                       value       │
     ├───────Call (with value)──────────▶
     │                                   │
     │               ◀────Return (bool)──┤
     │
     ├─── Combine Results ───┐
     │                       │
     └──── Create Alert ◀────┘
```

**Rule**: Executor = Orchestration only. Analyzer = Pure math. Validator = Logic checks.

---

## 📋 Refactoring Checklist (5 Steps)

### Step 1: Understand Original Code
- [ ] Identify the main loop
- [ ] List each validation step
- [ ] Map threshold values
- [ ] Note edge cases

### Step 2: Plan EAV Split
- [ ] Calculations → Analyzer
- [ ] Validations → Validator
- [ ] Orchestration → Executor

### Step 3: Implement Analyzer
- [ ] Create class that inherits Analyzer
- [ ] Add only custom calculation methods
- [ ] All methods: `@staticmethod`
- [ ] No business logic (no `if` statements)

### Step 4: Implement Validator
- [ ] Create class that inherits Validator
- [ ] Add custom validation methods
- [ ] All methods: `@staticmethod`
- [ ] Return boolean or raise exception

### Step 5: Implement Executor
- [ ] Create class that inherits Executor
- [ ] Implement `_find_alerts()` (NOT `run()`)
- [ ] Call `get_loop_setup()` from base
- [ ] Call `set_window_context()` from base
- [ ] Call analyzer then validator in loop
- [ ] Create alert if all validations pass

---

## 🚫 CRITICAL: What NOT to Do

| ❌ Wrong | ✅ Right |
|---------|---------|
| Put `if` statements in Analyzer | Put calculations in Analyzer |
| Do calculations in Validator | Compare values in Validator |
| Override `run()` in Executor | Implement `_find_alerts()` in Executor |
| Hardcode thresholds | Use `self.settings.threshold` |
| Mix concerns in one class | Separate Executor/Analyzer/Validator |
| Change threshold values | Use exact original values |
| Use strings for Approach | Use `Approach.ENUM` constants |
| Make methods non-static | Use `@staticmethod` for Analyzer/Validator |

---

## 📐 Code Templates

### Analyzer Template

```python
from src.stockreports.alert.analyzer import Analyzer

class MyAnalyzer(Analyzer):
    """My approach analyzer."""
    
    @staticmethod
    def my_calculation(candle: dict) -> float:
        """Pure calculation, no logic."""
        value = candle['high'] - candle['low']
        return value
    
    # ✅ That's it! Inherit 9 more methods from base.
```

### Validator Template

```python
from src.stockreports.alert.validator import Validator

class MyValidator(Validator):
    """My approach validator."""
    
    @staticmethod
    def my_validation(value: float, threshold: float) -> bool:
        """Check if value meets threshold."""
        return value >= threshold
    
    # ✅ That's it! Inherit 10 more methods from base.
```

### Executor Template

```python
from src.stockreports.alert.executor import Executor

class MyExecutor(Executor):
    """My approach executor."""
    
    def __init__(self, symbol: str):
        self.settings = MySettings(symbol)
        self.analyzer = MyAnalyzer()
        self.validator = MyValidator()
        super().__init__(symbol, Approach.MY_APPROACH, self.settings)
    
    def _find_alerts(self, df, new_candle_count=0):
        # Setup loop
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df, new_candle_count, self.settings.lookback_window
        )
        
        for i in range(loop_end, loop_start - 1, -1):
            # Extract window
            self.set_window_context(i, df_indexed, self.settings.lookback_window)
            if self.lookback_window_df is None:
                continue
            
            # Step 1: Calculate
            self.next_step()
            value = self.analyzer.my_calculation(self.last_candle)
            
            # Step 2: Validate
            if not self.validator.my_validation(value, self.settings.threshold):
                continue
            
            # Step 3: Alert
            self.next_step()
            alert = self._create_alert_with_details(...)
            self.alerts.append(alert)
        
        return self.alerts[::-1]
```

---

## 🔍 Validation Preservation Rules

### Rule 1: Preserve Conditions
```python
# Original
if x >= threshold:

# Refactored
if self.validator.check(x, threshold):  # Uses >= internally
```

### Rule 2: Preserve Thresholds
```python
# Original
if x >= 4.5:

# Refactored
if self.validator.check(x, self.settings.volume_multiplier):
# settings.volume_multiplier = 4.5  ✅ Same value
```

### Rule 3: Preserve Edge Cases
```python
# Original
if volume == 0:
    return float('inf')

# Refactored
if min_vol == 0 and alert_vol > 0:
    return float('inf')  # ✅ Preserved
```

### Rule 4: Preserve Flow
```python
# Original
if not check_a(): return None
if not check_b(): return None
return success

# Refactored
if not self.validator.check_a(): continue
if not self.validator.check_b(): continue
# Create alert
```

---

## 🧪 Verification in 60 Seconds

Run original and refactored side-by-side on same data:

```python
# Original approach
original_alerts = OriginalExecutor('VN30').run(df)

# Refactored approach
refactored_alerts = RefactoredExecutor('VN30').run(df)

# Compare
assert len(original_alerts) == len(refactored_alerts)
assert original_alerts[0].alert_time == refactored_alerts[0].alert_time
assert original_alerts[0].signal == refactored_alerts[0].signal
```

**If all assertions pass**: Logic is preserved! ✅

---

## 📚 Base Methods You Inherit

### Analyzer (9 Methods)
1. `calculate_body_ratio()` → float
2. `calculate_body_size()` → float
3. `get_candle_color()` → CandleColor
4. `get_window_size_and_trend()` → (float, Trend)
5. `calculate_window_price_range()` → dict
6. `calculate_conditional_window_price_range()` → dict
7. `get_max_volume_in_window()` → float
8. `get_max_volume_in_conditional_window()` → float
9. `get_opposite_color_candles()` → DataFrame

### Validator (10 Methods)
1. `validate_candle_color_consistency()` → bool
2. `validate_opposite_color_exists()` → bool
3. `validate_price_threshold()` → bool
4. `validate_ratio_threshold()` → bool
5. `validate_volume_threshold()` → bool
6. `validate_volume_multiplier()` → bool
7. `validate_dataframe_not_empty()` → bool
8. `validate_required_columns()` → bool
9. `validate_window_size()` → bool
10. `validate_data_quality()` → bool

**Use them!** Don't reinvent the wheel.

---

## 🎓 Key Patterns

### Pattern: Calculation in Analyzer
```python
# ✅ Correct
@staticmethod
def calculate_ratio(a, b):
    return a / b
```

### Pattern: Validation in Validator
```python
# ✅ Correct
@staticmethod
def validate_ratio(ratio, threshold):
    return ratio >= threshold
```

### Pattern: Orchestration in Executor
```python
# ✅ Correct
ratio = self.analyzer.calculate_ratio(a, b)
if not self.validator.validate_ratio(ratio, threshold):
    continue
```

### Pattern: Settings Centralized
```python
# ✅ Correct
self.settings.threshold = self.get("THRESHOLD_KEY")
# In executor: if not self.validator.check(..., self.settings.threshold):
```

---

## 🚨 Red Flags

**Stop and reread the docs if you see**:

- 📍 Analyzer with `if` statement → Move to Validator
- 📍 Validator with calculation → Move to Analyzer  
- 📍 Executor > 100 lines → Refactor further
- 📍 Hardcoded threshold → Use `self.settings`
- 📍 Non-static method in Analyzer/Validator → Make `@staticmethod`
- 📍 Overriding `run()` → Implement `_find_alerts()` instead
- 📍 String for Approach → Use `Approach.ENUM`
- 📍 Alert logic changed → Validation not preserved

---

## 📞 Quick Decision Tree

**"Where does this code go?"**

```
Is it a calculation?
├─ Yes → ANALYZER
└─ No → Is it a validation?
    ├─ Yes → VALIDATOR
    └─ No → EXECUTOR
```

```
Does it need to run multiple times in loop?
├─ Yes → ANALYZER or VALIDATOR (@staticmethod)
└─ No → EXECUTOR
```

```
Should it change based on configuration?
├─ Yes → VALIDATOR (threshold) or EXECUTOR (settings)
└─ No → ANALYZER (pure math)
```

---

## ✅ Sign of Good Refactoring

- [ ] Executor < 80 lines
- [ ] Analyzer ≤ 100 lines (mostly inherited)
- [ ] Validator 50-200 lines
- [ ] All original alerts reproduced
- [ ] No new bugs introduced
- [ ] Settings centralized
- [ ] No code duplication
- [ ] All methods static
- [ ] All enums used properly
- [ ] Documentation complete

---

## 🔗 Full Resources

- **Architecture Overview**: `docs/ARCHITECTURE/ARCHITECTURE_OVERVIEW.md`
- **Design Patterns**: `docs/ARCHITECTURE/DESIGN_PATTERNS_GUIDE.md`
- **Implementation Guide**: `docs/IMPLEMENTATION/CREATING_NEW_APPROACH.md`
- **Full AI Prompt**: `docs/REFACTORING_AI_PROMPT.md` (this file)
- **Base Analyzer**: `src/stockreports/alert/analyzer.py`
- **Base Validator**: `src/stockreports/alert/validator.py`
- **Reference**: `src/stockreports/alert/approach/STRONG_CANDLE/`

---

**Remember**: Refactoring preserves logic, improves architecture. Don't change behavior, only location.

