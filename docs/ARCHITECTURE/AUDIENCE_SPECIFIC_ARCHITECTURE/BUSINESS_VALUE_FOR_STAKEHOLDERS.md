# Never Miss a Trade. Never Get Spammed.

> Real-time trading alerts for Vietnam futures and crypto markets —
> fires when it matters, stays silent when it doesn't.

**For:** Business stakeholders · Fund managers · Potential clients · Sales teams
**Date:** May 29, 2026
**Read Time:** 10-15 minutes

---

## ❗ The Problem

Watching charts all day is exhausting — but missing one key price level can mean missing the trade entirely.

Most alert tools push **too many notifications** (every tick, every candle) until traders start ignoring them. Or they alert only once and go silent — missing legitimate re-entries later in the session.

**There's a smarter way.**

---

## ✅ What This System Does

The **Trading Alert System** monitors your symbols 24/7, fires alerts only when genuine signals appear, and stays silent when conditions don't warrant action.

**8 detection approaches** across two categories:

| Category | Approaches |
|----------|-----------|
| **TRADE (5 active)** — precision entry signals | STRONG_CANDLE · VRA · ICHIMOKU · CONSISTENT_MOMENTUM · REVERSAL_ANCHOR_SIGNAL_CANDLE |
| **ANNOUNCE (3)** — market movement awareness | LARGE_CANDLE · LARGE_VOLUME_CANDLE · PRICE_MOVEMENT |

> *(VOLUME_SPIKE_CONFIRMATION and CONSISTENT_VOLUME_ANCHOR exist in the codebase but are currently archived — not wired into execution.)*

**Delivered via:** Email ✅ · Slack ✅ · Ntfy ✅ (mobile & web push via ntfy.sh) · SMS ⚠️ not yet validated

**Validate first:** Run any strategy in **REPLAY mode** against historical data before risking real money.

> **⚡ Automated order execution:** For **BTCUSDT-PERP**, confirmed TRADE alerts can automatically place a full DCA bracket order (limit ladder entries + take-profit + stop-loss) via the Binance Futures API — no manual intervention needed.
> For **VN30F1M**, alerts are **notification-only** — Vietstock is a data provider and does not support order execution via API. Traders act on the alert manually.

---

## 📊 At a Glance

| Capability | Details |
|---|---|
| **Supported symbols** | VN30F1M (Vietnam futures) · BTCUSDT-PERP (Bitcoin perpetual) · extensible |
| **Data sources** | Vietstock · Binance API · Binance CCXT |
| **Operating modes** | LIVE (real-time, auto-recovery) · REPLAY (backtest, historical simulation) |
| **Alert cooldown** | Configurable per symbol — default 3 min, prevents repeat spam |
| **Repeated alerts** | Cooldown window (minutes) — same signal suppressed until window expires |
| **Symbol isolation** | Each symbol tracked independently — zero cross-contamination |
| **Deployment** | Docker · Kubernetes · Cloud · On-premises · Heroku (Procfile included) |

---

## 💡 5 Reasons Traders Choose This System

### 1. 🔕 Alerts Fire When It Matters — Silence When They Don't
A configurable **cooldown period** prevents the same signal from firing repeatedly within a short window. You get notified once → system goes quiet → fires again only after the cooldown window expires.

> **Config lever (TRADE approaches):** `cooldown_window` (minutes) — configured per approach in `executor_config.yaml`. After the cooldown expires, the same signal can fire again.
> **Config lever (PRICE_MOVEMENT approach):** `LEVEL_ALERT_COOLDOWN_MINUTES` (default: 3 min) — controls per-level cooldown for interval/fixed-level crossing alerts.

### 2. 🎛️ PRICE_MOVEMENT: Repeat or Once-Per-Cooldown
For the **PRICE_MOVEMENT** (ANNOUNCE) approach, there is an additional toggle:
- **`ALLOW_REPEATED_LEVEL_ALERTS = False`** *(default)* — a crossed level is suppressed until its cooldown window expires; after expiry it can fire again
- **`ALLOW_REPEATED_LEVEL_ALERTS = True`** — fires on every crossing regardless of prior alerts

> **Note:** This toggle applies only to `PRICE_MOVEMENT`. TRADE approaches (VRA, STRONG_CANDLE, etc.) use only the per-approach cooldown window.

### 3. 🔀 Multi-Symbol, Zero Interference
Monitor VN30F1M and BTCUSDT-PERP simultaneously with **completely independent** cooldown tracking per symbol. An alert on one never blocks alerts on another — even at the same price level.

