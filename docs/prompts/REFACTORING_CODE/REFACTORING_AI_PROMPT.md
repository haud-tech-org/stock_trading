# AI-Assisted Code Refactoring Prompt - Complete Guidelines

**Document Type**: Master Prompt Template for Code Refactoring  
**Purpose**: Guide AI models to refactor legacy code into Executor → Analyzer → Validator architecture without changing business logic or validations  
**Version**: 1.0  
**Created**: March 15, 2026  
**Status**: ✅ Proven & Verified (4 approaches successfully refactored)

---

## 🎯 Executive Prompt

You are an expert software architect specializing in code refactoring. Your task is to refactor a **legacy trading alert approach** into the modern **Executor → Analyzer → Validator (EAV) pattern** while preserving 100% of the business logic and validation rules.

### Critical Constraint

**⚠️ VALIDATION INTEGRITY GUARANTEE**: Every validation rule, condition, threshold check, and business logic branch MUST be preserved exactly as it exists in the original code. This is NOT a code cleanup—it is an architectural alignment operation.

---

## 📋 Technical Reference: Architecture Foundation - Read First

Before refactoring ANY approach, you MUST understand and internalize the following documents:

### Mandatory Reading (in this order):

1. **`docs/ARCHITECTURE/ARCHITECTURE_OVERVIEW.md`** (529 lines)
   - Read ENTIRE document: Lines 1-150 are especially critical
   - Understand the core EAV pattern: Executor → Analyzer → Validator
   - Learn the component responsibilities (Executor, Analyzer, Validator)
   - Key concept: Analyzer = Pure Calculations, Validator = Business Logic Checks

2. **`docs/ARCHITECTURE/DESIGN_PATTERNS_GUIDE.md`** (630 lines)
   - Read lines 1-150 carefully
   - Understand the CRITICAL PRINCIPLE: "Implement `_find_alerts()`, don't override `run()`"
   - Understand why this pattern solves the monolithic executor problem
   - Learn the anti-patterns (what NOT to do)

3. **`docs/ARCHITECTURE/EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md`**
   - Understand the abstract method design
   - Know when to implement vs. override
   - Learn the rule: Only RCM overrides `run()`, others implement `_find_alerts()`

4. **`docs/IMPLEMENTATION/CREATING_NEW_APPROACH.md`** (848 lines)
   - Read lines 1-200 for step-by-step guidance
   - Understand the complete implementation pattern
   - See the template structure for Executor, Analyzer, Validator

5. **Reference Implementations** (AFTER reading docs):
   - Study `src/stockreports/alert/approach/STRONG_CANDLE/` (90% refactored)
   - Study `src/stockreports/alert/approach/VRA/` (100% refactored + bug fixed)
   - These ARE the working examples of correct refactoring

### Critical Documents to Reference

- **Base Classes**:
  - `src/stockreports/alert/analyzer.py` (220 lines) - 9 inherited methods
  - `src/stockreports/alert/validator.py` (240 lines) - 10 inherited methods
  - `src/stockreports/alert/executor.py` (400+ lines) - loop setup, window context

- **Constants**:
  - `src/stockreports/alert/common/constants.py` - Approach, Signal, Trend, CandleColor enums
  - `src/stockreports/config/signal_settings.py` - Centralized configuration

- **Utilities**:
  - `src/stockreports/utils/candle_utils.py` - Common candle operations
  - `src/stockreports/utils/window_utils.py` - Window analysis utilities

---

## 🔍 Implementation Guides: Analysis - Understand the Original Code

### Step 1: Identify the Approach

**Input**: A legacy executor file (typically 300-500 lines)

**Task**: Determine what the approach does:
- What is the trading signal? (e.g., "Strong red candle with volume confirmation")
- What are the main validation steps?
- What data does it require? (OHLCV? Indicators?)
- What thresholds are used?

**Output**: A 1-2 paragraph summary describing the business logic

### Step 2: Extract Business Logic Flows

**Task**: Map out the EXACT validation flow

