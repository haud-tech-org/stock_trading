# Executor Implementation Guide (Layer 2 - Implementation Guide)

**Tier:** Implementation Guide (Layer 2)
**Purpose:** Practical guide for implementing executors in the context of symbol-centric configuration and session handling (2026+).

---

## Overview

This guide explains how to implement a new executor (trading strategy) under the 2026 symbol-centric, model-driven architecture. It covers:
- How to use TradingHoursConfig and List[Session]
- How to interact with TimeSimulator
- How to ensure your executor is compatible with both LIVE and REPLAY modes

---

## Implementation Steps

1. **Inherit from the Executor base class**
2. **Implement the _find_alerts() method**
3. **Use per-symbol configuration for thresholds, windows, and trading hours**
4. **Respect session boundaries and time progression via TimeSimulator**
5. **Test in both LIVE and REPLAY modes**

---

## References
- See TECHNICAL_REFERENCE/LAYER_2_SYMBOL_COORDINATION/EXECUTOR_PATTERN_REFERENCE.md for technical details.
- See CONFIGURATION_SERVICE/TRADING_HOURS_AND_MULTI_APPROACH_EXECUTION.md for configuration/session logic.
