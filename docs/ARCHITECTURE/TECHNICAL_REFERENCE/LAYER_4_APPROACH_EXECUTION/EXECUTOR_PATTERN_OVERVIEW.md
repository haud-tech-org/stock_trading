# Executor Pattern Overview - Foundational Guide

**Status**: ✅ Complete Reference Document (Tier 2)  
**Purpose**: Understand the Executor → Analyzer → Validator pattern used by all trading approaches  
**Scope**: **Executor-level architecture only** (not system-wide; for system overview see ../SYSTEM_ARCHITECTURE_OVERVIEW.md)  
**Audience**: Developers implementing trading approaches, architects  
**Last Updated**: April 10, 2026

---

## 🎯 Executive Summary

The stock trading analysis system uses a **modular Executor → Analyzer → Validator pattern** for implementing trading approaches. This architecture provides:

- **Type Safety**: Enums eliminate magic strings and enable IDE autocomplete
- **Modularity**: Clear separation of concerns (execution, analysis, validation)
- **Testability**: Pure static functions that are trivial to test
- **Maintainability**: Single responsibility principle applied throughout
- **Scalability**: Pattern replicable across 18+ trading approaches

---

## 🏗️ Core Architecture Pattern

### The Executor → Analyzer → Validator Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                      TRADING APPROACH                           │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ EXECUTOR (Orchestration Layer)                           │  │
│  │ ─────────────────────────────────────────────────────── │  │
│  │ • Entry point for analysis                              │  │
│  │ • Coordinates Analyzer and Validator                    │  │
│  │ • Manages state and configuration                       │  │
│  │ • Returns final signal (BUY/SELL/NEUTRAL)              │  │
│  │ • Handles error conditions                              │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ ANALYZER (Calculation Layer)                            │  │
│  │ ─────────────────────────────────────────────────────── │  │
│  │ Pure static methods for numerical calculations:         │  │
│  │ • Body size and ratio calculations                      │  │
│  │ • Candle color classification                           │  │
│  │ • Window-based aggregations                             │  │
│  │ • Price range calculations                              │  │
│  │ • Volume analysis                                        │  │
│  │ • Trend determination                                    │  │
│  └──────────────────────────────────────────────────────────┘  │
│                            ↓                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │ VALIDATOR (Verification Layer)                          │  │
│  │ ─────────────────────────────────────────────────────── │  │
│  │ Pure static methods for business logic validation:      │  │
│  │ • Color consistency checks                              │  │
│  │ • Threshold comparisons                                 │  │
│  │ • Ratio validation                                       │  │
│  │ • Volume multiplier checks                              │  │
│  │ • DataFrame structure validation                        │  │
│  │ • Required column verification                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

**EXECUTOR** (Orchestration)
- Loads market data (OHLCV)
- Applies settings (window sizes, thresholds)
- Calls Analyzer for calculations
- Calls Validator for verification
- Combines results into final signal
- Handles exceptions and edge cases

**ANALYZER** (Pure Calculations)
- Contains NO business logic
- Contains NO conditional branching based on values
- All methods are `@staticmethod`
- Input: DataFrame or single candle
- Output: Calculated value (number, color, boolean)
- Examples: body_size, candle_color, window_high, max_volume

**VALIDATOR** (Pure Verification)
- Checks if conditions are met
- Returns boolean or throws exception
- All methods are `@staticmethod`
- Accepts enums instead of strings
- Examples: color_consistent?, price_above_threshold?, volume_multiplied?

---

## 📚 Class Hierarchy

### Base Classes (Abstract Foundation)