**Method**:
1. Find the main loop (typically `for i in range(...):`)
2. Identify each validation step (usually prefixed with "# Step X:")
3. Document what each step checks
4. Note the conditions that lead to alert or rejection

**Output**: A flowchart or detailed checklist like:
```
Main Loop:
  ├─ Step 1: Validate candle A (check X, Y, Z)
  │   └─ If fails → continue (skip to next iteration)
  │   └─ If passes → return value_A
  ├─ Step 2: Validate candle B (check P, Q, R)
  │   └─ If fails → continue
  │   └─ If passes → return value_B
  ├─ Step 3: Validate relationship (check S, T, U using values from Step 1 & 2)
  │   └─ If fails → continue
  │   └─ If passes → proceed
  └─ Step 4: Create and return alert
```

### Step 3: Identify Validation Rules

**Task**: Extract EVERY validation rule and threshold

**Method**:
1. Search for `if not`, `if ... <`, `if ... >`, `if ... ==`
2. Document the exact condition and what it checks
3. Note the threshold values (e.g., `body_ratio >= 0.7`)
4. Identify any edge cases (e.g., "skip if volume == 0")

**Example from STRONG_CANDLE**:
```
✓ Body ratio must be >= 0.7
✓ Body size must be >= 10 (in price points)
✓ Volume must be > max_volume_in_window * multiplier
✓ All candles in window must be same color
✓ At least one opposite-color candle in window
✓ Price must move by at least magnitude_threshold
```

**Output**: Validation checklist (will be preserved in refactored code)

### Step 4: Identify Data Transformations

**Task**: Find where data is calculated vs. validated

**Method**:
1. Find mathematical operations (additions, divisions, min/max)
2. Determine if it's a pure calculation or includes validation logic
3. Mark for ANALYZER (if pure) or VALIDATOR (if includes logic)

**Example**:
```
candle_body_ratio = abs(close - open) / (high - low)
  → ANALYZER: calculate_body_ratio()

if candle_body_ratio >= min_ratio:
  → VALIDATOR: validate_body_ratio()
```

---

## 🏗️ Phase 3: Refactoring - Split into EAV

### Rule 1: Executor (Orchestration Only)

**Size**: 30-80 lines (not counting comments)

**Responsibility**: Coordinate, don't compute

**Structure**:
```python
class [ApproachName]Executor(Executor):
    def __init__(self, symbol: str):
        self.settings = [ApproachName]Settings(symbol)
        self.analyzer = [ApproachName]Analyzer()
        self.validator = [ApproachName]Validator()
        super().__init__(symbol, Approach.[APPROACH_NAME], self.settings)

    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        # 1. Setup loop using BASE CLASS utility
        df_indexed, loop_start, loop_end = self.get_loop_setup(...)
        
        for i in range(loop_end, loop_start - 1, -1):
            # 2. Extract window using BASE CLASS utility
            self.set_window_context(i, df_indexed, lookback_window_size)
            
            # 3. Call ANALYZER for calculations
            result_a = self.analyzer.some_calculation(self.last_candle)
            
            # 4. Call VALIDATOR for checks
            is_valid = self.validator.some_check(result_a, self.settings.threshold)
            if not is_valid:
                continue
            
            # 5. Combine and create alert
            alert = self._create_alert_with_details(...)
            self.alerts.append(alert)
        
        return self.alerts
```

**Key Patterns**:
- ✅ Use `self.get_loop_setup()` (inherited from base Executor)
- ✅ Use `self.set_window_context()` (inherited from base Executor)
- ✅ Call `self.analyzer.method()` for calculations
- ✅ Call `self.validator.method()` for validations
- ✅ Use `self.next_step()` and `self.next_validation()` for logging
- ❌ DO NOT do calculations in executor
- ❌ DO NOT put business logic in executor
- ❌ DO NOT override `run()` (implement `_find_alerts()` instead)

**Validation Preservation Example**:
```python
# ORIGINAL CODE:
if body_ratio < min_body_ratio:
    log("Body ratio too small")
    return None

# REFACTORED CODE:
if not self.validator.validate_body_ratio(body_ratio, self.settings.min_body_ratio):
    log("Body ratio too small")
    continue

# ✅ Logic preserved: same condition, same outcome
# ✅ Only location changed: moved to validator
```

