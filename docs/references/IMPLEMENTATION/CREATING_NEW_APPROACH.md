# Creating New Trading Approaches - Step-by-Step Guide

**Status**: ✅ Complete Implementation Guide  
**Purpose**: Build new trading approaches using proven pattern  
**Audience**: Developers implementing new approaches  
**Last Updated**: March 12, 2026

---

## 🎯 Quick Reference

**Time Required**: 2-4 hours (depending on complexity)  
**Pattern**: Executor → Analyzer → Validator  
**Base Methods**: 9 in Analyzer, 10 in Validator (inherit automatically)  
**Code Size**: 75-300 lines total (organized and modular)  
**Testing**: Pure functions make testing trivial  

---

## 📋 Pre-Implementation Checklist

Before you start, gather:

- [ ] **Trading Rules Document**
  - What are the buy/sell signals?
  - What validations are needed?
  - What thresholds apply?
  
- [ ] **Required Data**
  - OHLCV? (Open, High, Low, Close, Volume)
  - Additional indicators?
  - History requirements (how many past candles)?
  
- [ ] **Thresholds**
  - Price thresholds?
  - Volume thresholds?
  - Ratio thresholds?
  - Window sizes?
  
- [ ] **Approach Name**
  - What will you call it?
  - Snake_case or CamelCase?
  - Consistent with existing patterns?

---

## 🏗️ Complete Step-by-Step Implementation

### Step 1: Create Folder Structure

```bash
# Create the folder for your new approach
mkdir -p src/stockreports/alert/approach/YOUR_APPROACH_NAME

# Files to create
touch src/stockreports/alert/approach/YOUR_APPROACH_NAME/__init__.py
touch src/stockreports/alert/approach/YOUR_APPROACH_NAME/executor.py
touch src/stockreports/alert/approach/YOUR_APPROACH_NAME/analyzer.py
touch src/stockreports/alert/approach/YOUR_APPROACH_NAME/validator.py
```

Replace `YOUR_APPROACH_NAME` with your approach name (e.g., `STRONG_CANDLE`, `ICHIMOKU`).

### Step 2: Analyze Base Classes

Before writing code, understand what you inherit:

**Base Analyzer Provides** (9 methods):
```
1. calculate_body_ratio()        → float (0-1)
2. calculate_body_size()         → float (price difference)
3. get_candle_color()            → CandleColor (GREEN/RED/NEUTRAL)
4. get_window_size_and_trend()   → tuple(size, trend)
5. calculate_window_price_range()→ dict(low, high)
6. calculate_conditional_window_price_range() → dict(low, high)
7. get_max_volume_in_window()    → float (volume)
8. get_max_volume_in_conditional_window() → float (volume)
9. get_opposite_color_candles()  → DataFrame (filtered rows)
```

**Base Validator Provides** (10 methods):
```
1. validate_candle_color_consistency()  → bool
2. validate_opposite_color_exists()     → bool
3. validate_price_threshold()           → bool
4. validate_ratio_threshold()           → bool
5. validate_volume_threshold()          → bool
6. validate_volume_multiplier()         → bool
7. validate_dataframe_not_empty()       → bool
8. validate_required_columns()          → bool
9. validate_window_size()               → bool
10. validate_data_quality()             → bool
```

**Question**: Do you need any of these? If yes, you get it FREE via inheritance!

### Step 2.5: Create Settings Class

**File**: `src/stockreports/alert/approach/YOUR_APPROACH_NAME/settings.py`

```python
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings


class YourApproachSettings(BaseSettings):
    """
    Settings for the YOUR_APPROACH_NAME approach.
    
    All configuration parameters are loaded from the centralized signal_settings.py
    using the get() method inherited from BaseSettings.
    
    This approach keeps all thresholds in one place for easy tuning and backtesting.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize settings for a specific symbol.
        
        Args:
            symbol: Trading symbol (used to load symbol-specific settings if available)
        """
        # Initialize base settings (loads from centralized configuration)
        super().__init__(symbol, Approach.YOUR_APPROACH_NAME)
        
        # Load approach-specific parameters from centralized configuration
        # Format: self.SETTING_NAME = self.get("SETTING_KEY")
        
        # Window and lookback settings
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        
        # Threshold settings for your validations
        self.threshold_1 = self.get("THRESHOLD_1")
        self.threshold_2 = self.get("THRESHOLD_2")
        self.threshold_3 = self.get("THRESHOLD_3")
        
        # Volume and magnitude settings
        self.volume_multiplier = self.get("VOLUME_MULTIPLIER")
        self.magnitude_threshold = self.get("MAGNITUDE_THRESHOLD")
        
        # Cooldown settings (prevents over-alerting)
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
```

