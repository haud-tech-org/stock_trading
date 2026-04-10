# EAV Pattern Step-by-Step Implementation Guide

**Status**: ✅ Complete How-To Guide  
**Purpose**: Step-by-step walkthrough for implementing new executors using EAV pattern  
**Audience**: Developers implementing new trading approaches  
**Layer**: Layer 4 - Approach Execution  
**Last Updated**: April 10, 2026

---

## 📋 Overview

This guide provides **hands-on, step-by-step instructions** for implementing a new trading approach using the Executor-Analyzer-Validator (EAV) pattern. Follow these 6 steps to build production-ready code.

---

## 🎯 When to Use This Pattern

Use the EAV pattern when:

✅ Adding any new trading approach  
✅ Refactoring existing approach code  
✅ Need to test individual components  
✅ Want reusable analyzer/validator methods  
✅ Following project architecture standards  

---

## 🚀 Step 1: Decision Tree - What Do I Need?

### Question 1: Can I use all base Analyzer methods?

```python
# Base Analyzer has these 9 methods:
1. calculate_body_ratio(candle)
2. calculate_body_size(candle)
3. get_candle_color(candle)
4. calculate_window_price_range(dataframe)
5. get_max_volume_in_window(dataframe)
6. get_trend_direction(dataframe)
7. get_opposite_color_candles(dataframe, filter_color)
8. calculate_average_volume_in_window(dataframe)
9. get_price_at_position(dataframe, position)
```

**Decision:**
- ✅ **YES**: Derive your Analyzer from base, use all inherited methods
- ❌ **NO, need custom**: Derive from base, inherit what you can + add custom methods

### Question 2: Can I use all base Validator methods?

```python
# Base Validator has these 10 methods:
1. validate_candle_color_consistency(dataframe, target_color)
2. validate_price_threshold(price, threshold, comparison)
3. validate_volume_threshold(volume, threshold, comparison)
4. validate_ratio_threshold(ratio, threshold, comparison)
5. validate_volume_multiplier(current, average, multiplier)
6. validate_required_columns(dataframe, required_columns)
7. validate_minimum_window_size(dataframe, min_size)
8. validate_no_null_values(dataframe, columns)
9. validate_price_range(price, min_price, max_price)
10. validate_data_recency(last_timestamp, max_age_minutes)
```

**Decision:**
- ✅ **YES**: Derive your Validator from base, use all inherited methods
- ❌ **NO, need custom**: Derive from base, inherit what you can + add custom methods

### Question 3: How complex is orchestration?

```
Simple (30-40 lines):
- Load data
- Call analyzer 2-3 times
- Call validator 2-3 times
- Combine with AND logic
- Return signal

Medium (40-60 lines):
- Load and transform data
- Call analyzer 3-5 times
- Call validator 4-6 times
- Some conditional logic
- Multiple signal types

Complex (60-100 lines):
- Complex data preparation
- Multiple phases of analysis
- Complex validation chains
- State management
- Advanced orchestration
```

**Decision**: Affects Executor size but not methodology

---

## 🔧 Step 2: Create Your Analyzer Class

### Step 2a: Minimal Implementation (Reuses All Base Methods)

**Use this approach if**: Your strategy uses only the 9 base analyzer methods

**Location**: `src/stockreports/alert/executors/analyzers/YOUR_APPROACH_analyzer.py`

**Template**:
```python
from src.stockreports.alert.executors.analyzers.base_analyzer import Analyzer

class YourApproachAnalyzer(Analyzer):
    """
    Analyzer for YOUR_APPROACH strategy.
    
    Uses all 9 inherited base methods:
    - calculate_body_ratio
    - calculate_body_size
    - get_candle_color
    - calculate_window_price_range
    - get_max_volume_in_window
    - get_trend_direction
    - get_opposite_color_candles
    - calculate_average_volume_in_window
    - get_price_at_position
    
    No custom methods needed - all logic in inherited methods.
    """
    pass  # That's it!
```

**Example: StrongCandleAnalyzer**
```python
class StrongCandleAnalyzer(Analyzer):
    """
    Analyzer for STRONG_CANDLE strategy.
    Inherits all 9 base methods - no customization needed.
    """
    pass
```

