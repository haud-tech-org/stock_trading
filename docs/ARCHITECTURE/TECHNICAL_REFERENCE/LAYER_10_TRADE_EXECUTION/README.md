# Layer 10: Trade Execution Service — Technical Reference

**Purpose**: Architecture theory and design decisions for the Trade Execution Service  
**Audience**: Architects, senior developers  
**Scope**: DCA ladder + dynamic bracket lifecycle, Binance algo order design, integration patterns  
**Last Updated**: May 18, 2026

---

## 📍 Where Does This Layer Live?

```
SymbolAlerter (Layer 2)
    └─ _perform_monitoring_session / TASK-3
           │
           │  On every confirmed TRADE-type alert where:
           │    • MODE == DEPLOYMENT
           │    • alert_age ≤ TRADING_EXECUTION_EXPIRED_MINUTES (default 5 min)
           │
           ▼
    TradingServiceOrchestrator.orchestrate_bracket_order(alert, time_simulator)
    [dispatched in a daemon thread — monitoring loop never blocked]
           │
           ▼
    Layer 10: Trade Execution Service
```

The trade service is a **parallel branch** from Layer 2. It fires after notification
(Layer 7) and does not block or depend on any other layer. Each call runs in its own
daemon thread for the full DCA bracket lifecycle.

---

## 🏗️ Internal Architecture

```
src/stockreports/trade_service/
├── __init__.py
├── orchestrator.py              ← TradingServiceOrchestrator (public facade)
└── _internal/
    ├── base_trading.py          ← BaseTrading (abstract base class)
    ├── coordinator.py           ← TradingCoordinator (platform selection)
    ├── registry.py              ← TradingPlatformRegistry (symbol → platform mapping)
    ├── config/
    │   └── binance_perpetual_config.py   ← All config: endpoints, ladder, timeouts
    ├── model/
    │   └── enums.py             ← OrderType, OrderStatus, OcoOutcome, TimeInForce
    └── platforms/
        ├── binance_perpetual_trading.py  ← Live Binance implementation
        ├── mock_trading.py
        └── demo_trading.py
```

### Pattern: Facade + Registry + Strategy

| Pattern | Role | Class |
|---|---|---|
| **Facade** | Single public entry point; hides all internals | `TradingServiceOrchestrator` |
| **Registry** | Symbol → platform class mapping; extensible | `TradingPlatformRegistry` |
| **Strategy** | Per-platform order lifecycle implementation | `BinancePerpetualTrading` (implements `BaseTrading`) |

---

## 🔄 Full Lifecycle: `orchestrate_bracket_order`

### Step 1 — Leverage (once per symbol per process)
- `POST /fapi/v1/leverage` via `_ensure_leverage`
- Class-level `_leveraged_symbols` set prevents redundant calls

### Step 2 — DCA Ladder Placement
**Pre-flight guards** (all run before any order is submitted):
1. `_fetch_position_risk` — one API call shared by both guards below
2. `_close_diverged_same_side_position` — if same-side avg entry differs from new entry by > `same_side_price_level_diff` (100 USDT), close with `reduceOnly MARKET`
3. `_get_opposite_side_qty` — absorb counter-position into first order qty (no `reduceOnly` needed)
4. `_assert_sufficient_balance` — available USDT ≥ required margin × `min_balance_buffer_ratio` (1.5), or raise `ValueError`

**Order structure** (7 LIMIT orders via `POST /fapi/v1/batchOrders`):
```
Order 1: entry_price        qty = usdt_amount / entry_price
Order 2: ladder_p2          qty = usdt_amount × mult[0] / p2
Order 3: ladder_p3          qty = usdt_amount × mult[1] / p3
  ...
Order 7: ladder_p7          qty = usdt_amount × mult[5] / p7
```

**Ladder formula**:
```
entry_century = int(entry_price // 100)
BUY  → price[i] = (entry_century - offset[i]) × 100 + snap[i % 2]
SELL → price[i] = (entry_century + offset[i]) × 100 + snap[i % 2]
```

### Step 2b — Position Open Confirmation (guard before monitor)
- Poll `GET /fapi/v2/positionRisk` every `position_open_poll` (10s) up to `position_open_wait` (3600s)
- If `qty > 0`: confirmed, proceed to Step 3
- If timeout: `_cancel_ladder_orders`, return `OcoOutcome.TIMEOUT` — monitor loop never entered
- **Purpose**: ensures `oco_max_wait` clock only starts once a real position exists