---

### Rule 2: Analyzer (Pure Calculations Only)

**Size**: 0-100 lines (often just inherit 9 base methods)

**Responsibility**: Calculate values WITHOUT business logic

**Characteristics**:
- All methods are `@staticmethod`
- No conditional branching (no `if`, `else`)
- Return raw calculated values
- Accept candle (dict/Series) or DataFrame
- Return: float, int, CandleColor, or DataFrame

**Structure**:
```python
class [ApproachName]Analyzer(Analyzer):
    """
    Analyzer for [APPROACH_NAME] approach.
    
    Inherits 9 base methods:
    - calculate_body_ratio()
    - calculate_body_size()
    - get_candle_color()
    - get_window_size_and_trend()
    - calculate_window_price_range()
    - calculate_conditional_window_price_range()
    - get_max_volume_in_window()
    - get_max_volume_in_conditional_window()
    - get_opposite_color_candles()
    
    Custom methods for approach-specific calculations:
    - (Add only if NOT covered by base 9 methods)
    """
    
    @staticmethod
    def your_custom_calculation(candle: pd.Series) -> float:
        """
        Pure calculation: no business logic.
        
        Args:
            candle: OHLCV row
            
        Returns:
            float: Calculated value
        """
        # Mathematical operation only, NO validation
        value = (candle['high'] - candle['low']) * 0.5
        return value
```

**What Goes in Analyzer** (Pure Math):
```python
✓ body_ratio = abs(close - open) / (high - low)
✓ body_size = abs(close - open)
✓ window_high = max(df['high'])
✓ volume_ratio = alert_volume / min_volume
✓ trend = "uptrend" if close > open else "downtrend"
```

**What Does NOT Go in Analyzer** (Business Logic):
```python
✗ if body_ratio > threshold: → VALIDATOR
✗ if volume * multiplier < max_vol: → VALIDATOR
✗ if candle_index < min_index: → VALIDATOR
✗ all checks, conditions, validations → VALIDATOR
```

**Validation Preservation Example**:
```python
# ORIGINAL CODE (mixed logic):
def check_body_size():
    body_size = abs(close - open)
    if body_size < 10:
        return None
    return body_size

# REFACTORED CODE (separated):
# In Analyzer:
@staticmethod
def calculate_body_size(candle):
    return abs(candle['close'] - candle['open'])

# In Validator:
@staticmethod
def validate_body_size(body_size, min_size):
    return body_size >= min_size

# ✅ Calculation preserved: same formula
# ✅ Validation preserved: same threshold check
# ✅ Only location changed: split into two methods
```

---

### Rule 3: Validator (Business Logic Only)

**Size**: 50-200 lines (often inherits 10 base methods)

**Responsibility**: Check conditions and return boolean

**Characteristics**:
- All methods are `@staticmethod`
- Accept calculated values or DataFrames
- Compare against thresholds
- Return boolean or raise exception
- No data transformation

**Structure**:
```python
class [ApproachName]Validator(Validator):
    """
    Validator for [APPROACH_NAME] approach.
    
    Inherits 10 base methods:
    - validate_candle_color_consistency()
    - validate_opposite_color_exists()
    - validate_price_threshold()
    - validate_ratio_threshold()
    - validate_volume_threshold()
    - validate_volume_multiplier()
    - validate_dataframe_not_empty()
    - validate_required_columns()
    - validate_window_size()
    - validate_data_quality()
    
    Custom validations for approach-specific rules:
    - (Add only if NOT covered by base 10 methods)
    """
    
    @staticmethod
    def validate_custom_condition(
        value: float,
        threshold: float,
        optional_comparison: pd.DataFrame = None
    ) -> bool:
        """
        Validate a business logic condition.
        
        Checks: value >= threshold (for example)
        
        Args:
            value: Calculated value from analyzer
            threshold: Configuration threshold
            optional_comparison: DataFrame for additional checks
            
        Returns:
            bool: True if valid, False otherwise
        """
        # Pure validation: compare, check, return boolean
        if value < threshold:
            return False
        
        if optional_comparison is not None:
            if len(optional_comparison) == 0:
                return False
        
        return True
```

