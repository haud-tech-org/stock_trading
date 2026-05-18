# BinancePerpetualTrading — Full Technical Reference

**Layer**: 10 — Trade Execution Service  
**Location**: `docs/ARCHITECTURE/TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/`  
**Scope**: Complete method map, config reference, lifecycle diagrams, and API usage for `BinancePerpetualTrading`  
**See also**: [`README.md`](./README.md) for architecture theory and integration overview  
_Last updated: 2026-05-18_

---

## Overview

The `trade_service` module provides a clean, extensible, and centralized API for trading operations against Binance USDT-margined perpetual futures. It is structured around the **facade**, **registry**, and **strategy** patterns, with all internal logic hidden under `_internal/`.

The primary strategy implemented is a **DCA (Dollar-Cost Averaging) ladder** with a **dynamic bracket** (Take-Profit + Stop-Loss as a conditional algo OCO pair). The bracket automatically re-sizes whenever additional ladder orders fill and is only torn down once all open orders are gone.

---

## Module Structure

```
src/stockreports/trade_service/
├── __init__.py
├── orchestrator.py                     # TradingServiceOrchestrator — public API
└── _internal/
    ├── base_trading.py                 # BaseTrading — abstract base class
    ├── coordinator.py                  # TradingCoordinator — platform selection
    ├── registry.py                     # TradingPlatformRegistry — platform lookup
    ├── config/
    │   └── binance_perpetual_config.py # All config (endpoints, ladder, TP/SL, timeouts)
    ├── model/
    │   └── enums.py                    # OrderType, OrderStatus, OcoOutcome, TimeInForce, …
    └── platforms/
        ├── binance_perpetual_trading.py # BinancePerpetualTrading — live implementation
        ├── mock_trading.py
        └── demo_trading.py
```

---

## Key Components

| Component | Role |
|---|---|
| `TradingServiceOrchestrator` | Public facade. Accepts `AlertData`, delegates to `TradingCoordinator`. |
| `TradingCoordinator` | Selects the correct platform instance for a symbol via `TradingPlatformRegistry`. |
| `TradingPlatformRegistry` | Singleton registry mapping symbols → platform instances. |
| `BaseTrading` | Abstract base. All platforms must implement `place_order(alert) -> List[TradeResult]`. |
| `BinancePerpetualTrading` | Full live implementation — DCA ladder + dynamic bracket lifecycle. |
| `BINANCE_PERPETUAL_CONFIG` | Single source of truth for all endpoints, ladder params, and timeouts. |
| `enums.py` | `OrderType`, `TimeInForce`, `PositionSide`, `OrderStatus`, `OcoOutcome`. |
| `TradeResult` | Unified result object returned from every order action. |

---

## Enums Reference (`enums.py`)

### `OrderType` (used for order placement)
| Value | Usage |
|---|---|
| `LIMIT` | All DCA ladder entry orders |
| `TAKE_PROFIT_MARKET` | TP bracket leg — placed as a conditional algo order via `/fapi/v1/algoOrder` |
| `STOP_MARKET` | SL bracket leg — placed as a conditional algo order via `/fapi/v1/algoOrder` |
| `MARKET` | Used for `reduceOnly` position close orders (diverged same-side close, timeout close) |

### `OrderStatus`
`NEW` · `PARTIALLY_FILLED` · `FILLED` · `CANCELED` · `REJECTED` · `EXPIRED` · `WORKING` _(algo order active)_ · `WOULD_TRIGGER` _(-2021: triggerPrice already met at placement)_ · `UNKNOWN` _(fallback when query fails)_

### `OcoOutcome`
| Value | Meaning |
|---|---|
| `TP_FILLED` | Take-profit hit; stop-loss cancelled |
| `SL_FILLED` | Stop-loss hit; take-profit cancelled |
| `EXTERNAL_TERMINAL` | One leg cancelled/expired externally; non-terminal leg cancelled |
| `TIMEOUT` | Overall safety timeout elapsed; all orders cancelled, open position closed |

---

## Configuration (`binance_perpetual_config.py`)