### Step 3 — `_monitor_ladder` (long-running, runs inside daemon thread)

```
Phase A  — Waiting      No fills yet; poll position
Phase B  — Bracket live First fill → recalc TP/SL from avg_entry_price;
                         place TP + SL via POST /fapi/v1/algoOrder (CONDITIONAL)
Phase B′ — Re-bracket   Additional fill → cancel stale bracket; re-place
Phase C  — Timeout      elapsed ≥ ladder_order_max_wait → cancel LIMIT orders
Phase D  — OCO fires    TP FILLED → cancel SL → OcoOutcome.TP_FILLED
                        SL FILLED → cancel TP → OcoOutcome.SL_FILLED
Exit     — No orders    No open LIMIT + no open TP/SL → break loop
Safety   — oco_max_wait → cancel all; close position with MARKET; TIMEOUT
```

**Option B behaviour**: OCO fill does NOT cancel surviving LIMIT ladder orders. They remain open,
can fill later, and trigger another bracket re-placement on the next qty-change cycle.

---

## ⚠️ Key Binance API Design Constraints

| Constraint | Reason | Solution |
|---|---|---|
| TP/SL via `/fapi/v1/algoOrder` only | `/fapi/v1/order` returns -4120 for these types | All bracket orders use algo endpoint |
| Manual `urlencode` for signed requests | `params=` in `requests.get` reorders dict, invalidates HMAC | All GET/DELETE use `url + "?" + urlencode(params)` |
| `algoId` ≠ `orderId` | Algo orders use different ID field | `TradeResult.from_algo_response` maps `algoId → order_id` |
| `-2011` on cancel = success | Order already gone (idempotent) | Treated as success in `_cancel_algo_order` |
| `-2021` on placement | Market already past `triggerPrice` | Returns `WOULD_TRIGGER`; bracket resolved inline |
| Server time sync | Local clock drift causes -1021 | `_fetch_server_time_offset` at startup; all timestamps use `_now_ms()` |

---

## 🔌 Integration Points with Other Layers

| From | To | How |
|---|---|---|
| Layer 2 (`SymbolAlerter`) | Layer 10 (`TradingServiceOrchestrator`) | `trading_orchestrator.orchestrate_bracket_order(alert, time_simulator)` — fires in daemon thread |
| Layer 9 (`settings.py`) | Layer 10 | `TRADING_EXECUTION_EXPIRED_MINUTES` — expiry guard before dispatch |
| Layer 2 (`TimeSimulator`) | Layer 10 (`_monitor_ladder`) | `time_simulator.advance()` drives replay; `time.sleep()` drives live |
| `AlertData` model | Layer 10 | `alert.symbol`, `alert.signal`, `alert.alert_price` drive order params |
| `BINANCE_PERPETUAL_CONFIG` | Layer 10 | All endpoints, ladder params, timeouts — single source of truth |

---

## 📐 Design Principles

- **Non-blocking**: daemon thread ensures monitoring loop always continues regardless of trade lifecycle duration
- **Expiry guard**: stale alerts (> `TRADING_EXECUTION_EXPIRED_MINUTES`) are silently skipped — no stale trades on reconnect
- **USDT-based sizing**: `qty = order_usdt_amount / price` — consistent exposure across all price levels and multipliers
- **Dynamic bracket**: TP/SL recalculated from actual avg fill price on every qty change — never from stale entry assumptions
- **Config-driven**: zero magic numbers in trading logic; all parameters in `BINANCE_PERPETUAL_CONFIG`
- **Uniform result type**: every order action returns `TradeResult`; errors return `TradeResult(status="ERROR")`

---

## 📚 Related Documentation

- **Full BinancePerpetualTrading reference** → [`BINANCE_PERPETUAL_TRADING_REFERENCE.md`](./BINANCE_PERPETUAL_TRADING_REFERENCE.md)
- **Implementation guide** → [`IMPLEMENTATION_GUIDES/LAYER_10_TRADE_EXECUTION/README.md`](../../IMPLEMENTATION_GUIDES/LAYER_10_TRADE_EXECUTION/README.md)
- **System integration** → [`SYSTEM_ARCHITECTURE_OVERVIEW.md`](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) — Layer 10 block
- **Settings** → `src/stockreports/config/settings.py` — `TRADING_EXECUTION_EXPIRED_MINUTES`
- **Config** → `src/stockreports/trade_service/_internal/config/binance_perpetual_config.py`
