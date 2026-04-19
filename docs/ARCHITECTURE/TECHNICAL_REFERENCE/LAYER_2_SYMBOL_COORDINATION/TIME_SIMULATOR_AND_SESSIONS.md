# TimeSimulator & Session Model Integration (Layer 2)

**Layer:** 2 (Symbol Coordination)
**Tier:** Technical Reference
**Status:** Complete, 2026 Refactor

---

## Summary

The `TimeSimulator` class now uses a list of `Session` model objects for all session handling, ensuring type safety, validation, and consistency. This change is a core part of the symbol-centric, DRY configuration architecture.

---

## Key Implementation Details

- `TimeSimulator.sessions` is now always a `List[Session]`, not a dict or JSON.
- Sessions are validated at initialization via `Session.__post_init__()`.
- All session logic (start/end, iteration, validation) uses model methods.
- The change is fully backward compatible and transparent to users.

---

## Example: Initialization

```python
# With TradingHoursConfig (preferred)
trading_hours = ExecutorConfigurationOrchestrator.get_symbol_trading_hours(symbol)
simulator = TimeSimulator(
    replay_start_str="2026-04-17 09:00:00",
    interval_seconds=60,
    trading_hours=trading_hours
)

# Fallback (global settings)
simulator = TimeSimulator(
    replay_start_str=None,
    interval_seconds=60
)
```

---

## Benefits

- Type safety: All sessions are model objects
- Validation: Bad session data is caught early
- Consistency: Unified model across all layers
- Maintainability: Clear, DRY, and extensible

---

## See Also
- `ARCHITECTURE_TRANSFORMATION.md` (for the big picture)
- `LIST_SESSIONS_OPTIMIZATION.md` (for rationale and performance)
