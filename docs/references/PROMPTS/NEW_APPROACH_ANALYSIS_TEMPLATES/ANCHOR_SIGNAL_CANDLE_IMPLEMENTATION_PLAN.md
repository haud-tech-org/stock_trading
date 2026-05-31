# Anchor-Signal-Candle (ASC) Approach - Implementation Plan

**Purpose**: Detailed step-by-step plan for generating ASC approach code  
**Date**: April 10, 2026  
**Status**: ✅ READY FOR CODE GENERATION

---

## 🎯 Implementation Overview

This plan details how to generate production-ready code for the Anchor-Signal-Candle (ASC) trading approach following all existing architecture patterns, design principles, and code quality standards.

**Approach Name**: `ANCHOR_SIGNAL_CANDLE` (will be added to `Approach` enum)

**Structure**: 5 files mirroring all other approaches
```
src/stockreports/alert/approach/ANCHOR_SIGNAL_CANDLE/
├── __init__.py
├── settings.py
├── analyzer.py
├── validator.py
└── executor.py
```

---

## 📋 Phase 1: Settings Configuration (`settings.py`)

### File Purpose
Centralize all configuration parameters for the ASC approach. All values loaded from `signal_settings.py` via `BaseSettings` inheritance.

### Structure Template (Based on STRONG_CANDLE)

```python
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings

class AscSettings(BaseSettings):
    """
    Settings for the Anchor-Signal-Candle approach.
    All configuration parameters loaded from centralized signal_settings.py.
    """
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.ANCHOR_SIGNAL_CANDLE)
        
        # Window configuration
        self.lookback_window = self.get("LOOKBACK_WINDOW")
        
        # Validation 1: Window size threshold
        self.min_size_price_window = self.get("MIN_SIZE_PRICE_WINDOW")
        
        # Validation 2: Anchor candle thresholds
        self.min_size_candle = self.get("MIN_SIZE_CANDLE")
        self.multiplier_size = self.get("MULTIPLIER_SIZE")
        
        # Validation 3: Signal candle thresholds
        self.min_volume = self.get("MIN_VOLUME")
        self.multiplier_volume = self.get("MULTIPLIER_VOLUME")
        
        # Validation 4: Alert candle wick thresholds
        self.min_percentage = self.get("MIN_PERCENTAGE")
        self.max_percentage = self.get("MAX_PERCENTAGE")
        
        # Cooldown validation
        self.cooldown_window = self.get("COOLDOWN_WINDOW")
```

### Configuration Parameters to Add to signal_settings.py
```python
ANCHOR_SIGNAL_CANDLE = {
    "LOOKBACK_WINDOW": 50,
    "MIN_SIZE_PRICE_WINDOW": 0.5,
    "MIN_SIZE_CANDLE": 0.01,
    "MULTIPLIER_SIZE": 1.5,
    "MIN_VOLUME": 100000,
    "MULTIPLIER_VOLUME": 1.2,
    "MIN_PERCENTAGE": 0.2,
    "MAX_PERCENTAGE": 0.6,
    "COOLDOWN_WINDOW": 60,
}
```

### Key Points
- Use `Approach.ANCHOR_SIGNAL_CANDLE` enum (must be added)
- Class name: `AscSettings` (not `AscEditorSettings`)
- Inherit from `BaseSettings`
- All parameters loaded via `self.get(PARAM_NAME)`

---

## 📊 Phase 2: Analyzer Implementation (`analyzer.py`)

### File Purpose
Pure calculation functions for ASC approach. All static methods, no side effects.

### Inheritance
- Inherits from base `Analyzer` class
- Extends with ASC-specific calculations
- Can reuse base methods or add approach-specific ones

### ASC-Specific Analyzer Methods

#### Method 1: Calculate Average Candle Body Size
```python
@staticmethod
def calculate_average_candle_body_size(
    lookback_window_df: pd.DataFrame
) -> float:
    """
    Calculate average body size (HIGH - LOW) across all candles in window.
    
    Args:
        lookback_window_df (pd.DataFrame): Full lookback window
        
    Returns:
        float: Average body size (HIGH - LOW) / number of candles
    """
    # Logic: Sum of (HIGH - LOW) / count
```

