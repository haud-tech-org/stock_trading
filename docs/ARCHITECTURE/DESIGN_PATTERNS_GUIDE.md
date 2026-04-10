# Design Patterns Guide - Proven Approaches (Overview)

**Status**: ✅ Architectural Overview  
**Purpose**: Understand the design patterns and when to apply them  
**Audience**: Developers, architects, and code reviewers  
**Last Updated**: April 10, 2026  
**Layer**: System-wide (applies to all layers)

---

## 📚 Documentation Structure

This document provides **high-level pattern overview and philosophy**.

For **detailed technical implementation**, see:
- **EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md** (in TECHNICAL_REFERENCE/LAYER_4)
  - Complete technical deep dive into EAV pattern
  - All 19 base methods explained
  - Real-world examples with code

For **step-by-step implementation**, see:
- **EAV_PATTERN_STEP_BY_STEP.md** (in IMPLEMENTATION_GUIDES/LAYER_4)
  - Step-by-step walkthrough for building new approaches
  - Complete code templates
  - Testing strategies

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
- ❌ Monolithic executors (454 lines) mixing concerns
- ❌ Duplicated validation logic across approaches
- ❌ Difficult to test (interdependent components)
- ❌ Hard to understand flow (too much code in one place)
- ❌ Difficult to reuse (tightly coupled)

**Solution Benefits**:
- ✅ Single responsibility (each class has ONE job)
- ✅ Reusable base classes (19 common methods)
- ✅ Testable in isolation (pure functions)
- ✅ Easy to understand (clear flow)
- ✅ Scalable (apply to all 18+ approaches)

### When to Apply

**Use EAV Pattern When:**
- ✅ Adding any new trading approach
- ✅ Refactoring existing approach code
- ✅ Need to test individual components
- ✅ Want reusable analyzer/validator methods
- ✅ Following project architecture standards

---

## 🏗️ Pattern Structure (Quick Overview)

### Layer 1: Executor (30-50 lines)
- **Responsibility**: Orchestrate, don't implement
- **Role**: Coordinates Analyzer and Validator
- **Calls**: analyzer methods for calculations, validator methods for checks
- **Returns**: Trading signal (BUY, SELL, or NEUTRAL)

### Layer 2: Analyzer (20-80 lines)
- **Responsibility**: Pure numerical calculations
- **Methods**: All `@staticmethod` (no state)
- **Input**: Candle dict or DataFrame
- **Output**: Numbers, colors, or DataFrames
- **Base Class**: 9 inherited methods available

### Layer 3: Validator (25-100 lines)
- **Responsibility**: Verify business logic conditions
- **Methods**: All `@staticmethod` (no state)
- **Input**: Values and thresholds with Comparison enum
- **Output**: Boolean (True/False)
- **Base Class**: 10 inherited methods available

**See:** `TECHNICAL_REFERENCE/LAYER_4_APPROACH_EXECUTION/EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md` for complete technical details

---

## 🛡️ Type Safety Principles

### Principle 1: No Magic Strings

**❌ WRONG: Magic strings**
```python
if color == "GREEN":
    comparison = "greater"
```

**✅ CORRECT: Use enums**
```python
from src.stockreports.alert.common.constants import CandleColor, Comparison

if color == CandleColor.GREEN:
    comparison = Comparison.GREATER
```

### Principle 2: No Default Values on Required Parameters

**❌ WRONG: Silent defaults**
```python
def validate_threshold(value, threshold, comparison="greater"):
    # Developer might forget - uses default silently!
```

**✅ CORRECT: Required parameters**
```python
def validate_threshold(value: float, threshold: float, 
                      comparison: Comparison) -> bool:
    # Developer MUST specify - IDE catches if forgotten
```

### Principle 3: Inheritance Over Duplication

**❌ WRONG: Redefine in every analyzer**
```python
class Analyzer1:
    def calculate_body_ratio(self, candle):
        return (close - open) / hl_range

class Analyzer2:
    def calculate_body_ratio(self, candle):
        return (close - open) / hl_range  # Same code!
```