**What Goes in Validator** (Business Logic):
```python
✓ if ratio >= threshold: return True
✓ if volume < max_volume: return False
✓ if all colors match: return True
✓ Any condition checking thresholds
✓ Any filtering based on business rules
✓ Any "must have" or "must not have" checks
```

**What Does NOT Go in Validator** (Data Transformation):
```python
✗ body_ratio = abs(close - open) / (high - low) → ANALYZER
✗ volume_ratio = a / b → ANALYZER
✗ max_volume = df['volume'].max() → ANALYZER
✗ Any calculation, aggregation, transformation → ANALYZER
```

**Validation Preservation Example**:
```python
# ORIGINAL CODE:
if not min_vol_candle.name < max_vol_candle.name < alert_candle.name:
    return None  # Validation failed

# REFACTORED CODE:
@staticmethod
def validate_volume_sequence(min_candle, max_candle, alert_candle, window):
    min_idx = window.index.get_loc(min_candle.name)
    max_idx = window.index.get_loc(max_candle.name)
    alert_idx = window.index.get_loc(alert_candle.name)
    return min_idx < max_idx <= alert_idx  # Note: <= allows max==alert

# ✅ Logic preserved: same ordering check
# ✅ Validation preserved: same condition evaluated
# ✅ Note: If original had <, keep <. If original allowed <=, use <=.
```

---

## ⚠️ Phase 4: Validation Preservation - Critical Rules

### Rule 1: Preserve Exact Conditions

**Original Code**:
```python
if ratio >= 4.5:
    # ... alert
```

**Refactored Code**:
```python
if self.validator.validate_ratio(ratio, 4.5):
    # ... alert
```

**✓ Correct**: Same condition (`>=`), same threshold (4.5)
**✗ Wrong**: Changing to `>` or `5.0` changes business logic

### Rule 2: Preserve All Edge Cases

**Original Code**:
```python
if volume == 0:
    return float('inf')  # Special case for zero volume
elif volume > 0:
    ratio = alert_vol / volume
    if ratio >= threshold:
        return True
```

**Refactored Code**:
```python
# In Analyzer:
@staticmethod
def calculate_volume_ratio(alert_vol, min_vol):
    if min_vol == 0 and alert_vol > 0:
        return float('inf')  # Preserve edge case
    return alert_vol / min_vol

# In Validator:
@staticmethod
def validate_ratio(ratio, threshold):
    if ratio is None:
        return False
    if ratio == float('inf'):
        return True  # Preserve edge case
    return ratio >= threshold
```

**✓ Correct**: All edge cases preserved
**✗ Wrong**: Removing the `float('inf')` handling

### Rule 3: Preserve Loop Logic

**Original Code**:
```python
for i in range(loop_end, loop_start - 1, -1):
    self.set_window_context(i, df_indexed, window_size)
    
    # Step 1
    val_a = calc_a(self.last_candle)
    if not check_a(val_a):
        continue
    
    # Step 2
    val_b = calc_b(val_a)
    if not check_b(val_b):
        continue
    
    # Step 3: Create alert
```

**Refactored Code**:
```python
for i in range(loop_end, loop_start - 1, -1):
    self.set_window_context(i, df_indexed, window_size)
    
    # Step 1
    self.next_step()
    val_a = self.analyzer.calc_a(self.last_candle)
    if not self.validator.check_a(val_a, self.settings.threshold_a):
        continue
    
    # Step 2
    self.next_step()
    val_b = self.analyzer.calc_b(val_a)
    if not self.validator.check_b(val_b, self.settings.threshold_b):
        continue
    
    # Step 3: Create alert
```

**✓ Correct**: Same loop structure, same branching (continue if fails)
**✗ Wrong**: Changing the order of steps or validation flow

