# Implementation Best Practices & Field Reference

## 🎯 Quick Reference for Common Development Tasks

This document provides quick answers and practical examples for common development tasks using the established architectural patterns.

---

## 1. IMPLEMENTING A NEW TRADING APPROACH

### Quick Checklist

```
☐ Step 1: Understand the Algorithm
  └─ Read approach documentation or research source
  
☐ Step 2: Design Class Structure
  ├─ Create Executor (orchestration)
  ├─ Create Analyzer (calculations)
  └─ Create Validator (validation)

☐ Step 3: Implement Analyzer
  ├─ Inherit from base Analyzer (9 methods available)
  ├─ Create approach-specific calculation methods
  ├─ Use static methods only (no instance state)
  └─ Write docstrings with examples

☐ Step 4: Implement Validator
  ├─ Inherit from base Validator (10 methods available)
  ├─ Create validation methods for each validation step
  ├─ Use Comparison enum for clarity
  ├─ Use CandleColor enum for colors
  └─ Return bool or Optional values

☐ Step 5: Implement Executor
  ├─ Initialize analyzer and validator
  ├─ Implement main run() method
  ├─ Orchestrate analyzer/validator calls
  ├─ Handle logging and tracking
  └─ Return final Signal or None

☐ Step 6: Create Configuration
  ├─ Define approach-specific settings
  ├─ Document all parameters
  ├─ Provide reasonable defaults
  └─ Add to signal_settings.py

☐ Step 7: Write Tests
  ├─ Unit tests for analyzer methods
  ├─ Unit tests for validator methods
  ├─ Integration tests for executor
  ├─ Edge case testing
  └─ Real data testing

☐ Step 8: Documentation
  ├─ Create /algorithms/APPROACH_NAME.md
  ├─ Document all parameters
  ├─ Provide configuration examples
  ├─ Include real alert examples
  └─ Add to comparison documents

☐ Step 9: Code Review
  ├─ Verify pure functions
  ├─ Check type safety
  ├─ Validate code organization
  ├─ Test thoroughly
  └─ Get team approval

☐ Step 10: Deployment
  ├─ Merge to main branch
  ├─ Enable in settings
  ├─ Monitor in production
  └─ Gather metrics
```

### Time Estimate: 2-4 weeks (depending on complexity)

---

## 3. USING THE EAV PATTERN CORRECTLY

### Anti-patterns to AVOID

```
❌ DON'T: Put calculations in Executor
    executor.run():
        body_ratio = (close - open) / (high - low)  # WRONG!

✅ DO: Put calculations in Analyzer
    analyzer.calculate_body_ratio(candle)  # RIGHT!

❌ DON'T: Put business logic in Analyzer
    analyzer.validate_ratio():
        if ratio > 0.5:  # Business logic - WRONG!
            return True

✅ DO: Put validation in Validator
    validator.validate_ratio_threshold(ratio, threshold)  # RIGHT!

❌ DON'T: Use string parameters
    validator.validate("greater", 100.5, 100.0)  # Ambiguous

✅ DO: Use enum parameters
    validator.validate(Comparison.GREATER, 100.5, 100.0)  # Clear

❌ DON'T: Have mutable state in validators
    class BadValidator:
        count = 0
        def validate(self):
            self.count += 1  # State mutation - WRONG!

✅ DO: Use pure functions
    class GoodValidator:
        @staticmethod
        def validate(df):
            return len(df) > 0  # Pure function - RIGHT!
```

### Core Principles

```
EXECUTOR:
  Purpose: Orchestrate analyzer and validator
  Size: 30-50 lines typically
  State: Holds settings only
  Methods: run(), _find_alerts(), logging
  Returns: Signal or Alert

ANALYZER:
  Purpose: Pure calculations
  Size: 50-150 lines
  State: None (static methods)
  Methods: calculate_*, get_*
  Returns: float, int, DataFrame, CandleColor

VALIDATOR:
  Purpose: Pure validations
  Size: 50-150 lines
  State: None (static methods)
  Methods: validate_*
  Returns: bool or Optional value
```

