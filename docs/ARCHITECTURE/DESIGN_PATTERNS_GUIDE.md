# Design Patterns Guide - Proven Approaches

**Status**: ✅ Complete Reference Document  
**Purpose**: Understand when and how to apply design patterns  
**Audience**: Developers and architects  
**Last Updated**: March 12, 2026

---

## 🔴 CRITICAL PRINCIPLE: Executor Implementation Rule

> **In derived Executor classes: IMPLEMENT abstract method `_find_alerts()`, do NOT override concrete method `run()`**

Derived Executor classes MUST:
- ✅ Implement the abstract `_find_alerts()` method
- ❌ NOT override the concrete `run()` method (except RCM)
- ✅ Use inherited utilities: `get_loop_setup()`, `set_window_context()`, `next_step()`

Analyzer and Validator classes can:
- ✅ Inherit base methods
- ✅ Override base methods when needed
- ✅ Add custom methods

See: `/docs/ARCHITECTURE/EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md`

---

## 🎯 Core Pattern: Executor → Analyzer → Validator

### Pattern Overview

**Name**: **Executor-Analyzer-Validator (EAV) Pattern**

**Core Idea**: Separate orchestration, calculation, and verification into distinct layers

```
User Input
    ↓
┌─────────────────────────────────┐
│ Executor (Orchestration)        │
│ • Coordinates flow              │
│ • Manages state                 │
│ • Returns final result          │
└─────────────────────────────────┘
    ↓              ↓
 Analyzer    Validator
  (Pure      (Pure Logic
 Calcs)     Verification)
    ↓              ↓
  Output ← Combined Result
```

### Why This Pattern?

**Problem It Solves**:
- Monolithic executors (454 lines) mixing concerns
- Duplicated validation logic across approaches
- Difficult to test (interdependent components)
- Hard to understand flow (too much code in one place)
- Difficult to reuse (tightly coupled)

**Solution Benefits**:
- ✅ Single responsibility (each class has ONE job)
- ✅ Reusable base classes (19 common methods)
- ✅ Testable in isolation (pure functions)
- ✅ Easy to understand (clear flow)
- ✅ Scalable (apply to all 18+ approaches)

---

## 🏗️ Detailed Pattern Structure

### Layer 1: Executor (Orchestration)

**Responsibility**: Coordinate, don't implement

**Typical Size**: 30-50 lines

**Characteristics**:
- Has dependencies on Analyzer and Validator
- Holds configuration/settings
- Manages execution flow
- Returns final trading signal
- Handles errors and edge cases

**Example Pattern** (STRONG_CANDLE):
```python
class StrongCandleExecutor:
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = StrongCandleAnalyzer()
        self.validator = StrongCandleValidator()
    
    def run(self, dataframe):
        latest = dataframe.iloc[-1]
        
        # Call analyzer for calculations
        body_ratio = self.analyzer.calculate_body_ratio(latest)
        candle_color = self.analyzer.get_candle_color(latest)
        
        # Call validator for checks
        checks = [
            self.validator.validate_candle_color_consistency(
                dataframe, candle_color),
            self.validator.validate_ratio_threshold(
                body_ratio, self.settings.min_body_ratio)
        ]
        
        # Combine results
        if all(checks):
            return Signal.SELL
        return Signal.NEUTRAL
```

**Common Patterns**:
1. Create instances of Analyzer/Validator
2. Load and prepare data
3. Call analyzer methods for calculations
4. Call validator methods for checks
5. Combine results into final signal

**Anti-patterns** (What NOT to do):
- ❌ Implement calculations in executor
- ❌ Put business logic in executor
- ❌ Mix data access with orchestration
- ❌ Make it handle too many concerns

---

### Layer 2: Analyzer (Pure Calculation)

**Responsibility**: Pure numerical calculations (no business logic)

**Typical Size**: 20-50 lines (inherits 9 base methods)

**Characteristics**:
- All methods are `@staticmethod` (no instance state)
- No conditional logic based on thresholds
- Returns calculated values (numbers, colors, DataFrames)
- Input: candle (dict or row) or dataframe
- Output: float, int, CandleColor, or DataFrame

**Inheritance Model**:
```python
class Analyzer:  # Base class - 220 lines, 9 methods
    @staticmethod
    def calculate_body_ratio(candle): ...
    
    @staticmethod
    def calculate_body_size(candle): ...
    
    @staticmethod
    def get_candle_color(candle): ...
    # ... 6 more methods
```

```python
class StrongCandleAnalyzer(Analyzer):  # Only 29 lines
    # Inherits all 9 methods automatically
    # Add custom methods if needed
    
    @staticmethod
    def my_custom_calculation(candle):
        return value
```

**Examples of Analyzer Methods**:

1. **calculate_body_ratio()** - How big is the candle body?
   ```python
   Input:  {"open": 100, "close": 105, "high": 108, "low": 98}
   Output: 0.667  (body / hl_range)
   ```

2. **get_candle_color()** - Is it GREEN or RED?
   ```python
   Input:  {"open": 100, "close": 105}
   Output: CandleColor.GREEN  (close > open)
   ```

3. **get_max_volume_in_window()** - What's max volume?
   ```python
   Input:  DataFrame with 50 rows
   Output: 2500000  (highest volume in window)
   ```

4. **get_opposite_color_candles()** - Filter different color candles
   ```python
   Input:  DataFrame with 50 rows, filter_color=GREEN
   Output: DataFrame with 15 RED candles (opposite)
   ```

**Pure Function Guarantees**:
- Same input → Same output always ✅
- No side effects ✅
- Deterministic ✅
- Trivial to test ✅

---

### Layer 3: Validator (Pure Verification)

**Responsibility**: Verify business logic conditions

**Typical Size**: 30-50 lines (inherits 10 base methods)

**Characteristics**:
- All methods are `@staticmethod` (no instance state)
- No calculations, just comparisons
- Returns boolean (condition met or not)
- Takes enums instead of strings (type-safe)
- Input: value, threshold, comparison enum
- Output: True/False

**Type-Safe Parameters**:
```python
# ❌ Old way - strings, confusing
validate_price_threshold(100.5, 100.0, "greater")  # What is "greater"?

# ✅ New way - enums, crystal clear
validate_price_threshold(100.5, 100.0, Comparison.GREATER)  # Obvious intent
```

**Inheritance Model**:
```python
class Validator:  # Base class - 240 lines, 10 methods
    @staticmethod
    def validate_candle_color_consistency(df, target_color): ...
    
    @staticmethod
    def validate_price_threshold(price, threshold, comparison): ...
    
    @staticmethod
    def validate_volume_threshold(volume, threshold, comparison): ...
    # ... 7 more methods
```

```python
class StrongCandleValidator(Validator):  # Only 35 lines
    # Inherits all 10 methods automatically
    # Add approach-specific validation if needed
```

**Examples of Validator Methods**:

1. **validate_candle_color_consistency()** - Are most candles this color?
   ```python
   Input:  dataframe, target_color=CandleColor.GREEN
   Output: True/False
   ```

2. **validate_price_threshold()** - Is price above/below threshold?
   ```python
   Input:  price=100.5, threshold=100.0, comparison=Comparison.GREATER
   Output: True (100.5 > 100.0)
   ```

3. **validate_volume_threshold()** - Is volume high enough?
   ```python
   Input:  volume=2000000, threshold=1500000, comparison=Comparison.GREATER
   Output: True (2000000 > 1500000)
   ```

4. **validate_volume_multiplier()** - Is volume X times average?
   ```python
   Input:  current_volume=2000000, avg_volume=1000000, multiplier=1.5
   Output: True (2000000 >= 1.5 × 1000000)
   ```

**Required Parameters** (No Defaults!):
```python
# ❌ Old way - default comparison
def validate_price_threshold(price, threshold, comparison="greater"):
    # Developer might forget to specify, defaults to "greater"
    # Bug: sometimes wrong comparison used silently

# ✅ New way - required comparison
def validate_price_threshold(price, threshold, comparison: Comparison):
    # Developer MUST specify - no silent defaults
    # Bug: IDE catches if forgotten
```

---

## 🎓 Pattern Variations

### Variation 1: Simple Approach (Minimal Customization)

**When to use**: Approach logic is simple or reuses base methods

**Structure**:
```
Executor: 30 lines (pure orchestration)
Analyzer: 20 lines (only custom methods, inherits 9 base)
Validator: 25 lines (only custom methods, inherits 10 base)
Total: 75 lines (vs. 200-300 for monolithic)
```

**Example**: STRONG_CANDLE
- Executor: orchestrates pre-existing validation rules
- Analyzer: uses all 9 inherited methods
- Validator: uses all 10 inherited methods

### Variation 2: Extended Approach (Custom Methods)

**When to use**: Approach needs specialized calculations/validations

**Structure**:
```
Executor: 40 lines (orchestration + custom logic)
Analyzer: 80 lines (9 inherited + 5 custom calculation methods)
Validator: 60 lines (10 inherited + 3 custom validation methods)
Total: 180 lines (still much cleaner than monolithic)
```

**Example**: ICHIMOKU
- Executor: coordinates complex signal validation
- Analyzer: inherits 9 base + adds Tenkan, Kijun, etc. (5+ custom)
- Validator: inherits 10 base + adds ICHIMOKU-specific checks (3 custom)

### Variation 3: Heavy Customization (Significant Custom Logic)

**When to use**: Approach is complex with many custom calculations