### Endpoints
| Key | Value |
|---|---|
| `base_url` | `https://fapi.binance.com` |
| `demo_base_url` | `https://demo-fapi.binance.com` |
| `use_demo` | `True` (toggle to switch between live and demo) |
| `order_endpoint` | `/fapi/v1/order` (single orders and `_query_order` / `_cancel_order`) |
| `batch_orders_endpoint` | `/fapi/v1/batchOrders` (place ≤5 / cancel ≤10 per call) |
| `open_orders_endpoint` | `/fapi/v1/openOrders` (regular LIMIT orders) |
| `position_risk_endpoint` | `/fapi/v2/positionRisk` |
| *(inline)* | `/fapi/v1/algoOrder` (algo TP/SL — place, query, cancel) |
| *(inline)* | `/fapi/v1/openAlgoOrders` (list open conditional algo orders) |
| *(inline)* | `/fapi/v2/balance` (available USDT balance check) |
| *(inline)* | `/fapi/v1/leverage` (set symbol leverage) |
| *(inline)* | `/fapi/v1/time` (server clock sync at startup) |

### USDT-Based Quantity Sizing
All order quantities are derived at runtime from a USDT amount rather than a fixed coin count:

```
order_1 qty  = round(order_usdt_amount / entry_price,            qty_precision)
order_N qty  = round(order_usdt_amount × multiplier[N] / price_N, qty_precision)
```

| Key | Default | Description |
|---|---|---|
| `order_usdt_amount` | `200.0` | USDT value per individual LIMIT order (order 1 × 1; orders 2–N × their multiplier) |
| `qty_precision` | `3` | Decimal places to round computed qty (BTCUSDT lot size = 3 dp) |

### Ladder Config
| Key | Default | Description |
|---|---|---|
| `ladder_qty_multipliers` | `[2,2,3,3,4,4]` | Per-rung multiplier; also sets number of ladder orders (6 additional + 1 entry = 7 total) |
| `ladder_buy_century_offsets` | `[1,1,5,5,6,6]` | Century steps **down** from entry for BUY |
| `ladder_sell_century_offsets` | `[1,1,5,5,6,6]` | Century steps **up** from entry for SELL |
| `ladder_buy_snaps` | `[54, 16]` | Last-2-digit price snap, alternates by index (`i % 2`) |
| `ladder_sell_snaps` | `[68, 94]` | Last-2-digit price snap, alternates by index (`i % 2`) |
| `ladder_order_max_wait` | `2000 s` | Seconds before unfilled LIMIT orders are cancelled inside `_monitor_ladder` |

### Timing & Pricing
| Key | Default | Description |
|---|---|---|
| `poll_interval` | `2 s` | Sleep between monitor loop cycles |
| `oco_max_wait` | `4000 s` | Overall safety timeout for the monitor loop |
| `tp_price_diff` | `300.0` | Absolute USDT offset above/below avg entry for TP |
| `sl_price_diff` | `500.0` | Absolute USDT offset below/above avg entry for SL |
| `price_precision` | `1` | Decimal places for TP/SL `triggerPrice` (BTCUSDT tick = 0.1 → 1 dp) |
| `default_leverage` | `20` | Leverage applied before each ladder placement |

### Balance & Position Guards
| Key | Default | Description |
|---|---|---|
| `min_balance_buffer_ratio` | `1.5` | Available USDT must be ≥ 50% above required margin before submitting ladder |
| `same_side_price_level_diff` | `100.0` | If existing same-side avg entry diverges from new entry by this many USDT, close it first |

### Position Open Confirmation
| Key | Default | Description |
|---|---|---|
| `position_open_wait` | `3600 s` | Max seconds to wait for at least one ladder fill to open a position before aborting (step 2b) |
| `position_open_poll` | `10 s` | Poll interval while waiting for the position to open |

---

## `BinancePerpetualTrading` — Method Map

### Instance setup

| Item | Description |
|---|---|
| `self.logger` | `logging.getLogger(self.__class__.__name__)` — instance-level, subclass-friendly |
| `self.use_demo` | Set inline at `__init__` from config; drives initial `base_url` selection |
| `self.base_url` | Set inline at `__init__` (`demo_base_url` if `use_demo`, else `base_url`). Re-assigned at the top of `orchestrate_bracket_order` via `_resolve_base_url(time_simulator)` so the correct endpoint is locked in for the full orchestration run. |
| `self.api_key` | Set inline at `__init__` from config |
| `self.api_secret` | Set inline at `__init__` from config |
| `self._server_time_offset_ms` | Set once at `__init__` via `GET /fapi/v1/time`; corrects all subsequent `_now_ms()` calls |
| `_leveraged_symbols` | Class-level `set` — leverage is applied only once per symbol per process lifetime |