### Step 2b: Extended Implementation (Custom Methods)

**Use this approach if**: Your strategy needs additional calculations

**Location**: `src/stockreports/alert/executors/analyzers/YOUR_APPROACH_analyzer.py`

**Template**:
```python
from typing import Optional
import pandas as pd
from src.stockreports.alert.executors.analyzers.base_analyzer import Analyzer
from src.stockreports.alert.common.constants import CandleColumn

class YourApproachAnalyzer(Analyzer):
    """
    Analyzer for YOUR_APPROACH strategy.
    
    Inherits 9 base methods + adds X custom calculation methods.
    
    Inherited Methods:
    - calculate_body_ratio, calculate_body_size, get_candle_color
    - calculate_window_price_range, get_max_volume_in_window
    - get_trend_direction, get_opposite_color_candles
    - calculate_average_volume_in_window, get_price_at_position
    
    Custom Methods:
    - custom_calculation_1 (for specific strategy logic)
    - custom_calculation_2 (for specific strategy logic)
    """
    
    @staticmethod
    def custom_calculation_1(
        dataframe: pd.DataFrame,
        parameter1: float
    ) -> float:
        """
        Description of what this calculation does.
        
        Args:
            dataframe: OHLCV data with multiple candles
            parameter1: Specific parameter for this calculation
        
        Returns:
            float: Calculated value
            
        Example:
            >>> df = pd.DataFrame(...OHLCV data...)
            >>> result = YourApproachAnalyzer.custom_calculation_1(df, 0.5)
            >>> print(result)
            42.5
        """
        # Your calculation logic here
        pass
    
    @staticmethod
    def custom_calculation_2(
        candle: dict,
        parameter2: int
    ) -> str:
        """
        Description of what this calculation does.
        
        Args:
            candle: Single OHLCV candle as dict
            parameter2: Specific parameter for this calculation
        
        Returns:
            str: Calculated classification
            
        Example:
            >>> candle = {"open": 100, "close": 105, "high": 108, "low": 98}
            >>> result = YourApproachAnalyzer.custom_calculation_2(candle, 10)
            >>> print(result)
            "STRONG"
        """
        # Your calculation logic here
        pass
```

**Example: IchimokuAnalyzer**
```python
class IchimokuAnalyzer(Analyzer):
    """
    Analyzer for ICHIMOKU strategy.
    
    Inherits 9 base methods + adds 5 custom methods for Ichimoku calculations.
    """
    
    @staticmethod
    def calculate_tenkan_sen(dataframe: pd.DataFrame, period: int = 9) -> float:
        """Tenkan-sen: (9-period high + 9-period low) / 2"""
        high9 = dataframe[CandleColumn.HIGH].tail(period).max()
        low9 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high9 + low9) / 2
    
    @staticmethod
    def calculate_kijun_sen(dataframe: pd.DataFrame, period: int = 26) -> float:
        """Kijun-sen: (26-period high + 26-period low) / 2"""
        high26 = dataframe[CandleColumn.HIGH].tail(period).max()
        low26 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high26 + low26) / 2
    
    @staticmethod
    def calculate_senkou_span_a(dataframe: pd.DataFrame) -> float:
        """Senkou Span A: (Tenkan-sen + Kijun-sen) / 2"""
        tenkan = IchimokuAnalyzer.calculate_tenkan_sen(dataframe)
        kijun = IchimokuAnalyzer.calculate_kijun_sen(dataframe)
        return (tenkan + kijun) / 2
    
    @staticmethod
    def calculate_senkou_span_b(
        dataframe: pd.DataFrame,
        period: int = 52
    ) -> float:
        """Senkou Span B: (52-period high + 52-period low) / 2"""
        high52 = dataframe[CandleColumn.HIGH].tail(period).max()
        low52 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high52 + low52) / 2
    
    @staticmethod
    def calculate_chikou_span(dataframe: pd.DataFrame) -> float:
        """Chikou Span: Close plotted 26 periods back"""
        if len(dataframe) >= 26:
            return dataframe.iloc[-26][CandleColumn.CLOSE]
        return dataframe.iloc[0][CandleColumn.CLOSE]
```

### Step 2 Checklist