**Structure**:
```
Executor: 50 lines (orchestration + state management)
Analyzer: 150 lines (9 inherited + 15 custom calculations)
Validator: 100 lines (10 inherited + 8 custom validations)
Total: 300 lines (organized and modular)
```

**Example**: CVA (if heavily customized)
- Executor: complex orchestration
- Analyzer: inherits 9 base + many custom methods
- Validator: inherits 10 base + many custom checks

**Benefits Even at 300 Lines**:
- Still more readable than monolithic 500+ line executor
- Clear separation of concerns
- Easier to test each layer
- Base methods reusable in other approaches

---

## 🔄 Pattern Application Flowchart

```
START: Need a new trading approach?
│
├─ YES → Continue
└─ NO → Stop

Step 1: Identify base requirements
   ├─ Uses OHLCV data? → YES
   ├─ Needs color classification? → Probably YES
   ├─ Needs threshold validation? → Probably YES
   └─ Needs volume analysis? → Maybe

Step 2: Can base Analyzer cover it?
   ├─ body_ratio, body_size, candle_color?
   ├─ window_price_range, max_volume?
   ├─ trend_direction, opposite_color?
   └─ If YES → Inherits all 9 methods

Step 3: Can base Validator cover it?
   ├─ color_consistency, price_threshold?
   ├─ ratio_threshold, volume_threshold?
   ├─ volume_multiplier, required columns?
   └─ If YES → Inherits all 10 methods

Step 4: Custom needs?
   ├─ Custom calculations? → Add to Analyzer
   ├─ Custom validation? → Add to Validator
   └─ Complex orchestration? → Expand Executor

Step 5: Build structure
   ├─ Create Executor (30-50 lines)
   ├─ Create Analyzer (20-80 lines)
   ├─ Create Validator (25-100 lines)
   └─ Total: 75-230 lines (clean & maintainable)

Step 6: Test
   ├─ Test Analyzer methods (pure functions)
   ├─ Test Validator methods (pure functions)
   ├─ Test Executor flow (integration)
   └─ Test on real data

DONE: Production-ready approach
```

---

## 🚀 Real-World Example: STRONG_CANDLE

### Before Applying Pattern (Monolithic - 454 lines)
```python
class StrongCandleAlert:
    def run(self, dataframe):
        # 454 lines of mixed concerns:
        # - Data loading
        # - Calculations
        # - Validation logic
        # - Signal generation
        # - Error handling
        # - Everything in ONE place!
        
        # Problems:
        # ❌ Hard to test (too many dependencies)
        # ❌ Hard to understand (450+ lines to read)
        # ❌ Hard to reuse (tightly coupled)
        # ❌ Hard to maintain (change anywhere breaks something)
```

### After Applying Pattern (Modular - 107 lines total)

**Executor** (43 lines):
```python
class StrongCandleExecutor:
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = StrongCandleAnalyzer()
        self.validator = StrongCandleValidator()
    
    def run(self, dataframe):
        # Clear orchestration
        latest = dataframe.iloc[-1]
        body_ratio = self.analyzer.calculate_body_ratio(latest)
        candle_color = self.analyzer.get_candle_color(latest)
        
        checks = [
            self.validator.validate_candle_color_consistency(...),
            self.validator.validate_ratio_threshold(...)
        ]
        
        return Signal.SELL if all(checks) else Signal.NEUTRAL
```

**Analyzer** (29 lines):
```python
class StrongCandleAnalyzer(Analyzer):
    # Inherits 9 methods from base
    # Uses all: calculate_body_ratio, get_candle_color, etc.
    # Doesn't need to redefine anything!
    pass  # That's it!
```

**Validator** (35 lines):
```python
class StrongCandleValidator(Validator):
    # Inherits 10 methods from base
    # Uses all: validate_candle_color_consistency, etc.
    # Only adds 2 STRONG_CANDLE specific checks if needed
```

### Results

```
                Before    After    Reduction
Total Lines:    454       107      -76%
Complexity:     High      Low      Clear flow
Testability:    Difficult Easy     Pure functions
Reusability:    0%        100%     Inherits 19 methods
Readability:    Poor      Excellent Each class: <50 lines
```

---

## 🛡️ Common Mistakes to Avoid

### Mistake 1: Putting Calculations in Executor
```python
# ❌ WRONG - Executor should not calculate
class BadExecutor:
    def run(self, dataframe):
        body_ratio = abs(candle['close'] - candle['open']) / \
                     (candle['high'] - candle['low'])  # Calculation in executor!
```

```python
# ✅ CORRECT - Executor calls analyzer
class GoodExecutor:
    def run(self, dataframe):
        body_ratio = self.analyzer.calculate_body_ratio(candle)  # Clean!
```