#### Method 2: Find Anchor Candle
```python
@staticmethod
def find_anchor_candle(
    lookback_window_df: pd.DataFrame
) -> Optional[pd.Series]:
    """
    Find the candle with maximum body size (HIGH - LOW) in window.
    
    Args:
        lookback_window_df (pd.DataFrame): Full lookback window
        
    Returns:
        Optional[pd.Series]: Anchor candle row with max body, or None
    """
    # Logic: Return candle with MAX(HIGH - LOW)
```

#### Method 3: Calculate Average Volume
```python
@staticmethod
def calculate_average_volume(
    lookback_window_df: pd.DataFrame
) -> float:
    """
    Calculate average volume across all candles in window.
    
    Args:
        lookback_window_df (pd.DataFrame): Full lookback window
        
    Returns:
        float: Mean volume
    """
    # Logic: MEAN(all volumes)
```

#### Method 4: Find Signal Candle (Max Volume in Entire Window)
```python
@staticmethod
def find_signal_candle(
    lookback_window_df: pd.DataFrame
) -> Optional[pd.Series]:
    """
    Find candle with maximum volume in entire window.
    
    Search scope: Entire window (verification that signal >= anchor happens in validator)
    
    Args:
        lookback_window_df (pd.DataFrame): Full lookback window
        
    Returns:
        Optional[pd.Series]: Signal candle with max volume, or None
    """
    # Logic: Return candle with MAX(volume) in full window
```

#### Method 5: Get Candle Index in DataFrame
```python
@staticmethod
def get_candle_index(
    lookback_window_df: pd.DataFrame,
    target_candle: pd.Series
) -> Optional[int]:
    """
    Get the position/index of a target candle within a DataFrame.
    
    Args:
        lookback_window_df (pd.DataFrame): Window DataFrame
        target_candle (pd.Series): Target candle row
        
    Returns:
        Optional[int]: Index position (0-based), or None if not found
    """
    # Logic: Find position of target_candle in window
```

#### Method 6: Calculate Wick Size (Uptrend)
```python
@staticmethod
def calculate_upper_wick_size(alert_candle: pd.Series) -> float:
    """
    Calculate upper wick size for uptrend (HIGH - CLOSE).
    
    Args:
        alert_candle (pd.Series): Candle with OHLC data
        
    Returns:
        float: Upper wick size
    """
    # Logic: HIGH - CLOSE
```

#### Method 7: Calculate Wick Size (Downtrend)
```python
@staticmethod
def calculate_lower_wick_size(alert_candle: pd.Series) -> float:
    """
    Calculate lower wick size for downtrend (CLOSE - LOW).
    
    Args:
        alert_candle (pd.Series): Candle with OHLC data
        
    Returns:
        float: Lower wick size
    """
    # Logic: CLOSE - LOW
```

#### Method 8: Get Window Extremes
```python
@staticmethod
def get_window_price_extremes(
    lookback_window_df: pd.DataFrame,
    window_trend: Trend
) -> dict:
    """
    Get window HIGH/LOW/CLOSE extremes based on trend.
    
    Args:
        lookback_window_df (pd.DataFrame): Full lookback window
        window_trend (Trend): UPTREND or DOWNTREND
        
    Returns:
        dict: {
            'max_high': float,
            'max_close': float,
            'min_low': float,
            'min_close': float
        }
    """
    # Logic: Return all extremes (caller determines which to use based on trend)
```

### Reused Base Methods
- `calculate_body_ratio()` - inherited, available for other uses
- `get_window_size_and_trend()` - inherited, used in Executor Step 1
- Any other base `Analyzer` methods

### Key Principles
- ✅ All methods are `@staticmethod`
- ✅ No instance variables
- ✅ Pure calculations (no side effects)
- ✅ Type hints on all parameters and returns
- ✅ Google-style docstrings with 7 sections
- ✅ Handle edge cases (division by zero, empty DataFrames, etc.)

---

## ✅ Phase 3: Validator Implementation (`validator.py`)

### File Purpose
Pure validation functions for ASC approach. All static methods, return boolean or validation status.

### Inheritance
- Inherits from base `Validator` class
- Extends with ASC-specific validations
- Can reuse base methods or add approach-specific ones

### ASC-Specific Validator Methods

