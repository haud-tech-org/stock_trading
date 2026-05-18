# Layer 10: Trade Execution Service — Implementation Guide

**Purpose**: Practical how-to for extending and configuring the Trade Execution Service  
**Audience**: Developers working on live trading features  
**Scope**: Adding new symbols, new platforms, configuring the ladder, debugging  
**Last Updated**: May 18, 2026

---

## 🎯 What You'll Find Here

- How to register a new trading symbol
- How to implement a new trading platform (`BaseTrading` subclass)
- How to tune the DCA ladder and bracket configuration
- How to enable/disable trade execution
- How the alert expiry guard works
- Common issues and solutions

---

## ⚡ How Trade Execution Is Triggered

Trade execution fires from inside `SymbolAlerter._perform_monitoring_session` (Layer 2),
at the end of TASK-3 (trade approach alerters), once per confirmed alert:

```python
# In symbol_alerter.py — _perform_monitoring_session / TASK-3
if settings.MODE == Mode.DEPLOYMENT:
    expired_minutes = settings.TRADING_EXECUTION_EXPIRED_MINUTES
    if time_simulator.is_alert_expired(alert.alert_time, expired_minutes):
        self.logger.warning(f"[TASK-3] Skipping trade execution: alert is >{expired_minutes}m old.")
    else:
        self.trading_orchestrator.orchestrate_bracket_order(alert, time_simulator)
```

`TradingServiceOrchestrator.orchestrate_bracket_order` dispatches into a **daemon thread**,
so the monitoring loop is never blocked.

---

## 🔧 How to Register a New Symbol

Edit `TradingPlatformRegistry` in `_internal/registry.py`:

```python
TradingPlatformRegistry._platforms = {
    'BTCUSDT-PERP': BinancePerpetualTrading,
    'ETHUSDT-PERP': BinancePerpetualTrading,   # ← add new symbol here
    # 'XYZUSDT-PERP': MyCustomPlatform,       # ← or a different platform class
}
```

- The key must match `alert.symbol` exactly (including the `-PERP` suffix if present)
- Each `get_platform_for_symbol` call returns a **fresh instance** of the platform class

---

## 🔧 How to Implement a New Trading Platform

1. Create a new file in `_internal/platforms/`:

```python
from src.stockreports.trade_service._internal.base_trading import BaseTrading
from src.stockreports.alert.model.models import AlertData
from src.stockreports.utils.time_utils import TimeSimulator
from typing import Optional

class MyExchangeTrading(BaseTrading):
    def orchestrate_bracket_order(
        self,
        alert: AlertData,
        tp_price: float = None,
        sl_price: float = None,
        time_simulator: Optional[TimeSimulator] = None,
    ):
        # implement full DCA bracket lifecycle here
        ...
```

2. Register it in `TradingPlatformRegistry._platforms`.

---

## ⚙️ Configuration Reference

All parameters live in `_internal/config/binance_perpetual_config.py`.

### Most Commonly Tuned

| Key | Default | What to change |
|---|---|---|
| `order_usdt_amount` | `200.0` | USDT exposure per ladder rung |
| `tp_price_diff` | `300.0` | Take-profit offset from avg entry (USDT) |
| `sl_price_diff` | `500.0` | Stop-loss offset from avg entry (USDT) |
| `ladder_order_max_wait` | `2000 s` | How long to wait before cancelling unfilled LIMIT orders |
| `oco_max_wait` | `4000 s` | Overall bracket safety timeout |
| `position_open_wait` | `3600 s` | How long to wait for first fill before aborting |
| `use_demo` | `True` | Toggle between demo and live endpoint |
| `default_leverage` | `20` | Leverage set before each bracket |

### Alert Expiry Guard

Configured in `src/stockreports/config/settings.py`:
```python
TRADING_EXECUTION_EXPIRED_MINUTES = 5
```
Alerts older than this (relative to `TimeSimulator.get_current_time()`) are skipped.
Prevents stale signals (e.g., from a restart after downtime) from triggering real orders.

---

## 🐛 Common Issues

| Symptom | Likely Cause | Fix |
|---|---|---|
| `place_order skipped: no platform registered` | Symbol not in `TradingPlatformRegistry` | Add symbol mapping in `registry.py` |
| `-1111 Precision is over maximum` | `qty_precision` or `price_precision` too high | Lower to match symbol's lot/tick size |
| `-1021 Timestamp outside recvWindow` | Local clock skew | `_fetch_server_time_offset` auto-corrects; check network latency |
| `-2011 on cancel` | Order already gone | Already handled as success (idempotent) |
| `-2021 on TP/SL placement` | Market moved past trigger before order landed | Already handled as `WOULD_TRIGGER`; bracket resolved inline |
| `-4120 Invalid order type` | TP/SL placed on wrong endpoint | Ensure all bracket orders use `_place_algo_order` (not `_place_single_order`) |
| `400 Bad Request on query` | Signed request params reordered | All GET/DELETE use manual `urlencode` URL (not `params=`) |
| `No position opened within Xs` | No LIMIT fill in `position_open_wait` | Check that entry_price is realistic; market may not have reached it |

---

## 📚 Related Documentation

- **Architecture theory** → [`TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md`](../../TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md)
- **Full method map + config ref** → [`TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md`](../../TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md)
- **System integration** → [`SYSTEM_ARCHITECTURE_OVERVIEW.md`](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) — Layer 10 block
- **Source files**:
  - `src/stockreports/trade_service/orchestrator.py` — public facade
  - `src/stockreports/trade_service/_internal/registry.py` — symbol registration
  - `src/stockreports/trade_service/_internal/platforms/binance_perpetual_trading.py` — live impl
  - `src/stockreports/trade_service/_internal/config/binance_perpetual_config.py` — all config