- [ ] Created file: `src/stockreports/alert/executors/analyzers/YOUR_APPROACH_analyzer.py`
- [ ] Class inherits from `Analyzer` base class
- [ ] Docstring explains what methods are inherited
- [ ] Docstring lists any custom methods
- [ ] All custom methods are `@staticmethod`
- [ ] All custom methods have type hints
- [ ] All custom methods have docstrings with examples
- [ ] No instance state (no self. variables)
- [ ] No calculations in executor (all here in analyzer)

---

## ✓ Step 3: Create Your Validator Class

### Step 3a: Minimal Implementation (Reuses All Base Methods)

**Use this approach if**: Your strategy uses only the 10 base validator methods

**Location**: `src/stockreports/alert/executors/validators/YOUR_APPROACH_validator.py`

**Template**:
```python
from src.stockreports.alert.executors.validators.base_validator import Validator

class YourApproachValidator(Validator):
    """
    Validator for YOUR_APPROACH strategy.
    
    Uses all 10 inherited base methods:
    - validate_candle_color_consistency
    - validate_price_threshold
    - validate_volume_threshold
    - validate_ratio_threshold
    - validate_volume_multiplier
    - validate_required_columns
    - validate_minimum_window_size
    - validate_no_null_values
    - validate_price_range
    - validate_data_recency
    
    No custom methods needed - all logic in inherited methods.
    """
    pass  # That's it!
```

**Example: StrongCandleValidator**
```python
class StrongCandleValidator(Validator):
    """
    Validator for STRONG_CANDLE strategy.
    Inherits all 10 base methods - no customization needed.
    """
    pass
```

### Step 3b: Extended Implementation (Custom Methods)

**Use this approach if**: Your strategy needs additional validation logic

**Location**: `src/stockreports/alert/executors/validators/YOUR_APPROACH_validator.py`

**Template**:
```python
from typing import List, Optional
import pandas as pd
from datetime import datetime
from src.stockreports.alert.executors.validators.base_validator import Validator
from src.stockreports.alert.common.constants import Comparison, CandleColor

class YourApproachValidator(Validator):
    """
    Validator for YOUR_APPROACH strategy.
    
    Inherits 10 base methods + adds X custom validation methods.
    
    Inherited Methods:
    - validate_candle_color_consistency, validate_price_threshold
    - validate_volume_threshold, validate_ratio_threshold
    - validate_volume_multiplier, validate_required_columns
    - validate_minimum_window_size, validate_no_null_values
    - validate_price_range, validate_data_recency
    
    Custom Methods:
    - custom_validation_1 (for specific strategy logic)
    - custom_validation_2 (for specific strategy logic)
    """
    
    @staticmethod
    def custom_validation_1(
        value1: float,
        value2: float,
        threshold: float
    ) -> bool:
        """
        Description of what this validation checks.
        
        Args:
            value1: First value to validate
            value2: Second value to validate
            threshold: Threshold for comparison
        
        Returns:
            bool: True if validation passes, False otherwise
            
        Example:
            >>> result = YourApproachValidator.custom_validation_1(5.0, 3.0, 2.0)
            >>> print(result)
            True
        """
        # Your validation logic here
        return value1 > value2 + threshold
    
    @staticmethod
    def custom_validation_2(
        dataframe: pd.DataFrame,
        condition_parameter: str
    ) -> bool:
        """
        Description of what this validation checks.
        
        Args:
            dataframe: OHLCV data
            condition_parameter: Specific condition to validate
        
        Returns:
            bool: True if validation passes, False otherwise
            
        Example:
            >>> df = pd.DataFrame(...OHLCV data...)
            >>> result = YourApproachValidator.custom_validation_2(df, "bullish")
            >>> print(result)
            True
        """
        # Your validation logic here
        pass
```