#### Method 1: Validate Window Size
```python
@staticmethod
def validate_window_size(
    window_size: float,
    min_size_price_window: float
) -> bool:
    """
    Validate that window price range meets minimum threshold.
    
    Args:
        window_size (float): HIGH - LOW of window
        min_size_price_window (float): Minimum required size
        
    Returns:
        bool: True if window_size >= min_size_price_window
    """
    # Logic: return window_size >= min_size_price_window
```

#### Method 2: Validate Anchor Candle Body Size
```python
@staticmethod
def validate_anchor_candle_body(
    anchor_body_size: float,
    average_body_size: float,
    min_size_candle: float,
    multiplier_size: float
) -> bool:
    """
    Validate anchor candle meets BOTH absolute and relative thresholds.
    
    Args:
        anchor_body_size (float): MAX(HIGH - LOW) in window
        average_body_size (float): Average (HIGH - LOW) in window
        min_size_candle (float): Absolute minimum threshold
        multiplier_size (float): Relative multiplier threshold
        
    Returns:
        bool: True if passes both checks
    """
    # Logic: 
    # Check 1: anchor_body_size >= min_size_candle
    # Check 2: anchor_body_size >= (multiplier_size * average_body_size)
    # Return: Check1 AND Check2
```

#### Method 3: Validate Signal Candle Volume
```python
@staticmethod
def validate_signal_candle_volume(
    signal_volume: float,
    average_volume: float,
    min_volume: float,
    multiplier_volume: float
) -> bool:
    """
    Validate signal candle volume meets BOTH absolute and relative thresholds.
    
    Args:
        signal_volume (float): MAX(volume) in window
        average_volume (float): Average volume in window
        min_volume (float): Absolute minimum threshold
        multiplier_volume (float): Relative multiplier threshold
        
    Returns:
        bool: True if passes both checks
    """
    # Logic:
    # Check 1: signal_volume >= min_volume
    # Check 2: signal_volume >= (multiplier_volume * average_volume)
    # Return: Check1 AND Check2
```

#### Method 4: Validate Signal After Anchor
```python
@staticmethod
def validate_signal_after_anchor(
    anchor_index: int,
    signal_index: int
) -> bool:
    """
    Validate that signal candle occurs at or after anchor candle.
    
    Args:
        anchor_index (int): Position of anchor candle in window
        signal_index (int): Position of signal candle in window
        
    Returns:
        bool: True if signal_index >= anchor_index
    """
    # Logic: return signal_index >= anchor_index
```

#### Method 5: Validate Alert Candle Extremes (Uptrend)
```python
@staticmethod
def validate_alert_candle_extremes_uptrend(
    alert_candle: pd.Series,
    max_high: float,
    max_close: float
) -> bool:
    """
    Validate alert candle has highest HIGH and CLOSE (uptrend).
    
    Args:
        alert_candle (pd.Series): Alert candle row
        max_high (float): Window's maximum HIGH
        max_close (float): Window's maximum CLOSE
        
    Returns:
        bool: True if alert has both extremes
    """
    # Logic:
    # Check 1: alert_candle[HIGH] == max_high
    # Check 2: alert_candle[CLOSE] == max_close
    # Return: Check1 AND Check2
```

#### Method 6: Validate Alert Candle Extremes (Downtrend)
```python
@staticmethod
def validate_alert_candle_extremes_downtrend(
    alert_candle: pd.Series,
    min_low: float,
    min_close: float
) -> bool:
    """
    Validate alert candle has lowest LOW and CLOSE (downtrend).
    
    Args:
        alert_candle (pd.Series): Alert candle row
        min_low (float): Window's minimum LOW
        min_close (float): Window's minimum CLOSE
        
    Returns:
        bool: True if alert has both extremes
    """
    # Logic:
    # Check 1: alert_candle[LOW] == min_low
    # Check 2: alert_candle[CLOSE] == min_close
    # Return: Check1 AND Check2
```

#### Method 7: Validate Wick Percentage (Uptrend)
```python
@staticmethod
def validate_wick_percentage_uptrend(
    wick_percentage: float,
    min_percentage: float,
    max_percentage: float
) -> bool:
    """
    Validate upper wick percentage is within acceptable range (uptrend).
    
    Args:
        wick_percentage (float): (HIGH - CLOSE) / body_size
        min_percentage (float): Minimum acceptable (e.g., 0.2)
        max_percentage (float): Maximum acceptable (e.g., 0.6)
        
    Returns:
        bool: True if wick_percentage in [min, max]
    """
    # Logic: return (wick_percentage >= min_percentage) AND (wick_percentage <= max_percentage)
```

