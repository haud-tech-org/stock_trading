---
# Trading Hours & Multi-Approach Execution (2026 Symbol-Centric Refactor)

**Status:** Draft (2026 refactor, symbol-centric configuration)
**Purpose:** Deep dive into how trading hours, sessions, and approach execution are now handled per symbol using DRY, model-driven design.

---

## 🧩 Key Concepts

- **TradingHoursConfig**: Defines all trading sessions for a symbol, including timezone and session boundaries.
- **List[Session]**: Each symbol can have multiple sessions per day (e.g., stocks: morning/afternoon; crypto: 24/7).
- **TimeSimulator**: Abstracts time progression for both LIVE (real-time) and REPLAY (deterministic) modes.
- **Approach Mapping**: Each symbol's config specifies which approaches run at which resolutions.

---

## 🔄 How It Works (2026+)

1. **Configuration Loading**: On startup, the system loads all symbol configs, each with its own TradingHoursConfig and List[Session].
2. **Session Handling**: For each session, the monitoring loop only runs when the session is active (respects market open/close).
3. **Time Simulation**: TimeSimulator ensures correct time progression for both LIVE and REPLAY, using session boundaries.
4. **Approach Execution**: For each active session, all configured approaches are executed at their mapped resolutions.
5. **DRY Model-Driven Logic**: All logic is centralized in model classes, reducing duplication and improving maintainability.

---

## 📝 Example: Symbol Config (VN30F1M)

```python
symbol_config = SymbolConfig(
    symbol="VN30F1M",
    trading_hours=TradingHoursConfig(
        sessions=[
            Session(start="09:00", end="11:30"),
            Session(start="13:00", end="15:00"),
        ],
        timezone="Asia/Ho_Chi_Minh",
    ),
    approaches=[...],
)
```

---

## 🔗 References

- See `TECHNICAL_REFERENCE/LAYER_2_SYMBOL_COORDINATION/README.md` for symbol-level orchestration details.
- See `SYSTEM_ARCHITECTURE_OVERVIEW.md` for the complete system flow.

---

**Last Updated:** April 19, 2026