**Example: IchimokuValidator**
```python
class IchimokuValidator(Validator):
    """
    Validator for ICHIMOKU strategy.
    
    Inherits 10 base methods + adds 3 custom methods for Ichimoku signals.
    """
    
    @staticmethod
    def validate_ichimoku_signal(
        current_price: float,
        senkou_a: float,
        senkou_b: float
    ) -> bool:
        """Validate Ichimoku signal: price above Senkou Span"""
        upper_band = max(senkou_a, senkou_b)
        return current_price > upper_band
    
    @staticmethod
    def validate_tenkan_kijun_crossover(
        tenkan: float,
        kijun: float,
        is_bullish: bool
    ) -> bool:
        """Validate Tenkan-Kijun crossover"""
        if is_bullish:
            return tenkan > kijun
        else:
            return tenkan < kijun
    
    @staticmethod
    def validate_chikou_signal(
        chikou: float,
        current_price: float,
        is_above: bool
    ) -> bool:
        """Validate Chikou Span signal"""
        if is_above:
            return chikou > current_price
        else:
            return chikou < current_price
```

### Step 3 Checklist

- [ ] Created file: `src/stockreports/alert/executors/validators/YOUR_APPROACH_validator.py`
- [ ] Class inherits from `Validator` base class
- [ ] Docstring explains what methods are inherited
- [ ] Docstring lists any custom methods
- [ ] All custom methods are `@staticmethod`
- [ ] All custom methods have type hints
- [ ] All custom methods return boolean
- [ ] All custom methods have docstrings with examples
- [ ] No instance state (no self. variables)
- [ ] All custom parameters are required (no defaults)
- [ ] All enum parameters used (Comparison, CandleColor)

---

## 🎯 Step 4: Create Your Executor Class

**Location**: `src/stockreports/alert/executors/YOUR_APPROACH_executor.py`

### Structure Template

```python
from typing import Optional
import pandas as pd
from src.stockreports.alert.common.constants import Signal
from src.stockreports.alert.executors.analyzers.YOUR_APPROACH_analyzer import (
    YourApproachAnalyzer
)
from src.stockreports.alert.executors.validators.YOUR_APPROACH_validator import (
    YourApproachValidator
)

class YourApproachExecutor:
    """
    Executor for YOUR_APPROACH strategy.
    
    Orchestrates analyzer and validator to produce trading signals.
    
    Architecture:
    - Executor (orchestration): 40 lines
    - Analyzer (calculations): X lines
    - Validator (verification): Y lines
    """
    
    def __init__(self, settings: dict):
        """
        Initialize executor with settings.
        
        Args:
            settings: Configuration dictionary with parameters
                Example: {
                    "parameter1": 0.5,
                    "parameter2": 20,
                    "parameter3": "bullish"
                }
        """
        self.settings = settings
        self.analyzer = YourApproachAnalyzer()
        self.validator = YourApproachValidator()
    
    def run(self, dataframe: pd.DataFrame) -> Signal:
        """
        Execute YOUR_APPROACH strategy on provided data.
        
        Workflow:
        1. Extract latest candle
        2. Call analyzer for calculations
        3. Call validator for checks
        4. Combine results into signal
        5. Return trading signal
        
        Args:
            dataframe: OHLCV data with multiple candles (minimum 50 rows)
        
        Returns:
            Signal.BUY, Signal.SELL, or Signal.NEUTRAL
            
        Raises:
            ValueError: If data doesn't meet minimum requirements
        """
        try:
            # Step 1: Validate data
            if len(dataframe) < 50:
                raise ValueError("Minimum 50 candles required")
            
            # Step 2: Extract latest candle
            latest = dataframe.iloc[-1]
            
            # Step 3: Call analyzer for calculations
            calculation1 = self.analyzer.calculate_body_ratio(latest)
            calculation2 = self.analyzer.get_candle_color(latest)
            calculation3 = self.analyzer.calculate_max_volume_in_window(dataframe)
            
            # Step 4: Call validator for checks
            check1 = self.validator.validate_candle_color_consistency(
                dataframe, calculation2
            )
            check2 = self.validator.validate_ratio_threshold(
                calculation1,
                self.settings.get("min_ratio", 0.5)
            )
            check3 = self.validator.validate_volume_multiplier(
                latest['volume'],
                calculation3,
                self.settings.get("volume_multiplier", 1.5)
            )
            
            # Step 5: Combine results
            if check1 and check2 and check3:
                return Signal.SELL
            
            return Signal.NEUTRAL
            
        except Exception as e:
            # Log error and return neutral
            print(f"Error in YourApproachExecutor: {str(e)}")
            return Signal.NEUTRAL
```