---

## 4. ADDING NEW VALIDATION STEP

### Scenario: Add new validation to existing approach

**Example: Add "RSI validation" to STRONG_CANDLE**

```python
# Step 1: Add to Validator
class StrongCandleValidator(Validator):
    @staticmethod
    def validate_rsi_extreme(lookback_window_df: pd.DataFrame, min_rsi: float, max_rsi: float) -> bool:
        """
        Validate RSI is in extreme range (overbought/oversold).
        
        Args:
            lookback_window_df: Window data to calculate RSI
            min_rsi: Minimum RSI threshold (for SELL, should be >70)
            max_rsi: Maximum RSI threshold (for BUY, should be <30)
            
        Returns:
            bool: True if RSI in expected range
        """
        # Calculate RSI from window
        rsi = calculate_rsi(lookback_window_df, period=14)
        
        # Check if in range
        if rsi >= min_rsi or rsi <= max_rsi:
            return True
        return False

# Step 2: Add to Executor
class StrongCandleExecutor:
    def run(self, dataframe):
        # ... existing validations ...
        
        # Add new validation
        rsi_valid = self.validator.validate_rsi_extreme(
            lookback_window,
            self.settings.rsi_sell_threshold,
            self.settings.rsi_buy_threshold
        )
        
        # Track it
        self.validations.append(Validation(
            name='rsi_extreme',
            passed=rsi_valid,
            value=rsi
        ))
        
        # Add to checks list
        checks.append(rsi_valid)

# Step 3: Add Configuration
class StrongCandleSettings:
    RSI_SELL_THRESHOLD = 70.0  # Overbought
    RSI_BUY_THRESHOLD = 30.0   # Oversold

# Step 4: Update Tests
def test_validate_rsi_extreme():
    validator = StrongCandleValidator()
    
    # Test overbought (SELL signal)
    assert validator.validate_rsi_extreme(df_overbought, 70, 30) == True
    
    # Test oversold (BUY signal)
    assert validator.validate_rsi_extreme(df_oversold, 70, 30) == True
    
    # Test neutral
    assert validator.validate_rsi_extreme(df_neutral, 70, 30) == False
```

---

## 5. USING TYPE-SAFE ENUMS

### CandleColor Enum

```python
from src.stockreports.alert.common.constants import CandleColor

# ✅ RIGHT: Use enum
candle_color = CandleColor.GREEN
if candle_color == CandleColor.GREEN:
    print("Bullish candle")

# ❌ WRONG: Use string
candle_color = "green"  # No IDE support, error-prone
if candle_color == "Green":  # Case sensitivity issues
    print("Bullish candle")
```

### Comparison Enum

```python
from src.stockreports.alert.common.constants import Comparison

# ✅ RIGHT: Use enum with explicit comparison
validator.validate_price_threshold(100.5, 100.0, Comparison.GREATER)

# ❌ WRONG: Use string or default
validator.validate_price_threshold(100.5, 100.0, "greater")  # Ambiguous
validator.validate_price_threshold(100.5, 100.0)  # Silent default
```

### CandleColumn Enum

```python
from src.stockreports.alert.common.constants import CandleColumn

# ✅ RIGHT: Use enum
high = candle[CandleColumn.HIGH]
low = candle[CandleColumn.LOW]
close = candle[CandleColumn.CLOSE]

# ❌ WRONG: Use string
high = candle['high']  # Case sensitive, typo-prone
low = candle['LOW']    # Inconsistent casing
close = candle['Close']  # Wrong case
```

---

## 6. WRITING PURE FUNCTIONS

### Requirements for Pure Functions

```
✅ PURE FUNCTION CHECKLIST:

1. No Side Effects
   ☐ Doesn't modify input parameters
   ☐ Doesn't modify instance state (self)
   ☐ Doesn't read from global state
   ☐ Doesn't perform I/O operations

2. Deterministic
   ☐ Same input always produces same output
   ☐ No random number generation
   ☐ No time-dependent logic
   ☐ No external service calls

3. Testable
   ☐ Can be called independently
   ☐ No complex setup needed
   ☐ Clear input/output contract
   ☐ Edge cases easily defined

4. Reusable
   ☐ No dependencies on execution order
   ☐ No implicit assumptions
   ☐ Clear parameter requirements
   ☐ Documented behavior
```

