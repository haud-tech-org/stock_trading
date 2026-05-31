# Code Quality Standards & Best Practices

**Status**: ✅ Complete Reference Guide  
**Purpose**: Establish and enforce production-ready code standards  
**Audience**: All developers and code reviewers  
**Last Updated**: March 12, 2026

---

## 🎯 Quality Standards Overview

All production code must meet these standards before deployment:

```
TYPE SAFETY          ✅ 100% (no magic strings)
TYPE HINTS          ✅ 100% (all parameters and returns)
DOCSTRINGS          ✅ 100% (all public methods)
CODE STYLE          ✅ PEP 8 compliant
COMPLEXITY          ✅ Cyclomatic complexity < 10
TEST COVERAGE       ✅ 90%+ (critical paths)
REUSABILITY         ✅ DRY principle applied
MODULARITY          ✅ Single responsibility enforced
PERFORMANCE         ✅ O(n) or better
ERROR HANDLING      ✅ Graceful failure
DOCUMENTATION       ✅ Self-documenting code + comments
```

---

## 1️⃣ Type Safety Standards

### Rule: No Magic Strings

**Requirement**: All categorical values must use enums, never strings.

**Colors** → Use `CandleColor` enum:
```python
# ❌ WRONG - Magic string
candle_color = "GREEN"
if color == "GREEN":
    # ...

# ✅ CORRECT - Enum
from src.stockreports.alert.common.constants import CandleColor

candle_color = CandleColor.GREEN
if color == CandleColor.GREEN:
    # IDE autocomplete works
    # Type checking catches errors
```

**Comparisons** → Use `Comparison` enum:
```python
# ❌ WRONG - Magic string with default
def validate_threshold(price, threshold, comparison="greater"):
    # Bug: developer might forget to specify, uses default silently

# ✅ CORRECT - Enum, required parameter
from src.stockreports.alert.common.constants import Comparison

def validate_threshold(price, threshold, comparison: Comparison):
    # IDE catches if comparison forgotten
    # Type checking enforces required parameter
    if comparison == Comparison.GREATER:
        return price > threshold
```

**Columns** → Use `CandleColumn` enum:
```python
# ❌ WRONG - Magic string
df['open'].mean()  # What column is this?
price = candle['close']  # Hope this key exists

# ✅ CORRECT - Enum
from src.stockreports.alert.common.constants import CandleColumn

df[CandleColumn.OPEN].mean()  # Crystal clear
price = candle[CandleColumn.CLOSE]  # Caught by IDE if typo
```

**When to Create New Enums**:
- Multiple hardcoded values of same category
- Same values used in multiple places
- Likely to evolve in future
- Improves readability

---

## 2️⃣ Type Hints Standards

### Rule: Complete Type Annotations

**Requirement**: All methods must have type hints for parameters and returns.

**Function Signatures**:
```python
# ❌ WRONG - No type hints
def calculate_body_ratio(candle):
    return abs(candle['close'] - candle['open']) / ...

# ✅ CORRECT - Complete type hints
def calculate_body_ratio(candle: dict) -> float:
    """Calculate body ratio for candle."""
    return abs(candle['close'] - candle['open']) / ...
```

**Parameter Types**:
```python
# ❌ WRONG
def validate_threshold(price, threshold, comparison):
    pass

# ✅ CORRECT
def validate_threshold(
    price: float,
    threshold: float,
    comparison: Comparison
) -> bool:
    pass
```

**Complex Types**:
```python
# ❌ WRONG
def process_data(df, settings):
    pass

# ✅ CORRECT
import pandas as pd
from typing import Dict, List

def process_data(
    df: pd.DataFrame,
    settings: Dict[str, float]
) -> List[float]:
    pass
```

**Optional Parameters**:
```python
# ❌ WRONG
def analyze(data, threshold=None):
    pass

# ✅ CORRECT
from typing import Optional

def analyze(
    data: pd.DataFrame,
    threshold: Optional[float] = None
) -> float:
    pass
```

---

## 3️⃣ Docstring Standards

### Rule: Every Public Method Must Have Docstring

**Format**: Google-style docstrings