### Rule 4: Preserve Return Values

**Original Code**:
```python
def _step_validate(...):
    if condition_a:
        return None  # Failure
    
    if condition_b:
        return None  # Failure
    
    return calculated_value  # Success
```

**Refactored Code**:
```python
def _step_validate(...):
    self.next_step()
    
    is_valid_a = self.validator.check_a(...)
    if not is_valid_a:
        self.log_failure(...)
        return None
    
    is_valid_b = self.validator.check_b(...)
    if not is_valid_b:
        self.log_failure(...)
        return None
    
    return calculated_value
```

**✓ Correct**: Same None returns for failure, same value for success
**✗ Wrong**: Changing exception handling or return types

### Rule 5: Preserve Settings and Thresholds

**Original Code**:
```python
MIN_BODY_RATIO = 0.7
MIN_BODY_SIZE = 10

if body_ratio < MIN_BODY_RATIO:
    return None
if body_size < MIN_BODY_SIZE:
    return None
```

**Refactored Code**:
```python
# In settings.py:
self.min_body_ratio = self.get("MIN_BODY_RATIO")  # = 0.7
self.min_body_size = self.get("MIN_BODY_SIZE")    # = 10

# In executor:
if not self.validator.validate_body_ratio(body_ratio, self.settings.min_body_ratio):
    continue
if not self.validator.validate_body_size(body_size, self.settings.min_body_size):
    continue
```

**✓ Correct**: Same threshold values from centralized config
**✗ Wrong**: Hardcoding different values or changing defaults

---

## 🧪 Phase 5: Verification - Prove Logic is Preserved

### Checklist 1: Flow Verification

For each refactored approach, verify:

- [ ] Loop setup matches original (same loop bounds, same direction)
- [ ] Window context extraction matches (same window size, same indices)
- [ ] All original steps are present (same number of validation steps)
- [ ] All `continue` statements are preserved (same failure paths)
- [ ] All alert creation logic is preserved (same final result)

### Checklist 2: Condition Verification

For each validation step, verify:

- [ ] Exact same threshold values used
- [ ] Exact same comparison operators (`<`, `<=`, `>`, `>=`, `==`, `!=`)
- [ ] Exact same operands (same variables, same calculations)
- [ ] All edge cases handled (e.g., division by zero, NaN, infinity)
- [ ] All return values match (same success/failure indicators)

### Checklist 3: Calculation Verification

For each analyzer method, verify:

- [ ] Exact same mathematical formulas
- [ ] Exact same input parameters
- [ ] Exact same output types
- [ ] No business logic conditions in analyzer
- [ ] All methods are `@staticmethod`

### Checklist 4: Validator Verification

For each validator method, verify:

- [ ] Exact same threshold comparisons
- [ ] Exact same boolean logic
- [ ] All conditions preserved
- [ ] All return values are boolean (or raise exception)
- [ ] All methods are `@staticmethod`

### Verification Method: Line-by-Line Diff

**Tool**: Use unified diff to compare original vs. refactored

```bash
# Generate diff
diff -u original_executor.py refactored_executor.py > changes.diff

# Analysis:
# - Red (−): Lines moved to Analyzer/Validator
# - Green (+): New method calls to Analyzer/Validator
# - Yellow (context): Lines that stayed in Executor
# 
# Success: Red and Green should be balanced
#          Context lines should be < 50% of total
```

**Validation Success Criteria**:
- All calculations moved to Analyzer are identical
- All validations moved to Validator are identical
- Executor only orchestrates (calls Analyzer, Validator, combines results)
- No business logic is lost or changed

---

## 📝 Phase 6: Documentation - Record Changes

### Template Documentation File

Create a file: `docs/REFACTORING_VERIFICATION/[APPROACH_NAME].md`