### Public methods

| Method | Signature | Description |
|---|---|---|
| `orchestrate_bracket_order` | `(alert, tp_price?, sl_price?, time_simulator?) → dict` | Main entry point. Ensures leverage, places DCA ladder, waits for a position to open (step 2b), then runs monitor loop. Returns `{"main": List[TradeResult], "oco_outcome": OcoOutcome}`. `tp_price`/`sl_price` args accepted for API compat but unused — TP/SL are recalculated from actual avg fill price. If no position opens within `position_open_wait`, cancels all ladder orders and returns `OcoOutcome.TIMEOUT` immediately. |
| `place_order` | `(alert) → List[TradeResult]` | Derives USDT-based quantities, runs pre-flight guards (diverged same-side close, balance check), builds all ladder order dicts, submits via `_place_orders_batch`. |

### Private helpers — Order placement

| Method | Signature | Description |
|---|---|---|
| `_build_ladder_levels` | `(entry_price, signal) → List[(price, qty)]` | Computes (price, qty) for orders 2–N using century-offset + snap formula. qty = `(order_usdt_amount × multiplier) / price`. |
| `_place_orders_batch` | `(symbol, order_dicts) → List[TradeResult]` | Chunks order dicts into ≤5 per call → `POST /fapi/v1/batchOrders`. |
| `_place_tp_sl_batch` | `(symbol, qty, tp, sl, side) → (TradeResult, TradeResult)` | Places TAKE_PROFIT_MARKET + STOP_MARKET as conditional algo orders via `POST /fapi/v1/algoOrder`. Handles `-2021` (WOULD_TRIGGER) on either leg symmetrically. |
| `_place_algo_order` | `(order_dict) → TradeResult` | Single conditional algo order via `POST /fapi/v1/algoOrder`. Returns `WOULD_TRIGGER` on -2021, `ERROR` on other failures. |
| `_place_single_order` | `(order_dict) → TradeResult` | Single regular order via `POST /fapi/v1/order`. Used for `reduceOnly` MARKET close orders. |

### Private helpers — Cancellation

| Method | Signature | Description |
|---|---|---|
| `_cancel_orders_by_ids` | `(symbol, ids, caller) → int` | `DELETE /fapi/v1/batchOrders` in chunks of 10. Returns count cancelled. |
| `_cancel_tp_sl_orders` | `(symbol) → int` | Fetches open algo orders, cancels all `TAKE_PROFIT_MARKET` + `STOP_MARKET` legs. |
| `_cancel_ladder_orders` | `(symbol) → int` | Cancels all open `LIMIT` orders (unfilled ladder rungs) via `_cancel_orders_by_ids`. |
| `_cancel_order` | `(symbol, order_id) → bool` | `DELETE /fapi/v1/order` — single regular order cancel. |
| `_cancel_algo_order` | `(symbol, algo_id) → bool` | `DELETE /fapi/v1/algoOrder` — single algo order cancel. Treats -2011 ("already gone") as success. |

### Private helpers — Queries

| Method | Signature | Description |
|---|---|---|
| `_fetch_open_orders` | `(symbol) → List[dict]` | `GET /fapi/v1/openOrders` — regular LIMIT orders. |
| `_fetch_open_algo_orders` | `(symbol) → List[dict]` | `GET /fapi/v1/openAlgoOrders?algoType=CONDITIONAL` — TP/SL algo orders. |
| `_fetch_position_risk` | `(symbol) → List[dict]` | `GET /fapi/v2/positionRisk` — raw position list. Shared by all position helpers; called exactly once per `place_order`. |
| `_get_position_info` | `(symbol) → (qty, avg_entry_price)` | Calls `_fetch_position_risk`; raises `RuntimeError` if request fails, `ValueError` if no non-zero position. |
| `_get_open_limit_order_ids` | `(symbol) → List[int]` | `orderId` list of all open LIMIT orders. |
| `_get_open_tp_sl_order_ids` | `(symbol) → List[int]` | `algoId` list of all open TP/SL algo orders. |
| `_query_order` | `(symbol, order_id) → Optional[TradeResult]` | `GET /fapi/v1/order` — snapshot of a regular order. |
| `_query_algo_order` | `(symbol, algo_id) → Optional[TradeResult]` | `GET /fapi/v1/algoOrder?algoId=...` — snapshot of an algo order. Normalises `CANCELLED` → `CANCELED`, `WORKING` → `NEW`. Signs manually via `urlencode` (not `params=`) to preserve HMAC byte order. |
| `_fetch_available_balance` | `(asset="USDT") → float` | `GET /fapi/v2/balance` — returns `availableBalance` for the asset. |

