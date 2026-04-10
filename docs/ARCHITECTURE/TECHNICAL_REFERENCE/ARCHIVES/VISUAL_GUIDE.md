# Technical Reference Investigation - Visual Architecture Guide

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
         ┌────┴────┐                 ┌────┴────┐
         ▼         ▼                 ▼         ▼
    ┌────────┐ ┌──────────────────┐ ┌────────┐ ┌──────────────────┐
    │ResolCoord  ResolutionStorage  │ResolCoord  ResolutionStorage │
    │ (Maps      _resolution_dfs    │(Maps       _resolution_dfs   │
    │ approach   {1: df, 5: df, ..} │approach    {1: df, 5: df, ..}│
    │ →res)      (per symbol)       │→res)       (per symbol)      │
    └────────┘ └──────────────────┘ └────────┘ └──────────────────┘
         │              │                  │              │
         └──────────────┴──────────────────┴──────────────┘
                         │
              ┌──────────────────────────────┐
              ▼                               ▼
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
        │   │    ├─ UPDATE ALL RESOLUTIONS      │ │
        │   │    │  (multi-res data fetch)     │ │
        │   │    ├─ Run price movement alerts   │ │
        │   │    │  (on 1-min data)            │ │
        │   │    ├─ Run executors (each on     │ │
        │   │    │  its configured resolution) │ │
        │   │    └─ Notify via channels         │ │
        │   └────────────────────────────────────┘ │
        └──────────────────────────────────────────┘
```

---

## 2. DEBUG_REPLAY_START_TIME Impact - Decision Tree

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Only LIVE and REPLAY modes exist (starting Implementation Guides)

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
    │   ├─ Check Scheduled Notifications:
    │   │   │
    │   │   └─ unified_scheduler.check_and_notify()
    │   │       ├─ Check 1: Order Reminder (4 min)
    │   │       ├─ Check 2: Close Position (10 min)
    │   │       └─ Returns: List of notifications to send
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

REMOVED (Implementation Guides Cleanup):
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
└─ UnifiedScheduler        → Time-based order reminders + position closing

TIME LAYER:
└─ TimeSimulator           → System time vs simulated time

CONFIGURATION LAYER:
├─ settings.py             → Primary configuration
├─ data_provider_settings  → Provider configuration
├─ signal_settings         → Signal configuration
├─ price_alert_settings    → Price alert configuration
├─ notification_settings   → Notification channel configuration (Implementation Guides)
└─ validation_settings     → Profit/loss validation thresholds (Implementation Guides)
```

---

## 10. Key Decision Points Matrix

```
⚠️  CRITICAL: DEVELOPMENT MODE REMOVED
    Key decisions simplified to LIVE vs REPLAY only

┌─────────────────────────────────────────────────────────────────┐
│                KEY DECISION POINTS (IMPLEMENTATION_GUIDES+)                   │
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

REMOVED (Implementation Guides Cleanup):
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
│          SYSTEM STATE MACHINE (IMPLEMENTATION_GUIDES+)             │
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
    Configuration now uses LIVE vs REPLAY only (Implementation Guides+)

┌──────────────────────────────────────┐
│   CURRENT CONFIGURATION STATE (Technical Reference - Final)  │
├──────────────────────────────────────┤
│ MODE = "DEPLOYMENT"                  │
│ [TO BE REMOVED IN IMPLEMENTATION_GUIDES]            │
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

IMPLEMENTATION_GUIDES CHANGES (Upcoming):
├─ Remove MODE setting entirely
├─ Remove local JSON file loading
├─ Simplify to LIVE vs REPLAY only (via DEBUG_REPLAY_START_TIME)
└─ Clean up all DEVELOPMENT mode code paths
```

---

## 14. Performance Metrics & Report Generation (Implementation Guides)