**✅ CORRECT: Inherit from base**
```python
class Analyzer1(Analyzer):
    pass  # Inherits calculate_body_ratio

class Analyzer2(Analyzer):
    pass  # Inherits calculate_body_ratio
```

---

## 🚀 Real-World Example: Before & After

### Before Pattern (Monolithic - 454 lines)
```python
class StrongCandleAlert:  # 454 lines
    def run(self, dataframe):
        # 450+ lines of everything:
        # - Data loading
        # - Calculations
        # - Validation logic
        # - Signal generation
        # - Error handling
        pass
```

**Problems:**
- Hard to test (too many dependencies)
- Hard to understand (450+ lines to read)
- Hard to reuse (tightly coupled)
- Hard to maintain (change anywhere breaks something)

### After Pattern (Modular - 107 lines total)
```python
# Executor (43 lines):
class StrongCandleExecutor:
    def run(self, dataframe):
        latest = dataframe.iloc[-1]
        ratio = self.analyzer.calculate_body_ratio(latest)
        if self.validator.validate_ratio(ratio, threshold):
            return Signal.SELL
        return Signal.NEUTRAL

# Analyzer (29 lines):
class StrongCandleAnalyzer(Analyzer):
    pass  # Inherits all 9 methods

# Validator (35 lines):
class StrongCandleValidator(Validator):
    pass  # Inherits all 10 methods
```

**Results:**
- ✅ -76% reduction in lines
- ✅ Clear separation of concerns
- ✅ Testable in isolation
- ✅ Reusable components

---

## 🎓 Pattern Variations

### Variation 1: Simple Approach
- **Use When**: Logic is straightforward, mostly uses base methods
- **Analyzer**: ~20 lines (inherit 9 methods, no custom)
- **Validator**: ~25 lines (inherit 10 methods, no custom)
- **Example**: STRONG_CANDLE

### Variation 2: Extended Approach
- **Use When**: Need custom calculations or validation
- **Analyzer**: ~80 lines (inherit 9 + add 5 custom methods)
- **Validator**: ~60 lines (inherit 10 + add 3 custom methods)
- **Example**: ICHIMOKU

### Variation 3: Complex Approach
- **Use When**: Approach has significant custom logic
- **Analyzer**: ~150 lines (inherit 9 + add 15 custom methods)
- **Validator**: ~100 lines (inherit 10 + add 8 custom methods)
- **Total**: Still modular and organized (vs. 500+ monolithic)

---

## ⚠️ Common Mistakes to Avoid

### Mistake 1: Calculations in Executor
```python
# ❌ WRONG
def run(self, dataframe):
    ratio = abs(close - open) / (high - low)  # Calculation here!

# ✅ CORRECT
def run(self, dataframe):
    ratio = self.analyzer.calculate_body_ratio(candle)  # Clean!
```

### Mistake 2: Validation Logic in Analyzer
```python
# ❌ WRONG
class Analyzer:
    def analyze_ratio(self, candle):
        if ratio > 0.5:  # Business logic - belongs in Validator!
            return True

# ✅ CORRECT
class Analyzer:
    def analyze_ratio(self, candle):
        return ratio  # Just the number
```

### Mistake 3: String Parameters Instead of Enums
```python
# ❌ WRONG
validator.validate_threshold(100, 90, "greater")

# ✅ CORRECT
validator.validate_threshold(100, 90, Comparison.GREATER)
```

### Mistake 4: Hardcoded Values in Executor
```python
# ❌ WRONG
if ratio > 0.5:  # Magic number!

# ✅ CORRECT
if ratio > self.settings.get("min_ratio", 0.5):
```

---

## 📊 Base Methods Available (19 Total)

### Analyzer Base Methods (9)
1. `calculate_body_ratio(candle)` - Body size relative to range
2. `calculate_body_size(candle)` - |close - open|
3. `get_candle_color(candle)` - GREEN if close > open
4. `calculate_window_price_range(dataframe)` - High - Low
5. `get_max_volume_in_window(dataframe)` - Maximum volume
6. `get_trend_direction(dataframe)` - UP, DOWN, or SIDEWAYS
7. `get_opposite_color_candles(dataframe, color)` - Filter by color
8. `calculate_average_volume_in_window(dataframe)` - Mean volume
9. `get_price_at_position(dataframe, position)` - Price at index

