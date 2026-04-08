# Phase 1 Investigation - Visual Architecture Guide

**Created:** April 8, 2026

---

## 1. System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    STOCK TRADING SYSTEM                          │
│                    (DEPLOYMENT MODE)                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
        ┌───────────────────────────────────────┐
        │   SymbolAlertManager                  │
        │   (Multi-symbol orchestrator)         │
        │   ThreadPoolExecutor                  │
        └───────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
        ┌──────────────┐          ┌──────────────┐
        │ SymbolAlerter│          │ SymbolAlerter│
        │ (VN30F1M)    │          │ (VN30)       │
        └──────────────┘          └──────────────┘
              │                           │
              ▼                           ▼
        ┌──────────────────────────────────────────┐
        │   _run_deployment_mode()                 │
        │   [Supervisor Loop - Error Recovery]     │
        │                                          │
        │   ┌────────────────────────────────────┐ │
        │   │ _perform_monitoring_session()      │ │
        │   │ [Main Monitoring Loop]             │ │
        │   │                                    │ │
        │   │  TimeSimulator (Controls Time)    │ │
        │   │  ├─ is_running()                 │ │
        │   │  ├─ get_current_time()           │ │
        │   │  ├─ advance()                    │ │
        │   │  └─ is_replay_mode()             │ │
        │   │                                    │ │
        │   │  while time_simulator.is_running()│ │
        │   │    ├─ Check scheduled closes      │ │
        │   │    ├─ Check trading hours         │ │
        │   │    ├─ Fetch data                  │ │
        │   │    ├─ Run price movement alerts   │ │
        │   │    ├─ Run executors (6 approaches)│ │
        │   │    └─ Notify via channels         │ │
        │   └────────────────────────────────────┘ │
        └──────────────────────────────────────────┘
```

---

## 2. DEBUG_REPLAY_START_TIME Impact - Decision Tree

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Only LIVE and REPLAY modes exist (starting Phase 2)

                ┌─ START ─┐
                    │
                    ▼
        ┌──────────────────────────────┐
        │ DEBUG_REPLAY_START_TIME = ?  │
        └──────────────────────────────┘
             │                    │
            None             Timestamp
             │                    │
             ▼                    ▼
        ┌─────────┐          ┌─────────┐
        │ LIVE    │          │ REPLAY  │
        │ MODE    │          │ MODE    │
        └─────────┘          └─────────┘
             │                    │
   ┌─────────┴────────────────────┴─────────┐
   │                                        │
   ▼                                        ▼
Time Source:                          Time Source:
System.now()                          Simulated from timestamp
(Real current time)                   (Jump in intervals)

Loop Duration:                        Loop Duration:
Indefinite                            Until end_of_day
(Run forever)                         (Deterministic end)

Non-trading Hours:                    Non-trading Hours:
sleep(900)                            advance()
(Wait 15 minutes)                     (Jump instantly)

Error Handling:                       Error Handling:
Auto-restart                          Exit cleanly
(24/7 resilience)                     (Reproducible testing)

Report Directory:                     Report Directory:
reports/                              reports_replay/
(Production alerts)                   (Test alerts)
```

---

## 3. TimeSimulator State Machine

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    TimeSimulator only handles LIVE vs REPLAY (via DEBUG_REPLAY_START_TIME)

┌────────────────────────────────────────────────────────┐
│ TimeSimulator.__init__()                               │
│                                                        │
│ replay_start_str = None?  ────┬──────────────────────┐ │
│                               NO                     YES│
│                               │                        │
│                    ┌──────────▼──────┐    ┌──────────▼──────┐
│                    │ LIVE MODE       │    │ REPLAY MODE     │
│                    │ _is_replay=False│    │ _is_replay=True │
│                    │                 │    │                 │
│                    │ time = now()    │    │ time = timestamp │
│                    │ end_of_day=None │    │ end_of_day=calc │
│                    └─────────────────┘    └─────────────────┘
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Main Loop: while time_simulator.is_running()           │
│                                                        │
│ ┌─────────────────────┐        ┌──────────────────────┐│
│ │ LIVE is_running():  │        │ REPLAY is_running(): ││
│ │                     │        │                      ││
│ │ return True         │        │ current <= end_of_day││
│ │ (infinite)          │        │ (bounded)            ││
│ └─────────────────────┘        └──────────────────────┘│
└────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────┐
│ Current Time Update: time_simulator.advance()          │
│                                                        │
│ ┌─────────────────────┐        ┌──────────────────────┐│
│ │ LIVE advance():     │        │ REPLAY advance():    ││
│ │                     │        │                      ││
│ │ # No-op             │        │ time += interval     ││
│ │ # Real time         │        │ # Jump to next       ││
│ │ # advances itself   │        │                      ││
│ └─────────────────────┘        └──────────────────────┘│
└────────────────────────────────────────────────────────┘
```

---

## 4. Trading Hours Branching Logic

```
┌─ is_trading_hours(current_time)? ─┐
│                                    │
         YES                    NO
         │                      │
         ▼                      ▼
    Process data           ┌─────────────────┐
    & alerts              │ is_replay_mode() │
                          └─────────────────┘
                               │        │
                          YES  │        │  NO
                               │        │
                    ┌──────────▼┐      ┌▼──────────┐
                    │ REPLAY:   │      │ LIVE:     │
                    │ advance() │      │ sleep(900)│
                    │ continue  │      │ continue  │
                    └───────────┘      └───────────┘
                    
    RESULT:
    REPLAY: Jumps instantly to next trading slot
    LIVE:   Waits 15 minutes before checking again
