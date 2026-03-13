# Executor Abstract Method Principle

**Status:** ✅ CRITICAL PRINCIPLE CLARIFICATION  
**Date:** March 12, 2026  
**Priority:** HIGH - Architectural Foundation  
**Applies To:** All derived Executor classes

---

## The Core Principle

> **In derived Executor classes, developers ONLY IMPLEMENT the abstract method `_find_alerts()`. They do NOT OVERRIDE the concrete method `run()`.**

### Distinction: Implementation vs. Override

This distinction is fundamental to understanding the Template Method pattern used throughout the codebase.

| Concept | `run()` | `_find_alerts()` |
|---------|---------|-----------------|
| **Type** | Concrete method | Abstract method |
| **Location** | Base `Executor` class | Base `Executor` class |
| **Derived Classes Should** | ❌ **NOT override** | ✅ **MUST implement** |
| **Purpose in Base** | Orchestrates entire flow | Serves as customization hook |
| **Override Reason** | NEVER (except RCM exception) | Always - to provide approach logic |
| **What It Means** | Inheritance | Implementation of abstraction |

---

## Visual Comparison

### ❌ WRONG - Overriding `run()` (Anti-pattern)

```python
class MyExecutor(Executor):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.MY_APPROACH, MySettings(symbol))
    
    # ❌ BAD: Overriding concrete method
    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """This should NOT be here!"""
        alerts = self._find_alerts(df, new_candle_count)
        return AlertResult(approach_name=self.APPROACH_NAME, alerts=...)
    
    def _find_alerts(self, df, new_candle_count):
        return []
```

**Problems with this approach:**
- Loses base class orchestration logic
- Breaks consistency with other executors
- Duplicates error handling code
- Loses standardized logging
- Makes maintenance harder
- RCM is the ONLY documented exception

---

### ✅ CORRECT - Implementing `_find_alerts()` (Proper Pattern)

```python
class MyExecutor(Executor):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.MY_APPROACH, MySettings(symbol))
    
    # ✅ GOOD: Implementing abstract method only
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """Implements the hook method with approach-specific logic."""
        alerts = []
        loop_setup = self.get_loop_setup(df, new_candle_count)
        
        for index in range(loop_setup.start_index, loop_setup.end_index):
            self.set_window_context(df, index, lookback_period=...)
            
            if self._step_my_validation_one():
                if self._step_my_validation_two():
                    alerts.append(self._create_alert(...))
        
        return alerts
    
    def _step_my_validation_one(self) -> bool:
        """Custom validation step."""
        self.next_validation()
        # Implementation
        return result
```

**Benefits of this approach:**
- ✅ Uses base class `run()` method
- ✅ Consistent with all other executors
- ✅ Error handling automatically managed
- ✅ Logging standardized
- ✅ Clean separation of concerns
- ✅ Easy to maintain

---

## What Each Method Does

### `run()` - Base Class Concrete Method

**Location:** `src/stockreports/alert/executor.py` (lines 47-80)

**Responsibility:** Orchestration and framework

```python
def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Template method that coordinates the entire alert-finding process.
    DO NOT OVERRIDE IN DERIVED CLASSES.
    """
    try:
        # 1. Log execution start
        log(logger=self.logger, status=ValidationStatus.PASSED, ...)
        
        # 2. Call the hook method (_find_alerts) - overridden by derived class
        alerts_data = self._find_alerts(df, new_candle_count)
        
        # 3. Log results
        log(logger=self.logger, status=ValidationStatus.PASSED, ...)
        
        # 4. Format output
        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])
        gc.collect()
        
        # 5. Return standardized result
        return AlertResult(
            approach_name=self.APPROACH_NAME,
            alerts=alerts_df,
            confirmed_alerts=alerts_data
        )
    except Exception as e:
        # Error handling (should not be duplicated!)
        self.logger.error(f"Error: {e}", exc_info=True)
        gc.collect()
        return AlertResult(approach_name=self.APPROACH_NAME, 
                          alerts=pd.DataFrame(), 
                          status="FAILED", 
                          message=str(e))
```

**Why NOT override:**
- Handles standardized logging for all approaches
- Manages error handling consistently
- Ensures garbage collection
- Provides consistent return format
- Acts as the "template" in Template Method pattern

---

### `_find_alerts()` - Base Class Abstract Method

**Location:** `src/stockreports/alert/executor.py`

**Responsibility:** Approach-specific alert detection logic

```python
@abstractmethod
def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    """
    Hook method for derived classes.
    MUST BE IMPLEMENTED by all derived executor classes.
    
    Returns list of alerts found using approach-specific logic.
    """
    pass
```

**Why MUST be implemented:**
- Abstract method requires implementation in concrete classes
- Each approach has unique validation logic
- This is the customization point for different strategies
- Framework ensures all executors have this method

---

## Real-World Examples from Codebase

### Example 1: VRA Executor ✅ CORRECT

**File:** `src/stockreports/alert/approach/VRA/executor.py`