### Private helpers — Position guards

| Method | Signature | Description |
|---|---|---|
| `_get_opposite_side_qty` | `(signal, positions) → float` | Returns abs qty of any counter-position (to be absorbed into first ladder order). |
| `_get_same_side_position` | `(signal, positions) → (qty, avg_entry_price)` | Returns qty + avg price of any same-side position, or `(0.0, 0.0)`. |
| `_close_diverged_same_side_position` | `(symbol, signal, entry_price, positions)` | If same-side avg entry diverges from `entry_price` by > `same_side_price_level_diff`, issues a `reduceOnly MARKET` close before placing the new ladder. |
| `_assert_sufficient_balance` | `(symbol, order_dicts)` | Raises `ValueError` if available USDT < total required margin × `min_balance_buffer_ratio`. |

### Private helpers — Infrastructure

| Method | Signature | Description |
|---|---|---|
| `_ensure_leverage` | `(symbol)` | Calls `_set_leverage` once per symbol per process (class-level dedup via `_leveraged_symbols`). |
| `_set_leverage` | `(symbol, leverage)` | `POST /fapi/v1/leverage` — retries up to 3 times. |
| `_resolve_base_url` | `(time_simulator?) → None` | Re-assigns `self.use_demo`, `self.api_key`, `self.api_secret`, and `self.base_url`. Called only from `orchestrate_bracket_order` (not `__init__`) so the `time_simulator` context is available. Priority: (1) `use_demo=True` → `demo_base_url`; (2) replay mode → `base_url`; (3) default → `base_url`. |
| `_sign_params` | `(params) → params` | HMAC-SHA256 signature injection; removes stale signature before recomputing. |
| `_build_headers` | `(content_type?) → dict` | Builds `X-MBX-APIKEY` headers; omits `Content-Type` for GET/DELETE. |
| `_fetch_server_time_offset` | `() → int` | `GET /fapi/v1/time` at startup; returns ms offset between server and local clock. |
| `_now_ms` | `() → int` | `int(time.time() * 1000) + _server_time_offset_ms` — all signed requests use this. |

---

## Full Lifecycle: `orchestrate_bracket_order`

