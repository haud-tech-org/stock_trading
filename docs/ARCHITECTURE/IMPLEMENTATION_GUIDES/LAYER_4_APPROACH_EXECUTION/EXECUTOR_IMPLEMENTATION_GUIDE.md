# Executor Implementation Guide - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Codebase Analysis  
**Target Audience:** Developers creating new trading approaches  
**Prerequisites:** Understanding Technical Reference architecture  
**Tier**: Tier 3 - Implementation Guides (Practice-focused)

### 📚 Related Documentation

**Tier 2 - Theory & Architecture**:
- [ABSTRACT_BASE_CLASSES_ARCHITECTURE.md](../TECHNICAL_REFERENCE/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md) - Deep understanding of ABC design
- [DESIGN_PATTERNS_GUIDE.md](../DESIGN_PATTERNS_GUIDE.md) - Template Method pattern details

**Tier 3 - Practical Guides**:
- [ANALYZER_VALIDATOR_QUICK_REFERENCE.md](./ANALYZER_VALIDATOR_QUICK_REFERENCE.md) - Creating Analyzer/Validator helper classes
- [QUICK_REFERENCE_GUIDES.md](./QUICK_REFERENCE_GUIDES.md) - Fast code lookup

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Understanding the Actual Architecture](#understanding-the-actual-architecture)
3. [Executor Base Class](#executor-base-class)
4. [Implementation Pattern](#implementation-pattern)
5. [Step-by-Step Guide](#step-by-step-guide)
6. [Real Example: StrongCandleExecutor](#real-example-strongcandleexecutor)
7. [Complete Code Example](#complete-code-example)
8. [Testing](#testing)
9. [Integration Checklist](#integration-checklist)

---

## Overview

### What is an Executor?

An executor is a trading strategy that:
- **Inherits** from the `Executor` abstract base class
- **Analyzes** OHLCV data to detect trading opportunities
- **Returns** a list of `AlertData` objects via `_find_alerts()`
- **Wraps** results in `AlertResult` via the `run()` method
- **Works** in both LIVE mode (real-time) and REPLAY mode (testing)
- **Uses** settings loaded from configuration system

### Current Executors (6 Total)

Located in `/src/stockreports/alert/approach/`:

1. **StrongCandleExecutor** - STRONG_CANDLE approach
   - Detects strong candles with volume confirmation
   - Validates body size, volume, color consistency

2. **ConsistentMomentumExecutor** - CONSISTENT_MOMENTUM approach
   - Finds consistent color candles with anchor points
   - Validates momentum and price ranges

3. **VraExecutor** - VRA approach
   - Volume Rate of Change analysis
   - Range analysis with volume validation

4. **IchimokuExecutor** - ICHIMOKU approach
   - Ichimoku cloud indicator-based signals
   - Trend and support/resistance analysis

5. **VolumeSpikeConfirmationExecutor** - VOLUME_SPIKE_CONFIRMATION approach
   - Detects volume spikes with price confirmation
   - Trend validation and magnitude checks

6. **ConsistentVolumeAnchorExecutor** - CONSISTENT_VOLUME_ANCHOR approach
   - Consistent volume candles with anchor validation
   - Price range and volume confirmation

### Why Create a New Executor?

Create a new executor to:
- ✅ Implement a new trading strategy/approach
- ✅ Test a different analysis method
- ✅ Add a new technical indicator pattern
- ✅ Experiment with new signal conditions
- ❌ Don't create for parameter changes (use approach-specific settings instead)

---

## Understanding the Actual Architecture

### Mode System (IMPORTANT - IMPLEMENTATION_GUIDES+)

⚠️ **CRITICAL DECISION:** DEVELOPMENT mode is being removed in Phase 3!

**Only 1 Mode in Implementation Guides:**
```python
class Mode:
    DEPLOYMENT = "DEPLOYMENT"    # Only mode option
    # DEVELOPMENT being removed in Phase 3
    # See: CRITICAL_ARCHITECTURAL_DECISION.md
```

**IMPORTANT:** Time Control via TimeSimulator (Not Mode!)
- TimeSimulator determines LIVE vs REPLAY behavior
- LIVE Mode: Real system time, indefinite loop, auto-restart
- REPLAY Mode: Simulated time, bounded loop, deterministic exit
- Both use Mode.DEPLOYMENT for data access
- This allows testing with historical data in all scenarios

### Execution Flow

```
SymbolAlerter calls executor.run(df, new_candle_count)
    ↓
run() method (in Executor base class)
    ├─ Calls _find_alerts(df, new_candle_count) [abstract - implemented by subclass]
    ├─ Wraps results in AlertResult
    ├─ Handles exceptions gracefully
    ├─ Triggers garbage collection
    └─ Returns AlertResult

Your implementation in _find_alerts()
    ├─ Loops through DataFrame in reverse
    ├─ Validates conditions step-by-step
    ├─ Creates AlertData for each alert found
    ├─ Appends to self.alerts list
    └─ Returns self.alerts (list[AlertData])
```

---

## Executor Base Class

### Location
`/src/stockreports/alert/executor.py` (345 lines)

### Abstract Method (You Must Implement)

```python
@abstractmethod
def _find_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
    """
    Find and return alerts from the given DataFrame.
    
    Args:
        df: DataFrame with OHLCV data (indexed by 'time')
        new_candle_count: Number of new candles to scan (0 = full scan in REPLAY mode)
    
    Returns:
        list[AlertData]: List of alerts found (can be empty)
    
    Implementation Notes:
    - Must return list[AlertData], NOT AlertResult
    - run() method wraps your results in AlertResult
    - Loop through df in REVERSE (latest candles first)
    - Return self.alerts (initialized in __init__)
    """
    pass
```

### Concrete Methods (Available to Use)

#### `run(df, new_candle_count) → AlertResult`
```python
def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Public entry point. Calls _find_alerts() and wraps results.
    
    Handles:
    - Exception catching with error logging
    - Garbage collection before return
    - AlertResult wrapping
    
    Returns:
        AlertResult with:
        - approach_name: self.APPROACH_NAME
        - confirmed_alerts: List returned by _find_alerts()
        - status: Status.SUCCESS or Status.FAILED
        - message: Error message if status is FAILED
    """
```

#### `get_loop_setup(df, new_candle_count, lookback_window_size) → tuple`
```python
def get_loop_setup(
    self,
    df: pd.DataFrame,
    new_candle_count: int,
    lookback_window_size: int
) -> tuple[pd.DataFrame, int, int]:
    """
    Prepares loop boundaries for processing DataFrame.
    
    Returns:
        (df, loop_start, loop_end) - indices for reverse loop
        
    Behavior:
    - If REPLAY mode: loop_start = lookback_window_size (scan full history)
    - If LIVE mode: loop_start = len(df) - new_candle_count (scan new candles)
    
    Usage:
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df, new_candle_count, lookback_window_size
        )
        for i in range(loop_end, loop_start - 1, -1):
            self.set_window_context(i, df_indexed, lookback_window_size)
    """
```

#### `set_window_context(index, df, lookback_window_size) → None`
```python
def set_window_context(
    self,
    index: int,
    df: pd.DataFrame,
    lookback_window_size: int
) -> None:
    """
    Extracts a lookback window and sets context variables.
    
    Sets:
    - self.lookback_window_df: DataFrame with window of data
    - self.current_window_start_time: pd.Timestamp
    - self.current_window_end_time: pd.Timestamp
    - self.first_candle: pd.Series (first in window)
    - self.last_candle: pd.Series (last in window, index position)
    
    Check these before using:
        if self.lookback_window_df is None or self.last_candle is None:
            continue
    """
```

#### `next_step() → None` and `next_validation() → None`
```python
def next_step(self):
    """Increment current_step and reset validation_step. Call before each validation step."""
    self.current_step += 1
    self.validation_step = 0

def next_validation(self):
    """Increment validation_step within a step. Use for sub-validations."""
    self.validation_step += 1
```

#### `_step_cooldown_check(last_alert, signal, cooldown_window) → bool`
```python
def _step_cooldown_check(
    self,
    last_alert: AlertData,
    signal: Signal,
    cooldown_window: int
) -> bool:
    """
    Check if alert is too soon after previous alert.
    
    Returns:
        True if NOT in cooldown (alert OK)
        False if in cooldown (skip alert)
    
    Usage:
        if not self._step_cooldown_check(
            last_alert=MyExecutor.LATEST_ALERT,
            signal=signal,
            cooldown_window=self.settings.cooldown_window
        ):
            continue
    """
```

#### `update_alert_suggestions(alert) → None`
```python
def update_alert_suggestions(self, alert: AlertData) -> None:
    """
    Populate suggested prices in alert.
    
    Sets:
    - alert.structural_suggested_price
    - alert.performance_suggested_price
    - alert.suggested_profit_threshold
    
    Call before appending alert to self.alerts.
    """
```

### Context Variables (Set by Framework)

```python
class Executor:
    def __init__(self, symbol: str, approach: str, settings: Optional[BaseSettings] = None):
        self.symbol: str                    # Trading symbol
        self.APPROACH_NAME: str             # Approach name (e.g., "STRONG_CANDLE")
        self.settings: BaseSettings         # Loaded configuration
        self.logger: logging.Logger         # For logging
        
        # Window context (set by set_window_context())
        self.current_window_start_time: Optional[pd.Timestamp]
        self.current_window_end_time: Optional[pd.Timestamp]
        self.first_candle: Optional[pd.Series]
        self.last_candle: Optional[pd.Series]
        self.lookback_window_df: Optional[pd.DataFrame]
        
        # Step tracking
        self.current_step: int              # Which validation step (1-based)
        self.validation_step: int           # Which sub-validation (0-based)
        
        # Results accumulation
        self.alerts: list[AlertData]        # Alerts found in current run
        self.validations: list              # Validation records for debugging
        
        # Mode detection
        self.is_development_mode: bool      # True if REPLAY mode (DEVELOPMENT being removed)
```

### Data Models

#### AlertData
```python
@dataclass
class AlertData:
    approach: str                           # Approach name
    id: str                                 # Unique alert ID
    signal: str                             # "BUY" or "SELL"
    alert_price: float                      # Price at alert time
    alert_time: pd.Timestamp                # When alert triggered
    start_price: float                      # Starting price
    start_time: pd.Timestamp                # Start time
    details: Optional[str] = None           # JSON string with approach details
    trend: Optional[str] = None
    profit_loss: Optional[float] = None
    magnitude: Optional[float] = None
    structural_suggested_price: Optional[float] = None
    performance_suggested_price: Optional[float] = None
    suggested_profit_threshold: Optional[float] = None
    # ... more optional fields
```

#### AlertResult
```python
@dataclass
class AlertResult:
    approach_name: str                      # Which approach created this
    confirmed_alerts: List[AlertData]       # Primary data (list of alerts)
    status: str                             # "SUCCESS" or "FAILED"
    message: Optional[str] = None           # Error message if failed
```

---

## Implementation Pattern

### Step 1: Create Directory Structure

```
src/stockreports/alert/approach/YOUR_APPROACH/
├── __init__.py
├── executor.py           # Your executor implementation
├── settings.py           # Your settings class
├── analyzer.py           # (Optional) Helper analyzer class
├── validator.py          # (Optional) Helper validator class
└── config.yaml           # (Optional) Default configuration
```

### Step 2: Create Settings Class

```python
# src/stockreports/alert/approach/YOUR_APPROACH/settings.py
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings

class YourApproachSettings(BaseSettings):
    """Settings for YOUR_APPROACH approach."""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.YOUR_APPROACH)
        
        # Load settings via self.get(key)
        # Settings loaded from config system:
        # 1. approach_settings (APPROACH_CONFIG[approach_name])
        # 2. signal_settings
        # 3. validation_settings  
        # 4. global_settings
        
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        self.threshold_value = self.get("THRESHOLD_VALUE")
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
```

### ⭐ CRITICAL: IMPLEMENT `_find_alerts()` vs OVERRIDE `run()`

**GOLDEN RULE:** In your Executor, **IMPLEMENT** the abstract `_find_alerts()` method. **DO NOT OVERRIDE** the concrete `run()` method.

#### The Two Methods

| Method | Type | Your Action | Why |
|--------|------|-------------|-----|
| **`run()`** | Concrete (in base class) | **Inherit** - don't override | Handles logging, error handling, garbage collection, result formatting |
| **`_find_alerts()`** | Abstract (in base class) | **IMPLEMENT** - you must | Your approach-specific detection logic goes here |

#### Decision Tree

```
Creating a derived Executor?
│
├─ Should I override run()?
│  └─ NO! (Exception: RCM only)
│
└─ Should I implement _find_alerts()?
   └─ YES! (Always)
```

#### How It Works (Template Method Pattern)

```
User calls:  executor.run(df, new_candle_count)
    ↓
Base Executor.run():
    1. Log execution start
    2. Call: self._find_alerts(...)  ← Dispatches to YOUR implementation
    3. Log completion
    4. Wrap results in AlertResult
    5. Return AlertResult
```

#### Checklist

- [ ] ✅ **Implement** `_find_alerts()`
- [ ] ✅ Use inherited `get_loop_setup()`
- [ ] ✅ Use inherited `set_window_context()`
- [ ] ❌ **DO NOT** override `run()`
- [ ] ❌ **DO NOT** duplicate error handling
- [ ] ❌ **DO NOT** duplicate logging

#### Real Example: VRA Executor ✅ CORRECT

```python
class VraExecutor(Executor):
    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        super().__init__(symbol, Approach.VRA, self.settings)
    
    # ✅ Implements abstract method
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        alerts = []
        loop_setup = self.get_loop_setup(df, new_candle_count, ...)
        for i in range(loop_setup.start, loop_setup.end):
            self.set_window_context(i, df, ...)
            if self._step_volume_validation():
                alert = self._create_alert(...)
                alerts.append(alert)
        return alerts
    
    def _step_volume_validation(self) -> bool:
        self.next_step()
        # Volume validation logic
        return True
    
    # ✅ NO run() method override!
```

#### Exception: RCM

⚠️ **RCM is the ONLY exception** that overrides `run()`. This required special approval and documentation.

---

### Step 3: Create Executor Class

```python
# src/stockreports/alert/approach/YOUR_APPROACH/executor.py
import pandas as pd
import logging
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal
from src.stockreports.alert.model.models import AlertData
from .settings import YourApproachSettings

class YourApproachExecutor(Executor):
    """Executor for YOUR_APPROACH approach."""
    
    LATEST_ALERT: Optional[AlertData] = None  # Class variable for tracking
    
    def __init__(self, symbol: str):
        self.settings = YourApproachSettings(symbol)      # Create settings
        self.analyzer = YourApproachAnalyzer()            # Create analyzer (optional)
        self.validator = YourApproachValidator()          # Create validator (optional)
        approach_name = Approach.YOUR_APPROACH            # Get approach name
        super().__init__(symbol, approach_name, self.settings)  # Call parent init
        self.logger = logging.getLogger(__name__)         # Set logger
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """Find alerts using YOUR_APPROACH logic."""
        
        lookback_window_size = self.settings.lookback_window
        
        # Check minimum data requirement
        if len(df) < lookback_window_size:
            return self.alerts  # Return empty list if not enough data
        
        # Get loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df=df,
            new_candle_count=new_candle_count,
            lookback_window_size=lookback_window_size
        )
        
        # Loop in reverse (latest candles first)
        for i in range(loop_end, loop_start - 1, -1):
            # Set context: extracts lookback window and updates context variables
            self.set_window_context(i, df_indexed, lookback_window_size)
            if self.lookback_window_df is None or self.last_candle is None:
                continue
            
            # Step 1: Validate condition 1
            self.next_step()
            if not self._validate_condition_1():
                continue
            
            # Step 2: Validate condition 2
            self.next_step()
            if not self._validate_condition_2():
                continue
            
            # Step 3: Determine signal
            self.next_step()
            signal = self._determine_signal()
            if signal is None:
                continue
            
            # Step 4: Cooldown check
            self.next_step()
            if not self._step_cooldown_check(
                last_alert=YourApproachExecutor.LATEST_ALERT,
                signal=signal,
                cooldown_window=self.settings.cooldown_window
            ):
                continue
            
            # Create alert
            alert = AlertData(
                approach=self.APPROACH_NAME,
                id=f"{self.symbol}_{self.current_window_end_time.isoformat()}",
                signal=signal,
                alert_price=float(self.last_candle['close']),
                alert_time=self.current_window_end_time,
                start_price=float(self.first_candle['close']),
                start_time=self.current_window_start_time,
                magnitude=self._calculate_magnitude(),
                details=self._add_details_for_alert(...)
            )
            
            # Update suggestions
            self.update_alert_suggestions(alert)
            
            # Add to results
            self.alerts.append(alert)
            YourApproachExecutor.LATEST_ALERT = alert
        
        return self.alerts
    
    def _validate_condition_1(self) -> bool:
        """Your first validation condition."""
        # Use: self.last_candle, self.lookback_window_df
        # Return: True if condition met, False otherwise
        pass
    
    def _validate_condition_2(self) -> bool:
        """Your second validation condition."""
        pass
    
    def _determine_signal(self) -> Optional[str]:
        """Determine if signal is BUY or SELL, or None."""
        return Signal.BUY  # or Signal.SELL
    
    def _calculate_magnitude(self) -> float:
        """Calculate alert magnitude (0-1)."""
        return 0.5
```

---

## Step-by-Step Guide

### Step 1: Add Approach Name to Constants
```python
# src/stockreports/alert/common/constants.py
class Approach:
    YOUR_APPROACH = "YOUR_APPROACH"  # Add this line
```

### Step 2: Create Your Settings
Implement settings loading in `YOUR_APPROACH/settings.py`

### Step 3: Implement Your Executor
Follow the pattern above in `YOUR_APPROACH/executor.py`

### Step 4: Test
```python
# tests/test_your_approach.py
import pytest
from src.stockreports.alert.approach.YOUR_APPROACH.executor import YourApproachExecutor

def test_your_executor():
    executor = YourApproachExecutor(symbol="VN30")
    
    # Create sample DataFrame with OHLCV data
    df = ...
    
    # Call run()
    result = executor.run(df, new_candle_count=10)
    
    # Verify result
    assert result.status == "SUCCESS"
    assert isinstance(result.confirmed_alerts, list)
```

---

## Real Example: StrongCandleExecutor

### Structure
```
src/stockreports/alert/approach/STRONG_CANDLE/
├── __init__.py
├── executor.py (404 lines)
├── settings.py
├── analyzer.py
└── validator.py
```

### Key Characteristics
- Detects strong candles with volume confirmation
- Uses 5-6 validation steps per candle
- Tracks last alert via LATEST_ALERT class variable
- Uses analyzer and validator classes
- Settings loaded from BaseSettings

---

## Complete Code Example

See the actual StrongCandleExecutor implementation at:
`/src/stockreports/alert/approach/STRONG_CANDLE/executor.py`

---

## Testing

### Unit Tests
```python
# Test your executor in isolation
from your_approach.executor import YourApproachExecutor

def test_initialization():
    executor = YourApproachExecutor("VN30")
    assert executor.symbol == "VN30"
    assert executor.APPROACH_NAME == "YOUR_APPROACH"

def test_find_alerts():
    executor = YourApproachExecutor("VN30")
    df = create_test_dataframe()
    
    alerts = executor._find_alerts(df, new_candle_count=0)
    assert isinstance(alerts, list)

def test_run_method():
    executor = YourApproachExecutor("VN30")
    df = create_test_dataframe()
    
    result = executor.run(df)
    assert result.status in ["SUCCESS", "FAILED"]
    assert isinstance(result.confirmed_alerts, list)
```

### Integration Tests
```python
# Test executor in system context
def test_executor_in_system():
    from src.stockreports.alert.symbol_alerter import SymbolAlerter
    
    alerter = SymbolAlerter(...)
    result = alerter.process()
    
    # Check that your executor was called
    # Check alerts were generated
```

---

## Integration Checklist

When adding a new executor:

- [ ] Add approach name to `Approach` class in constants.py
- [ ] Create `YOUR_APPROACH/` directory
- [ ] Create settings class (YOUR_APPROACH/settings.py)
- [ ] Create executor class (YOUR_APPROACH/executor.py)
- [ ] Implement `_find_alerts()` method
- [ ] **Add resolution mapping to APPROACH_RESOLUTION_MAPPING in signal_settings.py**
- [ ] Add configuration to config system
- [ ] Write unit tests
- [ ] Test in REPLAY mode
- [ ] Verify LIVE mode compatibility
- [ ] Document your approach
- [ ] Add to integration tests

**NEW: Resolution Configuration (CRITICAL)**
Each executor must be mapped to a resolution:

```python
# In src/stockreports/config/signal_settings.py:
APPROACH_RESOLUTION_MAPPING = {
    # ... existing approaches
    "YOUR_APPROACH": 1,  # ← Add this line
                         # 1 = 1-minute, 5 = 5-min, 15 = 15-min, 60 = 60-min
}
```

The ResolutionCoordinator will:
- Read APPROACH_RESOLUTION_MAPPING at startup
- Validate that YOUR_APPROACH is a valid Approach constant
- Validate that the resolution (1, 5, 15, or 60) is supported
- Provide resolution lookups when SymbolAlerter runs your executor

**Common Resolution Choices:**
- High-frequency strategies (Strong Candle, Momentum): 1-minute
- Swing strategies (Ichimoku): 5-15 minutes
- Trend following: 15-60 minutes

---

**Status:** Corrected  
**Based On:** Actual codebase analysis  
**Last Updated:** April 8, 2026
