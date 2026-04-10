# Analyzer & Validator Implementation - Quick Reference

**Location**: `/docs/ARCHITECTURE/IMPLEMENTATION_GUIDES/`  
**Tier**: Tier 3 - Implementation Guides (Practice-focused)  
**Purpose**: Quick reference for using & extending Analyzer/Validator base classes  
**Audience**: Feature developers, approach creators  
**Prerequisite**: Understanding from ABSTRACT_BASE_CLASSES_ARCHITECTURE.md (Tier 2)

---

## 📋 Quick Overview

Two helper abstract base classes are available for building trading approaches:

### Analyzer (ABC)
- **Purpose**: Common calculation methods
- **Contains**: 9 static, pure calculation methods
- **Pattern**: @staticmethod (no instance state)
- **Use**: Inherit and extend with approach-specific calculations

### Validator (ABC)
- **Purpose**: Common validation methods
- **Contains**: 10 static, pure validation methods
- **Pattern**: @staticmethod (no instance state)
- **Use**: Inherit and extend with approach-specific validations

---

## 🎯 When to Create These Classes

### Create an Analyzer When You Need

- [ ] Repeated calculation patterns in your executor
- [ ] Price/volume analysis specific to your approach
- [ ] Window-based calculations
- [ ] Technical indicator computations
- [ ] Trend or pattern analysis

### Create a Validator When You Need

- [ ] Repeated validation checks in your executor
- [ ] Threshold-based validations
- [ ] Pattern matching conditions
- [ ] Business rule enforcement
- [ ] Conditional checks (comparisons, ranges, etc.)

### DON'T Create When

- ❌ You only have 1 or 2 calculations
- ❌ The code is specific to just 1 executor
- ❌ It's only used once in `_find_alerts()`

---

## 🚀 Implementation Pattern

### Step 1: Create Your Analyzer Class

```python
# src/stockreports/alert/approach/YOUR_APPROACH/analyzer.py
from src.stockreports.alert.analyzer import Analyzer
import pandas as pd

class YourApproachAnalyzer(Analyzer):
    """Analysis methods for YOUR_APPROACH."""
    
    @staticmethod
    def calculate_custom_metric(df: pd.DataFrame) -> float:
        """Calculate approach-specific metric."""
        # Your calculation logic
        return metric_value
    
    @staticmethod
    def get_signal_strength(candle: pd.Series) -> float:
        """Get strength of signal in candle."""
        # Your strength calculation
        return strength
```

### Step 2: Create Your Validator Class

```python
# src/stockreports/alert/approach/YOUR_APPROACH/validator.py
from src.stockreports.alert.validator import Validator
import pandas as pd

class YourApproachValidator(Validator):
    """Validation methods for YOUR_APPROACH."""
    
    @staticmethod
    def validate_custom_condition(df: pd.DataFrame, threshold: float) -> bool:
        """Check if custom condition is met."""
        # Your validation logic
        return is_valid
    
    @staticmethod
    def validate_signal_quality(strength: float, min_strength: float) -> bool:
        """Ensure signal meets quality threshold."""
        return strength >= min_strength
```

### Step 3: Use in Your Executor

```python
# src/stockreports/alert/approach/YOUR_APPROACH/executor.py
from .analyzer import YourApproachAnalyzer
from .validator import YourApproachValidator

class YourApproachExecutor(Executor):
    def __init__(self, symbol: str):
        self.settings = YourApproachSettings(symbol)
        self.analyzer = YourApproachAnalyzer()      # Create instance
        self.validator = YourApproachValidator()    # Create instance
        super().__init__(symbol, Approach.YOUR_APPROACH, self.settings)
    
    def _find_alerts(self, df, new_candle_count):
        alerts = []
        loop_setup = self.get_loop_setup(df, new_candle_count, ...)
        
        for i in range(loop_setup.start, loop_setup.end):
            self.set_window_context(i, df, ...)
            
            # Use analyzer to calculate metrics
            metric = self.analyzer.calculate_custom_metric(self.lookback_window_df)
            
            # Use validator to check conditions
            if self.validator.validate_custom_condition(self.lookback_window_df, metric):
                alert = self._create_alert(...)
                alerts.append(alert)
        
        return alerts
```

---

## 📚 Available Base Methods