#### Method 8: Validate Wick Percentage (Downtrend)
```python
@staticmethod
def validate_wick_percentage_downtrend(
    wick_percentage: float,
    min_percentage: float,
    max_percentage: float
) -> bool:
    """
    Validate lower wick percentage is within acceptable range (downtrend).
    
    Args:
        wick_percentage (float): (CLOSE - LOW) / body_size
        min_percentage (float): Minimum acceptable (e.g., 0.2)
        max_percentage (float): Maximum acceptable (e.g., 0.6)
        
    Returns:
        bool: True if wick_percentage in [min, max]
    """
    # Logic: return (wick_percentage >= min_percentage) AND (wick_percentage <= max_percentage)
```

#### Method 9: Validate Alert Candle Body Not Zero
```python
@staticmethod
def validate_alert_candle_body_not_zero(
    alert_candle: pd.Series
) -> bool:
    """
    Validate alert candle has non-zero body (not a doji).
    
    Purpose: Prevents division by zero in wick percentage calculation.
    
    Args:
        alert_candle (pd.Series): Alert candle row with OPEN, CLOSE
        
    Returns:
        bool: True if body_size > 0, False if doji
    """
    # Logic: 
    # body_size = ABS(CLOSE - OPEN)
    # return body_size > 0
```

#### Method 10: Validate Alert After Signal
```python
@staticmethod
def validate_alert_after_signal(
    alert_index: int,
    signal_index: int
) -> bool:
    """
    Validate that alert candle occurs at or after signal candle.
    
    Args:
        alert_index (int): Position of alert candle (always last in window)
        signal_index (int): Position of signal candle in window
        
    Returns:
        bool: True if alert_index >= signal_index
    """
    # Logic: return alert_index >= signal_index
```

### Reused Base Methods
- `validate_price_threshold()` - for threshold comparisons
- `validate_ratio_threshold()` - for percentage validations
- Any other base `Validator` methods

### Key Principles
- ✅ All methods are `@staticmethod`
- ✅ No instance variables
- ✅ Pure validations (no calculations, no side effects)
- ✅ Type hints on all parameters and returns
- ✅ Google-style docstrings with 7 sections
- ✅ Return boolean or structured result
- ✅ Handle edge cases (zero division, None values, etc.)

---

## 🚀 Phase 4: Executor Implementation (`executor.py`)

### File Purpose
Orchestrate the complete ASC alert detection flow. Implements `_find_alerts()` hook from base `Executor`.

### Class Structure

```python
class AscExecutor(Executor):
    LATEST_ALERT: Optional[AlertData] = None
    
    def __init__(self, symbol: str):
        self.settings = AscSettings(symbol)
        self.analyzer = AscAnalyzer()
        self.validator = AscValidator()
        approach_name = Approach.ANCHOR_SIGNAL_CANDLE
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)
```

### Method 1: `_find_alerts()` - Main Orchestration

```python
def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    """
    Main alert-finding function for Anchor-Signal-Candle approach.
    
    Flow:
    1. Validate sufficient data
    2. Setup loop with get_loop_setup()
    3. For each scan index (reverse loop):
       a. Extract window context with set_window_context()
       b. Execute 5 validation steps
       c. Create alert if all pass
       d. Check cooldown
       e. Add to alerts list
    4. Return alerts in forward order
    """
    # Step 0: Check minimum data
    lookback_window_size = self.settings.lookback_window
    if len(df) < lookback_window_size:
        log(...)
        return self.alerts
    
    # Step 0a: Setup loop
    df_indexed, loop_start, loop_end = self.get_loop_setup(
        df=df,
        new_candle_count=new_candle_count,
        lookback_window_size=lookback_window_size
    )
    
    # Step 1: Main reverse loop
    for i in range(loop_end, loop_start - 1, -1):
        self.set_window_context(i, df_indexed, lookback_window_size)
        if self.lookback_window_df is None:
            continue
        
        # Step 2: Execute 5 validation steps
        # ... (see methods below)
        
        # Step 3: Create alert
        if alert_data is not None:
            self.alerts.append(alert_data)
            AscExecutor.LATEST_ALERT = alert_data
        
        # Step 4: Stop after first alert in production mode
        if not self.is_development_mode and len(self.alerts) >= 1:
            return self.alerts
    
    # Step 5: Return alerts in forward order
    return self.alerts[::-1]
```