### Validator Base Methods (10)
1. `validate_candle_color_consistency(dataframe, color)` - % of target color
2. `validate_price_threshold(price, threshold, comparison)` - Price check
3. `validate_volume_threshold(volume, threshold, comparison)` - Volume check
4. `validate_ratio_threshold(ratio, threshold, comparison)` - Ratio check
5. `validate_volume_multiplier(current, avg, multiplier)` - Volume X times
6. `validate_required_columns(dataframe, columns)` - Column existence
7. `validate_minimum_window_size(dataframe, min_size)` - Data size
8. `validate_no_null_values(dataframe, columns)` - Null check
9. `validate_price_range(price, min, max)` - Range check
10. `validate_data_recency(timestamp, max_age_minutes)` - Freshness

**See:** `TECHNICAL_REFERENCE/LAYER_4_APPROACH_EXECUTION/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md` for all details

---

## 🔄 Decision Tree: When to Use What

```
START: Implementing new approach?
│
├─ Can reuse all 9 Analyzer base methods?
│  ├─ YES → class YourAnalyzer(Analyzer): pass
│  └─ NO  → Inherit + add custom methods
│
├─ Can reuse all 10 Validator base methods?
│  ├─ YES → class YourValidator(Validator): pass
│  └─ NO  → Inherit + add custom methods
│
├─ Executor complexity?
│  ├─ Simple (30-50 lines) → Good fit for EAV
│  ├─ Medium (50-100 lines) → Good fit for EAV
│  └─ Complex (100+ lines) → Still use EAV (might split further)
│
└─ RESULT: Always use EAV pattern
           (varies in customization, not application)
```

---

## 📚 Related Documentation

**For More Details:**
- **EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md** (TECHNICAL_REFERENCE/LAYER_4)
  - Technical deep dive with complete code examples
  - All 19 base methods explained with examples
  - Real-world STRONG_CANDLE walkthrough

- **EAV_PATTERN_STEP_BY_STEP.md** (IMPLEMENTATION_GUIDES/LAYER_4)
  - Step-by-step implementation guide
  - Code templates for all three classes
  - Complete testing strategies

**Related Patterns:**
- **EXECUTOR_PATTERN_OVERVIEW.md** - Pattern diagrams and concepts
- **EXECUTOR_PATTERN_DIAGRAMS.md** - Visual representations
- **ABSTRACT_BASE_CLASSES_ARCHITECTURE.md** - All base method implementations

**Quality Standards:**
- **CODE_QUALITY_STANDARDS.md** - All code quality requirements
- **ARCHITECTURE_OVERVIEW.md** - System-wide architecture

---

## ✅ Key Takeaways

1. **Always Use EAV Pattern**: For ALL trading approaches
2. **Executor**: Orchestrates (30-50 lines, no calculations)
3. **Analyzer**: Calculates (20-80 lines, pure functions)
4. **Validator**: Verifies (25-100 lines, returns booleans)
5. **Inheritance**: Reuse 19 common methods in base classes
6. **Type Safety**: Use enums, never magic strings
7. **Testability**: Each layer tested independently
8. **Scalability**: Pattern scales from simple to complex approaches

---

## 🎯 Next Steps

**To Implement a New Approach:**
1. Read this document (10 minutes)
2. Read EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md (30 minutes)
3. Follow EAV_PATTERN_STEP_BY_STEP.md (2-3 hours implementation)

**To Review Code:**
1. Check for EAV pattern application
2. Verify Executor has no calculations
3. Verify Analyzer is pure functions
4. Verify Validator returns booleans
5. Check type safety (enums, no defaults)

**To Understand Patterns:**
1. Study EXECUTOR_PATTERN_OVERVIEW.md
2. Review EXECUTOR_PATTERN_DIAGRAMS.md
3. Compare with STRONG_CANDLE_REFACTORING_COMPLETION_REPORT.md

---

**Status**: ✅ Architectural reference  
**Difficulty**: Beginner to Intermediate  
**Time**: 5-10 minutes to understand  
**Next**: See EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md for technical details