```

---

## 5. Error Recovery Branching

```
┌──────────────────────┐
│  Exception Caught    │
└──────────────────────┘
         │
         ▼
┌──────────────────────────────────┐
│ DEBUG_REPLAY_START_TIME is None? │
└──────────────────────────────────┘
    │                         │
   YES                       NO
    │                        │
    ▼                        ▼
┌──────────────┐        ┌──────────────┐
│ LIVE MODE:   │        │ REPLAY MODE: │
│              │        │              │
│ Log error    │        │ Log error    │
│ sleep(57)    │        │ break        │
│ continue     │        │ (exit)       │
│ (restart)    │        │              │
└──────────────┘        └──────────────┘

RESULT:
LIVE:   Auto-recovery ensures 24/7 uptime
REPLAY: Deterministic exit for reproducible testing
```

---

## 6. Report Directory Selection

```
┌─────────────────────────────────────┐
│ get_reports_directory_name()        │
│                                     │
│ DEBUG_REPLAY_START_TIME is None?    │
└─────────────────────────────────────┘
    │                            │
   YES                          NO
    │                           │
    ▼                           ▼
┌────────────┐            ┌──────────────┐
│ "reports"  │            │ "reports_    │
│            │            │ replay"      │
│ LIVE       │            │              │
│ Production │            │ REPLAY       │
│ Alerts     │            │ Test Alerts  │
└────────────┘            └──────────────┘

DIRECTORY STRUCTURE:
reports/
├── VN30F1M/
│   └── deployment/
│       └── alert_notification_*.json
└── VN30/
    └── deployment/
        └── alert_notification_*.json

reports_replay/
├── VN30F1M/
│   └── deployment/
│       └── alert_notification_*.json
└── VN30/
    └── deployment/
        └── alert_notification_*.json
```

---

## 7. Data Flow - Complete Request Path

```
SymbolAlerter._perform_monitoring_session()
    │
    ├─ while time_simulator.is_running():
    │   │
    │   ├─ current_time = time_simulator.get_current_time()
    │   │
    │   ├─ if not is_trading_hours():
    │   │   ├─ LIVE:   time.sleep(900)
    │   │   └─ REPLAY: time_simulator.advance()
    │   │
    │   ├─ Fetch Data:
    │   │   │
    │   │   └─ DataServiceOrchestrator.fetch_and_process()
    │   │       │
    │   │       ├─ HistoricalDataManager (Cache)
    │   │       │  │
    │   │       │  └─ DataProviderCoordinator
    │   │       │      │
    │   │       │      ├─ VietstockProvider
    │   │       │      ├─ BinanceAPIProvider
    │   │       │      └─ BinanceCCXTProvider
    │   │       │
    │   │       └─ DataProcessor
    │   │           ├─ Timezone conversion
    │   │           └─ Price adjustment
    │   │
    │   ├─ Analyze Alerts:
    │   │   │
    │   │   ├─ PriceMovementAlerter.execute()
    │   │   │   └─ AlertResult
    │   │   │
    │   │   └─ For each approach:
    │   │       └─ Executor.run()
    │   │           └─ AlertResult
    │   │
    │   ├─ Send Notifications:
    │   │   │
    │   │   └─ NotificationManager.process_and_notify()
    │   │       │
    │   │       ├─ Email Service
    │   │       ├─ SMS Service
    │   │       └─ Ntfy Service
    │   │
    │   ├─ Check Scheduled Closes:
    │   │   │
    │   │   └─ close_position_scheduler.check_and_notify()
    │   │       └─ "CLOSE POSITION" notification
    │   │
    │   └─ time_simulator.advance()
    │       ├─ LIVE:   No-op (real time advances)
    │       └─ REPLAY: current_time += interval
    │
    └─ Exit when:
        ├─ LIVE:   KeyboardInterrupt or crash
        └─ REPLAY: current_time > end_of_day