```
  CALLER                    BinancePerpetualTrading               BINANCE EXCHANGE
  ──────                    ───────────────────────               ────────────────
  orchestrate_bracket_order(alert, time_simulator?)
      │
      │── _ensure_leverage ──────────────────────────────────────────────────────
      │   (skipped if symbol already in _leveraged_symbols set)
      │   _set_leverage(symbol, 20) ───────────────────────────► POST /fapi/v1/leverage
      │
      │── resolve entry_price ─────────────────────────────────────────────────
      │   get_primary_suggested_price(alert) || alert.alert_price
      │
      │── place_order(alert) ──────────────────────────────────────────────────
      │       │
      │       ├─ base_qty = round(order_usdt_amount / entry_price, qty_precision)
      │       │
      │       ├─ _fetch_position_risk(symbol) ──────────────────► GET /fapi/v2/positionRisk
      │       │   (one call, passed to both guards below)
      │       │
      │       ├─ _close_diverged_same_side_position(...)
      │       │   if |same_side_avg - entry_price| > same_side_price_level_diff:
      │       │       _place_single_order(reduceOnly MARKET) ───► POST /fapi/v1/order
      │       │
      │       ├─ _get_opposite_side_qty → first_qty = base_qty + opposite_qty
      │       │
      │       ├─ _assert_sufficient_balance
      │       │   available < required_margin × 1.5 → raise ValueError (abort)
      │       │
      │       ├─ build order_dicts (order 1 @ entry, orders 2–7 from _build_ladder_levels)
      │       │
      │       └─ _place_orders_batch ────────────────────────────► POST /fapi/v1/batchOrders ×2
      │               → List[TradeResult]
      │
      │   Exchange state after placement:
      │   ┌────────────────────────────────────────────────────────────────────┐
      │   │  LIMIT #1 @ entry_price        qty = usdt/price        status=NEW  │
      │   │  LIMIT #2 @ ladder_p2          qty = usdt×2/p2         status=NEW  │
      │   │  LIMIT #3 @ ladder_p3          qty = usdt×2/p3         status=NEW  │
      │   │  LIMIT #4 @ ladder_p4          qty = usdt×3/p4         status=NEW  │
      │   │  LIMIT #5 @ ladder_p5          qty = usdt×3/p5         status=NEW  │
      │   │  LIMIT #6 @ ladder_p6          qty = usdt×4/p6         status=NEW  │
      │   │  LIMIT #7 @ ladder_p7          qty = usdt×4/p7         status=NEW  │
      │   └────────────────────────────────────────────────────────────────────┘
      │
      │── step 2b: wait for position to open ───────────────────────────────────
      │       Poll _get_position_info every position_open_poll (10s)
      │       up to position_open_wait (3600s).
      │
      │       each poll cycle:
      │           if time_simulator.is_replay_mode(): time_simulator.advance()
      │           else: time.sleep(position_open_poll)
      │           _get_position_info(symbol)
      │               qty > 0  → position_confirmed = True; break
      │               ValueError → no fill yet; keep polling
      │               RuntimeError → log warning; keep polling
      │
      │       position_confirmed = False after timeout:
      │           _cancel_ladder_orders(symbol)
      │           return { "main": ladder_results, "oco_outcome": TIMEOUT }
      │
      └─ _monitor_ladder(symbol, signal, time_simulator?)
             │
             │  ═══════════════════════ MONITOR LOOP ═══════════════════════
             │  live mode:   time.sleep(poll_interval=2s) each cycle
             │  replay mode: time_simulator.advance() + elapsed from sim clock
             │
             │  ── Phase A: Waiting for fills ────────────────────────────
             │
             │  cycle N: _get_position_info → ValueError (nothing filled)
             │  │         current_qty=0, no bracket → skip OCO check
             │  │         open_limits=[#1…#7]  open_tp_sl=[] → continue
             │  │
             │  ·  ·  ·  (LIMIT #1 fills on exchange)
             │  │
             │  cycle N+k: current_qty > 0 ≠ last_qty=0
             │  │          ┌── qty changed! ───────────────────────────────┐
             │  │          │  _cancel_tp_sl_orders (none yet)              │
             │  │          │  recalc tp/sl from avg_entry_price            │
             │  │          │  _place_tp_sl_batch ─────────────────────────► POST /fapi/v1/algoOrder ×2
             │  │          │  ◄──────────────────────────────────────────── [TP #8, SL #9]
             │  │          │  last_qty = current_qty                       │
             │  │          └───────────────────────────────────────────────┘
             │  │
             │  │   Exchange state:
             │  │   ┌──────────────────────────────────────────────────────────┐
             │  │   │  LIMIT  #1  FILLED                                       │
             │  │   │  LIMIT  #2…#7  still NEW                                 │
             │  │   │  ALGO   #8  TAKE_PROFIT_MARKET  @ tp_price  WORKING      │
             │  │   │  ALGO   #9  STOP_MARKET         @ sl_price  WORKING      │
             │  │   └──────────────────────────────────────────────────────────┘
             │  │
             │  ── Phase B: Bracket live — poll LIMIT + algo TP/SL ───────
             │
             │  cycle N+k+1:
             │  │   ③ OCO check:
             │  │       _query_algo_order(#8) → WORKING/NEW  → no action
             │  │       _query_algo_order(#9) → WORKING/NEW  → no action
             │  │
             │  ·  ·  ·  (LIMIT #2 fills, qty increases)
             │  │
             │  cycle N+m: current_qty ≠ last_qty
             │  │          ┌── qty changed again! ─────────────────────────┐
             │  │          │  _cancel_tp_sl_orders(#8, #9) ────────────────► DELETE /fapi/v1/algoOrder ×2
             │  │          │  recalc tp/sl from new avg_entry_price         │
             │  │          │  _place_tp_sl_batch ─────────────────────────► POST /fapi/v1/algoOrder ×2
             │  │          │  ◄──────────────────────────────────────────── [TP #10, SL #11]
             │  │          └───────────────────────────────────────────────┘
             │  │
             │  ── Phase C: Timeout — cancel remaining LIMIT rungs ───────
             │
             │  cycle T: elapsed ≥ ladder_order_max_wait (2000s)
             │  │        _cancel_ladder_orders() ──────────────────────────► DELETE /fapi/v1/batchOrders
             │  │        ladder_cancelled = True
             │  │
             │  ── Phase D: OCO resolution ─────────────────────────────
             │
             │  ·  ·  ·  (price reaches tp_price — algo TP #10 fills)
             │  │
             │  cycle T+j: _query_algo_order(#10) → FILLED
             │  │           _cancel_algo_order(#11) ──────────────────────► DELETE /fapi/v1/algoOrder
             │  │           oco_outcome = TP_FILLED
             │  │           tp_result = sl_result = None
             │  │
             │  │           open_limits=[]  open_tp_sl=[] → BREAK
             │  │
             │  ══════════════════ loop exits ════════════════════════════
             │
  ◄──────────── return { "main": List[TradeResult], "oco_outcome": TP_FILLED }
```

