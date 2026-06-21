# Logging Level Rules - Strict Enforcement Guide

**Status**: ✅ VERIFIED - June 21, 2026

---

## The Rule (STRICT)

```
┌─────────────────────────────────────────────────────────────────┐
│                    LOGGING LEVEL RULES                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  VALIDATION FAILURE (Expected behavior):                        │
│  ├─ When condition fails → LogLevel.DEBUG                       │
│  ├─ Example: "Price range below threshold"                      │
│  └─ NOT logged as error (normal filtering in production)        │
│                                                                 │
│  EXCEPTION (Unexpected behavior):                               │
│  ├─ When try/except catches exception → LogLevel.ERROR          │
│  ├─ Example: f"Momentum validation failed - {str(e)}"           │
│  └─ MUST be logged as error (proper alerting)                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Pattern (From DOJI_ANCHOR)

### Pattern Template

```python
def _step_validate_something(self, ...) -> bool:
    """Validate something."""
    self.next_validation()
    try:
        # Perform validation
        is_valid = self.validator.validate_something(...)
        
        if not is_valid:
            # RULE 1: Validation failure → LogLevel.DEBUG
            log(
                logger=self.logger,
                status=ValidationStatus.FAILED,
                name=self.__class__.__name__,
                alert_time=self.current_window_end_time,
                step=self.current_step,
                validation=self.validation_step,
                message="Condition not met",
                log_level=LogLevel.DEBUG,  # ← ALWAYS DEBUG for validation failures
                execution_symbol=self.symbol,
                approach=self.APPROACH_NAME
            )
            return False
        
        # Success: append validation and return True
        self.validations.append(Validation(...))
        return True
        
    except Exception as e:
        # RULE 2: Exception → LogLevel.ERROR
        log(
            logger=self.logger,
            status=ValidationStatus.FAILED,
            name=self.__class__.__name__,
            alert_time=self.current_window_end_time,
            step=self.current_step,
            validation=self.validation_step,
            message=f"Operation failed - {str(e)}",
            log_level=LogLevel.ERROR,  # ← ALWAYS ERROR for exceptions
            execution_symbol=self.symbol,
            approach=self.APPROACH_NAME
        )
        return False
```

---

## Verified Implementation (DOJI_ANCHOR)

### Rule 1: Validation Failures → DEBUG

**Location**: `executor.py` _step_* methods (validation failures)

**Examples**:

1. **Line 152** (_step_find_doji - no doji found):
   ```python
   log(..., message="No doji found with body_ratio <= ...", log_level=LogLevel.DEBUG)
   ```

2. **Line 203** (_step_prepare_candles - no doji):
   ```python
   log(..., message="No doji found during candle preparation", log_level=LogLevel.DEBUG)
   ```

3. **Line 225** (_step_prepare_candles - anchor discovery failed):
   ```python
   log(..., message="Failed to discover anchor with trend for doji at ...", log_level=LogLevel.DEBUG)
   ```

4. **Line 275** (_step_validate_momentum - momentum failed):
   ```python
   log(..., message="Momentum validation failed: price move below ...", log_level=LogLevel.DEBUG)
   ```

5. **Line 317** (_step_validate_trend_candle - trend_idx is None):
   ```python
   log(..., message="Trend candle validation failed: trend_candle_idx is None", log_level=LogLevel.DEBUG)
   ```

6. **Line 339** (_step_validate_trend_candle - validation failed):
   ```python
   log(..., message="Trend candle validation failed at index ...", log_level=LogLevel.DEBUG)
   ```

7. **Line 393** (_step_validate_alert_candle - validation failed):
   ```python
   log(..., message="Alert candle validation failed at index ..., trend=...", log_level=LogLevel.DEBUG)
   ```

**Count**: 7 validation failures → all use LogLevel.DEBUG ✅

---

### Rule 2: Exceptions → ERROR

**Location**: `executor.py` _step_* methods (exception handlers)

**Examples**:

1. **Line 174** (_step_find_doji exception):
   ```python
   except Exception as e:
       log(..., message=f"Doji detection failed - {str(e)}", log_level=LogLevel.ERROR)
   ```

2. **Line 250** (_step_prepare_candles exception):
   ```python
   except Exception as e:
       log(..., message=f"Candle preparation failed - {str(e)}", log_level=LogLevel.ERROR)
   ```

3. **Line 297** (_step_validate_momentum exception):
   ```python
   except Exception as e:
       log(..., message=f"Momentum validation failed - {str(e)}", log_level=LogLevel.ERROR)
   ```

4. **Line 362** (_step_validate_trend_candle exception):
   ```python
   except Exception as e:
       log(..., message=f"Trend candle validation failed - {str(e)}", log_level=LogLevel.ERROR)
   ```

5. **Line 415** (_step_validate_alert_candle exception):
   ```python
   except Exception as e:
       log(..., message=f"Alert candle validation failed - {str(e)}", log_level=LogLevel.ERROR)
   ```

**Count**: 5 exceptions → all use LogLevel.ERROR ✅

---

### Also: Pre-step Data Preparation (Line 48)

**Location**: `_find_alerts` method (data preparation failure)
```python
log(..., message=f"Not enough data for ...: requires ..., have ...", log_level=LogLevel.DEBUG)
```

**Reasoning**: This is a data requirement check (expected behavior), not an exception → DEBUG ✅

---

## Verification Summary

| Method | Validation Failures | Exceptions | Status |
|--------|-------------------|-----------|--------|
| _step_find_doji | 1 × DEBUG | 1 × ERROR | ✅ |
| _step_prepare_candles | 2 × DEBUG | 1 × ERROR | ✅ |
| _step_validate_momentum | 1 × DEBUG | 1 × ERROR | ✅ |
| _step_validate_trend_candle | 2 × DEBUG | 1 × ERROR | ✅ |
| _step_validate_alert_candle | 1 × DEBUG | 1 × ERROR | ✅ |
| **TOTAL** | **7 × DEBUG** | **5 × ERROR** | **✅** |

---

## Why This Matters

### LogLevel.DEBUG for Validation Failures

**Why**:
- Validation failures are **expected behavior** (normal filtering)
- Not every candle passes validation
- Production systems want to filter out these routine messages
- DEBUG level suppression is standard practice

**Result in Production**:
- Validation failures NOT displayed (filtered)
- Cleaner logs, easier to spot real issues

### LogLevel.ERROR for Exceptions

**Why**:
- Exceptions are **unexpected behavior** (bugs or data corruption)
- Must be surfaced to monitoring/alerting
- Developers need to know something went wrong
- ERROR level ensures visibility

**Result in Production**:
- Exceptions ALWAYS displayed (never filtered)
- Proper alerting through monitoring systems
- Debugging starts immediately

---

## Implementation Checklist

### When Implementing a New Approach

- [ ] **Every validation method** has TRY/EXCEPT
- [ ] **Validation failures** (if not is_valid) → LogLevel.DEBUG
- [ ] **Exceptions** (except Exception) → LogLevel.ERROR
- [ ] **Pre-step checks** (expected failures) → LogLevel.DEBUG
- [ ] **Never mix**: Don't use ERROR for validation failures
- [ ] **Never mix**: Don't use DEBUG for exceptions

### Code Review Checklist

```python
# ✅ CORRECT - Pattern to verify
def _step_validate_xyz(...) -> bool:
    self.next_validation()
    try:
        is_valid = self.validator.validate_xyz(...)
        if not is_valid:
            log(..., log_level=LogLevel.DEBUG)  # ← Validation failure
            return False
        self.validations.append(...)
        return True
    except Exception as e:
        log(..., log_level=LogLevel.ERROR)  # ← Exception
        return False