```markdown
# [Approach Name] Refactoring Verification

**Status**: ✅ Verified
**Date**: [Date]
**Executor Lines**: Original X → Refactored Y (Z% reduction)
**Validation Integrity**: 100% Preserved

## Original Structure
- Main loop: ...
- Step 1: ...
- Step 2: ...

## Refactored Structure
- Executor._find_alerts(): Orchestration only
- Analyzer: Calculations (inherited 9 base methods)
- Validator: Business logic (custom methods for approach-specific rules)

## Validations Preserved
- [ ] Flow and loop logic
- [ ] All threshold checks
- [ ] All edge cases
- [ ] All return values
- [ ] Settings and configuration

## Known Issues & Fixes
- (If any issues were found and fixed)

## Commit
- SHA: ...
- Message: ...
```

---

## 🚀 Complete Example: VRA Approach

### Original Problem
```python
# ORIGINAL: 469 lines, mixed concerns
class VraExecutor:
    def _find_alerts(self, df):
        for i in range(loop_end, loop_start - 1, -1):
            # Calculate + Validate mixed
            max_vol = df['volume'].max()
            min_vol = df['volume'].min()
            alert_vol = df.iloc[-1]['volume']
            ratio = alert_vol / min_vol
            
            if ratio < multiplier:  # Business logic in executor
                continue
            
            if min_vol_idx >= max_vol_idx:  # Business logic in executor
                continue
```

### Refactored Solution
```python
# REFACTORED: 350 lines, separated concerns

# Analyzer (Calculation)
class VraAnalyzer(Analyzer):
    @staticmethod
    def calculate_volume_ratio(alert_vol, min_vol):
        if min_vol == 0 and alert_vol > 0:
            return float('inf')
        return alert_vol / min_vol

# Validator (Business Logic)
class VraValidator(Validator):
    @staticmethod
    def validate_volume_ratio(ratio, threshold):
        if ratio == float('inf'):
            return True
        return ratio >= threshold

# Executor (Orchestration)
class VraExecutor(Executor):
    def _find_alerts(self, df):
        for i in range(loop_end, loop_start - 1, -1):
            # Step 1: Calculate
            ratio = self.analyzer.calculate_volume_ratio(alert_vol, min_vol)
            
            # Step 2: Validate
            if not self.validator.validate_volume_ratio(ratio, self.settings.volume_multiplier):
                continue
            
            if not self.validator.validate_volume_sequence(min_candle, max_candle, alert_candle, window):
                continue
```

**Verification**:
- ✅ Calculation preserved: exact same formula
- ✅ Validation preserved: exact same threshold check
- ✅ Edge case preserved: `float('inf')` handling for zero volume
- ✅ Logic preserved: same conditions, same outcomes

---

## 🎓 Key Principles Summary

1. **Analyzer = Math Only**
   - No `if`, `else`, or conditions
   - Pure calculations
   - Returns raw values

2. **Validator = Logic Only**
   - Compare and check
   - Return boolean
   - No data transformation

3. **Executor = Coordination Only**
   - Call Analyzer, then Validator
   - Combine results
   - Return final signal

4. **Preserve Everything**
   - Same thresholds
   - Same conditions
   - Same edge cases
   - Same flow

5. **Use Base Classes**
   - Inherit 9 Analyzer methods
   - Inherit 10 Validator methods
   - Use base Executor utilities

---

## 📚 Reference Checklist

When refactoring, keep this close:

- [ ] Read ARCHITECTURE_OVERVIEW.md (full)
- [ ] Read DESIGN_PATTERNS_GUIDE.md (full)
- [ ] Read EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md
- [ ] Study STRONG_CANDLE approach (reference implementation)
- [ ] Study VRA approach (complex reference with fixes)
- [ ] Understand base Analyzer class (220 lines, 9 methods)
- [ ] Understand base Validator class (240 lines, 10 methods)
- [ ] Review constants.py for enums (Approach, Signal, Trend, CandleColor)
- [ ] Review signal_settings.py for centralized config
- [ ] Create approach-specific settings.py (inherit BaseSettings)
- [ ] Create executor.py (implement _find_alerts, not run)
- [ ] Create analyzer.py (inherit base, add custom methods)
- [ ] Create validator.py (inherit base, add custom methods)

---

## 🔍 Common Pitfalls & How to Avoid Them