```python
def validate_price_threshold(
    price: float,
    threshold: float,
    comparison: Comparison
) -> bool:
    """
    Validate if price meets threshold using comparison operator.
    
    Pure function - no side effects. Returns True if condition met,
    False otherwise. Uses Comparison enum for type safety.
    
    Args:
        price: Current price to validate (float).
        threshold: Price threshold to compare against (float).
        comparison: Comparison type (Comparison enum).
                   Must be explicitly specified (no defaults).
    
    Returns:
        bool: True if condition met (e.g., price > threshold
              when comparison=Comparison.GREATER), False otherwise.
    
    Raises:
        ValueError: If comparison not in Comparison enum.
    
    Example:
        >>> from src.stockreports.alert.common.constants import Comparison
        >>> validate_price_threshold(100.5, 100.0, Comparison.GREATER)
        True
        >>> validate_price_threshold(99.5, 100.0, Comparison.GREATER)
        False
    
    Note:
        - Pure function (deterministic, no side effects)
        - Works with any float values (positive, negative, zero)
        - Comparison must be explicit (no default "greater")
    """
    if comparison == Comparison.GREATER:
        return price > threshold
    elif comparison == Comparison.LESS:
        return price < threshold
    # ... handle other comparisons
```

**Docstring Components**:

1. **One-line summary** (first line)
   - Verb-noun format ("Calculate...", "Validate...", "Get...")
   - Keep to 79 characters max
   - Be specific (not "Process data", but "Validate price threshold")

2. **Detailed description** (2-3 lines)
   - Explain WHY method exists
   - Note if pure function (no side effects)
   - List key assumptions

3. **Args section**
   - Each parameter on new line
   - Format: `name: type: Description`
   - Include constraints/allowed values

4. **Returns section**
   - Describe return value
   - Include type and meaning
   - What does True/False mean?

5. **Raises section** (if applicable)
   - What exceptions can be raised?
   - Under what conditions?

6. **Example section**
   - Real usage example(s)
   - Should be runnable if possible
   - Show common patterns

7. **Note section** (optional)
   - Important caveats
   - Performance considerations
   - Backward compatibility notes

---

## 4️⃣ Code Style Standards

### PEP 8 Compliance

**Class Names** → PascalCase:
```python
# ✅ CORRECT
class StrongCandleAnalyzer(Analyzer):
    pass

class IchimokuValidator(Validator):
    pass
```

**Function Names** → snake_case:
```python
# ✅ CORRECT
def calculate_body_ratio(candle):
    pass

def validate_price_threshold(price, threshold, comparison):
    pass
```

**Constants** → UPPER_SNAKE_CASE:
```python
# ✅ CORRECT
MAX_WINDOW_SIZE = 100
MIN_VOLUME_MULTIPLIER = 1.0
REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]
```

**Line Length** → 79 characters (PEP 8):
```python
# ❌ WRONG - 92 characters
result = validator.validate_candle_color_consistency(dataframe, CandleColor.GREEN)

# ✅ CORRECT - Break into multiple lines
result = validator.validate_candle_color_consistency(
    dataframe,
    CandleColor.GREEN
)
```

**Imports** → Organized:
```python
# ✅ CORRECT - Standard library first, then third-party, then local
import pandas as pd
from typing import Dict, List

from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.alert.common.constants import CandleColumn
```

---

## 5️⃣ Complexity Standards

### Rule: Keep Methods Simple

**Cyclomatic Complexity** < 10:

```python
# ❌ WRONG - Complexity = 6 (too many branches)
def validate_multiple_conditions(data, settings):
    if data is None:
        return False
    if len(data) < settings.min_size:
        return False
    if data['volume'].sum() < settings.min_volume:
        return False
    if data['close'].mean() > settings.max_price:
        return False
    if data['high'].max() - data['low'].min() > settings.max_range:
        return False
    return True

# ✅ CORRECT - Each method has complexity 1 or 2
def validate_multiple_conditions(data, settings):
    checks = [
        validate_not_empty(data),
        validate_size(data, settings.min_size),
        validate_volume(data, settings.min_volume),
        validate_price_range(data, settings.max_price),
        validate_price_spread(data, settings.max_range)
    ]
    return all(checks)

def validate_not_empty(data):
    return data is not None and len(data) > 0

def validate_size(data, min_size):
    return len(data) >= min_size

# ... more single-responsibility functions
```