### Key Implementation Points

**1. Clear Orchestration**
```python
# Good: Clear flow
calculation1 = self.analyzer.calc1(data)
calculation2 = self.analyzer.calc2(data)
check1 = self.validator.validate1(calculation1, threshold)
return Signal.SELL if check1 else Signal.NEUTRAL
```

**2. No Inline Calculations**
```python
# Bad: Calculation in executor
ratio = abs(latest['close'] - latest['open']) / (latest['high'] - latest['low'])

# Good: Call analyzer
ratio = self.analyzer.calculate_body_ratio(latest)
```

**3. Use Settings, Not Hardcoding**
```python
# Bad: Hardcoded values
if ratio > 0.5:  # Magic number!

# Good: From settings
if ratio > self.settings.get("min_ratio", 0.5):
```

**4. Required Enum Parameters**
```python
# Bad: String parameters
self.validator.validate_threshold(100, 90, "greater")

# Good: Enum parameters
from src.stockreports.alert.common.constants import Comparison
self.validator.validate_threshold(100, 90, Comparison.GREATER)
```

### Step 4 Checklist

- [ ] Created file: `src/stockreports/alert/executors/YOUR_APPROACH_executor.py`
- [ ] Class named `YourApproachExecutor`
- [ ] `__init__` method initializes analyzer and validator
- [ ] `run` method accepts `dataframe: pd.DataFrame`
- [ ] `run` method returns `Signal` enum value
- [ ] No calculations in run method (delegated to analyzer)
- [ ] No validation logic in run method (delegated to validator)
- [ ] Uses settings, not hardcoded values
- [ ] 30-60 lines total
- [ ] Error handling included
- [ ] Type hints on all parameters and returns
- [ ] Comprehensive docstrings

---

## 🧪 Step 5: Create Unit Tests

### Analyzer Tests

**File**: `tests/alert/executors/analyzers/test_YOUR_APPROACH_analyzer.py`

```python
import unittest
import pandas as pd
from src.stockreports.alert.executors.analyzers.YOUR_APPROACH_analyzer import (
    YourApproachAnalyzer
)
from src.stockreports.alert.common.constants import CandleColor

class TestYourApproachAnalyzer(unittest.TestCase):
    """Test YourApproachAnalyzer calculations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.analyzer = YourApproachAnalyzer()
        self.sample_candle = {
            'open': 100,
            'close': 105,
            'high': 108,
            'low': 98
        }
        self.sample_dataframe = pd.DataFrame({
            'open': [100, 101, 102],
            'close': [105, 104, 103],
            'high': [108, 109, 110],
            'low': [98, 99, 100]
        })
    
    def test_calculate_body_ratio_positive(self):
        """Test body_ratio calculation with normal candle."""
        result = self.analyzer.calculate_body_ratio(self.sample_candle)
        expected = 5 / 10  # (105-100)/(108-98)
        self.assertAlmostEqual(result, expected, places=2)
    
    def test_get_candle_color_green(self):
        """Test candle color when close > open."""
        result = self.analyzer.get_candle_color(self.sample_candle)
        self.assertEqual(result, CandleColor.GREEN)
    
    def test_get_candle_color_red(self):
        """Test candle color when close < open."""
        red_candle = {
            'open': 105,
            'close': 100,
            'high': 108,
            'low': 98
        }
        result = self.analyzer.get_candle_color(red_candle)
        self.assertEqual(result, CandleColor.RED)

if __name__ == '__main__':
    unittest.main()
```

### Validator Tests

**File**: `tests/alert/executors/validators/test_YOUR_APPROACH_validator.py`