```
┌─────────────────────────────────────────────────────────┐
│ Analyzer (Base Class - 220 lines)                       │
│ ─────────────────────────────────────────────────────── │
│ Location: src/stockreports/alert/analyzer.py           │
│                                                          │
│ 9 Common Static Methods:                                │
│  1. calculate_body_ratio()                              │
│  2. calculate_body_size()                               │
│  3. get_candle_color()                                  │
│  4. get_window_size_and_trend()                         │
│  5. calculate_window_price_range()                      │
│  6. calculate_conditional_window_price_range()          │
│  7. get_max_volume_in_window()                          │
│  8. get_max_volume_in_conditional_window()              │
│  9. get_opposite_color_candles()                        │
│                                                          │
│ All methods use CandleColumn enums:                     │
│  • CandleColumn.OPEN                                    │
│  • CandleColumn.HIGH                                    │
│  • CandleColumn.LOW                                     │
│  • CandleColumn.CLOSE                                   │
│  • CandleColumn.VOLUME                                  │
│                                                          │
│ Returns type-safe results:                              │
│  • get_candle_color() → CandleColor enum                │
│  • Others → float, int, pd.DataFrame                    │
└─────────────────────────────────────────────────────────┘
                         △
                         │ Inherited by
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   STRONG_CANDLE    ICHIMOKU         VRA (future)
   Analyzer         Analyzer         Analyzer
```

```
┌─────────────────────────────────────────────────────────┐
│ Validator (Base Class - 240 lines)                      │
│ ─────────────────────────────────────────────────────── │
│ Location: src/stockreports/alert/validator.py          │
│                                                          │
│ 10 Common Static Methods:                               │
│  1. validate_candle_color_consistency()                 │
│  2. validate_opposite_color_exists()                    │
│  3. validate_price_threshold()                          │
│  4. validate_ratio_threshold()                          │
│  5. validate_volume_threshold()                         │
│  6. validate_volume_multiplier()                        │
│  7. validate_dataframe_not_empty()                      │
│  8. validate_required_columns()                         │
│  9. validate_window_size()                              │
│  10. validate_data_quality()                            │
│                                                          │
│ Type-safe parameters:                                   │
│  • validate_candle_color_consistency(df, target_color: │
│    CandleColor)                                         │
│  • validate_price_threshold(price, threshold,          │
│    comparison: Comparison) - NO DEFAULT                │
│  • validate_volume_threshold(volume, threshold,        │
│    comparison: Comparison) - NO DEFAULT                │
│                                                          │
│ All return: boolean (True = condition met)              │
└─────────────────────────────────────────────────────────┘
                         △
                         │ Inherited by
                         │
        ┌────────────────┼────────────────┐
        │                │                │
  STRONG_CANDLE      ICHIMOKU         VRA (future)
  Validator          Validator        Validator
```

### Concrete Implementations

**STRONG_CANDLE Approach**
```
StrongCandleExecutor
    ├─ Inherits: ExecutorBase (abstract pattern)
    ├─ Has: StrongCandleAnalyzer
    ├─ Has: StrongCandleValidator
    └─ Settings: min_body_ratio, min_volume_multiplier, lookback

StrongCandleAnalyzer
    ├─ Inherits: Analyzer (9 methods)
    ├─ Adds: 0 new methods (uses all base)
    └─ Includes: Body ratio, candle color, volume analysis

StrongCandleValidator
    ├─ Inherits: Validator (10 methods)
    ├─ Adds: 2 specific methods
    └─ Includes: Color consistency, threshold validation
```

**ICHIMOKU Approach**
```
IchimokuExecutor
    ├─ Inherits: ExecutorBase
    ├─ Has: IchimokuAnalyzer
    ├─ Has: IchimokuValidator
    └─ Settings: conversion_period, base_period, ahead_period

IchimokuAnalyzer
    ├─ Inherits: Analyzer (9 methods)
    ├─ Adds: 5+ custom methods (tenkan, kijun, etc.)
    └─ Combines: Base methods + custom calculations

IchimokuValidator
    ├─ Inherits: Validator (10 methods)
    ├─ Adds: 3 custom validation methods
    └─ Includes: Cloud validation, trend validation
```

---

## 🔤 Type Safety System

### Enum Classes for Self-Documenting Code

**CandleColor** (Color Classification)
```python
class CandleColor:
    """Candle color classification"""
    GREEN = "GREEN"      # Close > Open
    RED = "RED"          # Close < Open
    NEUTRAL = "NEUTRAL"  # Close = Open
```

**Comparison** (Comparison Operators)
```python
class Comparison:
    """Threshold comparison types"""
    GREATER = "greater"              # value > threshold
    LESS = "less"                    # value < threshold
    EQUAL = "equal"                  # value == threshold
    GREATER_EQUAL = "greater_equal"  # value >= threshold
    LESS_EQUAL = "less_equal"        # value <= threshold
```