**Method Size** < 50 lines:
```python
# ❌ WRONG - 200 line method
class Executor:
    def run(self, dataframe):
        # 200 lines of mixed logic
        # Hard to understand
        # Hard to test

# ✅ CORRECT - 40 line method calling helpers
class Executor:
    def run(self, dataframe):
        calculations = self._run_calculations(dataframe)
        validations = self._run_validations(calculations)
        return self._generate_signal(validations)
    
    def _run_calculations(self, dataframe):
        # 10 lines
        pass
    
    def _run_validations(self, calculations):
        # 15 lines
        pass
    
    def _generate_signal(self, validations):
        # 10 lines
        pass
```

---

## 6️⃣ Testing Standards

### Rule: Critical Path 90%+ Coverage

**Test Structure**:
```python
import pytest

class TestYourComponent:
    """Test suite for your component."""
    
    @pytest.fixture
    def sample_data(self):
        """Create test data."""
        return {"open": 100, "close": 105}
    
    def test_normal_case(self, sample_data):
        """Test normal operation."""
        # Arrange
        expected = 1.05
        
        # Act
        result = calculate(sample_data)
        
        # Assert
        assert result == expected
    
    def test_edge_case_zero(self):
        """Test division by zero case."""
        result = calculate({"open": 0, "close": 100})
        assert result == 0  # Or whatever is appropriate
    
    def test_error_case_invalid_input(self):
        """Test with invalid input."""
        with pytest.raises(ValueError):
            calculate(None)
```

**What to Test**:
- ✅ Normal cases (happy path)
- ✅ Edge cases (zero, negative, empty)
- ✅ Error cases (invalid input, None)
- ✅ Boundary conditions
- ✅ Type combinations

**What NOT to Test**:
- ❌ Third-party library behavior
- ❌ Language features (if/else works)
- ❌ Trivial getters/setters

---

## 7️⃣ DRY Principle: Don't Repeat Yourself

### Rule: Extract Common Code to Base Classes

**Problem** - Duplicated code:
```python
# In Analyzer1
def calculate_body_size(candle):
    return abs(candle['close'] - candle['open'])

# In Analyzer2 (DUPLICATE!)
def calculate_body_size(candle):
    return abs(candle['close'] - candle['open'])

# In Analyzer3 (DUPLICATE AGAIN!)
def calculate_body_size(candle):
    return abs(candle['close'] - candle['open'])
```

**Solution** - Extract to base class:
```python
# In base Analyzer
class Analyzer:
    @staticmethod
    def calculate_body_size(candle):
        return abs(candle['close'] - candle['open'])

# In specific analyzers
class Analyzer1(Analyzer):
    pass  # Inherits calculate_body_size

class Analyzer2(Analyzer):
    pass  # Inherits calculate_body_size
```

**Benefits**:
- ✅ Update once, all approaches benefit
- ✅ Consistency guaranteed
- ✅ Easier maintenance
- ✅ Reduced bugs (less code)

---

## 8️⃣ Modularity Standards

### Rule: Single Responsibility Principle

**Each Class Has ONE Reason to Change**:

```python
# ❌ WRONG - Executor does too much
class BadExecutor:
    def run(self, dataframe):
        # Load data
        # Calculate body ratio
        # Validate conditions
        # Generate signal
        # Handle errors
        # Log results
        # Multiple reasons to change!

# ✅ CORRECT - Clear separation
class GoodExecutor:
    def run(self, dataframe):
        calcs = self.analyzer.calculate(dataframe)  # Calculation concern
        valid = self.validator.validate(calcs)      # Validation concern
        signal = self._combine(valid)                # Orchestration only
        return signal                                # Single responsibility
```

**Dependency Injection**:
```python
# ❌ WRONG - Executor creates its dependencies
class BadExecutor:
    def __init__(self):
        self.analyzer = SpecificAnalyzer()  # Tightly coupled
        self.validator = SpecificValidator()

# ✅ CORRECT - Dependencies injected
class GoodExecutor:
    def __init__(self, analyzer, validator):
        self.analyzer = analyzer    # Loosely coupled
        self.validator = validator
```

---

## 9️⃣ Performance Standards

### Rule: Reasonable Time Complexity

**Acceptable Complexity**:
- ✅ O(1) - Constant time (best)
- ✅ O(n) - Linear time (good)
- ✅ O(n log n) - Reasonable
- ❌ O(n²) - Quadratic (avoid unless necessary)