### Lifecycle Phases Summary

| Phase | Trigger | Action |
|---|---|---|
| **2b — Position confirm** | After ladder placement, before monitor loop | Poll `_get_position_info` every `position_open_poll` (10s) up to `position_open_wait` (3600s); abort with `TIMEOUT` if no fill |
| **A — Waiting** | Loop start, no position | Poll position; no bracket yet |
| **B — Bracket live** | First LIMIT fills → qty > 0 | Recalculate TP/SL from `avg_entry_price`; place TP+SL algo orders |
| **B′ — Re-bracket** | Additional LIMIT fills → qty increases | Cancel stale bracket; re-place with updated qty and freshly computed TP/SL |
| **Immediate trigger** | `WOULD_TRIGGER` on `_place_tp_sl_batch` | Resolve bracket outcome inline, skip next poll |
| **C — Timeout** | `elapsed ≥ ladder_order_max_wait` | Cancel all remaining LIMIT orders |
| **D — OCO fires** | TP or SL algo `FILLED` | Cancel the other leg; record `oco_outcome` |
| **External terminal** | Either leg `CANCELED`/`EXPIRED` externally | Cancel non-terminal leg; record `EXTERNAL_TERMINAL` |
| **Exit** | No LIMIT + no TP/SL algo open | Break loop; return `oco_outcome` |
| **Safety** | `elapsed ≥ oco_max_wait` | Cancel everything; close open position with MARKET; return `TIMEOUT` |

---

## Core Loop: `_monitor_ladder`

```
Config: poll_interval=2s  |  ladder_order_max_wait=2000s  |  oco_max_wait=4000s

State:  last_qty=0.0, tp_result=None, sl_result=None,
        oco_outcome=None, ladder_cancelled=False

Time control:
  is_replay = time_simulator is not None and time_simulator.is_replay_mode()
  REPLAY → elapsed = (time_simulator.get_current_time() - loop_start).total_seconds()
            time_simulator.advance()  [instead of time.sleep]
  LIVE   → elapsed += poll_interval after each time.sleep(poll_interval)

┌─ Loop (every poll_interval) ──────────────────────────────────────────────────┐
│                                                                               │
│  ① LIMIT timeout                                                              │
│     if not ladder_cancelled and elapsed ≥ ladder_order_max_wait:             │
│         _cancel_ladder_orders(symbol)                                         │
│         ladder_cancelled = True                                               │
│                                                                               │
│  ② Position qty tracking                                                      │
│     (qty, avg_entry_price) = _get_position_info(symbol)                      │
│         ValueError  → (0.0, 0.0)   [no open position]                        │
│         RuntimeError → keep last_qty  [query failed, no spurious reset]      │
│                                                                               │
│     if current_qty != last_qty and current_qty > 0:                          │
│         tp_price = avg_entry ± tp_price_diff                                 │
│         sl_price = avg_entry ∓ sl_price_diff                                 │
│         _cancel_tp_sl_orders(symbol)                                          │
│         tp, sl = _place_tp_sl_batch(symbol, current_qty, tp, sl, side)       │
│         last_qty = current_qty                                                │
│         oco_outcome = None                                                    │
│                                                                               │
│         Immediate-trigger guard:                                              │
│           tp.status == WOULD_TRIGGER → cancel SL; oco = TP_FILLED            │
│           sl.status == WOULD_TRIGGER → cancel TP; oco = SL_FILLED            │
│                                                                               │
│  ③ Inline OCO check  (only when bracket is active)                           │
│     tp_status = _query_algo_order(tp_result.order_id).status                 │
│     sl_status = _query_algo_order(sl_result.order_id).status                 │
│                                                                               │
│     TP FILLED          → cancel SL algo        → oco = TP_FILLED             │
│     SL FILLED          → cancel TP algo        → oco = SL_FILLED             │
│     Either terminal    → cancel non-terminal   → oco = EXTERNAL_TERMINAL     │
│                                                                               │
│  ④ Exit condition                                                             │
│     if _get_open_limit_order_ids() == [] and                                 │
│        _get_open_tp_sl_order_ids() == []: break                              │
│                                                                               │
│  ⑤ Safety timeout                                                            │
│     if elapsed ≥ oco_max_wait:                                               │
│         _cancel_ladder_orders + _cancel_tp_sl_orders                         │
│         if open position → _place_single_order(reduceOnly MARKET)            │
│         return OcoOutcome.TIMEOUT                                             │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘

Return: oco_outcome  (TP_FILLED | SL_FILLED | EXTERNAL_TERMINAL | TIMEOUT)
```