```python
class VraExecutor(Executor):
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        approach_name = Approach.VRA
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    # ✅ Implements abstract method (does NOT override run())
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """VRA-specific alert detection logic."""
        alerts = []
        # VRA implementation
        loop_setup = self.get_loop_setup(df, new_candle_count)
        for index in range(loop_setup.start_index, loop_setup.end_index):
            self.set_window_context(df, index, ...)
            if self._step_volume_validation():
                if self._step_trend_and_magnitude_validation():
                    if self._step_cooldown_check(...):
                        alert = self._step_create_alert_with_details(...)
                        alerts.append(alert)
        return alerts

    def _step_volume_validation(self) -> bool:
        """VRA-specific step."""
        # Implementation
        pass

    # ... other _step_* methods
```

**Verification:**
- ❌ Does NOT have `def run(...)` - **Uses inherited**
- ✅ HAS `def _find_alerts(...)` - **Implements abstract method**
- ✅ Uses `self.get_loop_setup()` - **Inherited utility**
- ✅ Uses `self.set_window_context()` - **Inherited utility**
- ✅ Implements `_step_*()` methods - **Approach-specific steps**

---

### Example 2: CONSISTENT_MOMENTUM Executor ✅ CORRECT

**File:** `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py`

```python
class ConsistentMomentumExecutor(Executor):
    """Executor for the Consistent Momentum approach."""
    LATEST_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        self.settings = ConsistentMomentumSettings(symbol)
        approach_name = Approach.CONSISTENT_MOMENTUM
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)

    # ✅ Implements abstract method (does NOT override run())
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """Consistent Momentum alert detection logic."""
        alerts = []
        # CM implementation with anchor-point detection
        loop_setup = self.get_loop_setup(df, new_candle_count)
        for index in range(loop_setup.start_index, loop_setup.end_index):
            self.set_window_context(df, index, ...)
            if self._step_determine_signal_from_color():
                if self._step_find_anchor_candle():
                    if self._step_extract_confirmation_window():
                        # More validations...
                        alert = self._create_alert(...)
                        alerts.append(alert)
        return alerts

    def _step_determine_signal_from_color(self) -> bool:
        """CM-specific step."""
        pass

    # ... other _step_* methods
```

**Verification:**
- ❌ Does NOT have `def run(...)` - **Uses inherited**
- ✅ HAS `def _find_alerts(...)` - **Implements abstract method**
- ✅ Uses `self.get_loop_setup()` - **Inherited utility**
- ✅ Uses `self.set_window_context()` - **Inherited utility**
- ✅ Implements custom `_step_*()` methods - **Approach-specific logic**

---

### Example 3: RCM Executor ⚠️ DOCUMENTED EXCEPTION

**File:** `src/stockreports/alert/approach/RCM/executor.py`

```python
class RcmExecutor(Executor):
    """RCM executor with custom run() override."""
    
    def __init__(self, symbol: str):
        self.settings = RcmSettings(symbol)
        approach_name = Approach.RCM
        super().__init__(symbol, approach_name, self.settings)
    
    # ⚠️ EXCEPTION: RCM overrides run() for special requirements
    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """Custom implementation needed for RCM workflow."""
        # RCM-specific orchestration
        pass
    
    def _find_alerts(self, df, new_candle_count):
        # Also implements _find_alerts
        pass
```

**Why RCM is an exception:**
- RCM has fundamentally different execution requirements
- Cannot fit standard Template Method pattern
- Requires custom orchestration logic
- **This is the ONLY documented exception in the codebase**
- Any new executor that needs to override `run()` MUST:
  1. Document the reason clearly
  2. Include comprehensive comments
  3. Explain why standard pattern doesn't work
  4. Get architectural review

---

## The Template Method Pattern Explained

The base `Executor` class implements the **Template Method design pattern**:

```
Template Method Pattern
=======================

┌────────────────────────────────────────────────────┐
│ Executor Base Class                                │
│                                                    │
│ def run(df, new_candle_count):                    │
│   1. Log start ─────────────────┐                 │
│   2. Call _find_alerts() ──┐    │ Fixed template  │
│   3. Log results ──────────┼────┤ (never changes) │
│   4. Format output ────────┤    │                 │
│   5. Return result ────────┤    │                 │
│   6. Handle errors    ─────┘    │                 │
│                                │                 │
│ @abstractmethod                 │                 │
│ def _find_alerts():             │                 │
│   # Customization hook ◄────────┘                 │
│   pass                                            │
└────────────────────────────────────────────────────┘
         ▲
         │ Inherits run()
         │ Implements _find_alerts()
         │
┌────────┴─────────────────────────────────────────┐
│ Derived Executor Classes                         │
│                                                  │
│ VraExecutor:                                     │
│   def _find_alerts():  ← VRA-specific logic     │
│     # Volume validation                          │
│     # Trend validation                           │
│     # Cooldown check                             │
│                                                  │
│ ConsistentMomentumExecutor:                      │
│   def _find_alerts():  ← CM-specific logic      │
│     # Anchor candle detection                    │
│     # Momentum validation                        │
│     # Volume consistency                         │
│                                                  │
│ ... (16 more approaches)                         │
└──────────────────────────────────────────────────┘
```