**Key Settings Pattern**:
- ✅ Inherit from `BaseSettings` (provides common functionality)
- ✅ Call `super().__init__(symbol, Approach.YOUR_APPROACH_NAME)`
- ✅ Load settings via `self.get("SETTING_KEY")` from centralized config
- ✅ Use `Approach` enum for approach name (prevents typos)
- ✅ Settings are symbol-aware (can have different thresholds per symbol)
- ✅ All configuration in one place for easy tuning

### Step 3: Create Analyzer Class

**File**: `src/stockreports/alert/approach/YOUR_APPROACH_NAME/analyzer.py`

**Basic Template** (Minimal):
```python
from src.stockreports.alert.analyzer import Analyzer

class YourApproachAnalyzer(Analyzer):
    """
    Analyzer for YOUR_APPROACH_NAME trading approach.
    
    Inherits 9 calculation methods from base Analyzer:
    - calculate_body_ratio()
    - calculate_body_size()
    - get_candle_color()
    - get_window_size_and_trend()
    - calculate_window_price_range()
    - calculate_conditional_window_price_range()
    - get_max_volume_in_window()
    - get_max_volume_in_conditional_window()
    - get_opposite_color_candles()
    """
    
    # If you don't need any custom methods, you're done!
    # Executor can call all 9 inherited methods directly.
    pass
```

**With Custom Methods**:
```python
from src.stockreports.alert.analyzer import Analyzer
from src.stockreports.alert.common.constants import CandleColumn

class YourApproachAnalyzer(Analyzer):
    """
    Analyzer for YOUR_APPROACH_NAME trading approach.
    
    Inherits 9 base methods + adds custom calculations.
    """
    
    @staticmethod
    def your_custom_calculation(candle: dict) -> float:
        """
        Description of what you calculate.
        
        Args:
            candle: dict with OHLCV keys
        
        Returns:
            float: calculated value
        
        Example:
            >>> custom = YourApproachAnalyzer.your_custom_calculation(
            ...     {"open": 100, "close": 105, "high": 108, "low": 98})
            >>> custom
            1.05
        """
        # Your calculation logic
        # Use CandleColumn enum for column access
        open_price = candle[CandleColumn.OPEN]
        close_price = candle[CandleColumn.CLOSE]
        
        return close_price / open_price if open_price != 0 else 0
    
    @staticmethod
    def another_custom_method(dataframe) -> float:
        """Another custom calculation."""
        # Your logic here
        return float
```