**Option B behaviour**: when a bracket OCO fires, surviving LIMIT ladder orders are deliberately left open. If any subsequent rung fills, the loop detects the qty increase at step ②, recalculates TP/SL from the new `avg_entry_price`, places a fresh bracket, and continues monitoring.

---

## DCA Ladder Price Formula

```
entry_century = int(entry_price // 100)

BUY  ladder (steps DOWN):
    price[i] = (entry_century - buy_century_offsets[i]) * 100 + buy_snaps[i % 2]

SELL ladder (steps UP):
    price[i] = (entry_century + sell_century_offsets[i]) * 100 + sell_snaps[i % 2]

qty[i] = round((order_usdt_amount × ladder_qty_multipliers[i]) / price[i], qty_precision)
```

Example — BUY entry at 97,412 USDT (`entry_century = 974`, `order_usdt_amount = 200`):

| Rung | Offset | Century | Snap (`i%2`) | Price | Multiplier | USDT | Qty (3 dp) |
|---|---|---|---|---|---|---|---|
| 1 (entry) | — | 974 | — | 97,412 | ×1 | 200 | 0.002 |
| 2 | 1 | 973 | 54 (i=0) | 97,354 | ×2 | 400 | 0.004 |
| 3 | 1 | 973 | 16 (i=1) | 97,316 | ×2 | 400 | 0.004 |
| 4 | 5 | 969 | 54 (i=2) | 96,954 | ×3 | 600 | 0.006 |
| 5 | 5 | 969 | 16 (i=3) | 96,916 | ×3 | 600 | 0.006 |
| 6 | 6 | 968 | 54 (i=4) | 96,854 | ×4 | 800 | 0.008 |
| 7 | 6 | 968 | 16 (i=5) | 96,816 | ×4 | 800 | 0.008 |

---

## API Usage Reference

| Endpoint | HTTP Method | Max per call | Used by |
|---|---|---|---|
| `/fapi/v1/batchOrders` | `POST` | 5 orders | `_place_orders_batch` |
| `/fapi/v1/batchOrders` | `DELETE` | 10 IDs | `_cancel_orders_by_ids` |
| `/fapi/v1/openOrders` | `GET` | — | `_fetch_open_orders` |
| `/fapi/v1/order` | `POST` | — | `_place_single_order` (reduceOnly MARKET) |
| `/fapi/v1/order` | `GET` | — | `_query_order` |
| `/fapi/v1/order` | `DELETE` | — | `_cancel_order` |
| `/fapi/v1/algoOrder` | `POST` | — | `_place_algo_order` (TP/SL CONDITIONAL) |
| `/fapi/v1/algoOrder` | `GET` | — | `_query_algo_order` |
| `/fapi/v1/algoOrder` | `DELETE` | — | `_cancel_algo_order` |
| `/fapi/v1/openAlgoOrders` | `GET` | — | `_fetch_open_algo_orders` |
| `/fapi/v2/positionRisk` | `GET` | — | `_fetch_position_risk` |
| `/fapi/v2/balance` | `GET` | — | `_fetch_available_balance` |
| `/fapi/v1/leverage` | `POST` | — | `_set_leverage` |
| `/fapi/v1/time` | `GET` | — | `_fetch_server_time_offset` (startup only) |

> **Important**: TP/SL orders (`TAKE_PROFIT_MARKET`, `STOP_MARKET`) **cannot** be placed via `/fapi/v1/order` or `/fapi/v1/batchOrders` — Binance returns -4120 and redirects to the algo endpoint. They use `algoId` (not `orderId`) as their identifier throughout the lifecycle.

