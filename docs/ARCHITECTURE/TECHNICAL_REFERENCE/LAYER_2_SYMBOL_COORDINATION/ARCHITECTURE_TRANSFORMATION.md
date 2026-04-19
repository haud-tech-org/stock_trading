# Architecture Transformation: Symbol-Centric Configuration (Layer 2)

**Layer:** 2 (Symbol Coordination)
**Tier:** Technical Reference
**Status:** Complete, 2026 Refactor

---

## Executive Summary

This document summarizes the 2026 transformation to a symbol-centric, DRY, model-driven configuration for trading hours, sessions, and approach orchestration. It is the authoritative reference for how symbol-level configuration, session handling, and the TimeSimulator now work in the system.

---

## Configuration Flow

```
ExecutorConfigurationOrchestrator.get_symbol_trading_hours(symbol)
    └─→ TradingHoursConfig
        ├── name: "CRYPTO_24H"
        ├── timezone: "Asia/Ho_Chi_Minh"
        ├── sessions: [Session(...), ...]
        └── trading_days: [0, 1, 2, 3, 4, 5, 6]
            └─→ TimeSimulator(trading_hours=trading_hours_config)
                    └─ Uses timezone, sessions, and trading_days directly

(Separate: get(symbol, approach) returns ApproachSymbolConfiguration)
    └─→ ApproachSymbolConfiguration
        ├── symbol
        ├── approach
        ├── resolution          ← Approach-level only
        └── approach_config     ← Approach-level only
```

---

## Symbol Alerter Initialization

```
approaches_to_run = get_supported_approaches(symbol)
trading_hours = get_symbol_trading_hours(symbol)  # Direct, symbol-level
TimeSimulator(trading_hours=trading_hours)
```

---

## Data Model

```
BTC/USDT:USDT
├── trading_hours: CRYPTO_24H     ← Single copy (symbol-level)
│
├── Approach 1: REVERSAL_ANCHOR_SIGNAL_CANDLE
│   ├── resolution: 15
│   └── approach_config: {...}
│
├── Approach 2: VRA
│   ├── resolution: 1
│   └── approach_config: {...}
│
└── Approach N: [...]
    ├── resolution: X
    └── approach_config: {...}
```

---

## Method Signatures

```python
def __init__(self, 
             replay_start_str: Optional[str], 
             interval_seconds: int,
             trading_hours: Optional[TradingHoursConfig] = None):
    # param trading_hours: Only what's needed
    # Direct use: trading_hours.timezone, trading_hours.sessions, trading_hours.trading_days
```

---

## Orchestrator API

```python
# Direct access to symbol's trading hours:
trading_hours = ExecutorConfigurationOrchestrator.get_symbol_trading_hours(symbol)
```

---

## Dependency Graph

```
TimeSimulator
    └─ depends on: TradingHoursConfig
        ├─ uses: timezone
        ├─ uses: sessions
        └─ uses: trading_days

symbol_alerter._perform_monitoring_session
    ├─ calls: ExecutorConfigurationOrchestrator.get_symbol_trading_hours(symbol)
    │   └─ returns: TradingHoursConfig
    └─ passes: trading_hours → TimeSimulator
```

---

## Summary

- Symbol-level trading hours are now the single source of truth for all approaches.
- TimeSimulator and all consumers use only the data they need: timezone, sessions, trading_days.
- No redundant config loading or data duplication.
- Architecture is DRY, clear, and maintainable.

---

**See also:**
- `TIME_SIMULATOR_REFACTOR_COMPLETE.md` (for implementation details)
- `LIST_SESSIONS_OPTIMIZATION.md` (for session structure rationale)