```

---

## 8. Configuration Hierarchy

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Configuration simplified to only LIVE and REPLAY modes

┌─────────────────────────────────────────────────────────┐
│                CONFIGURATION SYSTEM                      │
└─────────────────────────────────────────────────────────┘

TIER 1: Time Behavior (Via DEBUG_REPLAY_START_TIME)
┌────────────────────────────────────────────────────────┐
│ DEBUG_REPLAY_START_TIME = None OR "YYYY-MM-DD HH:MM:SS"│
├────────────────────────────────────────────────────────┤
│ None = LIVE MODE:           │ Timestamp = REPLAY MODE: │
│ - Current system time       │ - Simulated time         │
│ - Indefinite loop           │ - Bounded by end_of_day  │
│ - Auto-restart on crash     │ - Exit on crash          │
│ - reports/ storage          │ - reports_replay/ storage│
└────────────────────────────────────────────────────────┘

TIER 2: Analysis Logic (Approach Selection)
┌────────────────────────────────────────────────────────┐
│ SYMBOL_ALERT_APPROACHES (per-symbol)                   │
│ ALERT_APPROACHES_DEFAULT (fallback)                    │
│ ALERT_APPROACHES (legacy fallback)                     │
│                                                        │
│ Each maps to Executor in alert/approach/[NAME]/        │
└────────────────────────────────────────────────────────┘

REMOVED (Phase 2 Cleanup):
├─ MODE setting (DEVELOPMENT/DEPLOYMENT distinction)
├─ DEV_DATA_DATE_RANGE configuration
└─ Local JSON file loading logic
```

---

## 9. Component Responsibility Map

```
┌───────────────────────────────────────────────────────────────┐
│              COMPONENT RESPONSIBILITY MAP                     │
└───────────────────────────────────────────────────────────────┘

ORCHESTRATION LAYER:
├─ SymbolAlertManager      → Multi-symbol coordination (threads)
└─ SymbolAlerter           → Single-symbol supervision (resilience)

DATA LAYER:
├─ DataServiceOrchestrator → Unified data access (facade)
├─ HistoricalDataManager   → Caching & retrieval
├─ DataProviderCoordinator → Provider routing & auto-detect
├─ 3 Providers             → External data sources
└─ DataProcessor           → Timezone, price adjustments

ANALYSIS LAYER:
├─ Executor (Abstract)     → Framework for approaches
├─ 6 Approach Executors    → Specific detection logic
├─ PriceMovementAlerter    → Price level monitoring
└─ Analyzer (Abstract)     → Shared calculations

NOTIFICATION LAYER:
├─ NotificationManager     → Multi-channel dispatch
├─ Email Service           → Email notifications
├─ SMS Service             → SMS notifications
├─ Ntfy Service            → Ntfy notifications
└─ ClosePositionScheduler  → Time-based position closing

TIME LAYER:
└─ TimeSimulator           → System time vs simulated time

CONFIGURATION LAYER:
├─ settings.py             → Primary configuration
├─ data_provider_settings  → Provider configuration
├─ signal_settings         → Signal configuration
├─ price_alert_settings    → Price alert configuration
├─ notification_settings   → Notification channel configuration (Phase 2)
└─ validation_settings     → Profit/loss validation thresholds (Phase 2)
```

---

## 10. Key Decision Points Matrix

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Key decisions simplified to LIVE vs REPLAY only

┌─────────────────────────────────────────────────────────────────┐
│                KEY DECISION POINTS (PHASE 2+)                   │
└─────────────────────────────────────────────────────────────────┘

Decision              Location                Line   Decides
─────────────────────────────────────────────────────────────────
TimeSimulator init    symbol_alerter.py       251    LIVE vs REPLAY
Loop exit             time_utils.py           78     Indefinite vs Bounded
Time advancement      time_utils.py           74     Simulate or not
Trading hours skip    symbol_alerter.py       273    Sleep vs Jump
Error recovery        symbol_alerter.py       234    Restart vs Exit
Report directory      report_utils.py         54     reports/ vs replay/
Approach selection    symbol_alerter.py       160    Symbol vs default
Data provider         data_services/          ?      Which provider
Notification send     notification_mgr.py     ?      Deduplication check