### Mistake 2: Putting Validation Logic in Analyzer
```python
# ❌ WRONG - Analyzer should not validate
class BadAnalyzer:
    @staticmethod
    def analyze_body_ratio(candle):
        ratio = ...
        if ratio > 0.5:  # Business logic - belongs in Validator!
            return True
```

```python
# ✅ CORRECT - Analyzer calculates, Validator validates
class GoodAnalyzer:
    @staticmethod
    def analyze_body_ratio(candle):
        return ratio  # Just the number

class GoodValidator:
    @staticmethod
    def validate_ratio(ratio, threshold):
        return ratio > threshold  # Business logic here
```

### Mistake 3: Using String Parameters Instead of Enums
```python
# ❌ WRONG - String is ambiguous
validator.validate_price_threshold(100.5, 100.0, "greater")

# ✅ CORRECT - Enum is clear
validator.validate_price_threshold(100.5, 100.0, Comparison.GREATER)
```

### Mistake 4: Having Default Values on Required Parameters
```python
# ❌ WRONG - Developer might forget to specify
def validate_threshold(value, threshold, comparison="greater"):
    # Silent bug if comparison not specified!

# ✅ CORRECT - No default, must specify
def validate_threshold(value, threshold, comparison: Comparison):
    # IDE catches if comparison forgotten!
```

### Mistake 5: Not Using Inheritance for Common Methods
```python
# ❌ WRONG - Redefine calculate_body_ratio in every analyzer
class BadAnalyzer1:
    def calculate_body_ratio(self, candle):
        return (candle['close'] - candle['open']) / ...

class BadAnalyzer2:
    def calculate_body_ratio(self, candle):
        return (candle['close'] - candle['open']) / ...  # Same code!

# ✅ CORRECT - Inherit from base
class GoodAnalyzer1(Analyzer):
    pass  # Inherits calculate_body_ratio

class GoodAnalyzer2(Analyzer):
    pass  # Inherits calculate_body_ratio
```

---

## 🔍 Pattern Checklist

When designing a new approach, verify:

### Executor Layer
- [ ] Loads data correctly
- [ ] Initializes Analyzer and Validator
- [ ] Calls analyzer for calculations (no direct calculation)
- [ ] Calls validator for checks (no direct validation)
- [ ] Combines results into final signal
- [ ] 30-50 lines (not more than 100)
- [ ] No hardcoded values (use settings)
- [ ] Handles errors gracefully

### Analyzer Layer
- [ ] All methods are `@staticmethod`
- [ ] No instance state
- [ ] No conditional logic based on thresholds
- [ ] Returns values (numbers, colors, DataFrames)
- [ ] Uses CandleColumn enums (not strings)
- [ ] Pure functions (same input → same output)
- [ ] Inherits 9 base methods
- [ ] 20-80 lines (depends on custom methods)

### Validator Layer
- [ ] All methods are `@staticmethod`
- [ ] No instance state
- [ ] Returns boolean only
- [ ] Uses Comparison enum (no string defaults)
- [ ] Uses CandleColor enum (not strings)
- [ ] Pure functions (no side effects)
- [ ] Inherits 10 base methods
- [ ] 25-100 lines (depends on custom methods)

### Type Safety
- [ ] No magic strings for colors
- [ ] No magic strings for comparisons
- [ ] No magic strings for columns
- [ ] All enums used correctly
- [ ] Type hints on all parameters
- [ ] IDE autocomplete works

### Testing
- [ ] All Analyzer methods have tests
- [ ] All Validator methods have tests
- [ ] Executor tested with mock Analyzer/Validator
- [ ] Integration tests on real data
- [ ] Edge cases covered

---

## 📚 Related Documentation

- **ARCHITECTURE_OVERVIEW.md** - System-wide architecture
- **ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md** - All 19 base methods
- **CREATING_NEW_APPROACH.md** - Step-by-step implementation guide
- **CODE_QUALITY_STANDARDS.md** - What makes code production-ready
- **STRONG_CANDLE_REFACTORING_COMPLETION_REPORT.md** - Real-world example

---

## ✅ Key Takeaways

1. **EAV Pattern**: Executor → Analyzer → Validator
2. **Clear Roles**: Orchestration, Calculation, Verification
3. **Type Safety**: Use enums, not strings
4. **Pure Functions**: No side effects or state
5. **Inheritance**: 19 common methods in base classes
6. **Modularity**: Each class 20-100 lines (readable!)
7. **Scalability**: Apply pattern to all 18+ approaches
8. **Maintainability**: Changes propagate to all approaches

---

**Status**: ✅ Complete reference document  
**Next**: See CREATING_NEW_APPROACH.md for step-by-step guide  
**Recommended Time**: 25 minutes to understand  
**Difficulty**: Intermediate developers (assumes basic OOP knowledge)