### From Analyzer Base Class

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `calculate_body_ratio()` | candle | float (0-1) | Ratio of candle body to full range |
| `calculate_body_size()` | candle | float | Absolute size of candle body |
| `get_candle_color()` | candle | str | GREEN/RED/NEUTRAL |
| `get_window_size_and_trend()` | df | Tuple | Window size + trend |
| `calculate_window_price_range()` | df | Optional[float] | Price range high-low |
| `get_max_volume_in_window()` | df | float | Maximum volume |
| `get_opposite_color_candles()` | df, alert | List | Opposite-colored candles |
| `calculate_hl2()` | candle | float | (High + Low) / 2 |
| `calculate_median_volume()` | df | float | Median volume in window |

### From Validator Base Class

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `validate_candle_color_consistency()` | df, color | bool | All match color? |
| `validate_opposite_color_exists()` | df, alert | bool | Any opposite color? |
| `validate_price_threshold()` | price, thresh, cmp | bool | Price meets threshold? |
| `validate_ratio_threshold()` | ratio, min, max | bool | Within bounds? |
| `validate_volume_threshold()` | volume, thresh, cmp | bool | Volume meets threshold? |
| `validate_volume_multiplier()` | curr, ref, mult | bool | curr >= ref * mult? |
| `validate_dataframe_not_empty()` | df | bool | Has data? |
| `validate_required_columns()` | df, cols | bool | All columns exist? |
| `validate_window_size()` | df, min, max | bool | Within bounds? |
| `validate_price_levels()` | candle, levels | bool | Price at expected levels? |

---

## 💡 Usage Examples

### Example 1: Simple Validator Usage

```python
class MyExecutor(Executor):
    def _find_alerts(self, df, new_candle_count):
        alerts = []
        
        for i in range(...):
            self.set_window_context(i, df, lookback_period=20)
            
            # Use inherited validator method
            if not self.validator.validate_dataframe_not_empty(self.lookback_window_df):
                continue
            
            # Use inherited validator with custom threshold
            max_vol = self.analyzer.get_max_volume_in_window(self.lookback_window_df)
            if self.validator.validate_volume_multiplier(
                current=self.last_candle['volume'],
                reference=max_vol,
                multiplier=0.8
            ):
                alerts.append(self._create_alert(...))
        
        return alerts
```

### Example 2: Custom Method + Base Methods

```python
class VolumeAnalyzer(Analyzer):
    @staticmethod
    def calculate_volume_ratio(df: pd.DataFrame) -> float:
        """Calculate custom volume ratio."""
        max_vol = Analyzer.get_max_volume_in_window(df)
        median_vol = Analyzer.calculate_median_volume(df)
        return max_vol / median_vol if median_vol > 0 else 0

class VolumeValidator(Validator):
    @staticmethod
    def validate_volume_spike(df: pd.DataFrame, threshold: float) -> bool:
        """Check if volume spike exists."""
        ratio = VolumeAnalyzer.calculate_volume_ratio(df)
        return Validator.validate_ratio_threshold(
            ratio=ratio,
            min_threshold=threshold,
            max_threshold=float('inf')
        )
```

### Example 3: Using in Executor Steps

```python
def _find_alerts(self, df, new_candle_count):
    alerts = []
    
    for i in range(...):
        self.set_window_context(i, df, ...)
        
        # Step 1: Validate basic requirements
        self.next_step()
        if not self.validator.validate_required_columns(
            self.lookback_window_df,
            ['open', 'high', 'low', 'close', 'volume']
        ):
            continue
        
        # Step 2: Analyze metrics
        self.next_step()
        body_ratio = self.analyzer.calculate_body_ratio(self.last_candle)
        
        # Step 3: Validate metric
        self.next_step()
        if not self.validator.validate_ratio_threshold(
            ratio=body_ratio,
            min_threshold=0.7,
            max_threshold=1.0
        ):
            continue
        
        # Step 4: Check color consistency
        self.next_step()
        color = self.analyzer.get_candle_color(self.last_candle)
        if not self.validator.validate_candle_color_consistency(
            self.lookback_window_df,
            color
        ):
            continue
        
        # Alert found!
        alert = self._create_alert(...)
        alerts.append(alert)
    
    return alerts
```

---

## 🔄 Inheritance Pattern

### Analyzer Inheritance

```
Analyzer (ABC)
├─ 9 static methods
└─ @staticmethod decorator
    ↓
YourApproachAnalyzer(Analyzer)
├─ Inherits 9 methods from parent
├─ Adds 2-3 custom methods
└─ All still @staticmethod
    ↓
YourExecutor uses:
├─ self.analyzer.inherited_method()  # From Analyzer
├─ self.analyzer.custom_method()     # Custom
└─ All static (no instance state)
```

### Validator Inheritance