**How It Works:**
1. User calls: `vra_executor.run(df, new_candle_count)`
2. Base `run()` executes (inherited from base class)
3. Base `run()` logs the start
4. Base `run()` calls `self._find_alerts(df, new_candle_count)`
5. Derived class's `_find_alerts()` executes (VRA-specific logic)
6. Result returns to base `run()`
7. Base `run()` logs completion and returns `AlertResult`

**Benefits:**
- ✅ Consistent logging across all approaches
- ✅ Consistent error handling
- ✅ Consistent output format
- ✅ Each approach only implements its unique logic
- ✅ Easy to understand the pattern
- ✅ Easy to add new approaches

---

## Implementation Checklist

When creating a new derived Executor class:

- [ ] Class inherits from `Executor`: `class MyExecutor(Executor)`
- [ ] Constructor calls `super().__init__(symbol, approach_name, settings)`
- [ ] Settings instance created: `self.settings = MySettings(symbol)`
- [ ] Approach name set: `approach_name = Approach.MY_APPROACH`
- [ ] ❌ **DO NOT** override `run()` method
- [ ] ✅ **DO** implement `_find_alerts()` method
- [ ] ✅ Use inherited `get_loop_setup()` for loop boundaries
- [ ] ✅ Use inherited `set_window_context()` for window extraction
- [ ] ✅ Implement custom `_step_*()` validation methods
- [ ] ✅ Call `self.next_step()` for step tracking
- [ ] ✅ Call `update_alert_suggestions()` before returning alerts
- [ ] ✅ Return `list[AlertData]` from `_find_alerts()`

---

## Common Mistakes to Avoid

### ❌ Mistake 1: Overriding `run()`

```python
class BadExecutor(Executor):
    def run(self, df, new_candle_count):  # ❌ WRONG!
        # Custom orchestration
        alerts = self._find_alerts(df, new_candle_count)
        return AlertResult(...)
    
    def _find_alerts(self, df, new_candle_count):
        pass
```

**Problem:** Loses base class benefits (logging, error handling)  
**Fix:** Remove the `run()` override

---

### ❌ Mistake 2: Not Implementing `_find_alerts()`

```python
class BadExecutor(Executor):
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.BAD, BadSettings(symbol))
    
    # ❌ Missing _find_alerts() implementation
    # This will cause: TypeError: Can't instantiate abstract class
```

**Problem:** `_find_alerts()` is abstract and must be implemented  
**Fix:** Add the `_find_alerts()` method

---

### ❌ Mistake 3: Duplicating Base Methods

```python
class BadExecutor(Executor):
    def _find_alerts(self, df, new_candle_count):
        alerts = []
        
        # ❌ Duplicating base method logic
        loop_setup = self.get_loop_setup(df, new_candle_count)
        loop_setup = self._my_custom_get_loop_setup(df, new_candle_count)
        
        # This creates confusion and maintenance issues
        pass
```

**Problem:** Duplicate code and inconsistency  
**Fix:** Use inherited `get_loop_setup()` directly

---

## Terminology Clarification

| Term | Meaning | Example |
|------|---------|---------|
| **Abstract Method** | Method declared in base class but not implemented (marked with `@abstractmethod`). Derived classes MUST implement it. | `_find_alerts()` in base `Executor` |
| **Implementation** | Writing the actual code body for an abstract method in a derived class. | VRA's `_find_alerts()` implementation |
| **Override** | Replacing a concrete method from base class with a new version in derived class. Usually not recommended unless necessary. | RCM's override of `run()` (exception case) |
| **Concrete Method** | Method with a full implementation in base class. Derived classes inherit it (can override but shouldn't usually). | `run()` in base `Executor` |
| **Inherit** | Derived class automatically gets all methods from base class. Can use them without re-declaring. | VRA inherits `run()` from `Executor` |

---

## Related Documentation

- **Executor Inheritance Pattern Analysis:** `/docs/ARCHITECTURE/EXECUTOR_INHERITANCE_PATTERN_ANALYSIS.md`
- **Design Patterns Guide:** `/docs/ARCHITECTURE/DESIGN_PATTERNS_GUIDE.md`
- **Abstract Base Classes Implementation:** `/docs/ARCHITECTURE/ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md`
- **Master Reference Documentation:** `/docs/MASTER_REFERENCE_DOCUMENTATION.md`

---

## Summary

| What | How | When | Why |
|-----|-----|------|-----|
| **Implement `_find_alerts()`** | Write the method body | Always | It's an abstract method that must be implemented |
| **Override `run()`** | Replace the inherited method | Never (except RCM) | Base class `run()` provides essential orchestration |
| **Inherit `run()`** | Don't declare it, just use it | Always | Base class method handles logging, errors, formatting |
| **Use `get_loop_setup()`** | Call the inherited method | Always | Provides standardized loop boundary calculation |

---

## Revision History

| Date | Change | Author |
|------|--------|--------|
| 2025-03-12 | Created clarification document for abstract method principle | Code Review |
| 2025-03-12 | Emphasized distinction between "implement" vs "override" | Architectural Guidance |
| 2025-03-12 | Added RCM exception documentation | Pattern Exception |