REMOVED (Phase 2 Cleanup):
├─ MODE selection → No longer DEVELOPMENT vs DEPLOYMENT
└─ Data loading logic → No local JSON file processing
```

---

## 11. Execution Timeline - REPLAY MODE Example

```
CONFIG:
  DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"
  MONITORING_INTERVAL_SECONDS = 57
  Last trading session ends at 14:27

TIMELINE:

09:05:00 ─ Loop iteration 1
           current_time = 09:05:00
           is_trading_hours? YES
           fetch_data & process
           advance() → 09:05:57

09:05:57 ─ Loop iteration 2
           current_time = 09:05:57
           is_trading_hours? YES
           fetch_data & process
           advance() → 09:06:54

... (many iterations) ...

11:30:00 ─ Morning session ends
           current_time = 11:30:00
           is_trading_hours? NO (between sessions)
           advance() → 11:30:57
           continue

12:00:00 ─ Still between sessions
           current_time = 12:00:00
           is_trading_hours? NO
           advance() → 12:00:57
           continue

13:00:00 ─ Afternoon session starts
           current_time = 13:00:00
           is_trading_hours? YES
           fetch_data & process
           advance() → 13:00:57

... (many iterations) ...

14:27:00 ─ Loop iteration N
           current_time = 14:27:00
           is_running()? NO (current > end_of_day)
           Loop exits
           Session completes

STATUS: Reports saved to reports_replay/
```

---

## 12. System States & Transitions

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    System now simplified with only LIVE and REPLAY

┌──────────────────────────────────────────────────────┐
│          SYSTEM STATE MACHINE (PHASE 2+)             │
└──────────────────────────────────────────────────────┘

                    STARTUP
                       │
                       ▼
        ┌──────────────────────────┐
        │ SymbolAlertManager       │
        │ .execute()               │
        └──────────────────────────┘
                       │
         ┌─────────────┴─────────────┐
         │                           │
         ▼                           ▼
    LIVE MODE                  REPLAY MODE
    │                           │
    ├─ SUPERVISOR LOOP          ├─ SUPERVISOR LOOP
    │  ├─ MONITORING SESSION     │  ├─ MONITORING SESSION
    │  │  ├─ LIVE_RUNNING        │  │  ├─ REPLAY_RUNNING
    │  │  │  └─ SUSPENDED        │  │  │  └─ WAITING
    │  │  │     (non-hours)      │  │  │     (non-hours)
    │  │  │                      │  │  │
    │  │  └─ Auto-restart        │  │  └─ Clean exit
    │  │     (crashes)           │  │     (end_of_day)
    │  │                         │  │
    │  └─ 24/7 Operation         │  └─ Deterministic
    │                            │     Single run
    │                            │
    └─────────────────────────────┘
              │
              ▼
         SHUTDOWN

TRANSITIONS:
- LIVE:   Supervisor continuously restarts failed sessions
- REPLAY: Exits cleanly when end_of_day reached or error occurs
```

---

## 13. Current System Configuration (April 8, 2026)

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Configuration now uses LIVE vs REPLAY only (Phase 2+)

┌──────────────────────────────────────┐
│   CURRENT CONFIGURATION STATE (Phase 1 - Final)  │
├──────────────────────────────────────┤
│ MODE = "DEPLOYMENT"                  │
│ [TO BE REMOVED IN PHASE 2]            │
│                                       │
│ DEBUG_REPLAY_START_TIME =            │
│    "2026-04-08 09:05:00"            │
│ SYMBOLS = ["VN30F1M", "VN30"]        │
│ MONITORING_INTERVAL_SECONDS = 57     │
│ MARKET_COUNTRY_CODE = "VN"           │
│ ENABLED_NOTIFICATION_CHANNELS =      │
│    [Email, SMS, Ntfy]                │
└──────────────────────────────────────┘

EXECUTION MODE: REPLAY DEPLOYMENT

BEHAVIOR:
├─ TimeSimulator Mode: REPLAY
├─ Time Source: Simulated from 09:05 on April 8
├─ Loop Exit: 14:27 (end of last trading session)
├─ Non-trading Hours: Jump forward
├─ Error Handling: Exit immediately
├─ Report Directory: reports_replay/
└─ Status: Simulating trading day in fast-forward

