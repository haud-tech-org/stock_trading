# Executor Pattern Reference (Layer 2 - Technical Reference)

**Tier:** Technical Reference (Layer 2)
**Purpose:** Deep-dive on the executor pattern, symbol-centric configuration, session handling, and DRY model-driven design as of the 2026 refactor.

---

## Overview

This document provides a technical reference for the executor pattern as it applies to symbol-level orchestration. It covers:
- Symbol-centric configuration
- TradingHoursConfig and List[Session]
- TimeSimulator abstraction
- How executors interact with symbol/session/resolution logic

---

## 2026 Symbol-Centric Configuration & Session Handling

Executors now operate within a symbol-centric, model-driven configuration. Each symbol has its own TradingHoursConfig, List[Session], and approach mapping. The monitoring loop is driven by a TimeSimulator abstraction, supporting both LIVE and REPLAY modes in a DRY, maintainable way.

**Key Points:**
- All configuration (thresholds, windows, trading hours, sessions) is loaded per-symbol from a central config model.
- Executors receive only the data for the current symbol/session/resolution, as orchestrated by the parent SymbolAlerter and ResolutionCoordinator.
- The monitoring loop respects session boundaries and time progression via TimeSimulator.
- This enables deterministic backtesting and robust live operation with minimal code duplication.

---

## References
- See SYSTEM_ARCHITECTURE_OVERVIEW.md for the complete system flow.
- See CONFIGURATION_SERVICE/TRADING_HOURS_AND_MULTI_APPROACH_EXECUTION.md for deep-dive on configuration/session logic.