# ❌ WRONG - Don't do this
except Exception as e:
    log(..., log_level=LogLevel.DEBUG)  # ❌ Should be ERROR

# ❌ WRONG - Don't do this
if not is_valid:
    log(..., log_level=LogLevel.ERROR)  # ❌ Should be DEBUG
```

---

## Quick Reference

| Scenario | Log Level | Context |
|----------|-----------|---------|
| Validation returns False | DEBUG | Normal filtering |
| Validation raises exception | ERROR | Unexpected issue |
| Data insufficient (expected) | DEBUG | Normal check |
| Data corruption (unexpected) | ERROR | Exceptional case |
| Price threshold not met | DEBUG | Expected failure |
| Calculator throws error | ERROR | Unexpected failure |
| Candle doesn't match pattern | DEBUG | Expected result |
| Invalid data format | ERROR | Unexpected result |

---

## Documentation References

Updated with strict logging rules:

1. **DOJI_ANCHOR_SIGNAL_CANDLE_IMPLEMENTATION_PLAN.md** § 3.4
   - Logging pattern documented
   - Exception handling explained

2. **APPROACH_GENERATION_REFINE_SUMMARY.md** § Code Quality Standards
   - 📖 Location: `/docs/references/TEMPLATES/APPROACH_GENERATION_TEMPLATE/APPROACH_GENERATION_REFINE_SUMMARY.md`
   - Logging pattern with examples
   - ERROR vs DEBUG distinction

3. **AI_APPROACH_GENERATION_PROMPT.md** § Critical Executor Implementation Patterns
   - 📖 Location: `/docs/references/PROMPTS/APPROACH_GENERATION_CODE/AI_APPROACH_GENERATION_PROMPT.md`
   - Private step methods pattern
   - Logging levels strictly defined

---

## Files Verified

- ✅ `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/executor.py`
  - 7 validation failures → all DEBUG
  - 5 exceptions → all ERROR
  - 1 pre-check → DEBUG
  - Total: 100% compliance

---

**Status**: ✅ COMPLETE

**Verified**: June 21, 2026

**Implementation**: DOJI_ANCHOR_SIGNAL_CANDLE (637 lines of code)

**Rules**: STRICT - No exceptions, no deviations

**Enforcement**: Code review checklist provided