**Guidelines for Custom Methods**:
- ✅ Use `@staticmethod` (no instance state)
- ✅ Use `CandleColumn` enum for column names
- ✅ Return calculated values (numbers, colors, DataFrames)
- ✅ NO business logic (that's for Validator)
- ✅ NO conditions based on thresholds
- ✅ Pure functions (same input → same output)
- ✅ Add docstrings with Args, Returns, Examples

### Step 4: Create Validator Class

**File**: `src/stockreports/alert/approach/YOUR_APPROACH_NAME/validator.py`

**Basic Template** (Minimal):
```python
from src.stockreports.alert.validator import Validator

class YourApproachValidator(Validator):
    """
    Validator for YOUR_APPROACH_NAME trading approach.
    
    Inherits 10 validation methods from base Validator:
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
    """
    
    # If you don't need any custom validations, you're done!
    # Executor can call all 10 inherited methods directly.
    pass
```

**With Custom Methods**:
```python
from src.stockreports.alert.validator import Validator
from src.stockreports.alert.common.constants import Comparison, CandleColor

class YourApproachValidator(Validator):
    """
    Validator for YOUR_APPROACH_NAME trading approach.
    
    Inherits 10 base methods + adds custom validations.
    """
    
    @staticmethod
    def validate_custom_condition(
        value: float,
        threshold: float,
        comparison: Comparison
    ) -> bool:
        """
        Validate custom business condition.
        
        Args:
            value: calculated value to check
            threshold: threshold to compare against
            comparison: Comparison enum (GREATER, LESS, etc.)
        
        Returns:
            bool: True if condition met, False otherwise
        
        Example:
            >>> is_valid = YourApproachValidator.validate_custom_condition(
            ...     value=100.5, threshold=100.0, 
            ...     comparison=Comparison.GREATER)
            >>> is_valid
            True
        """
        if comparison == Comparison.GREATER:
            return value > threshold
        elif comparison == Comparison.LESS:
            return value < threshold
        elif comparison == Comparison.EQUAL:
            return value == threshold
        elif comparison == Comparison.GREATER_EQUAL:
            return value >= threshold
        elif comparison == Comparison.LESS_EQUAL:
            return value <= threshold
        else:
            return False
    
    @staticmethod
    def another_custom_validation(data, requirement) -> bool:
        """Another custom validation."""
        # Your logic here
        return bool
```

**Guidelines for Custom Methods**:
- ✅ Use `@staticmethod` (no instance state)
- ✅ Use `Comparison` enum (not string defaults!)
- ✅ Use `CandleColor` enum (not strings!)
- ✅ Return boolean ONLY
- ✅ Pure functions (no side effects)
- ✅ NO calculations (that's for Analyzer)
- ✅ Add docstrings with Args, Returns, Examples

### Step 5: Create Executor Class

**File**: `src/stockreports/alert/approach/YOUR_APPROACH_NAME/executor.py`

**Complete Template** (Based on STRONG_CANDLE structure):

```python
import pandas as pd
import logging
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, ValidationStatus, LogLevel, Trend
from src.stockreports.alert.model.models import AlertData, Validation
from varname import nameof
from src.stockreports.utils.log_factory import log

from .settings import YourApproachSettings
from .analyzer import YourApproachAnalyzer
from .validator import YourApproachValidator


class YourApproachExecutor(Executor):
    """
    Executor for the YOUR_APPROACH_NAME approach.
    
    ⚠️ CRITICAL PRINCIPLE:
    - IMPLEMENT the abstract method _find_alerts()
    - DO NOT override the concrete method run()
    - The base class run() provides orchestration: logging, exception handling, formatting
    
    This class orchestrates Analyzer (calculations) and Validator (checks)
    to find trading signals.
    """
    
    def __init__(self, symbol: str):
        """
        Initialize executor with settings.
        
        Args:
            symbol: Trading symbol (e.g., 'AAPL', 'EURUSD')
        """
        # Initialize settings (loads from centralized configuration)
        self.settings = YourApproachSettings(symbol)
        
        # Initialize analyzer and validator
        self.analyzer = YourApproachAnalyzer()
        self.validator = YourApproachValidator()
        
        # Call parent constructor with symbol, approach name, and settings
        # This initializes: logger, context variables, alerts list, etc.
        approach_name = Approach.YOUR_APPROACH_NAME  # Add to constants if needed
        super().__init__(symbol, approach_name, self.settings)
        
        self.logger = logging.getLogger(__name__)
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        IMPLEMENT this abstract method to find alerts in the dataframe.
        
        The base class run() method calls this and handles:
        - Exception handling
        - Logging
        - Result formatting into AlertResult
        - Garbage collection
        
        Args:
            df: OHLCV data as pandas DataFrame
            new_candle_count: Number of new candles (for optimization, 0 = process all)
        
        Returns:
            list[AlertData]: List of found alerts (empty list if none found)
        
        Implementation Pattern:
        1. Validate input data
        2. Setup loop boundaries (using get_loop_setup())
        3. For each candle (backward loop): extract context, run validation steps
        4. Create AlertData when all conditions pass
        5. Handle deployment vs development mode
        6. Return list of alerts
        """
        # Validate minimum data requirements
        lookback_window_size = self.settings.lookback_window
        
        if len(df) < lookback_window_size:
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time="N/A",
                step=0,
                message=f"Not enough data: requires {lookback_window_size}, have {len(df)}",
                log_level=LogLevel.DEBUG,
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return self.alerts  # Return empty alerts list from base class
        
        # --- Setup loop (base class utility) ---
        # Prepares indexed DataFrame and determines loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )
        
        # --- Main loop: process candles backward ---
        for i in range(loop_end, loop_start - 1, -1):
            # Extract window context using base class utility
            # Sets: lookback_window_df, first_candle, last_candle, current_window_start_time, etc.
            self.set_window_context(i, df_indexed, lookback_window_size)
            
            if self.lookback_window_df is None or self.last_candle is None:
                continue
            
            # === STEP 1: Your first validation ===
            self.next_step()  # Increment step counter for logging
            
            # Run validation using Validator
            validation_1_result = self.validator.your_first_validation(
                self.last_candle,
                self.settings.threshold_1
            )
            
            if not validation_1_result:
                continue  # Skip to next candle
            
            # Log successful validation using base class utility
            self.validations.append(Validation(
                name=nameof(self.settings.threshold_1),
                step=self.current_step,
                validation=self.next_validation(),
                message="Validation 1 passed",
                status=ValidationStatus.PASSED
            ))
            
            # === STEP 2: Your second validation ===
            self.next_step()
            
            validation_2_result = self.validator.your_second_validation(
                self.lookback_window_df,
                self.last_candle,
                self.settings.threshold_2
            )
            
            if not validation_2_result:
                continue
            
            self.validations.append(Validation(
                name=nameof(self.settings.threshold_2),
                step=self.current_step,
                validation=self.validation_step,
                message="Validation 2 passed",
                status=ValidationStatus.PASSED
            ))
            
            # === STEP 3: Cooldown check (base class utility) ===
            self.next_step()
            
            # Check if enough time has passed since last alert (prevents over-alerting)
            if not self._step_cooldown_check(
                last_alert=None,  # Or store LATEST_ALERT as class variable
                signal=Signal.BUY,
                cooldown_window=self.settings.cooldown_window
            ):
                continue  # Still in cooldown period
            
            # === CREATE ALERT ===
            self.next_step()
            
            # Build alert details
            details_dict = self._add_details_for_alert(
                threshold_1_value=validation_1_result,
                threshold_2_value=validation_2_result,
                candle_time=self.last_candle['time'].isoformat()
            )
            
            # Create alert using base class utility
            alert_data = self._create_alert_with_details(
                final_signal=Signal.BUY,  # Or SELL based on your logic
                final_trend=Trend.UPTREND,  # Or determine from data
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.magnitude_threshold,
                details=details_dict
            )
            
            if alert_data is not None:
                self.alerts.append(alert_data)
                
                # In DEPLOYMENT mode: return immediately after first alert
                # In DEVELOPMENT mode: continue to find all alerts
                if not self.is_development_mode:
                    return self.alerts
        
        # Return all found alerts (empty list if none)
        return self.alerts
```

**Key Features of Template**:
- ✅ Uses base class utilities: `get_loop_setup()`, `set_window_context()`, `next_step()`, `next_validation()`
- ✅ Proper inheritance: calls `super().__init__(symbol, approach_name, settings)`
- ✅ Settings: loaded from centralized configuration via `BaseSettings`
- ✅ Backward loop: processes candles latest-first (standard pattern)
- ✅ Step-by-step validation: each check increments step counter for logging
- ✅ Alert creation: uses `_create_alert_with_details()` from base class
- ✅ Deployment vs Development: returns early in deployment mode
- ✅ Error handling: managed by base class `run()` method

### Step 6: Create `__init__.py`

**File**: `src/stockreports/alert/approach/YOUR_APPROACH_NAME/__init__.py`

```python
"""
YOUR_APPROACH_NAME Alert Approach Package.

Exports:
- YourApproachExecutor: Main executor for alert detection
- YourApproachAnalyzer: Pure calculation functions
- YourApproachValidator: Pure validation functions
- YourApproachSettings: Configuration settings
"""

from .executor import YourApproachExecutor
from .analyzer import YourApproachAnalyzer
from .validator import YourApproachValidator
from .settings import YourApproachSettings

__all__ = [
    'YourApproachExecutor',
    'YourApproachAnalyzer',
    'YourApproachValidator',
    'YourApproachSettings',
]
```

**Pattern Notes**:
- ✅ Import from local modules (using relative imports: `.module`)
- ✅ Export all four classes in `__all__`
- ✅ Settings imported from its own file
- ✅ Clear docstring explaining what each class does

---

## ✅ Implementation Checklist

### Design Phase
- [ ] Trading rules documented clearly
- [ ] Required data identified (OHLCV, etc.)
- [ ] Thresholds determined
- [ ] Signal logic defined (when to BUY/SELL)
- [ ] Approach name finalized

### Code Phase
- [ ] Folder structure created
- [ ] Analyzer class created (inherits 9 base methods)
- [ ] Validator class created (inherits 10 base methods)
- [ ] Executor class created (orchestrates flow)
- [ ] `__init__.py` file created
- [ ] All imports work correctly

### Quality Phase
- [ ] Type hints on all methods
- [ ] Docstrings with Args, Returns, Examples
- [ ] All methods are `@staticmethod` (Analyzer/Validator)
- [ ] No hardcoded values (use settings)
- [ ] Settings have validation
- [ ] Edge cases handled

### Testing Phase
- [ ] Unit tests for Analyzer methods
- [ ] Unit tests for Validator methods
- [ ] Integration test with real data
- [ ] Edge cases tested
- [ ] Settings validation tested

### Production Phase
- [ ] Code reviewed (against CODE_QUALITY_STANDARDS.md)
- [ ] Passes all tests
- [ ] Documentation complete
- [ ] Ready to deploy

---

## 🧪 Writing Tests

### Test Analyzer Methods

```python
import pytest
from src.stockreports.alert.approach.YOUR_APPROACH_NAME.analyzer import (
    YourApproachAnalyzer
)

class TestYourApproachAnalyzer:
    """Test suite for analyzer."""
    
    def test_custom_calculation_valid_input(self):
        """Test custom calculation with valid input."""
        candle = {"open": 100, "close": 105, "high": 108, "low": 98}
        result = YourApproachAnalyzer.your_custom_calculation(candle)
        
        assert isinstance(result, float)
        assert result == 1.05  # (close / open)
    
    def test_custom_calculation_zero_open(self):
        """Test custom calculation when open is zero."""
        candle = {"open": 0, "close": 105, "high": 108, "low": 98}
        result = YourApproachAnalyzer.your_custom_calculation(candle)
        
        assert result == 0  # Should handle division by zero
```

### Test Validator Methods

```python
from src.stockreports.alert.common.constants import Comparison

class TestYourApproachValidator:
    """Test suite for validator."""
    
    def test_validate_custom_condition_greater(self):
        """Test greater than comparison."""
        result = YourApproachValidator.validate_custom_condition(
            value=100.5,
            threshold=100.0,
            comparison=Comparison.GREATER
        )
        assert result is True
    
    def test_validate_custom_condition_less(self):
        """Test less than comparison."""
        result = YourApproachValidator.validate_custom_condition(
            value=99.5,
            threshold=100.0,
            comparison=Comparison.LESS
        )
        assert result is True
```

### Test Executor Integration

```python
import pandas as pd

class TestYourApproachExecutor:
    """Test suite for executor."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data."""
        import pandas as pd
        from datetime import datetime
        
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        return pd.DataFrame({
            'open': [100 + i*0.5 for i in range(50)],
            'high': [105 + i*0.5 for i in range(50)],
            'low': [95 + i*0.5 for i in range(50)],
            'close': [102 + i*0.5 for i in range(50)],
            'volume': [1000 + i*10 for i in range(50)]
        }, index=dates)
    
    def test_executor_returns_alert_result(self, sample_data):
        """Test executor returns AlertResult from run()."""
        executor = YourApproachExecutor(symbol='TEST')
        result = executor.run(sample_data)
        
        # Should return AlertResult (not a dict)
        assert hasattr(result, 'alerts')
        assert hasattr(result, 'confirmed_alerts')
        assert hasattr(result, 'status')
    
    def test_executor_implements_find_alerts(self, sample_data):
        """Test executor implements _find_alerts()."""
        executor = YourApproachExecutor(symbol='TEST')
        alerts = executor._find_alerts(sample_data)
        
        # _find_alerts returns list of AlertData
        assert isinstance(alerts, list)
        if len(alerts) > 0:
            assert hasattr(alerts[0], 'signal')
            assert hasattr(alerts[0], 'alert_time')
```

---

## 🚀 Quick Start Template

Copy and use this complete minimal setup (all 4 files):

```python
# settings.py
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings

class MyApproachSettings(BaseSettings):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.MY_APPROACH)
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.threshold_1 = self.get("THRESHOLD_1")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")

# analyzer.py
from src.stockreports.alert.analyzer import Analyzer

class MyApproachAnalyzer(Analyzer):
    """Analyzer for MyApproach - inherits all base calculation methods."""
    pass

# validator.py
from src.stockreports.alert.validator import Validator

class MyApproachValidator(Validator):
    """Validator for MyApproach - inherits all base validation methods."""
    pass

# executor.py
import pandas as pd
import logging
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, ValidationStatus, LogLevel
from src.stockreports.alert.model.models import AlertData, Validation
from varname import nameof
from src.stockreports.utils.log_factory import log
from .settings import MyApproachSettings
from .analyzer import MyApproachAnalyzer
from .validator import MyApproachValidator

class MyApproachExecutor(Executor):
    """REMEMBER: Implement _find_alerts(), DO NOT override run()"""
    
    def __init__(self, symbol: str):
        self.settings = MyApproachSettings(symbol)
        self.analyzer = MyApproachAnalyzer()
        self.validator = MyApproachValidator()
        super().__init__(symbol, Approach.MY_APPROACH, self.settings)
        self.logger = logging.getLogger(__name__)
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """IMPLEMENT this abstract method - base run() calls this."""
        if len(df) < self.settings.lookback_window:
            return self.alerts
        
        # Setup loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df, new_candle_count, self.settings.lookback_window
        )
        
        # Process each candle
        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, self.settings.lookback_window)
            
            if self.lookback_window_df is None or self.last_candle is None:
                continue
            
            # Your validation logic here
            self.next_step()
            # ... add your checks ...
            
        return self.alerts

# __init__.py
from .executor import MyApproachExecutor
from .analyzer import MyApproachAnalyzer
from .validator import MyApproachValidator
from .settings import MyApproachSettings

__all__ = [
    'MyApproachExecutor',
    'MyApproachAnalyzer',
    'MyApproachValidator',
    'MyApproachSettings',
]
```

**Quick Start Checklist**:
- ✅ Settings extends `BaseSettings` and loads from centralized config
- ✅ Analyzer and Validator inherit from base classes (can be empty)
- ✅ Executor extends `Executor` and implements `_find_alerts()`
- ✅ Executor uses base class utilities: `get_loop_setup()`, `set_window_context()`, `next_step()`
- ✅ All imports use relative imports in `__init__.py`
- ✅ Ready to test and deploy!

---

## 🔗 Related Documentation

- **ARCHITECTURE_OVERVIEW.md** - System architecture
- **DESIGN_PATTERNS_GUIDE.md** - Pattern variations
- **ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md** - All 19 base methods
- **CODE_QUALITY_STANDARDS.md** - Production-ready code requirements
- **TESTING_STRATEGY.md** - Comprehensive testing guide

---

## 📞 Common Questions

**Q: Do I HAVE to inherit from Analyzer/Validator?**  
A: No, but you SHOULD. You get 19 free methods and 100% consistency.

**Q: How many custom methods do I add?**  
A: Usually 2-5. If more than 10, consider redesign.

**Q: What if I don't need all base methods?**  
A: That's fine! You inherit them but don't have to use them. They're there when needed.

**Q: Can I modify inherited methods?**  
A: Not recommended. Override in your class if different behavior needed.

**Q: How do I test if it works?**  
A: Create a simple executor test with sample data and verify output.

---

**Status**: ✅ Complete step-by-step guide  
**Next**: See TESTING_STRATEGY.md for testing approach  
**Time to Implement**: 2-4 hours (includes testing)  
**Difficulty**: Intermediate