```
Validator (ABC)
├─ 10 static methods
└─ @staticmethod decorator
    ↓
YourApproachValidator(Validator)
├─ Inherits 10 methods from parent
├─ Adds 2-4 custom methods
└─ All still @staticmethod
    ↓
YourExecutor uses:
├─ self.validator.inherited_method()  # From Validator
├─ self.validator.custom_method()     # Custom
└─ All static (no instance state)
```

---

## ✅ Checklist for Implementation

### Analyzer Class

- [ ] Extends `Analyzer` base class
- [ ] All methods are `@staticmethod`
- [ ] Each method is pure (no side effects)
- [ ] No instance variables used
- [ ] Input types documented
- [ ] Return types documented
- [ ] Docstring explains calculation

### Validator Class

- [ ] Extends `Validator` base class
- [ ] All methods are `@staticmethod`
- [ ] Return boolean (True/False)
- [ ] No instance variables used
- [ ] Input types documented
- [ ] Docstring explains validation
- [ ] Handles edge cases (None, empty, etc.)

### Usage in Executor

- [ ] Analyzer instance created in `__init__`
- [ ] Validator instance created in `__init__`
- [ ] Methods called via `self.analyzer.method()`
- [ ] Methods called via `self.validator.method()`
- [ ] Used inside `_find_alerts()` method
- [ ] Called within step tracking (`self.next_step()`)

---

## 🚫 Common Mistakes to Avoid

### ❌ Mistake 1: Instance Variables in Static Methods

```python
# WRONG
class MyAnalyzer(Analyzer):
    @staticmethod
    def calculate_metric(df):
        self.value = df.mean()  # ❌ Can't use 'self' in @staticmethod
        return self.value
```

**Fix**: Don't use instance variables in static methods:
```python
# CORRECT
class MyAnalyzer(Analyzer):
    @staticmethod
    def calculate_metric(df):
        value = df.mean()  # ✅ Just use local variable
        return value
```

### ❌ Mistake 2: Not Decorating with @staticmethod

```python
# WRONG
class MyValidator(Validator):
    def validate_condition(self, value):  # ❌ Missing @staticmethod
        return value > 0
```

**Fix**: Add @staticmethod decorator:
```python
# CORRECT
class MyValidator(Validator):
    @staticmethod
    def validate_condition(value):  # ✅ @staticmethod decorator
        return value > 0
```

### ❌ Mistake 3: Calling Like Instance Methods

```python
# WRONG
validator = MyValidator()
result = validator.validate_condition(value)  # Works but unclear pattern

# CORRECT
result = MyValidator.validate_condition(value)  # Clear it's static
# or
validator = MyValidator()
result = validator.validate_condition(value)  # Also works, but less clear
```

### ❌ Mistake 4: Too Many Analyzer/Validator Classes

```python
# WRONG - Too many helpers
class MyExecutor(Executor):
    self.analyzer1 = MyAnalyzer1()
    self.analyzer2 = MyAnalyzer2()
    self.analyzer3 = MyAnalyzer3()
    self.validator1 = MyValidator1()
    self.validator2 = MyValidator2()
    # This is overkill!
```

**Fix**: Keep helpers focused, one analyzer and one validator:
```python
# CORRECT - Clear separation
class MyExecutor(Executor):
    self.analyzer = MyAnalyzer()    # All analysis methods
    self.validator = MyValidator()  # All validation methods
```

---

## 📖 For More Information

**Learn More About**:
- Theory & Architecture → `/docs/ARCHITECTURE/TECHNICAL_REFERENCE/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md`
- Executor Pattern → `/docs/ARCHITECTURE/IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md`
- Design Patterns → `/docs/ARCHITECTURE/DESIGN_PATTERNS_GUIDE.md`

**See Examples**:
- VRA Approach → `/src/stockreports/alert/approach/VRA/`
- StrongCandle Approach → `/src/stockreports/alert/approach/STRONG_CANDLE/`
- Any other approach → `/src/stockreports/alert/approach/`

---

## Summary

| Task | How | Where | Why |
|------|-----|-------|-----|
| **Inherit methods** | Extend class and use parent methods | In Analyzer/Validator | Base class provides common patterns |
| **Add custom methods** | Define @staticmethod in derived class | In Analyzer/Validator | Extend functionality for your approach |
| **Use in executor** | Create instance and call methods | In Executor.__init__ and _find_alerts() | Keeps code organized and reusable |
| **Call static method** | ClassName.method() or instance.method() | Anywhere | Standard Python static method call |

**Status**: Tier 3 - Implementation Guide ✅  
**Focus**: Practical how-to for Analyzer/Validator usage  
**Last Updated**: April 10, 2026