### Examples

```python
# ❌ IMPURE: Depends on instance state, has side effects
def validate_price(self, price):
    self.last_price = price  # Side effect
    return price > self.threshold  # Depends on self.threshold

# ✅ PURE: Deterministic, no state mutation
@staticmethod
def validate_price_threshold(price: float, threshold: float, comparison: Comparison) -> bool:
    if comparison == Comparison.GREATER:
        return price > threshold
    return False

# ❌ IMPURE: Side effect (logging)
def calculate_volume(df):
    result = df['volume'].max()
    print(f"Max volume: {result}")  # Side effect
    return result

# ✅ PURE: No side effects, logging handled separately
@staticmethod
def calculate_max_volume(df: pd.DataFrame) -> float:
    return df['volume'].max()
    # Logging happens in executor, not here
```

---

## 7. TESTING STRATEGY

### Unit Test Levels

```
Level 1: Analyzer Methods (Pure Calculation Tests)
├─ Test each static method
├─ Use simple test data
├─ Verify mathematical correctness
├─ Test edge cases
└─ 20-30 tests per analyzer

Level 2: Validator Methods (Pure Validation Tests)
├─ Test each static method
├─ Test all condition paths
├─ Test boundary conditions
├─ Test edge cases
└─ 30-40 tests per validator

Level 3: Executor Integration Tests
├─ Test with mock analyzer/validator
├─ Test execution flow
├─ Test alert generation
├─ Test logging
└─ 10-15 integration tests

Level 4: End-to-End Tests
├─ Real data sets
├─ Full flow testing
├─ Known signal verification
├─ Performance validation
└─ 5-10 E2E tests per approach
```

### Test Code Template

```python
import pytest
from src.stockreports.alert.approach.STRONG_CANDLE.analyzer import StrongCandleAnalyzer
from src.stockreports.alert.approach.STRONG_CANDLE.validator import StrongCandleValidator

class TestStrongCandleAnalyzer:
    """Unit tests for analyzer pure functions"""
    
    def test_calculate_body_ratio_green_candle(self):
        """Test body ratio calculation for green candle"""
        candle = pd.Series({
            'open': 100.0,
            'close': 102.0,
            'high': 105.0,
            'low': 99.0
        })
        
        ratio = StrongCandleAnalyzer.calculate_body_ratio(candle)
        
        # Body = 102 - 100 = 2
        # Range = 105 - 99 = 6
        # Ratio = 2/6 = 0.333
        assert abs(ratio - 0.333) < 0.01
    
    def test_calculate_body_ratio_doji_candle(self):
        """Test body ratio for doji (open == close)"""
        candle = pd.Series({
            'open': 100.0,
            'close': 100.0,
            'high': 105.0,
            'low': 95.0
        })
        
        ratio = StrongCandleAnalyzer.calculate_body_ratio(candle)
        
        # Body = 0, Ratio = 0
        assert ratio == 0.0

class TestStrongCandleValidator:
    """Unit tests for validator pure functions"""
    
    def test_validate_alert_candle_body_passes(self):
        """Test body validation passes for strong candle"""
        strong_candle = pd.Series({
            'open': 100.0,
            'close': 105.0,
            'high': 107.0,
            'low': 99.0,
            'volume': 1000000
        })
        
        body_size = StrongCandleValidator.validate_alert_candle_body(
            strong_candle,
            min_body_ratio=0.5,
            min_body_size=2.0
        )
        
        assert body_size is not None
        assert body_size >= 2.0
    
    def test_validate_alert_candle_body_fails_weak_ratio(self):
        """Test body validation fails for weak ratio"""
        weak_candle = pd.Series({
            'open': 100.0,
            'close': 100.5,  # Very small body
            'high': 105.0,
            'low': 95.0,
            'volume': 1000000
        })
        
        body_size = StrongCandleValidator.validate_alert_candle_body(
            weak_candle,
            min_body_ratio=0.5,
            min_body_size=2.0
        )
        
        assert body_size is None  # Validation fails
```