### 4. 🧪 Validate Before You Risk Real Money
Every strategy can be tested in **REPLAY mode** against historical data before going live. See how your approach would have performed, then make an informed decision about whether it's ready.

### 5. 📲 Instant Delivery, Multiple Channels
Alerts reach you via **Email, Slack, or Ntfy** (mobile push + web via ntfy.sh) — or all three simultaneously. Each notification includes symbol, price, approach triggered, and environment context.

---

## 💼 Real-World Use Cases

### 🟦 Use Case 1: VN30F1M Futures Trader
**Scenario**: A trader wants to execute on VN30F1M futures movements

**Setup**:
- Monitor VN30F1M at interval-based levels: 1,756.2, 1,765.2, 1,774.2, 1,783.2, etc. (9-point intervals)
- 3-minute cooldown to prevent re-alerts for the same level within the cooldown window
- `ALLOW_REPEATED_LEVEL_ALERTS = False` (default) — level suppressed until cooldown expires, then can fire again

**Workflow**:
```
Market Event → Price crosses 1,774.2 → Alert triggered → Notification sent
   ↓
Trader reviews alert (Email/Slack/Ntfy) → Manually enters trade
   ↓               ⚠️ VietStock is data-only — no API order execution
Price later touches 1,774.2 again (within 3 mins) → No alert (cooldown active)
   ↓
Next day → Price touches 1,774.2 again → Alert triggered (new day)
```

**Benefits**:
- Never miss key technical levels
- Focus on trading, not constant chart-watching
- Automatic alert suppression prevents decision paralysis

> **Result:** Clean signals on VN30F1M, zero noise, zero decision paralysis.

---

### 🟠 Use Case 2: VN30F1M Interval Scalper
**Scenario**: Day trader monitoring VN30F1M futures with interval-based levels
- Monitor intervals of 9-point movements from reference price 1,765.2
- 10-minute cooldown to limit re-alerts on the same level
- `ALLOW_REPEATED_LEVEL_ALERTS = True` — fires on every crossing regardless of prior alerts *(PRICE_MOVEMENT approach only)*

**Workflow**:
```
Reference: 1,765.2 → Intervals: 1,756.2, 1,747.2, 1,774.2, 1,783.2...
   ↓
Crosses 1,774.2 (up) → Alert → Enters position
   ↓
Drops to 1,765.2 → Different interval → Alert → Exits position
   ↓
Bounces up to 1,774.2 again (within 10 mins) → No alert (cooldown)
   ↓
Wait 10 mins → 1,774.2 again → Alert → Can re-enter
```

**Benefits**:
- Track momentum through price bands
- Quick reaction to volatility
- Aggressive cooldown for frequent traders
- Flexible interval sizing matches trading style

> **Result:** Catches every meaningful cross, ignores the noise in between.

---

### 🟢 Use Case 3: Multi-Symbol Portfolio
**Scenario**: Trader monitoring both VN30F1M and BTCUSDT-PERP simultaneously

**Setup**:
- VN30F1M: Interval-based levels (9-point bands) during Vietnam trading hours → **notification-only** (manual execution)
- BTCUSDT-PERP: ANNOUNCE + TRADE approaches running 24/7 → **automated DCA bracket order placement** via Binance Futures API
- Unified notification system with symbol context in each alert

**Workflow**:
```
VN30F1M @ 1,774.2 ← Alert fires → Trader notified → Manually enters trade
                                    ⚠️ VietStock is data-only
Parallel ↓
BTCUSDT-PERP @ 95,500 ← Alert fires → System automatically places
                         DCA bracket order (ladder + TP + SL) on Binance Futures API

Both alerts route to trader → Each clearly labeled with symbol + approach
```

**Benefits**:
- One system covers both VN futures (manual trading) and crypto (automated orders)
- No alert interference between symbols
- Independent cooldowns per symbol

---

## ⚙️ Operational Workflow

> ⚠️ **Scope note:** The `triggered_levels_today` state and `ALLOW_REPEATED_LEVEL_ALERTS` toggle described in this section apply specifically to the **PRICE_MOVEMENT approach** (`PriceMovementAlerter`). TRADE approaches (VRA, STRONG_CANDLE, ICHIMOKU, etc.) use a separate per-approach `cooldown_window` (in minutes) with no "once per day" mode.

### Daily Trading Cycle

#### Morning (Market Open)
```
T = 09:00 → Market opens
Service automatically initializes with fresh state
- triggered_levels_today = {}  # Starts empty (PRICE_MOVEMENT approach class variable)
- All symbols ready to alert

T = 09:15 → First price movement
- VN30F1M crosses a configured level (e.g. via absolute_interval)
- Alert generated: "VN30F1M crossed above 1,774.2"
- triggered_levels_today["VN30F1M"][1,774.2] = 09:15
- Trader receives notification
```