### Method 2: `_step_window_validation()` - Validation 1

```python
def _step_window_validation(
    self,
    lookback_window_df: pd.DataFrame
) -> Optional[tuple[float, Trend]]:
    """
    Step 1: Window Size & Trend Determination
    
    Validates window has sufficient price range and determines trend direction.
    
    Returns:
        Tuple[float, Trend]: (window_size, trend) if passes
        None: if fails
    """
    self.next_step()
    
    # Sub-validation 1: Calculate window size
    self.next_validation()
    window_size = AscAnalyzer.calculate_window_size(lookback_window_df)
    
    # Sub-validation 2: Validate window size threshold
    self.next_validation()
    is_size_valid = self.validator.validate_window_size(
        window_size,
        self.settings.min_size_price_window
    )
    if not is_size_valid:
        log(...)
        return None
    
    # Sub-validation 3: Determine trend
    self.next_validation()
    window_size_val, window_trend = AscAnalyzer.get_window_size_and_trend(
        lookback_window_df
    )
    
    if window_trend is None:
        log(...)
        return None
    
    # Log validation pass
    self.validations.append(Validation(...))
    
    return (window_size, window_trend)
```

### Method 3: `_step_anchor_validation()` - Validation 2

```python
def _step_anchor_validation(
    self,
    lookback_window_df: pd.DataFrame
) -> Optional[pd.Series]:
    """
    Step 2: Anchor Candle Identification
    
    Finds and validates the candle with abnormally large body size.
    
    Returns:
        pd.Series: Anchor candle if passes
        None: if fails
    """
    self.next_step()
    
    # Sub-validation 1: Calculate average body size
    self.next_validation()
    average_body_size = AscAnalyzer.calculate_average_candle_body_size(
        lookback_window_df
    )
    
    # Sub-validation 2: Find anchor candle
    self.next_validation()
    anchor_candle = AscAnalyzer.find_anchor_candle(lookback_window_df)
    
    if anchor_candle is None:
        log(...)
        return None
    
    anchor_body_size = anchor_candle[CandleColumn.HIGH] - anchor_candle[CandleColumn.LOW]
    
    # Sub-validation 3: Validate anchor meets thresholds
    self.next_validation()
    is_anchor_valid = self.validator.validate_anchor_candle_body(
        anchor_body_size,
        average_body_size,
        self.settings.min_size_candle,
        self.settings.multiplier_size
    )
    
    if not is_anchor_valid:
        log(...)
        return None
    
    # Log validation pass
    self.validations.append(Validation(...))
    
    return anchor_candle
```

### Method 4: `_step_signal_validation()` - Validation 3

```python
def _step_signal_validation(
    self,
    lookback_window_df: pd.DataFrame,
    anchor_candle: pd.Series
) -> Optional[pd.Series]:
    """
    Step 3: Signal Candle Identification
    
    Finds highest-volume candle and validates it occurs at/after anchor.
    
    Returns:
        pd.Series: Signal candle if passes
        None: if fails
    """
    self.next_step()
    
    # Sub-validation 1: Calculate average volume
    self.next_validation()
    average_volume = AscAnalyzer.calculate_average_volume(lookback_window_df)
    
    # Sub-validation 2: Find signal candle (max volume in entire window)
    self.next_validation()
    signal_candle = AscAnalyzer.find_signal_candle(lookback_window_df)
    
    if signal_candle is None:
        log(...)
        return None
    
    signal_volume = signal_candle[CandleColumn.VOLUME]
    
    # Sub-validation 3: Validate signal volume thresholds
    self.next_validation()
    is_volume_valid = self.validator.validate_signal_candle_volume(
        signal_volume,
        average_volume,
        self.settings.min_volume,
        self.settings.multiplier_volume
    )
    
    if not is_volume_valid:
        log(...)
        return None
    
    # Sub-validation 4: Verify signal at or after anchor
    self.next_validation()
    anchor_index = AscAnalyzer.get_candle_index(lookback_window_df, anchor_candle)
    signal_index = AscAnalyzer.get_candle_index(lookback_window_df, signal_candle)
    
    is_signal_after_anchor = self.validator.validate_signal_after_anchor(
        anchor_index,
        signal_index
    )
    
    if not is_signal_after_anchor:
        log(...)
        return None
    
    # Log validation pass
    self.validations.append(Validation(...))
    
    return signal_candle
```