```python
import unittest
from src.stockreports.alert.executors.validators.YOUR_APPROACH_validator import (
    YourApproachValidator
)
from src.stockreports.alert.common.constants import Comparison, CandleColor

class TestYourApproachValidator(unittest.TestCase):
    """Test YourApproachValidator checks."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.validator = YourApproachValidator()
    
    def test_validate_price_threshold_greater(self):
        """Test price validation with GREATER comparison."""
        result = self.validator.validate_price_threshold(
            100.5, 100.0, Comparison.GREATER
        )
        self.assertTrue(result)
    
    def test_validate_price_threshold_less(self):
        """Test price validation with LESS comparison."""
        result = self.validator.validate_price_threshold(
            99.5, 100.0, Comparison.LESS
        )
        self.assertTrue(result)
    
    def test_validate_volume_multiplier_pass(self):
        """Test volume multiplier validation when condition met."""
        result = self.validator.validate_volume_multiplier(
            current_volume=2000000,
            average_volume=1000000,
            multiplier=1.5
        )
        self.assertTrue(result)
    
    def test_validate_volume_multiplier_fail(self):
        """Test volume multiplier validation when condition not met."""
        result = self.validator.validate_volume_multiplier(
            current_volume=1200000,
            average_volume=1000000,
            multiplier=1.5
        )
        self.assertFalse(result)

if __name__ == '__main__':
    unittest.main()
```

### Executor Tests

**File**: `tests/alert/executors/test_YOUR_APPROACH_executor.py`

```python
import unittest
from unittest.mock import Mock, patch
import pandas as pd
from src.stockreports.alert.executors.YOUR_APPROACH_executor import (
    YourApproachExecutor
)
from src.stockreports.alert.common.constants import Signal, CandleColor

class TestYourApproachExecutor(unittest.TestCase):
    """Test YourApproachExecutor orchestration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.settings = {
            "min_ratio": 0.5,
            "volume_multiplier": 1.5
        }
        self.executor = YourApproachExecutor(self.settings)
        
        # Sample dataframe with 50+ rows (minimum required)
        self.valid_dataframe = pd.DataFrame({
            'open': [100] * 50,
            'close': [105] * 50,
            'high': [108] * 50,
            'low': [98] * 50,
            'volume': [1000000] * 50
        })
    
    def test_run_returns_signal(self):
        """Test that run method returns a Signal."""
        result = self.executor.run(self.valid_dataframe)
        self.assertIn(result, [Signal.BUY, Signal.SELL, Signal.NEUTRAL])
    
    def test_run_requires_minimum_data(self):
        """Test that run returns NEUTRAL for insufficient data."""
        small_df = self.valid_dataframe.head(10)  # Only 10 rows
        result = self.executor.run(small_df)
        self.assertEqual(result, Signal.NEUTRAL)
    
    def test_analyzer_called(self):
        """Test that analyzer is called in run method."""
        with patch.object(self.executor.analyzer, 'calculate_body_ratio',
                         return_value=0.6):
            self.executor.run(self.valid_dataframe)
            self.executor.analyzer.calculate_body_ratio.assert_called()
    
    def test_validator_called(self):
        """Test that validator is called in run method."""
        with patch.object(self.executor.validator, 'validate_ratio_threshold',
                         return_value=True):
            self.executor.run(self.valid_dataframe)
            self.executor.validator.validate_ratio_threshold.assert_called()

if __name__ == '__main__':
    unittest.main()
```

### Step 5 Checklist

- [ ] Created test file for Analyzer
- [ ] Created test file for Validator
- [ ] Created test file for Executor
- [ ] All analyzer methods have at least 2 tests (pass/fail)
- [ ] All validator methods have at least 2 tests (pass/fail)
- [ ] Executor tested with mocks for isolation
- [ ] Integration tests on real data included
- [ ] Tests run successfully: `pytest tests/alert/executors/`
- [ ] Test coverage > 90%

---

## 🔗 Step 6: Integration & Registration

### Register Your Executor

**File**: `src/stockreports/alert/executors/executor_registry.py`

```python
from src.stockreports.alert.executors.YOUR_APPROACH_executor import (
    YourApproachExecutor
)

# Add to executor registry
EXECUTOR_REGISTRY = {
    "STRONG_CANDLE": StrongCandleExecutor,
    "ICHIMOKU": IchimokuExecutor,
    "YOUR_APPROACH": YourApproachExecutor,  # Add here
    # ... other executors
}
```

### Run Integration Tests

```bash
# Test your specific executor
pytest tests/alert/executors/test_YOUR_APPROACH_executor.py -v

# Run all executor tests
pytest tests/alert/executors/ -v

# Run with coverage
pytest tests/alert/executors/ --cov=src.stockreports.alert.executors --cov-report=html
```

### Step 6 Checklist