### Pitfall 1: Putting Business Logic in Analyzer

**Wrong**:
```python
class MyAnalyzer(Analyzer):
    @staticmethod
    def calculate_value(candle):
        value = some_math(candle)
        if value > threshold:  # ❌ Business logic!
            return processed_value
        return raw_value
```

**Right**:
```python
class MyAnalyzer(Analyzer):
    @staticmethod
    def calculate_value(candle):
        value = some_math(candle)
        return value  # Return raw value, no logic

class MyValidator(Validator):
    @staticmethod
    def validate_value(value, threshold):
        return value > threshold  # Business logic here
```

### Pitfall 2: Changing Thresholds During Refactoring

**Wrong**:
```python
# Original: if ratio >= 4.5
# Refactored: self.validator.validate_ratio(ratio, 4.0)  # ❌ Changed!

# This changes the alert behavior!
```

**Right**:
```python
# Original: if ratio >= 4.5
# Refactored: self.validator.validate_ratio(ratio, self.settings.volume_multiplier)
# settings.volume_multiplier = 4.5  # ✅ Preserved!
```

### Pitfall 3: Forgetting Edge Cases

**Wrong**:
```python
# Original handles: if volume == 0, return float('inf')
# Refactored ignores this case ❌
```

**Right**:
```python
@staticmethod
def calculate_volume_ratio(alert_vol, min_vol):
    if min_vol == 0 and alert_vol > 0:
        return float('inf')  # ✅ Preserved!
    return alert_vol / min_vol
```

### Pitfall 4: Overcomplicating Executor

**Wrong**:
```python
def _find_alerts(self, df):
    for i in range(...):
        # 200 lines of logic here
        # Mixing calculation with validation
        # ❌ Executor became a monolith again!
```

**Right**:
```python
def _find_alerts(self, df):
    for i in range(...):
        self.next_step()
        val = self.analyzer.method()
        if not self.validator.check(val):
            continue
        # Alert creation only
```

---

## ✨ Success Criteria

When refactoring is complete:

- ✅ 100% of business logic is preserved
- ✅ 100% of validation rules are preserved
- ✅ 100% of threshold values are preserved
- ✅ 100% of edge cases are preserved
- ✅ Executor is < 100 lines (orchestration only)
- ✅ Analyzer is 0-100 lines (mostly inherited, minimal custom)
- ✅ Validator is 50-200 lines (business logic)
- ✅ All methods are static (@staticmethod)
- ✅ All enums are used (Approach, Signal, Trend, CandleColor)
- ✅ All settings are centralized
- ✅ No circular dependencies
- ✅ Tests pass with 100% of original alerts reproduced

---

## 🎯 Before You Start

**Ask yourself**:

1. Do I understand the EAV pattern? (If no: read docs again)
2. Can I explain why Analyzer ≠ Validator? (If no: read docs again)
3. Have I studied STRONG_CANDLE and VRA examples? (If no: study them)
4. Do I understand the base classes? (If no: read analyzer.py and validator.py)
5. Can I map original code → Analyzer → Validator? (If no: practice with simple example)

**If you can answer YES to all 5**: You're ready to refactor!

---

## 📞 Questions to Ask When Stuck

1. **"Is this a calculation or a validation?"**
   - If it transforms/aggregates data → Analyzer
   - If it checks/compares → Validator

2. **"Does this change the business logic?"**
   - If yes → Don't do it
   - If no → Proceed

3. **"Is there a base method for this?"**
   - Check Analyzer.py (9 methods)
   - Check Validator.py (10 methods)
   - If yes → Inherit and use

4. **"What would the test case be?"**
   - If you can't write a test → Logic unclear
   - Reread original code

5. **"Does this preserve the original alert behavior?"**
   - Run both (original and refactored)
   - Compare alerts produced
   - If different → Bug in refactoring

---

## Final Words

> **Refactoring is NOT rewriting. Every line of business logic must be preserved, moved, not modified. The architecture changes, the logic stays exactly the same.**

Good luck! 🚀