### Method 5: `_step_alert_validation()` - Validation 4

```python
def _step_alert_validation(
    self,
    lookback_window_df: pd.DataFrame,
    signal_candle: pd.Series,
    window_trend: Trend,
    window_size: float
) -> Optional[bool]:
    """
    Step 4: Alert Candle Confirmation
    
    Validates final candle has extremes and correct wick characteristics.
    
    Returns:
        bool: True if passes all checks
        None: if fails
    """
    self.next_step()
    
    alert_candle = self.last_candle
    alert_index = len(lookback_window_df) - 1
    signal_index = AscAnalyzer.get_candle_index(lookback_window_df, signal_candle)
    
    # Sub-validation 1: Verify alert after signal
    self.next_validation()
    is_alert_after_signal = self.validator.validate_alert_after_signal(
        alert_index,
        signal_index
    )
    
    if not is_alert_after_signal:
        log(...)
        return None
    
    # Sub-validation 2: Validate body not zero (doji check)
    self.next_validation()
    has_body = self.validator.validate_alert_candle_body_not_zero(alert_candle)
    
    if not has_body:
        log(...)
        return None
    
    # Sub-validation 3: Get window extremes
    self.next_validation()
    extremes = AscAnalyzer.get_window_price_extremes(
        lookback_window_df,
        window_trend
    )
    
    # Sub-validation 4: Validate price extremes (based on trend)
    self.next_validation()
    if window_trend == Trend.UPTREND:
        is_extremes_valid = self.validator.validate_alert_candle_extremes_uptrend(
            alert_candle,
            extremes['max_high'],
            extremes['max_close']
        )
    else:  # DOWNTREND
        is_extremes_valid = self.validator.validate_alert_candle_extremes_downtrend(
            alert_candle,
            extremes['min_low'],
            extremes['min_close']
        )
    
    if not is_extremes_valid:
        log(...)
        return None
    
    # Sub-validation 5: Validate wick percentage (based on trend)
    self.next_validation()
    candle_body_size = abs(alert_candle[CandleColumn.CLOSE] - alert_candle[CandleColumn.OPEN])
    
    if window_trend == Trend.UPTREND:
        wick_size = AscAnalyzer.calculate_upper_wick_size(alert_candle)
        wick_percentage = wick_size / candle_body_size
        
        is_wick_valid = self.validator.validate_wick_percentage_uptrend(
            wick_percentage,
            self.settings.min_percentage,
            self.settings.max_percentage
        )
    else:  # DOWNTREND
        wick_size = AscAnalyzer.calculate_lower_wick_size(alert_candle)
        wick_percentage = wick_size / candle_body_size
        
        is_wick_valid = self.validator.validate_wick_percentage_downtrend(
            wick_percentage,
            self.settings.min_percentage,
            self.settings.max_percentage
        )
    
    if not is_wick_valid:
        log(...)
        return None
    
    # Log validation pass
    self.validations.append(Validation(...))
    
    return True
```

### Method 6: `_step_cooldown_check()` - Inherited

Uses base class method `_step_cooldown_check()` (inherited from Executor).

### Method 7: Alert Creation

```python
def _create_alert_with_details(
    self,
    window_trend: Trend,
    window_size: float,
    anchor_candle: pd.Series,
    signal_candle: pd.Series,
    reversal_signal: Signal,
    reversal_trend: Trend
) -> Optional[AlertData]:
    """
    Create alert with ASC-specific details.
    
    Uses base class method with custom details dict.
    """
    details = {
        "window_trend": window_trend.value,
        "window_size": window_size,
        "anchor_index": AscAnalyzer.get_candle_index(self.lookback_window_df, anchor_candle),
        "signal_index": AscAnalyzer.get_candle_index(self.lookback_window_df, signal_candle),
        "alert_index": len(self.lookback_window_df) - 1,
    }
    
    return super()._create_alert_with_details(
        final_signal=reversal_signal,
        final_trend=reversal_trend,
        final_alert_candle=self.last_candle,
        final_magnitude=window_size,
        details=details
    )
```