#### Mid-Day (Ongoing Monitoring)
```
T = 10:00 → Volatility increases
- Multiple symbols active
- VN30F1M triggers 3 alerts (different levels)
- BTCUSDT-PERP triggers 2 alerts (different levels, independent)
- Each symbol's cooldown independent
- Examples:
  * VN30F1M @ 1,774.2: triggered at 09:15 → cooldown until 09:18
  * VN30F1M @ 1,783.2: triggered at 09:45 → cooldown until 09:48
  * Different levels, same symbol, independent cooldown timings ✓

T = 12:00 → Lunch break approaches
- Market quieter
- Triggered levels aging
- Service runs automatic cleanup (during next alerter creation)
- Levels older than LEVEL_ALERT_COOLDOWN_MINUTES are removed
```

#### Afternoon (Continued Monitoring)
```
T = 13:30 → Market reopens
- Fresh monitoring resumes
- Expired levels from morning are cleared (on next PriceMovementAlerter instantiation)
- Traders can now re-trigger PRICE_MOVEMENT alerts for the same levels
- Example: VN30F1M @ 1,774.2 
  * Originally triggered at 09:15
  * Cooldown expires at 09:18 (3 min default)
  * After 09:18, _remove_expired_levels() removes it → can trigger again
```

#### Close (Market End)
```
T = 15:30 → Market closes
- Last price updates processed
- Service continues monitoring (in case of after-hours events)
- All state preserved for next trading day

T = 23:59 → End of day
- triggered_levels_today state persists
- Next day will start with fresh state at market open
```

---

### Cooldown Mechanism in Action

#### Scenario: VN30F1M at a Configured Level

```
Timeline:

09:15:00 → VN30F1M price crosses 1,774.2 going UP
           ✓ Alert triggered
           ✓ triggered_levels_today["VN30F1M"][1,774.2] = 09:15:00
           ✓ Trader notified

09:16:00 → VN30F1M price still near 1,774.2
           ✗ Check: 1,774.2 in triggered_levels_today["VN30F1M"]? YES
           ✗ Cooldown active (from 09:15 to 09:18)
           ✗ Alert SUPPRESSED (prevents spam)

09:17:00 → VN30F1M still above 1,774.2
           ✗ Cooldown still active
           ✗ Alert SUPPRESSED

09:18:00 → VN30F1M drops back below 1,774.2 (crosses DOWN)
           ✓ IF ALLOW_REPEATED_LEVEL_ALERTS = True (PRICE_MOVEMENT only):
               Alert triggered "VN30F1M crossed below 1,774.2"
               triggered_levels_today["VN30F1M"][1,774.2] = 09:18:00
           ✗ IF ALLOW_REPEATED_LEVEL_ALERTS = False (default, PRICE_MOVEMENT only):
               Alert SUPPRESSED (level still in cooldown — not yet expired)
               triggered_levels_today["VN30F1M"][1,774.2] = 09:15:00 (unchanged)

10:00:00 → VN30F1M crosses 1,774.2 UP again
           ✓ IF ALLOW_REPEATED_LEVEL_ALERTS = True (PRICE_MOVEMENT only):
               Alert triggered "VN30F1M crossed above 1,774.2"
           ✓ IF ALLOW_REPEATED_LEVEL_ALERTS = False (default, PRICE_MOVEMENT only):
               Cooldown from 09:15:00 + 3 mins = expired at 09:18:00
               Level removed from triggered_levels_today → Alert triggered
```

---

### Symbol Isolation Demonstrated

#### Scenario: VN30F1M & BTCUSDT-PERP Both Cross Their Respective Levels

```
09:15:00 → VN30F1M crosses 1,774.2 UP
           ✓ Alert: "VN30F1M crossed above 1,774.2"
           ✓ triggered_levels_today["VN30F1M"][1,774.2] = 09:15:00

09:16:00 → BTCUSDT-PERP crosses 95,500 UP
           ✓ Alert: "BTCUSDT-PERP crossed above 95,500"  ← INDEPENDENT!
           ✓ triggered_levels_today["BTCUSDT-PERP"][95500] = 09:16:00
           ✓ VN30F1M's tracking unaffected!

09:17:00 → BTCUSDT-PERP briefly touches 95,500 again
           ✗ Check: 95,500 in triggered_levels_today["BTCUSDT-PERP"]? YES
           ✗ Cooldown active (09:16:00 to 09:19:00)
           ✗ Alert SUPPRESSED for BTCUSDT-PERP

09:17:30 → VN30F1M briefly touches 1,774.2 again
           ✗ Check: 1,774.2 in triggered_levels_today["VN30F1M"]? YES
           ✗ Cooldown active (09:15:00 to 09:18:00)
           ✗ Alert SUPPRESSED for VN30F1M

RESULT: Each symbol has independent cooldown!
        VN30F1M expires at 09:18:00
        BTCUSDT-PERP expires at 09:19:00
        No interference between symbols
```

