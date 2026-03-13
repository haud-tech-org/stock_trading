# Executor: Implement vs. Override - Quick Reference Card

**Quick Answer:** In Executor classes, IMPLEMENT `_find_alerts()`, do NOT override `run()`

---

## One-Sentence Summary

Derived Executor classes must **implement** the abstract `_find_alerts()` method (approach-specific logic) and **inherit** the concrete `run()` method (framework orchestration).

---

## Decision Tree

```
Are you creating a derived Executor class?
│
├─ YES → Continue
└─ NO → Skip this

Should I override the run() method?
│
├─ "My approach needs custom orchestration"
│  └─ WAIT! → Ask architecture team → Almost always the answer is NO
│
├─ "I need to implement the abstract method"
│  └─ YES! → Implement _find_alerts() → CORRECT PATTERN
│
└─ "I see RCM overrides run()"
   └─ RCM IS THE EXCEPTION → Don't follow this pattern → Requires approval
```

---

## The Two Methods at a Glance

### `run()` - Concrete Method in Base Class

```python
# Base Executor class
def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    try:
        log("Starting...")
        alerts_data = self._find_alerts(df, new_candle_count)  # Call the hook
        log("Complete!")
        return AlertResult(...)  # Return formatted result
    except Exception as e:
        log("Error!")
        return AlertResult(status="FAILED")
```

**In your derived executor:**
```python
# ❌ DO NOT DO THIS
def run(self, df, new_candle_count):
    # Your custom code
    pass

# ✅ DO THIS (don't define it, just use the inherited one)
# Executor.run() will automatically call your _find_alerts()
```

---

### `_find_alerts()` - Abstract Method in Base Class

```python
# Base Executor class
@abstractmethod
def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    pass  # Abstract - must be implemented by derived class
```

**In your derived executor:**
```python
# ✅ DO THIS - implement the abstract method
def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
    """Your approach-specific alert detection logic."""
    alerts = []
    loop_setup = self.get_loop_setup(df, new_candle_count)
    
    for index in range(loop_setup.start_index, loop_setup.end_index):
        self.set_window_context(df, index, ...)
        if self._step_validation_one():
            alerts.append(self._create_alert(...))
    
    return alerts
```

---

## Comparison Table

| Aspect | `run()` | `_find_alerts()` |
|--------|---------|-----------------|
| **Type** | Concrete | Abstract |
| **Location** | Base Executor | Base Executor |
| **Your Action** | Inherit (don't override) | Implement (must) |
| **Purpose** | Framework orchestration | Approach-specific logic |
| **Error Handling** | Automatic (in base) | Your responsibility |
| **Logging** | Automatic (in base) | Call self.next_step() |
| **Input** | df, new_candle_count | df, new_candle_count |
| **Output** | AlertResult | list[AlertData] |
| **Calls** | Calls _find_alerts() | Called by run() |

---

## Code Pattern Template

### ✅ CORRECT Pattern

```python
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.approach.MY_APPROACH.settings import MySettings
from src.stockreports.alert.common.constants import Approach

class MyExecutor(Executor):
    def __init__(self, symbol: str):
        self.settings = MySettings(symbol)
        approach_name = Approach.MY_APPROACH
        super().__init__(symbol, approach_name, self.settings)
        self.logger = logging.getLogger(__name__)
    
    # ✅ Implement abstract method
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """Approach-specific logic."""
        alerts = []
        loop_setup = self.get_loop_setup(df, new_candle_count)
        
        for index in range(loop_setup.start_index, loop_setup.end_index):
            self.current_step += 1
            self.set_window_context(df, index, lookback_period=20)
            
            if self._step_my_validation():
                alert = self._create_alert(...)
                alerts.append(alert)
        
        return alerts
    
    def _step_my_validation(self) -> bool:
        self.next_validation()
        # Your validation logic
        return True
```

### ❌ WRONG Pattern

```python
class MyExecutor(Executor):
    # ❌ WRONG: Overriding concrete method
    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """This should NOT be here!"""
        alerts = self._find_alerts(df, new_candle_count)
        return AlertResult(...)
    
    def _find_alerts(self, df, new_candle_count):
        return []
```

---

## Example from Codebase

### VRA Executor ✅ CORRECT

```python
class VraExecutor(Executor):
    def __init__(self, symbol: str):
        self.settings = VraSettings(symbol)
        super().__init__(symbol, Approach.VRA, self.settings)
        self.logger = logging.getLogger(__name__)
    
    # ✅ Implements _find_alerts() only
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        alerts = []
        loop_setup = self.get_loop_setup(df, new_candle_count)
        
        for index in range(loop_setup.start_index, loop_setup.end_index):
            self.set_window_context(df, index, lookback_period=...)
            
            if self._step_volume_validation():
                if self._step_trend_and_magnitude_validation():
                    if self._step_cooldown_check(...):
                        alert = self._step_create_alert_with_details(...)
                        alerts.append(alert)
        
        return alerts
    
    def _step_volume_validation(self) -> bool:
        self.next_validation()
        # VRA-specific validation
        return True
    
    # No run() method - uses inherited from Executor
```

---

## Checklist: Creating a New Executor

- [ ] Class extends `Executor`: `class MyExecutor(Executor)`
- [ ] Constructor defined with `super().__init__(...)`
- [ ] Settings instance created: `self.settings = MySettings(symbol)`
- [ ] Approach name set: `approach_name = Approach.MY_APPROACH`
- [ ] ✅ `_find_alerts()` method implemented
- [ ] ✅ Custom `_step_*()` methods implemented
- [ ] ✅ Uses `get_loop_setup()` inherited method
- [ ] ✅ Uses `set_window_context()` inherited method
- [ ] ✅ Calls `self.next_step()` and `self.next_validation()`
- [ ] ❌ NO `run()` method override
- [ ] ❌ NO duplicated error handling
- [ ] ❌ NO duplicated logging code

---

## FAQ

**Q: What if I need different error handling?**
A: You don't. Base `run()` handles all errors. If you think you need different handling, talk to architecture team.

**Q: What if my approach needs custom logging?**
A: Add logging inside your `_find_alerts()` or `_step_*()` methods. Base `run()` handles framework logging.

**Q: Can I call `run()` directly?**
A: Yes, that's the intended use: `alerts = my_executor.run(df, new_candle_count)`

**Q: Will `run()` call my `_find_alerts()`?**
A: Yes, automatically. Base `run()` calls `self._find_alerts()` which dispatches to your implementation.

**Q: What's the RCM exception?**
A: RCM Executor is the ONLY documented exception that overrides `run()`. This was necessary due to special requirements. Any new override needs architecture team approval.

**Q: Where do I put validation steps?**
A: Create `_step_*()` methods inside your executor. Call them from `_find_alerts()`.

---

## Related Documents

📄 **EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md** - Complete detailed explanation  
📄 **DESIGN_PATTERNS_GUIDE.md** - Pattern context and variations  
📄 **ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md** - ABC overview  
📄 **DOCUMENTATION_CORRECTION_SUMMARY.md** - What was corrected

---

## Key Takeaway

When creating a derived Executor class:

1. **Implement** `_find_alerts()` - Put your approach-specific logic here
2. **Inherit** `run()` - Let the framework handle orchestration
3. **Never** override `run()` - Unless you're the RCM exception with approval

That's it. That's the pattern.