```
⚠️  NOTE: Report generation layer added in Implementation Guides
    Based on actual codebase: VALIDATION_SETTINGS.PY configuration

REPORT GENERATION ARCHITECTURE:

CentralizedReportGenerator
├─ Purpose: Orchestrate backtesting and trade simulation with multiple scenarios
├─ Input: Historical data + trading alerts
├─ Process: For each profit/loss scenario → Run daily simulations → Consolidate results
└─ Output: Scenario-based performance metrics and profitability analysis

CORE WORKFLOW (2 Required Steps):

Step 1: IndividualTradeSimulator (for each scenario, each day)
│       ├─ Loads alerts for the day
│       ├─ Simulates entry/exit for each alert
│       ├─ Applies profit_threshold and loss_threshold
│       ├─ Records outcomes: profitable, loss, breakeven
│       ├─ Dynamic profit logic: max(magnitude × 0.7, 2.0) points
│       └─ Output: Daily report for this scenario

Step 2: ConsolidateReports (once per scenario, after all days)
        ├─ Aggregates all daily reports for scenario
        ├─ Calculates metrics: win rate, avg profit/loss, max drawdown
        ├─ Summarizes across entire backtest period
        └─ Output: Consolidated scenario summary

SCENARIO SYSTEM (Based on validation_settings.py):

Profit Thresholds Configuration:
├─ VALIDATION_PRICE_THRESHOLD_PROFIT = [2.0]  (Currently: 1 value)
│  └─ Note: Actual profits use dynamic logic (magnitude × VALIDATION_MAGNITUDE_PROFIT_FACTOR)
│          Default factor: 0.7 (70% of alert magnitude)
│          Minimum profit: VALIDATION_MIN_PROFIT_FOR_SUCCESS = 1.5 points

Loss Thresholds Configuration:
├─ VALIDATION_PRICE_THRESHOLD_LOSS = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
│  └─ 9 different stop-loss levels (in points, not %)

Total Scenarios: 1 × 9 = 9 combinations
Each scenario iterates through ALL days with SAME profit/loss threshold pair

OPTIONAL FEATURES (Independent, not sequential):

Optional: Support/Resistance Detection
├─ Flag: run_sr = True/False (CLI: --run-sr-detector)
├─ File: support_resistance_detector.py
├─ Function: Detect S/R levels from historical data
├─ Parameters: start_time, end_time, resolution, min_touches
└─ Output: Updates S/R level database for future simulations

Optional: Suggested Price Updates
├─ Flag: suggestion_type = None/"structural"/"performance"/"all" (CLI: --suggestion-type)
├─ File: update_alert_files_with_suggestion.py
├─ Function: Recalculate suggested entry/exit prices
├─ Types:
│  ├─ "structural": Based on support/resistance levels
│  ├─ "performance": Based on historical profitability
│  └─ "all": Both methods
└─ Output: Updated alert files with new suggested_price fields

Optional: Performance Analysis
├─ Flag: run_analysis_flag = True/False (CLI: --run-analysis)
├─ File: analyze_overall_performance.py (src/tools/analysis/)
├─ Function: Compare scenarios, identify best/worst configurations
├─ Process: Load all consolidated reports, generate comparisons
└─ Output: Analysis report with optimization recommendations

REPORT STRUCTURE:

reports_replay/[symbol]/
├─ deployment/
│  ├─ daily_alerts/        → Individual trading alerts
│  ├─ daily_reports/       → Daily performance (one file per scenario-day)
│  └─ consolidated/        → Aggregated results per scenario
│
├─ scenarios/              → Separate results for each profit/loss combo
│  ├─ profit_2.0_loss_2.5/  → Scenario 1: profit=2.0, loss=2.5
│  ├─ profit_2.0_loss_3.0/  → Scenario 2: profit=2.0, loss=3.0
│  ├─ profit_2.0_loss_3.5/  → Scenario 3: profit=2.0, loss=3.5
│  ├─ ... (9 total scenarios)
│  └─ profit_2.0_loss_9.0/  → Scenario 9: profit=2.0, loss=9.0
│
└─ analysis/ (if --run-analysis)
   ├─ scenario_comparison.json
   ├─ best_worst_config.json
   └─ optimization_recommendations.json

CONFIGURATION PARAMETERS (validation_settings.py):

Key Trade Simulation Parameters:
├─ VALIDATION_TIME_WINDOW_MINUTES = 15
│  └─ Minutes to check if profit/loss target was met
├─ MAX_TIME_TO_TRIGGER_MINUTES = 5
│  └─ Max time from alert generation to trade entry
├─ VALIDATION_MAGNITUDE_PROFIT_FACTOR = 0.7
│  └─ Multiplier for dynamic profit calculation (70% of magnitude)
├─ VALIDATION_MIN_PROFIT_FOR_SUCCESS = 1.5
│  └─ Minimum profit (in points) to be "Success" if neither target hit
└─ VALIDATION_DATE_FILTER = None
   └─ Single date filter (None = all dates in dataset)

WORKFLOW EXECUTION PATTERN:

for profit_threshold in VALIDATION_PRICE_THRESHOLD_PROFIT:
    for loss_threshold in VALIDATION_PRICE_THRESHOLD_LOSS:
        # This is ONE SCENARIO
        
        # Step 1: For each day in date range
        for day in date_range:
            individual_trade_simulator(
                profit_threshold=profit_threshold,
                loss_threshold=loss_threshold,
                day=day
            )
        
        # Step 2: After all days for this scenario
        consolidate_reports(
            profit_threshold=profit_threshold,
            loss_threshold=loss_threshold
        )

# After ALL scenarios:
if run_sr:
    support_resistance_detector(...)
    
if suggestion_type:
    update_alert_files_with_suggestion(...)
    
if run_analysis_flag:
    analyze_overall_performance(...)
```