### Method 8: Determine Reversal Signal & Trend

```python
def _get_reversal_signal_and_trend(
    self,
    original_trend: Trend
) -> tuple[Signal, Trend]:
    """
    Determine reversal signal and trend from original trend.
    
    Logic:
    - If original_trend = UPTREND → original_signal = BUY → reversal_signal = SELL, reversal_trend = DOWNTREND
    - If original_trend = DOWNTREND → original_signal = SELL → reversal_signal = BUY, reversal_trend = UPTREND
    """
    if original_trend == Trend.UPTREND:
        reversal_trend = Trend.DOWNTREND
        reversal_signal = Signal.SELL
    else:  # DOWNTREND
        reversal_trend = Trend.UPTREND
        reversal_signal = Signal.BUY
    
    return reversal_signal, reversal_trend
```

### Key Executor Principles
- ✅ Implements `_find_alerts()` abstract method
- ✅ Uses `get_loop_setup()` for loop initialization
- ✅ Uses `set_window_context()` for window extraction
- ✅ Calls `next_step()` and `next_validation()` for tracking
- ✅ Returns alerts in forward order (reverse loop, reverse result)
- ✅ Stops after first alert in production mode
- ✅ Comprehensive logging with `log()` function
- ✅ Validation tracking for alert details
- ✅ Error handling for edge cases

---

## 📦 Phase 5: Module Initialization (`__init__.py`)

```python
# src/stockreports/alert/approach/ANCHOR_SIGNAL_CANDLE/__init__.py

from .settings import AscSettings
from .analyzer import AscAnalyzer
from .validator import AscValidator
from .executor import AscExecutor

__all__ = [
    "AscSettings",
    "AscAnalyzer",
    "AscValidator",
    "AscExecutor",
]
```

---

## 🔧 Phase 6: Constants Registration

### Add to `src/stockreports/alert/common/constants.py`

```python
class Approach:
    # ... existing approaches ...
    ANCHOR_SIGNAL_CANDLE = "ANCHOR_SIGNAL_CANDLE"
```

### Add to `src/stockreports/alert/common/base_settings.py`

In the settings file where other approaches are configured, add:

```python
ANCHOR_SIGNAL_CANDLE: {
    "LOOKBACK_WINDOW": 50,
    "MIN_SIZE_PRICE_WINDOW": 0.5,
    "MIN_SIZE_CANDLE": 0.01,
    "MULTIPLIER_SIZE": 1.5,
    "MIN_VOLUME": 100000,
    "MULTIPLIER_VOLUME": 1.2,
    "MIN_PERCENTAGE": 0.2,
    "MAX_PERCENTAGE": 0.6,
    "COOLDOWN_WINDOW": 60,
}
```

---

## 🎯 Complete Implementation Checklist

### Pre-Implementation Review
- [x] All validations documented and approved
- [x] Architecture patterns understood
- [x] Base classes reviewed (Executor, Analyzer, Validator)
- [x] Existing implementations studied (VRA, STRONG_CANDLE)

### Code Generation Phase
- [ ] Phase 1: `settings.py` - 11 lines config
- [ ] Phase 2: `analyzer.py` - ~8 methods, ~300 lines
- [ ] Phase 3: `validator.py` - ~10 methods, ~350 lines
- [ ] Phase 4: `executor.py` - ~8 methods, ~600 lines
- [ ] Phase 5: `__init__.py` - ~5 lines
- [ ] Phase 6: Update constants (2 files)

### Testing & Validation
- [ ] All 100+ tests pass
- [ ] Code quality standards met (type hints, docstrings, style)
- [ ] No lint or compilation errors
- [ ] Manual verification with sample data

### Documentation
- [ ] Docstrings complete and accurate
- [ ] Architecture decisions documented
- [ ] Configuration guide created
- [ ] Testing guide created

---

## 🚀 Ready to Proceed

**Status**: ✅ **READY FOR IMPLEMENTATION**

All phases are clearly defined, architecture patterns are understood, and all clarification questions are answered.

**Next Action**: Generate code for all 5 files following this implementation plan.