EXECUTION:
├─ Symbol 1: VN30F1M → Separate thread
├─ Symbol 2: VN30 → Separate thread
├─ Concurrent monitoring of both symbols
└─ Alerts saved to reports_replay/[symbol]/deployment/

PHASE 2 CHANGES (Upcoming):
├─ Remove MODE setting entirely
├─ Remove local JSON file loading
├─ Simplify to LIVE vs REPLAY only (via DEBUG_REPLAY_START_TIME)
└─ Clean up all DEVELOPMENT mode code paths
```

---

## 14. Performance Metrics & Report Generation (Phase 2)

```
⚠️  NOTE: Report generation layer added in Phase 2

REPORT GENERATION ARCHITECTURE:

CentralizedReportGenerator
├─ Purpose: Orchestrate backtesting and trade simulation
├─ Input: Historical data + trading alerts
├─ Process: Run traders for each day → Consolidate results
└─ Output: Performance metrics and scenario analysis

WORKFLOW (2 Base + 3 Optional Steps):

Base Steps:
├─ Step 1: IndividualTradeSimulator
│          ├─ Simulates trades for each day
│          ├─ Applies profit/loss thresholds (validation_settings)
│          ├─ Generates daily reports
│          └─ Tracks scenario metrics (5 profit × 4 loss = 20 scenarios)
│
└─ Step 2: ConsolidateReports
           ├─ Aggregates daily results
           ├─ Summarizes across entire backtest period
           └─ Creates consolidated performance report

Optional Steps (Enhancement):
├─ Step 3: SupportResistanceDetector
│          ├─ Detects support/resistance levels
│          ├─ Correlates with alerts
│          └─ Improves analysis accuracy (optional)
│
├─ Step 4: PerformanceAnalyzer
│          ├─ Analyzes overall metrics
│          ├─ Calculates statistical measures
│          └─ Provides deep performance insights (optional)
│
└─ Step 5: [Custom Extensions]
           └─ Framework allows additional analysis modules

SCENARIO SYSTEM:

Profit Thresholds (5 options):
├─ 1%
├─ 2%
├─ 3%
├─ 5%
└─ 10%

Loss Thresholds (4 options):
├─ -1%
├─ -2%
├─ -3%
└─ -5%

Total Scenarios: 5 × 4 = 20 combinations
Each scenario generates separate performance metrics

REPORT STRUCTURE:

reports_replay/
├─ [symbol]/
│  ├─ deployment/
│  │  ├─ daily_alerts/    → Individual trading alerts
│  │  ├─ daily_reports/   → Daily performance by scenario
│  │  └─ consolidated/    → Aggregated results
│  │
│  ├─ scenarios/          → 20 separate scenario folders
│  │  ├─ profit_1_loss_1/
│  │  ├─ profit_1_loss_2/
│  │  └─ ... [18 more combinations]
│  │
│  └─ analysis/           → Overall performance analysis
│     ├─ metrics_summary.json
│     └─ visualization_data.json
│
└─ [symbol 2]/
   └─ [same structure]

CONFIGURATION FOR REPORT GENERATION:

notification_settings.py
├─ Report generation channel selection
├─ Email recipients for consolidated reports
└─ Notification frequency and triggers

validation_settings.py
├─ Profit thresholds (%, values)
├─ Loss thresholds (%, values)
└─ Validation rules for scenario acceptance

DATA FLOW:

Raw Alerts → IndividualTradeSimulator
               ↓
           (Run for each day)
               ↓
           Daily Reports (per scenario)
               ↓
         ConsolidateReports
               ↓
       Consolidated Report (per scenario)
               ↓
     (Optional) SupportResistanceDetector
               ↓
     (Optional) PerformanceAnalyzer
               ↓
    Final Performance Analysis
```

---

## ⚠️ Critical Architectural Decision

**DEVELOPMENT MODE IS BEING REMOVED IN PHASE 2**

All visual guides in this document have been updated to reflect the critical architectural decision:
- ❌ DEVELOPMENT mode → **WILL BE REMOVED**
- ✅ LIVE mode → Determined by `DEBUG_REPLAY_START_TIME = None`
- ✅ REPLAY mode → Determined by `DEBUG_REPLAY_START_TIME = "timestamp"`

**For complete details, see:** `CRITICAL_ARCHITECTURAL_DECISION.md`

---

**These visual guides complement the detailed text documentation.**

**See PHASE1_INDEX.md for navigation between the three documentation files.**