---

## 12. Multi-Resolution Architecture (NEW)

```
ResolutionCoordinator: Maps Approaches to Resolutions

CONFIGURATION (APPROACH_RESOLUTION_MAPPING):
┌──────────────────────────────────────────────────┐
│ "CONSISTENT_MOMENTUM" → 1   (1-minute)           │
│ "ICHIMOKU" → 1              (1-minute)           │
│ "STRONG_CANDLE" → 1         (1-minute)           │
│ "VRA" → 1                   (1-minute)           │
│ "VOLUME_SPIKE_CONFIRMATION" → 1  (1-minute)     │
│ "CONSISTENT_VOLUME_ANCHOR" → 1   (1-minute)     │
└──────────────────────────────────────────────────┘

PER-SYMBOL RESOLUTION STORAGE:

For Symbol "VN30F1M":
┌────────────────────────────────────────────────────┐
│ _resolution_dataframes = {                         │
│     1: DataFrame[...],      ← 1-min candles       │
│     5: DataFrame[...],      ← 5-min candles       │
│    15: DataFrame[...]       ← 15-min candles      │
│ }                                                  │
└────────────────────────────────────────────────────┘
        │
        ├─ Resolution 1 (Always included)
        │  ├─ Required by: PriceMovementAlerter
        │  ├─ Required by: All approaches (in this config)
        │  └─ Used as: First-run indicator
        │
        ├─ Resolution 5 (If configured)
        │  └─ Required by: Any approach mapped to 5-min
        │
        └─ Resolution 15 (If configured)
           └─ Required by: Any approach mapped to 15-min

MULTI-RESOLUTION DATA FETCH:

for each resolution in _resolution_dataframes.keys():
    latest_df = orchestrator.fetch_and_process(
        symbol=self.symbol,
        start_time=from_dt,
        end_time=to_dt,
        resolution=resolution  ← KEY: Different for each
    )
    
    if latest_df not None:
        if _resolution_dataframes[resolution] is None:
            _resolution_dataframes[resolution] = latest_df
        else:
            concat + deduplicate + sort

APPROACH EXECUTION:

for approach_name in approaches_to_run:
    resolution = coordinator.get_resolutions(approach_name)
    
    approach_df = _resolution_dataframes[resolution]
    
    executor = get_executor(approach_name)
    result = executor.run(df=approach_df)

EXAMPLE: ICHIMOKU on 15-min vs STRONG_CANDLE on 1-min

┌─────────────────────┐         ┌─────────────────────┐
│ ICHIMOKU            │         │ STRONG_CANDLE       │
│ (15-minute candles) │         │ (1-minute candles)  │
│                     │         │                     │
│ Data: 15-min df     │         │ Data: 1-min df      │
│ Lookback: 200 bars  │         │ Lookback: 50 bars   │
│ Signal: T+15        │         │ Signal: T+1         │
└─────────────────────┘         └─────────────────────┘
        └─────────────┬──────────┘
                      ▼
            Both trigger on same candle
            (if signals align)
```

---

## ⚠️ Critical Architectural Decision

**DEVELOPMENT MODE IS BEING REMOVED IN IMPLEMENTATION_GUIDES**

All visual guides in this document have been updated to reflect the critical architectural decision:
- ❌ DEVELOPMENT mode → **WILL BE REMOVED**
- ✅ LIVE mode → Determined by `DEBUG_REPLAY_START_TIME = None`
- ✅ REPLAY mode → Determined by `DEBUG_REPLAY_START_TIME = "timestamp"`

**For complete details, see:** `CRITICAL_ARCHITECTURAL_DECISION.md`

---

**These visual guides complement the detailed text documentation.**

**See PHASE1_INDEX.md for navigation between the three documentation files.**