---

## 8. LOGGING & DEBUGGING

### Standard Logging Pattern

```python
from src.stockreports.utils.logging_utils import log
from src.stockreports.alert.common.constants import ValidationStatus

# In executor
def _step_validate_alert_candle_body(self):
    self.next_validation()
    
    body_size = self.validator.validate_alert_candle_body(...)
    
    if body_size is None:
        # Log failure
        log(
            logger=self.logger,
            status=ValidationStatus.FAILED,
            symbol=self.symbol,
            message=f"Body size {actual} < {required}"
        )
        return False
    
    # Log success
    log(
        logger=self.logger,
        status=ValidationStatus.PASSED,
        symbol=self.symbol,
        message=f"Body size {body_size} >= {min_required}"
    )
    
    # Track validation
    self.validations.append(Validation(
        name='body_size_validation',
        status=ValidationStatus.PASSED,
        value=body_size
    ))
    
    return True
```

### Debug Output Structure

```python
# Enable debug mode for detailed output
executor = StrongCandleExecutor('VN30F1M', debug=True)

# Output includes:
# ├─ Validation 1: Check body ratio → PASS
# ├─ Validation 2: Check body size → PASS
# ├─ Validation 3: Check window color → PASS
# ├─ Validation 4: Check window trend → PASS
# └─ Signal: SELL generated
```

---

## 9. CONFIGURATION MANAGEMENT

### Pattern: Settings Class

```python
from pydantic import BaseModel

class StrongCandleSettings(BaseModel):
    """
    Configuration for STRONG_CANDLE approach
    
    All parameters with defaults are optional.
    Parameters must be explicitly provided.
    """
    
    # Lookback window
    LOOKBACK_WINDOW: int = 10
    
    # Body validations
    MIN_BODY_RATIO: float = 0.5
    MIN_BODY_SIZE: float = 2.5
    
    # Volume validation
    MAX_VOLUME_MULTIPLIER: float = 1.3
    
    # Window validations
    MIN_WINDOW_SIZE_THRESHOLD: float = 1.0
    MAX_WINDOW_SIZE_THRESHOLD: float = 4.0
    MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE: float = 0.5
    
    # Alert settings
    MAGNITUDE_THRESHOLD: float = 2.0
    COOLDOWN_WINDOW: int = 3
    
    class Config:
        frozen = True  # Immutable after creation
```

### Usage

```python
# Load settings
settings = StrongCandleSettings()

# Access settings
window_size = settings.LOOKBACK_WINDOW
min_ratio = settings.MIN_BODY_RATIO

# Create executor with settings
executor = StrongCandleExecutor('VN30F1M', settings=settings)

# Override for testing
custom_settings = StrongCandleSettings(
    MIN_BODY_RATIO=0.3,  # More sensitive
    LOOKBACK_WINDOW=5     # Smaller window
)
```

---

## 10. PERFORMANCE OPTIMIZATION

### Optimization Checklist

```
☐ Profile code to identify bottlenecks
☐ Avoid unnecessary DataFrame operations
☐ Cache calculations when possible
☐ Use pandas built-ins (min, max) not loops
☐ Avoid string operations in loops
☐ Pre-compute expensive operations
☐ Use numpy where appropriate
☐ Test performance regression
```

### Example: Inefficient vs Efficient