**CandleColumn** (OHLCV Access)
```python
class CandleColumn:
    """Candle column names for DataFrame access"""
    OPEN = "open"      # Opening price
    HIGH = "high"      # Highest price
    LOW = "low"        # Lowest price
    CLOSE = "close"    # Closing price
    VOLUME = "volume"  # Trading volume
```

### Type-Safe Constants with Enums

Using Python enums provides:
- **IDE Support**: Full autocomplete for all available options
- **Type Checking**: IDE catches typos and invalid values before runtime
- **Safe Refactoring**: Rename enum values safely across codebase
- **Self-Documentation**: Intent is clear from enum member names
- **Maintainability**: Single source of truth for all constants
- **Error Prevention**: Impossible to use invalid string values

---

## 🔄 Data Flow

### Complete Analysis Flow

```
┌──────────────────────────────────────────────────────────────┐
│ 1. INPUT DATA                                                │
│ ─────────────────────────────────────────────────────────── │
│ • Market data (OHLCV) for current symbol                    │
│ • Time period (lookback window)                             │
│ • Settings (thresholds, parameters)                         │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 2. EXECUTOR INITIALIZATION                                   │
│ ─────────────────────────────────────────────────────────── │
│ • Load market data                                          │
│ • Validate settings                                         │
│ • Initialize Analyzer (inherits 9 methods)                 │
│ • Initialize Validator (inherits 10 methods)               │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 3. ANALYSIS PHASE                                            │
│ ─────────────────────────────────────────────────────────── │
│ Analyzer.calculate_body_ratio(latest_candle)                │
│   → Returns: float (e.g., 0.65)                             │
│                                                              │
│ Analyzer.get_candle_color(latest_candle)                   │
│   → Returns: CandleColor.GREEN | CandleColor.RED           │
│                                                              │
│ Analyzer.get_max_volume_in_window(dataframe)                │
│   → Returns: float (e.g., 2500000)                          │
│                                                              │
│ Analyzer.get_opposite_color_candles(dataframe)              │
│   → Returns: pd.DataFrame (filtered rows)                   │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 4. VALIDATION PHASE                                          │
│ ─────────────────────────────────────────────────────────── │
│ Validator.validate_candle_color_consistency(                │
│     dataframe,                                              │
│     target_color=CandleColor.GREEN)                         │
│   → Returns: bool                                           │
│                                                              │
│ Validator.validate_price_threshold(                         │
│     current_price=100.5,                                    │
│     threshold=100.0,                                        │
│     comparison=Comparison.GREATER)                          │
│   → Returns: bool                                           │
│                                                              │
│ Validator.validate_volume_threshold(                        │
│     current_volume=2000000,                                 │
│     threshold=1500000,                                      │
│     comparison=Comparison.GREATER)                          │
│   → Returns: bool                                           │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 5. SIGNAL GENERATION                                         │
│ ─────────────────────────────────────────────────────────── │
│ Executor combines all validations:                          │
│   if (all_validators_pass) then SELL                        │
│   else NEUTRAL                                              │
└──────────────────────────────────────────────────────────────┘
                            ↓
┌──────────────────────────────────────────────────────────────┐
│ 6. OUTPUT                                                    │
│ ─────────────────────────────────────────────────────────── │
│ • Signal: BUY | SELL | NEUTRAL                              │
│ • Confidence: Low | Medium | High                           │
│ • Rationale: List of triggered conditions                   │
│ • Metadata: Calculation details                             │
└──────────────────────────────────────────────────────────────┘
```

---

## 🎓 Design Principles

### 1. Single Responsibility Principle
- **Executor**: Orchestration only
- **Analyzer**: Calculation only
- **Validator**: Verification only

Each class has one reason to change.

### 2. Pure Functions
- All Analyzer methods are pure (no side effects)
- All Validator methods are pure (no side effects)
- Testable without mocking or setup

### 3. Type Safety
- No magic strings anywhere
- Enums used for all categorical values
- Type hints on all parameters and returns
- IDE can catch errors before runtime

### 4. Composition Over Inheritance
- Executor USES Analyzer (composition)
- Executor USES Validator (composition)
- Analyzer INHERITS common methods (inheritance where appropriate)
- Validator INHERITS common methods (inheritance where appropriate)