---

## 🛡️ Built for Production

### What You Can Rely On

#### 1. **Error Handling**
- Missing data: Service continues, logs warning
- Missing configuration: Non-blocking, service continues
- Invalid data types: Auto-conversion and validation
- Network failures: Automatic recovery and retry

#### 2. **Audit Trail**
- Complete logging of all alerts generated
- Timestamp for every trade execution trigger
- Symbol-specific tracking for compliance
- Configurable log levels for different environments

#### 3. **Data Validation**
- Price data integrity checks
- Timezone handling for international markets
- Missing data point detection
- Automatic data cleanup and expiration

---

## 📈 Performance Characteristics

| Metric | Description |
|--------|-------------|
| **Alert Latency** | Real-time response driven by data provider tick rate |
| **Memory per Symbol** | Lightweight in-memory state (cooldown dict + approach state) |
| **Configuration Updates** | Config file changes take effect on next service restart |

> **Note:** Specific latency benchmarks (< 1ms, 100K ticks/day, 99.9% uptime) have not been measured against the current codebase and are not guaranteed.

---

## 🚀 Deployment Options

### Where Does It Run?

**Option 1: Cloud (AWS/Azure/GCP)**
- Auto-scaling based on symbol count
- Geographic redundancy
- Managed infrastructure

**Option 2: On-Premises**
- Docker containers for easy deployment
- Kubernetes orchestration available
- Full data privacy control

**Option 3: Hybrid**
- Production in cloud
- Backup on-premises failover
- Best of both worlds

---

## 💡 Getting Started in 3 Steps

### Step 1: Configuration
Define your monitoring levels (VN30F1M futures, BTCUSDT-PERP crypto):
```yaml
PRICE_ALERTS:
  VN30F1M:
    reference_price: 1765.2
    absolute_interval: 9.0
  BTCUSDT-PERP:
    reference_price: 95000
    absolute_interval: 500.0
```

### Step 2: Integration
Connect your notification channels (Email ✅, Slack ✅, Ntfy ✅ — all validated):
```
→ Real-time alerts to your preferred channel
→ Alert enrichment with price and symbol context
→ Trader action tracking
```

### Step 3: Optimization
Adjust cooldown settings based on your trading style:
```
# PRICE_MOVEMENT approach (price level crossings):
LEVEL_ALERT_COOLDOWN_MINUTES = 3        # minutes before same level can fire again
ALLOW_REPEATED_LEVEL_ALERTS = false     # true = fire on every crossing regardless of cooldown

# TRADE approaches (VRA, STRONG_CANDLE, ICHIMOKU, etc.):
# cooldown_window configured per-approach in executor_config.yaml (minutes only — no once-per-day mode)
```

---

## 📞 Support & Documentation

For technical implementation details, see:
- 👉 [TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md](../TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md) - Complete technical architecture
- 👉 [TECHNICAL_REFERENCE/VISUAL_GUIDE.md](../TECHNICAL_REFERENCE/VISUAL_GUIDE.md) - Architecture diagrams and state machines
- 👉 [IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md](../IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md) - How to extend the system

For operational procedures, see:
- 👉 [IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md](../IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md) - Deployment and configuration
- 👉 [IMPLEMENTATION_GUIDES/REPLAY_MODE_ARCHITECTURE.md](../IMPLEMENTATION_GUIDES/REPLAY_MODE_ARCHITECTURE.md) - Testing and replay modes

---

## ✅ Ready to Move Forward?

**Contact the team with:**
- Which symbols to monitor (VN30F1M, BTCUSDT-PERP, or custom)
- Preferred notification channels
- Trading style (conservative cooldown vs. aggressive re-entry)
- Deployment environment preference (cloud, on-premises, hybrid)

**Want to explore the technical details?** See:
- 👉 [TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md](../TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md) - Complete technical architecture
- 👉 [TECHNICAL_REFERENCE/VISUAL_GUIDE.md](../TECHNICAL_REFERENCE/VISUAL_GUIDE.md) - Architecture diagrams
- 👉 [IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md](../IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md) - Deployment procedures