- [ ] Registered executor in executor registry
- [ ] Import statement works correctly
- [ ] Integration tests pass
- [ ] Test coverage > 90%
- [ ] No import errors
- [ ] Can instantiate executor: `executor = YourApproachExecutor(settings)`
- [ ] Can run executor: `signal = executor.run(dataframe)`
- [ ] Real data tests pass

---

## 📋 Final Verification Checklist

### Code Structure
- [ ] Analyzer: 20-80 lines, inherits Analyzer base class
- [ ] Validator: 25-100 lines, inherits Validator base class
- [ ] Executor: 30-60 lines, orchestrates analyzer/validator
- [ ] Total: 75-240 lines (clean and maintainable)

### Type Safety
- [ ] No magic strings (use enums)
- [ ] All parameters have type hints
- [ ] All return types specified
- [ ] CandleColumn used for column references
- [ ] CandleColor used for candle colors
- [ ] Comparison used for comparison operators

### Code Quality
- [ ] All classes have docstrings
- [ ] All methods have docstrings
- [ ] All methods documented with examples
- [ ] No hardcoded values (use settings)
- [ ] Error handling included
- [ ] No calculations in Executor
- [ ] No validation in Analyzer
- [ ] Pure functions (no side effects)

### Testing
- [ ] Unit tests for Analyzer methods
- [ ] Unit tests for Validator methods
- [ ] Integration tests for Executor
- [ ] Edge case tests included
- [ ] All tests pass
- [ ] Test coverage > 90%

### Documentation
- [ ] File locations documented
- [ ] Settings parameters documented
- [ ] Configuration examples provided
- [ ] Usage examples provided
- [ ] Related documentation linked

---

## 🎓 Quick Reference: File Template

### Analyzer File Template
```python
# src/stockreports/alert/executors/analyzers/YOUR_APPROACH_analyzer.py

from src.stockreports.alert.executors.analyzers.base_analyzer import Analyzer

class YourApproachAnalyzer(Analyzer):
    """Analyzer for YOUR_APPROACH strategy."""
    pass  # Inherit all 9 base methods
```

### Validator File Template
```python
# src/stockreports/alert/executors/validators/YOUR_APPROACH_validator.py

from src.stockreports.alert.executors.validators.base_validator import Validator

class YourApproachValidator(Validator):
    """Validator for YOUR_APPROACH strategy."""
    pass  # Inherit all 10 base methods
```

### Executor File Template
```python
# src/stockreports/alert/executors/YOUR_APPROACH_executor.py

import pandas as pd
from src.stockreports.alert.common.constants import Signal
from src.stockreports.alert.executors.analyzers.YOUR_APPROACH_analyzer import YourApproachAnalyzer
from src.stockreports.alert.executors.validators.YOUR_APPROACH_validator import YourApproachValidator

class YourApproachExecutor:
    def __init__(self, settings: dict):
        self.settings = settings
        self.analyzer = YourApproachAnalyzer()
        self.validator = YourApproachValidator()
    
    def run(self, dataframe: pd.DataFrame) -> Signal:
        # Your orchestration logic
        pass
```

---

## 📚 Related Documentation

- **EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md** - Technical deep dive
- **DESIGN_PATTERNS_GUIDE.md** (root) - Pattern overview
- **CODE_QUALITY_STANDARDS.md** - Code quality requirements
- **ABSTRACT_BASE_CLASSES_ARCHITECTURE.md** - All 19 base methods
- **EXECUTOR_PATTERN_OVERVIEW.md** - Pattern diagrams

---

## ✅ Success Criteria

After completing all 6 steps:

✅ 3 new files created (Executor, Analyzer, Validator)  
✅ 3 test files created (one for each class)  
✅ All tests pass with >90% coverage  
✅ Executor registered in executor registry  
✅ Total code: 75-240 lines (clean and modular)  
✅ No hardcoded values (all from settings)  
✅ Type-safe (all enums used correctly)  
✅ Well-documented (docstrings throughout)  
✅ Ready for production  

---

**Status**: ✅ Complete implementation guide  
**Recommended Time**: 2-3 hours for complete implementation  
**Difficulty Level**: Intermediate developers  
**Next**: Deploy to production and monitor performance