### 5. DRY (Don't Repeat Yourself)
- 19 common methods in base classes
- Used by all trading approaches
- Update once, all approaches benefit
- Zero code duplication

### 6. Testability
- Static methods = no instance state
- Pure functions = no setup needed
- Direct input/output = trivial assertions
- 100% coverage achievable with minimal tests

---

##  How Files Connect

```
src/stockreports/alert/
│
├─ analyzer.py (Base Class - 220 lines)
│  ├─ 9 common static methods
│  ├─ Uses CandleColumn enums
│  ├─ Returns CandleColor, float, int, DataFrame
│  └─ Inherited by all specific analyzers
│
├─ validator.py (Base Class - 240 lines)
│  ├─ 10 common static methods
│  ├─ Uses Comparison enum
│  ├─ Uses CandleColor enum
│  ├─ Returns boolean
│  └─ Inherited by all specific validators
│
├─ common/constants.py (Type-Safe Constants)
│  ├─ CandleColor: GREEN, RED, NEUTRAL
│  ├─ Comparison: GREATER, LESS, EQUAL, etc.
│  ├─ CandleColumn: OPEN, HIGH, LOW, CLOSE, VOLUME
│  └─ Signal: BUY, SELL, NEUTRAL
│
└─ approach/
   ├─ STRONG_CANDLE/
   │  ├─ executor.py
   │  ├─ analyzer.py (inherits 9 methods)
   │  └─ validator.py (inherits 10 methods)
   │
   ├─ ICHIMOKU/
   │  ├─ executor.py
   │  ├─ analyzer.py (base methods + custom)
   │  └─ validator.py
   │
   └─ VRA/, RCM/, CVA/, ... (16 more approaches)
```

---

## 🚀 Implementation Pattern

### Creating a New Approach

**Step 1: Create Executor** (30 lines typical)
```python
from src.stockreports.alert.executor_base import ExecutorBase
from src.stockreports.alert.approach.MyApproach.analyzer import MyAnalyzer
from src.stockreports.alert.approach.MyApproach.validator import MyValidator

class MyExecutor(ExecutorBase):
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = MyAnalyzer()
        self.validator = MyValidator()
    
    def run(self, dataframe):
        # Orchestrate analysis and validation
        # Return signal
```

**Step 2: Create Analyzer** (20-50 lines)
```python
from src.stockreports.alert.analyzer import Analyzer

class MyAnalyzer(Analyzer):
    # Inherit all 9 common methods
    # Add 2-3 custom methods if needed
    
    @staticmethod
    def my_custom_calculation(candle):
        return float
```

**Step 3: Create Validator** (30-50 lines)
```python
from src.stockreports.alert.validator import Validator

class MyValidator(Validator):
    # Inherit all 10 common methods
    # Add 2-3 custom validation methods if needed
    
    @staticmethod
    def my_custom_validation(data, threshold):
        return bool
```

**Result**: ~100 lines of code total (much smaller!)

---

## 📚 Related Documentation

- **DESIGN_PATTERNS_GUIDE.md** - Deep dive into pattern variations
- **TECHNICAL_REFERENCE/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md** - Architecture and design patterns (Tier 2)
- **IMPLEMENTATION_GUIDES/ANALYZER_VALIDATOR_QUICK_REFERENCE.md** - Step-by-step guide for creating helper classes (Tier 3)
- **IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md** - Complete guide for creating executors (Tier 3)
- **CODE_QUALITY_STANDARDS.md** - Type hints, docstrings, formatting requirements

---

## ✅ Key Takeaways

1. **Architecture Pattern**: Executor → Analyzer → Validator
2. **Type Safety**: Enums (CandleColor, Comparison, CandleColumn)
3. **Reusability**: Base classes with 19 common methods
4. **Modularity**: Clear separation of concerns
5. **Testability**: Pure static methods throughout
6. **Scalability**: Pattern works for all 18+ trading approaches
7. **Maintainability**: Changes propagate to all approaches automatically

---

**Status**: ✅ Foundation document complete  
**Next**: Read DESIGN_PATTERNS_GUIDE.md for pattern variations  
**Recommended Time**: 20 minutes to understand  
**Difficulty**: Beginner-friendly with diagrams