```python
# ❌ INEFFICIENT: Loop for max
def get_max_volume_slow(df):
    max_vol = 0
    for _, row in df.iterrows():
        if row['volume'] > max_vol:
            max_vol = row['volume']
    return max_vol

# ✅ EFFICIENT: Use pandas built-in
@staticmethod
def get_max_volume_in_window(df: pd.DataFrame) -> float:
    return df[CandleColumn.VOLUME].max()

# ❌ INEFFICIENT: Multiple DataFrame operations
def validate_multiple(df, threshold1, threshold2):
    df_filtered = df[df['close'] > threshold1]
    df_filtered2 = df_filtered[df_filtered['volume'] > threshold2]
    return len(df_filtered2) > 0

# ✅ EFFICIENT: Single operation with boolean mask
def validate_multiple_fast(df, threshold1, threshold2):
    mask = (df['close'] > threshold1) & (df['volume'] > threshold2)
    return mask.any()
```

---

## 11. TROUBLESHOOTING COMMON ISSUES

### Issue: "ImportError: Cannot import module"

```python
# ❌ WRONG: Relative import
from analyzer import StrongCandleAnalyzer

# ✅ RIGHT: Absolute import from workspace root
from src.stockreports.alert.approach.STRONG_CANDLE.analyzer import StrongCandleAnalyzer
```

### Issue: "Attribute 'NoneType' has no attribute 'validate'"

```python
# Cause: Analyzer/Validator not instantiated

# ❌ WRONG: Not initialized
class StrongCandleExecutor:
    def run(self):
        self.analyzer.validate(...)  # self.analyzer is None!

# ✅ RIGHT: Initialize in __init__
class StrongCandleExecutor:
    def __init__(self, symbol, settings):
        self.analyzer = StrongCandleAnalyzer()
        self.validator = StrongCandleValidator()
        
    def run(self):
        self.analyzer.validate(...)  # Works!
```

### Issue: "Test passes locally but fails in CI"

```python
# Cause: Timing or randomness

# ❌ WRONG: Time-dependent test
def test_signal():
    signal = executor.run(data)
    assert signal == executor.get_latest_signal()  # Timing dependent!

# ✅ RIGHT: Deterministic test
def test_signal():
    signal = executor.run(test_data)
    assert signal == Signal.SELL  # Fixed expectation
```

### Issue: "Validator returns None unexpectedly"

```python
# Cause: Validation failed without clear reason

# ❌ POOR: Unclear return value
def validate_something(data):
    if condition1:
        return None
    if condition2:
        return None
    if condition3:
        return None
    return True  # Which path succeeded?

# ✅ BETTER: Add logging or debug info
@staticmethod
def validate_something(data, logger=None):
    if condition1:
        if logger:
            logger.debug("Condition 1 failed")
        return False
    if condition2:
        if logger:
            logger.debug("Condition 2 failed")
        return False
    if condition3:
        if logger:
            logger.debug("Condition 3 failed")
        return False
    return True
```

---

## 12. CODE REVIEW CHECKLIST

Use when reviewing code for new approach or refactoring:

```
Architecture:
☐ Clear separation: Executor/Analyzer/Validator
☐ No mixed concerns
☐ Appropriate file organization
☐ Proper inheritance from base classes

Code Quality:
☐ Type hints on all parameters
☐ Docstrings with examples
☐ No magic numbers or strings
☐ Proper error handling

Type Safety:
☐ Uses CandleColor enum
☐ Uses Comparison enum
☐ Uses CandleColumn enum
☐ No string-based configuration

Pure Functions:
☐ All static methods in Analyzer
☐ All static methods in Validator
☐ No state mutations
☐ Deterministic behavior

Testing:
☐ Unit tests for analyzers (30+ tests)
☐ Unit tests for validators (40+ tests)
☐ Integration tests for executor (10+ tests)
☐ 90%+ code coverage
☐ Edge cases tested

Documentation:
☐ Docstrings complete
☐ Parameter descriptions clear
☐ Return values documented
☐ Algorithm documentation created
☐ Added to comparison documents

Performance:
☐ No unnecessary loops
☐ Efficient pandas operations
☐ Caching where needed
☐ No performance regression

Backward Compatibility:
☐ External API unchanged
☐ Configuration compatible
☐ No breaking changes
☐ All existing tests pass
```

---

**Version**: 1.0  
**Last Updated**: March 12, 2026  
**Status**: ✅ Ready for Production Use