---

## Pre-flight Guards in `place_order`

```
1. _fetch_position_risk(symbol)         ← one API call shared by guards 2 and 3

2. _close_diverged_same_side_position(symbol, signal, entry_price, positions)
       same_side_qty, same_side_avg = _get_same_side_position(signal, positions)
       if |same_side_avg - entry_price| > same_side_price_level_diff (100 USDT):
           _place_single_order(reduceOnly MARKET)   ← close stale position
       else:
           log "within tolerance, keeping open"

3. _get_opposite_side_qty(signal, positions)
       first_qty = base_qty + opposite_qty    ← absorbs counter-position in 1 order

4. _assert_sufficient_balance(symbol, order_dicts)
       total_notional = Σ(price × qty)
       required_margin = total_notional / leverage
       threshold = required_margin × min_balance_buffer_ratio (1.5)
       if _fetch_available_balance("USDT") < threshold:
           raise ValueError  ← aborts before any order is submitted
```

## Post-placement Guard in `orchestrate_bracket_order` (step 2b)

```
After _place_orders_batch succeeds, before _monitor_ladder starts:

    poll every position_open_poll (10s) up to position_open_wait (3600s):
        _get_position_info(symbol)
            qty > 0          → position_confirmed = True; proceed to monitor
            ValueError       → no fill yet; keep polling
            RuntimeError     → log warning; keep polling

    if not position_confirmed:
        _cancel_ladder_orders(symbol)
        return { "main": ladder_results, "oco_outcome": OcoOutcome.TIMEOUT }

Purpose: ensures the oco_max_wait clock only starts once a real position exists.
         Without this guard, the monitor loop could burn its entire budget waiting
         for a fill that never comes, or place TP/SL before any position is open.
```

---

## Usage Example

```python
from src.stockreports.trade_service.orchestrator import TradingServiceOrchestrator
from src.stockreports.utils.time_utils import TimeSimulator

orchestrator = TradingServiceOrchestrator()

# Full DCA ladder + dynamic bracket lifecycle (runs in a daemon thread)
result = orchestrator.orchestrate_bracket_order(alert, time_simulator=time_simulator)
# result = {
#     "main": List[TradeResult],    # ladder order placement results
#     "oco_outcome": OcoOutcome,    # TP_FILLED | SL_FILLED | EXTERNAL_TERMINAL | TIMEOUT
# }
```

---

## Design Principles

- **Facade**: Only `TradingServiceOrchestrator` is exposed; all other logic is under `_internal/`.
- **Single responsibility**: Each private helper does exactly one thing (fetch, cancel, query, or batch-post).
- **Shared position fetch**: `_fetch_position_risk` is called once per `place_order` and passed to both `_close_diverged_same_side_position` and `_get_opposite_side_qty` — no duplicate API calls.
- **Algo vs regular order split**: All bracket orders go through `/fapi/v1/algoOrder`; all LIMIT ladder orders go through `/fapi/v1/batchOrders`. The two sets are tracked and queried via separate endpoints (`openOrders` vs `openAlgoOrders`).
- **USDT-based sizing**: All order quantities are derived from `order_usdt_amount / price` — no hardcoded coin amounts. Exposure scales consistently across price levels and multipliers.
- **Server time sync**: `_fetch_server_time_offset` runs at startup; all signed requests use `_now_ms()` to stay within Binance's `recvWindow` regardless of local clock drift.
- **Signature correctness**: All `GET`/`DELETE` signed requests build the query string with `urlencode` and append it directly to the URL. Passing `params=` to `requests.get/delete` allows the library to reorder the dict and invalidate the HMAC — this is why `_query_algo_order` and `_cancel_algo_order` use manual URL building.
- **Uniform result type**: Every order action returns `TradeResult`; errors return `TradeResult(status="ERROR")` — callers never handle raw HTTP exceptions.
- **Option B lifecycle**: OCO fills do not cancel surviving ladder rungs, enabling continuous DCA accumulation within a single `orchestrate_bracket_order` call.
- **Config-driven**: All prices, quantities, timeouts, and endpoints are in `BINANCE_PERPETUAL_CONFIG` — no magic numbers in trading logic.
- **Instance logger**: `self.logger = logging.getLogger(self.__class__.__name__)` — subclass-friendly, avoids shared class-level state.