**Example**:
```python
# ❌ WRONG - O(n²) unnecessary
def analyze_candles(dataframe):
    for i, candle in enumerate(dataframe):
        for j, other_candle in enumerate(dataframe):  # O(n²)
            if candle['close'] == other_candle['close']:
                # ...

# ✅ CORRECT - O(n) acceptable
def analyze_candles(dataframe):
    for candle in dataframe:  # O(n)
        color = get_color(candle)
        ratio = get_ratio(candle)
```

---

## 🔟 Error Handling Standards

### Rule: Graceful Failure

**Input Validation**:
```python
# ❌ WRONG - No validation
def analyze(dataframe):
    return dataframe['close'].mean()  # Crashes if missing column

# ✅ CORRECT - Validate first
def analyze(dataframe):
    if 'close' not in dataframe.columns:
        raise ValueError("DataFrame missing 'close' column")
    if dataframe.empty:
        raise ValueError("DataFrame is empty")
    return dataframe['close'].mean()
```

**Meaningful Errors**:
```python
# ❌ WRONG - Cryptic error
result = calculate_ratio(0)  # Returns: `inf` or crashes

# ✅ CORRECT - Meaningful error
def calculate_ratio(denominator):
    if denominator == 0:
        raise ValueError("Denominator cannot be zero")
    return numerator / denominator
```

---

## 1️⃣1️⃣ Code Review Checklist

Before submitting code for review:

### Type Safety
- [ ] No magic strings (all values in enums)
- [ ] All parameters have type hints
- [ ] All returns have type hints
- [ ] Comparison parameter has NO default (required)
- [ ] Using Comparison enum (not string)
- [ ] Using CandleColor enum (not string)
- [ ] Using CandleColumn enum (not string)

### Docstrings
- [ ] Every public method has docstring
- [ ] Docstrings include Args, Returns, Example
- [ ] Examples are accurate and runnable
- [ ] Special cases documented

### Code Quality
- [ ] PEP 8 compliant (run `black` or `flake8`)
- [ ] Methods < 50 lines
- [ ] Cyclomatic complexity < 10
- [ ] Single responsibility principle followed
- [ ] DRY principle applied
- [ ] No duplicate code in inheritance chain

### Testing
- [ ] Unit tests written for methods
- [ ] Edge cases tested
- [ ] Error cases tested
- [ ] Test coverage 90%+

### Performance
- [ ] No O(n²) operations on large data
- [ ] Database queries optimized
- [ ] No unnecessary iterations

### Documentation
- [ ] Docstrings complete
- [ ] Comments explain WHY not WHAT
- [ ] Complex logic explained

---

## 1️⃣2️⃣ Production Readiness Checklist

Before deploying to production:

### Functionality
- [ ] All tests pass (100% pass rate)
- [ ] Integration tests pass
- [ ] Real data tested (VN30F1M, market conditions)
- [ ] Edge cases handled
- [ ] Error paths tested

### Code Quality
- [ ] Code review approved
- [ ] Standards complied with
- [ ] Documentation complete
- [ ] No technical debt introduced

### Performance
- [ ] Response time acceptable
- [ ] Memory usage reasonable
- [ ] No memory leaks detected
- [ ] Load tested if applicable

### Compatibility
- [ ] Backward compatible (no breaking changes)
- [ ] Works with existing code
- [ ] All dependencies available

### Monitoring
- [ ] Logging in place
- [ ] Error handling tested
- [ ] Can diagnose issues in production
- [ ] Performance metrics collected

---

## 📚 Related Documentation

- **ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md** - How inheritance reduces code
- **DESIGN_PATTERNS_GUIDE.md** - When to apply patterns
- **CREATING_NEW_APPROACH.md** - Step-by-step template
- **TESTING_STRATEGY.md** - How to write tests effectively

---

## ✅ Quick Checklist for Every Commit

```
Before committing code:

Type Safety:
  [ ] No magic strings anywhere
  [ ] All parameters typed
  [ ] Using enums (not strings)

Docstrings:
  [ ] Every public method has docstring
  [ ] Examples included

Code Style:
  [ ] PEP 8 compliant
  [ ] < 50 lines per method
  [ ] Single responsibility

Testing:
  [ ] Tests written
  [ ] Tests pass
  [ ] Edge cases covered

Documentation:
  [ ] Complex logic explained
  [ ] No TODO comments left
```

---

**Status**: ✅ Complete quality standards guide  
**Enforcement**: Use as code review checklist  
**Updates**: Add standards as needed  
**Difficulty**: All levels
