# System Architecture Overview - Complete End-to-End

**Status**: ✅ Complete System Reference  
**Purpose**: Understand the entire trading alert system architecture, from entry point to delivery  
**Scope**: **Complete system-wide architecture** (from SymbolAlertManager through all components to report generation and live trade execution)  
**Audience**: All developers, architects, operations, stakeholders  
**Last Updated**: May 29, 2026

---

## 🎯 Executive Summary

The **Stock Trading Alert System** is a real-time market analysis platform that:

1. **Monitors** multiple symbols across different exchanges (Vietstock, Binance)
2. **Analyzes** price action using 8 trading approaches: TRADE (5 active) and ANNOUNCE (3) — plus 2 archived TRADE approaches not currently wired
3. **Detects** trading opportunities via per-approach resolution analysis (configurable: 1m, 5m, 15m, 1h, etc.)
4. **Validates** signals using threshold-based rules
5. **Notifies** users via 4 registered channels: Email ✅, Slack ✅, Ntfy ✅ (validated); SMS ⚠️ (not yet validated)
6. **Executes** live DCA bracket trades on Binance perpetual futures (DEPLOYMENT mode only)
7. **Records** alerts and generates performance reports

**Core Operating Modes**:
- 🔴 **LIVE Mode** - Real-time production monitoring (indefinite, auto-recovering)
- 🟢 **REPLAY Mode** - Historical simulation and backtesting (deterministic, bounded)

---

## 🏗️ System Architecture (Complete Flow)

```
┌────────────────────────────────────────────────────────────────────────────┐
│                    TRADING ALERT SYSTEM - END TO END                       │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: ENTRY POINT                                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ SymbolAlertManager (Multi-Symbol Orchestrator)                      │  │
│  │ Location: src/stockreports/alert/symbol_alert_manager.py           │  │
│  │ Responsibility: Coordinate monitoring of multiple symbols           │  │
│  │ Pattern: ThreadPoolExecutor for concurrent symbol processing       │  │
│  │                                                                     │  │
│  │ For each SYMBOL:                                                   │  │
│  │ ├─ Load symbol configuration                                       │  │
│  │ ├─ Initialize SymbolAlerter                                        │  │
│  │ └─ Submit to thread pool for monitoring                            │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: SYMBOL-LEVEL COORDINATION                                        │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ SymbolAlerter (Symbol-Specific Orchestrator)                        │  │
│  │ Location: src/stockreports/alert/symbol_alerter.py                 │  │
│  │ Responsibility: Main monitoring loop for one symbol                 │  │
│  │ Threading: Runs in dedicated thread from ThreadPoolExecutor         │  │
│  │                                                                     │  │
│  │ Per Monitoring Cycle:                                              │  │
│  │ ├─ Fetch latest OHLCV candle for the symbol                       │  │
│  │ ├─ Call ResolutionCoordinator to map approaches to resolutions     │  │
│  │ ├─ For each resolution: run configured approaches                 │  │
│  │ ├─ Combine results from all resolutions                           │  │
│  │ ├─ Store alerts to report files                                   │  │
│  │ └─ Sleep until next monitoring interval                           │  │
│  │                                                                     │  │
│  │ Modes:                                                              │  │
│  │ • LIVE:  Indefinite loop, auto-restart on errors                  │  │
│  │ • REPLAY: Loop until end_of_day, exit on errors                   │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: RESOLUTION & APPROACH COORDINATION                                │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ ConfigurationOrchestrator (Approach & Resolution Mapper)            │  │
│  │ Location: src/stockreports/services/executor_configuration_service/ │  │
│  │           orchestrator.py                                           │  │
│  │ Responsibility: Resolve which approaches to run and at what         │  │
│  │                 resolution for a given symbol                       │  │
│  │                                                                     │  │
│  │ Called by SymbolAlerter._perform_monitoring_session():              │  │
│  │ ├─ get_supported_approaches(symbol)        → all approach names     │  │
│  │ ├─ get_supported_approaches(symbol,        → TRADE approach names   │  │
│  │ │     ApproachType.TRADE)                                          │  │
│  │ ├─ get_supported_approaches(symbol,        → ANNOUNCE approach names│  │
│  │ │     ApproachType.ANNOUNCE)                                       │  │
│  │ ├─ get(symbol, approach_name)              → approach config        │  │
│  │ │    └─ config.resolution  (e.g. 1, 5, 15, 60)                    │  │
│  │ └─ get_symbol_trading_hours(symbol)        → trading session config │  │
│  │                                                                     │  │
│  │ ApproachType (src/stockreports/model/approach_type.py):             │  │
│  │ • TRADE   — signal-based strategies → full Executor pipeline        │  │
│  │ • ANNOUNCE — real-time event alerts → AnnouncementAlerterBase       │  │
│  │                                                                     │  │
│  │ Source config: executor_approach_configuration.json                 │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│              ┌──────────────────┴──────────────────┐                      │
│              │ TRADE approaches                    │ ANNOUNCE approaches   │
│              ▼                                     ▼                      │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4a: TRADE APPROACH EXECUTION (7 Signal-Based Strategies)             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TASK-3 in SymbolAlerter._perform_monitoring_session()                     │
│  For each TRADE approach at its configured resolution:                     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Executor (Trading Strategy Implementation)                         │  │
│  │ Pattern: Executor → Analyzer → Validator                           │  │
│  │ Location: src/stockreports/alert/approach/{APPROACH}/              │  │
│  │ Responsibility: Detect trading signals for this strategy           │  │
│  │                                                                     │  │
│  │ Common Executor Actions (ALL approaches follow this pattern):       │  │
│  │ ├─ Load approach-specific configuration via ConfigurationOrchestrator│  │
│  │ │  ├─ Thresholds (price, volume, ratio limits)                    │  │
│  │ │  └─ Window sizes (lookback periods)                             │  │
│  │ │  └─ Source: executor_approach_configuration.json                │  │
│  │ │                                                                  │  │
│  │ ├─ Analyze market data using Analyzer                             │  │
│  │ │  └─ Call pure calculation methods (body ratio, volume, etc.)    │  │
│  │ │                                                                  │  │
│  │ ├─ Validate signals against business rules using Validator        │  │
│  │ │  └─ Call pure verification methods (threshold checks, etc.)    │  │
│  │ │                                                                  │  │
│  │ ├─ Generate alerts if all validations pass                        │  │
│  │ │  └─ Create AlertData with: timestamp, symbol, signal, metrics   │  │
│  │ │                                                                  │  │
│  │ ├─ Handle exceptions gracefully                                   │  │
│  │ │  └─ Missing data, invalid inputs, errors                       │  │
│  │ │                                                                  │  │
│  │ └─ Return AlertResult (confirmed_alerts: List[AlertData])         │  │
│  │                                                                     │  │
│  │ TRADE APPROACHES (5 active):                                      │  │
│  │ • STRONG_CANDLE             - Strong candle body detection         │  │
│  │ • VRA                       - Volume Rate of Change analysis       │  │
│  │ • ICHIMOKU                  - Ichimoku cloud analysis              │  │
│  │ • CONSISTENT_MOMENTUM       - Consistent candle color patterns     │  │
│  │ • REVERSAL_ANCHOR_SIGNAL_CANDLE - Reversal with anchor candle      │  │
│  │                                                                     │  │
│  │ ARCHIVED (not wired into orchestrator):                            │  │
│  │ • VOLUME_SPIKE_CONFIRMATION - Volume spike with price confirmation │  │
│  │ • CONSISTENT_VOLUME_ANCHOR  - Volume-anchored consistency pattern  │  │
│  │                                                                     │  │
│  │ Key Characteristic: Each approach is INDEPENDENT                  │  │
│  │ ├─ Can use different analyzers and validators                     │  │
│  │ ├─ Can have different thresholds and rules                        │  │
│  │ ├─ Each approach runs at its own configured resolution            │  │
│  │ └─ One failure doesn't affect others                              │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4b: ANNOUNCE APPROACH EXECUTION (3 Real-Time Event Alerts)           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  TASK-2 in SymbolAlerter._perform_monitoring_session()                     │
│  For each ANNOUNCE approach at its configured resolution:                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ AnnouncementAlertOrchestrator                                       │  │
│  │ Location: src/stockreports/alert/announce/orchestrator.py          │  │
│  │ Responsibility: Run announcement-type alerters (price/volume events)│  │
│  │                                                                     │  │
│  │ Pattern: AnnouncementAlerterBase (ABC) — no Analyzer/Validator     │  │
│  │ Factory: _AnnouncementAlertFactory                                  │  │
│  │          (src/stockreports/alert/announce/factory.py)               │  │
│  │                                                                     │  │
│  │ ANNOUNCE APPROACHES (3):                                           │  │
│  │ • LARGE_CANDLE        - Large candle body detection                │  │
│  │   Location: src/stockreports/alert/announce/approach/LARGE_CANDLE/ │  │
│  │ • LARGE_VOLUME_CANDLE - Large candle with volume confirmation       │  │
│  │   Location: …/announce/approach/LARGE_VOLUME_CANDLE/               │  │
│  │ • PRICE_MOVEMENT      - Price level crossing alerts                 │  │
│  │   Location: …/announce/approach/PRICE_MOVEMENT/                    │  │
│  │                                                                     │  │
│  │ Returns: AlertResult (confirmed_alerts: List[AlertData])           │  │
│  │ On alert → immediately dispatched to NotificationServiceOrchestrator│  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 5: DATA SERVICES                                                     │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ DataServiceOrchestrator (Data Fetching & Caching)                   │  │
│  │ Location: src/stockreports/data_services/orchestrator.py            │  │
│  │ Responsibility: Unified data access across multiple sources         │  │
│  │                                                                     │  │
│  │ Features:                                                            │  │
│  │ ├─ Smart caching (avoid redundant API calls)                       │  │
│  │ ├─ Multi-source support (Vietstock, Binance API, Binance CCXT)     │  │
│  │ ├─ Resolution aggregation (convert 1m → 5m, 15m, 1h, etc.)        │  │
│  │ ├─ Error handling with fallbacks                                   │  │
│  │ ├─ Data validation                                                 │  │
│  │ └─ Automatic refresh intervals                                     │  │
│  │                                                                     │  │
│  │ Supported Data Providers (Provider enum):                           │  │
│  │ • Provider.VIETSTOCK    → VietstockProvider                         │  │
│  │   Location: …/providing/vietstock/provider.py                      │  │
│  │ • Provider.BINANCE      → BinanceAPIProvider                        │  │
│  │   Location: …/providing/binance/api_provider.py                    │  │
│  │ • Provider.BINANCE_CCXT → BinanceCCXTProvider                       │  │
│  │   Location: …/providing/binance/ccxt_provider.py                   │  │
│  │                                                                     │  │
│  │ All providers extend BaseDataProvider (ABC) and use the context     │  │
│  │ manager pattern — connection cleanup guaranteed each cycle:         │  │
│  │ ├─ Guarantees connection cleanup on every monitoring cycle          │  │
│  │ ├─ Solves 1-2 hour timeout issue from connection reuse             │  │
│  │ ├─ Fresh connection every cycle prevents stale sockets             │  │
│  │ └─ Validated for 24+ hour operation without timeouts ✅            │  │
│  │                                                                     │  │
│  │ Technical Details:                                                  │  │
│  │ • DataProviderCoordinator uses: with provider: pattern             │  │
│  │ • BaseDataProvider provides: __enter__(), __exit__(), close()      │  │
│  │ • BinanceAPIProvider overrides close() for HTTP session cleanup     │  │
│  │ • BinanceCCXTProvider overrides close() for exchange cleanup       │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 6: ALERT AGGREGATION & STORAGE                                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Report Generation & Storage                                         │  │
│  │ Location: src/stockreports/utils/report_utils.py                   │  │
│  │ Responsibility: Collect and store alerts with metadata              │  │
│  │                                                                     │  │
│  │ Storage Strategy:                                                   │  │
│  │ • LIVE Mode:  reports/ (production alerts)                         │  │
│  │ • REPLAY Mode: reports_replay/ (test simulations)                  │  │
│  │                                                                     │  │
│  │ Alert Format:                                                       │  │
│  │ ├─ DataFrame with columns:                                         │  │
│  │ │  • timestamp                                                     │  │
│  │ │  • symbol                                                        │  │
│  │ │  • approach                                                      │  │
│  │ │  • resolution (1m/5m/15m/1h)                                   │  │
│  │ │  • signal (BUY/SELL/NEUTRAL)                                    │  │
│  │ │  • confidence                                                    │  │
│  │ │  • metrics (calculated values)                                   │  │
│  │ └─ Sortable by timestamp                                           │  │
│  │                                                                     │  │
│  │ Deduplication:                                                      │  │
│  │ • Same symbol + approach + resolution within 5 min → merged        │  │
│  │ • Prevents duplicate notifications                                 │  │
│  │ • Maintains alert integrity                                        │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐

│ LAYER 7: NOTIFICATION DELIVERY                                             │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Notification Delivery Orchestrator (Config-Driven Multi-Channel Delivery) │  │
│  │ Location: src/stockreports/services/external/                       │  │
│  │           notification_services/orchestrator.py                     │  │
│  │ Responsibility: Modular, config-driven notification dispatch, deduplication, and channel orchestration │  │
│  │                                                                     │  │
│  │ Channel System (ChannelFactory + ChannelType enum):                 │  │
│  │ ├─ ChannelType.EMAIL → EmailNotificationChannel  (SMTP)            │  │
│  │ ├─ ChannelType.SMS   → SMSNotificationChannel                      │  │
│  │ ├─ ChannelType.NTFY  → NtfyNotificationChannel  (web push)         │  │
│  │ └─ ChannelType.SLACK → SlackNotificationChannel (Block Kit webhook) │  │
│  │                                                                     │  │
│  │ All channels extend BaseNotificationChannel (ABC):                  │  │
│  │ ├─ send(notification) → normalize → _send(AlertNotification)       │  │
│  │ ├─ validate_config()  → raises ValueError if misconfigured         │  │
│  │ └─ _get_run_context_footer() → NotificationContext                 │  │
│  │      (appends Env + RunMode footer to every payload)               │  │
│  │                                                                     │  │
│  │ Scheduler Integration:                                              │  │
│  │ ├─ Scheduler handles reminders, close position, and per-symbol/approach delays │  │
│  │ ├─ Robust state management for scheduled notifications              │  │
│  │                                                                     │  │
│  │ Delivery Features:                                                  │  │
│  │ ├─ Deduplication of notifications                                  │  │
│  │ ├─ Configurable enablement per symbol/approach/signal/channel      │  │
│  │ ├─ Retry on failure, channel isolation                             │  │
│  │ ├─ Filtering by alert type, symbol, approach, resolution, confidence│  │
│  │ └─ All logic driven by hierarchical configuration                   │  │
│  │                                                                     │  │
│  │ Error Handling:                                                     │  │
│  │ ├─ Channel failure isolation (one failure ≠ system failure)        │  │
│  │ ├─ Automatic retry with exponential backoff                        │  │
│  │ ├─ Failed alerts logged for manual review                          │  │
│  │ └─ Alert not lost if delivery fails                                │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 8: PERFORMANCE ANALYSIS (Optional)                                   │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Trade Simulation & Backtesting Engine                               │  │
│  │ Location: src/stockreports/utils/report_utils.py                   │  │
│  │           src/stockreports/alert/model/reports_models.py           │  │
│  │ Responsibility: Analyze strategy performance offline                │  │
│  │                                                                     │  │
│  │ Features:                                                            │  │
│  │ ├─ Historical trade simulation                                      │  │
│  │ ├─ Multi-scenario testing (9 stop-loss levels: 2.5-9.0 points)    │  │
│  │ ├─ Fixed profit target analysis (2.0 points)                       │  │
│  │ ├─ Performance metrics calculation                                  │  │
│  │ │  • Win rate                                                      │  │
│  │ │  • Profit factor                                                 │  │
│  │ │  • Max drawdown                                                  │  │
│  │ │  • Sharpe ratio                                                  │  │
│  │ ├─ Optional support/resistance level detection                     │  │
│  │ └─ Optional parameter optimization                                 │  │
│  │                                                                     │  │
│  │ Output: CSV reports with detailed trade logs                       │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 9: OPERATIONAL SUPPORT                                               │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Multiple Operational Capabilities                                   │  │
│  │ Location: src/stockreports/web.py, src/stockreports/cli.py,        │  │
│  │           src/stockreports/utils/log_factory.py, Dockerfile,       │  │
│  │           docker-compose.yml                                        │  │
│  │                                                                     │  │
│  │ 1. WEB API & HEALTH CHECKS                                          │  │
│  │    • Flask REST API (src/stockreports/web.py)                      │  │
│  │    • Health endpoint: GET /health                                   │  │
│  │      └─ Returns: {"status": "ok"}                                   │  │
│  │    • Background thread management                                   │  │
│  │    • Graceful shutdown handling                                     │  │
│  │    • Docker & Gunicorn integration                                  │  │
│  │                                                                     │  │
│  │ 2. STRUCTURED LOGGING                                               │  │
│  │    • Unified logging via log_factory.py                            │  │
│  │    • Per-symbol file logging: logs/{MODE}/alerter_{SYMBOL}.log    │  │
│  │    • Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL             │  │
│  │    • Manager logging: logs/{MODE}/alerter.log                      │  │
│  │    • Flexible destination: console + file (in interactive mode)    │  │
│  │    • Structured context: symbol, approach, status, validation      │  │
│  │                                                                     │  │
│  │ 3. ERROR RECOVERY                                                   │  │
│  │    • ThreadPoolExecutor with exception handlers                     │  │
│  │    • Per-symbol thread isolation (failure ≠ system failure)         │  │
│  │    • Graceful degradation on data fetch errors                      │  │
│  │    • Automatic log file rotation                                    │  │
│  │    • Detailed error context capture                                 │  │
│  │                                                                     │  │
│  │ 4. CONFIGURATION MANAGEMENT                                         │  │
│  │    • Settings validation at startup (symbol list, thresholds)       │  │
│  │    • Environment variables for deployment injection                 │  │
│  │    • Timezone & market code configuration                           │  │
│  │    • Modular settings via config/loader.py                         │  │
│  │                                                                     │  │
│  │ 5. DEPLOYMENT INFRASTRUCTURE                                        │  │
│  │    • Docker containerization (Python 3.12 slim)                    │  │
│  │    • Docker Compose: Development, Staging, Production              │  │
│  │    • Kubernetes manifests for orchestration                         │  │
│  │    • Resource limits & guarantees (CPU, memory)                     │  │
│  │    • Credential injection via environment variables                 │  │
│  │    • Multi-channel notification support (Email ✅, Slack ✅, Ntfy ✅; SMS ⚠️ not yet validated) │  │
│  │                                                                     │  │
│  │ 6. MODE SWITCHING                                                   │  │
│  │    • DEPLOYMENT: Concurrent monitoring (indefinite, auto-recover)  │  │
│  │    • DEVELOPMENT: Sequential processing (for debugging)             │  │
│  │    • REPLAY: Historical simulation with fixed timestamps            │  │
│  │    • Mode-specific output directories                               │  │
│  │                                                                     │  │
│  │ 7. COMMAND-LINE INTERFACE                                           │  │
│  │    • Python CLI (src/stockreports/cli.py)                          │  │
│  │    • Mode selection: --mode [deployment|development]                │  │
│  │    • Verbose logging: --verbose flag                                │  │
│  │    • Help documentation: --help                                     │  │
│  │                                                                     │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Status: All operational support components implemented and documented     │
│  Dependencies: Flask (web), logging (Python stdlib), Docker, Gunicorn     │
│  Documentation: OPERATIONS_DEPLOYMENT_GUIDE.md, API_DOCUMENTATION.md     │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 10: TRADE EXECUTION SERVICE  ⚡ NEW                                  │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Integration Point: Fired from Layer 2 (SymbolAlerter TASK-3) in a        │
│  daemon thread whenever a TRADE-type approach produces a confirmed alert   │
│  AND the alert is not expired AND MODE == DEPLOYMENT.                      │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ TradingServiceOrchestrator (Public Facade)                          │  │
│  │ Location: src/stockreports/trade_service/orchestrator.py            │  │
│  │ Responsibility: Thin facade — receives AlertData from SymbolAlerter, │  │
│  │   dispatches orchestrate_bracket_order in a dedicated daemon thread. │  │
│  │                                                                     │  │
│  │ Pattern: Facade + Registry + Strategy                               │  │
│  │                                                                     │  │
│  │ Internal chain:                                                     │  │
│  │ ├─ TradingCoordinator                                              │  │
│  │ │  └─ Selects the correct platform for the alert's symbol          │  │
│  │ ├─ TradingPlatformRegistry                                         │  │
│  │ │  └─ Symbol → Platform mapping (e.g. BTCUSDT-PERP →              │  │
│  │ │     BinancePerpetualTrading)                                     │  │
│  │ └─ BinancePerpetualTrading (live implementation)                   │  │
│  │    └─ orchestrate_bracket_order(alert, time_simulator)             │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                                 ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ BinancePerpetualTrading — Full DCA Bracket Lifecycle                │  │
│  │ Location: …/platforms/binance_perpetual_trading.py                  │  │
│  │                                                                     │  │
│  │ Step 1 — Set leverage (once per symbol per process)                │  │
│  │   POST /fapi/v1/leverage                                           │  │
│  │                                                                     │  │
│  │ Step 2 — Place DCA ladder (7 LIMIT orders, USDT-sized)             │  │
│  │   Pre-flight guards:                                               │  │
│  │   ├─ Close diverged same-side position if price drifted > 100 USDT │  │
│  │   ├─ Absorb any opposite-side position into first order qty        │  │
│  │   └─ Assert available balance ≥ required margin × 1.5             │  │
│  │   POST /fapi/v1/batchOrders (chunks of ≤5)                        │  │
│  │                                                                     │  │
│  │ Step 2b — Wait for position to open                                │  │
│  │   Poll _get_position_info every 10s up to 3600s                   │  │
│  │   If no position confirmed → cancel ladder, return TIMEOUT         │  │
│  │                                                                     │  │
│  │ Step 3 — _monitor_ladder (blocking, runs in daemon thread)         │  │
│  │   ├─ Phase A: Poll position until first LIMIT fills               │  │
│  │   ├─ Phase B: On each fill → recalculate TP/SL from avg entry,    │  │
│  │   │           cancel stale bracket, place new TP + SL algo orders  │  │
│  │   │           POST /fapi/v1/algoOrder ×2 (CONDITIONAL type)       │  │
│  │   ├─ Phase B′: On subsequent fills → re-bracket with updated qty  │  │
│  │   ├─ Phase C: Cancel remaining LIMIT orders after 2000s timeout   │  │
│  │   ├─ Phase D: On TP fill → cancel SL; on SL fill → cancel TP     │  │
│  │   │           OcoOutcome: TP_FILLED | SL_FILLED |                 │  │
│  │   │           EXTERNAL_TERMINAL | TIMEOUT                         │  │
│  │   └─ Exit: when no open LIMIT + no open TP/SL algo orders remain  │  │
│  │                                                                     │  │
│  │ Config: src/…/config/binance_perpetual_config.py                   │  │
│  │ Trade doc: TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/              │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Key design rules:                                                         │
│  • Trade execution NEVER blocks the SymbolAlerter monitoring loop         │
│    (always dispatched in a daemon thread)                                  │
│  • Only fires in MODE == DEPLOYMENT and only for non-expired alerts        │
│    (expiry = TRADING_EXECUTION_EXPIRED_MINUTES, default 5 min)            │
│  • All TP/SL as conditional algo orders via /fapi/v1/algoOrder —          │
│    NOT /fapi/v1/order (Binance returns -4120 otherwise)                   │
│  • Quantities are USDT-based: qty = order_usdt_amount / price             │
│  • Server time sync at startup prevents -1021 timestamp errors            │
│                                                                             │
│  Location: src/stockreports/trade_service/                                │
│  Reference: TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/                 │
│                                                                             │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow: Complete Journey of an Alert

```
1. START
   └─ Main entry point: SymbolAlertManager
      └─ For each symbol in configuration

2. FETCH DATA
   └─ Symbol monitoring loop (SymbolAlerter._perform_monitoring_session)
      └─ Retrieve latest market data for all required resolutions
         └─ DataServiceOrchestrator → DataProviderCoordinator
            └─ Provider per symbol (Vietstock / BinanceAPI / BinanceCCXT)
               └─ Returns: OHLCV candle DataFrames, keyed by resolution

3. COORDINATE APPROACHES
   └─ ConfigurationOrchestrator (per symbol)
      ├─ get_supported_approaches(symbol, ApproachType.ANNOUNCE) → announce list
      └─ get_supported_approaches(symbol, ApproachType.TRADE)    → trade list
         └─ get(symbol, approach_name).resolution → per-approach resolution

4a. EXECUTE ANNOUNCE APPROACHES  [TASK-2]
   └─ For each ANNOUNCE approach (LARGE_CANDLE, LARGE_VOLUME_CANDLE, PRICE_MOVEMENT)
      └─ AnnouncementAlertOrchestrator.run(approach, symbol, df)
         └─ _AnnouncementAlertFactory → AnnouncementAlerterBase subclass
            └─ Returns: AlertResult (confirmed_alerts: List[AlertData])
               └─ On alert → NotificationServiceOrchestrator.send_notification()

4b. EXECUTE TRADE APPROACHES  [TASK-3]
   └─ For each active TRADE approach (STRONG_CANDLE, VRA, ICHIMOKU, CONSISTENT_MOMENTUM,
      REVERSAL_ANCHOR_SIGNAL_CANDLE)
      └─ get_approach_executor(symbol, approach, resolution) → Executor
         ├─ ANALYZE: Analyzer — pure calculations (body ratio, volume, etc.)
         ├─ VALIDATE: Validator — threshold checks, business rules
         └─ GENERATE: AlertData if all validations pass

5. AGGREGATE ALERTS
   └─ Collect confirmed_alerts (List[AlertData]) from all approaches
      └─ report_utils.py
         ├─ Deduplicate overlapping signals
         └─ Save to reports/ (LIVE) or reports_replay/ (REPLAY)

6. NOTIFY  (parallel with step 6b)
   └─ NotificationServiceOrchestrator.send_notification(alert)
      └─ ChannelFactory → configured per notification_service_config.json
         ├─ EmailNotificationChannel  ✅ validated
         ├─ SlackNotificationChannel  ✅ validated
         ├─ NtfyNotificationChannel   ✅ validated
         └─ SMSNotificationChannel    ⚠️ not yet validated
            └─ All channels send independently
               └─ One channel failure doesn't block others

6b. EXECUTE TRADE  (parallel with step 6, DEPLOYMENT mode only)
   └─ For each TRADE alert where alert_age ≤ TRADING_EXECUTION_EXPIRED_MINUTES:
      └─ TradingServiceOrchestrator.orchestrate_bracket_order(alert, time_simulator)
         └─ Dispatched in daemon thread → monitoring loop never blocked
            └─ BinancePerpetualTrading runs full DCA bracket lifecycle:
               ├─ Set leverage
               ├─ Place 7 LIMIT orders (DCA ladder via /fapi/v1/batchOrders)
               ├─ Wait for position to open (poll /fapi/v2/positionRisk)
               └─ _monitor_ladder: re-bracket on fills → OCO resolution
                  (TP/SL via /fapi/v1/algoOrder — CONDITIONAL type)

7. ANALYSIS (Optional)
   └─ Trade performance analysis (report_utils.py + reports_models.py)
      └─ Offline backtesting with generated alerts
         └─ Generate performance reports and metrics

8. END
   └─ Sleep until next monitoring interval (TimeSimulator.advance())
      └─ Return to FETCH DATA (loop continues)
```

---

## 🔌 Component Dependencies

```
SymbolAlertManager
├─ SymbolAlerter
│  ├─ ConfigurationOrchestrator
│  │  └─ executor_approach_configuration.json
│  │
│  ├─ DataServiceOrchestrator
│  │  ├─ DataProviderCoordinator
│  │  │  ├─ VietstockProvider        (Provider.VIETSTOCK)
│  │  │  ├─ BinanceAPIProvider       (Provider.BINANCE)
│  │  │  └─ BinanceCCXTProvider      (Provider.BINANCE_CCXT)
│  │  └─ ProviderFactory
│  │
│  ├─ AnnouncementAlertOrchestrator  [TASK-2: ANNOUNCE approaches]
│  │  └─ _AnnouncementAlertFactory
│  │     ├─ LargeCandleAlerter        (LARGE_CANDLE)
│  │     ├─ LargeVolumeCandleAlerter  (LARGE_VOLUME_CANDLE)
│  │     └─ PriceMovementAlerter      (PRICE_MOVEMENT)
│  │
│  ├─ 5 Executors via get_approach_executor() [TASK-3: TRADE approaches — active]
│  │  ├─ StrongCandleExecutor         (STRONG_CANDLE)
│  │  │  ├─ StrongCandleAnalyzer
│  │  │  └─ StrongCandleValidator
│  │  ├─ VRAExecutor                  (VRA)
│  │  │  ├─ VRAAnalyzer
│  │  │  └─ VRAValidator
│  │  ├─ IchimokuExecutor             (ICHIMOKU)
│  │  ├─ ConsistentMomentumExecutor   (CONSISTENT_MOMENTUM)
│  │  └─ ReversalAnchorSignalCandleExecutor (REVERSAL_ANCHOR_SIGNAL_CANDLE)
│  │  [archived — code exists, not wired:]
│  │  ├─ VolumeSpikeConfirmationExecutor (VOLUME_SPIKE_CONFIRMATION)
│  │  └─ ConsistentVolumeAnchorExecutor  (CONSISTENT_VOLUME_ANCHOR)
│  │
│  └─ NotificationServiceOrchestrator
│     ├─ NotificationScheduler
│     └─ ChannelFactory
│        ├─ EmailNotificationChannel  (ChannelType.EMAIL) ✅ validated
│        ├─ SlackNotificationChannel  (ChannelType.SLACK) ✅ validated
│        ├─ NtfyNotificationChannel   (ChannelType.NTFY)  ✅ validated
│        └─ SMSNotificationChannel    (ChannelType.SMS)   ⚠️ not yet validated
│           └─ BaseNotificationChannel (ABC — shared footer logic)
│
├─ TradingServiceOrchestrator  (DEPLOYMENT mode only)
│  └─ TradingCoordinator
│     └─ TradingPlatformRegistry
│        └─ BinancePerpetualTrading
│           ├─ orchestrate_bracket_order
│           │  ├─ place_order (DCA ladder via /fapi/v1/batchOrders)
│           │  ├─ position open guard (poll /fapi/v2/positionRisk)
│           │  └─ _monitor_ladder
│           │     ├─ _place_tp_sl_batch (/fapi/v1/algoOrder ×2)
│           │     ├─ _query_algo_order  (/fapi/v1/algoOrder GET)
│           │     └─ _cancel_algo_order (/fapi/v1/algoOrder DELETE)
│           └─ Config: binance_perpetual_config.py
│
└─ (Optional) Trade Simulation Engine
   └─ Performance metrics generation
```

---

## 📊 Configuration & Modes

### LIVE Mode (Production)
```python
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = None  # Real system time

Behavior:
├─ Real-time market data fetching
├─ Indefinite monitoring loop
├─ Auto-restart on errors (supervisor pattern)
├─ Alerts saved to reports/
└─ Real notifications sent
```

### REPLAY Mode (Testing/Simulation)
```python
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"  # Specific timestamp

Behavior:
├─ Simulated market data (historical)
├─ Deterministic time progression
├─ Exit on errors (strict validation)
├─ Alerts saved to reports_replay/
└─ Notifications sent (but to test channels)
```

---

## 🎯 Multi-Resolution Strategy

Each approach is independently configured with its own resolution. The system fetches all required resolutions in one batch per cycle:

```
Symbol: VN30F1M  (example)

Resolution 1m  (always fetched — used by ANNOUNCE approaches + price alerter):
├─ LARGE_CANDLE approach       → Alert (if triggered)
├─ LARGE_VOLUME_CANDLE approach → Alert (if triggered)
└─ PRICE_MOVEMENT approach     → Alert (if triggered)

Resolution 5m  (fetched if any approach is configured at 5m):
├─ STRONG_CANDLE approach      → Alert (if triggered)
└─ VRA approach                → Alert (if triggered)

Resolution 15m (fetched if any approach is configured at 15m):
├─ ICHIMOKU approach           → Alert (if triggered)
└─ CONSISTENT_MOMENTUM approach → Alert (if triggered)

Resolution 60m (fetched if any approach is configured at 60m):
└─ REVERSAL_ANCHOR_SIGNAL_CANDLE → Alert (if triggered)

FINAL RESULT: Alerts from triggered (approach, resolution) pairs, independently
              delivered to all enabled notification channels
```

**Design**: Each approach's resolution is defined in `executor_approach_configuration.json`.  
Only the resolutions actually needed are fetched — no wasted API calls.

---

## ✅ Key Design Principles

### 1. **Separation of Concerns**
- **Executor** = Orchestration only
- **Analyzer** = Pure calculations
- **Validator** = Pure verification
- Each layer has single responsibility

### 2. **Multi-Threading Safety**
- ThreadPoolExecutor for concurrent symbol processing
- Each symbol runs in its own thread
- No shared state between threads
- Thread-safe data structures

### 3. **Error Isolation**
- Executor failure → Symbol monitoring pauses, not entire system
- Notification channel failure → Other channels still send
- Data provider failure → Fallback to alternate providers
- One approach failure → Other approaches continue

### 4. **Deterministic Testing**
- REPLAY mode with fixed timestamp
- Same input → Same output (reproducible)
- Useful for backtesting and regression testing

### 5. **Type Safety**
- Enums for all string-based identifiers
- Type hints on all functions
- IDE autocomplete support
- Catch errors at development time

### 6. **Scalability**
- Add new approaches: Just implement Executor interface
- Add new data providers: Implement provider interface
- Add new notification channels: Implement channel interface
- Minimal impact on existing code

---

## 📈 System Capabilities Matrix

| Capability | LIVE Mode | REPLAY Mode | Notes |
|------------|-----------|------------|-------|
| Multi-symbol monitoring | ✅ | ✅ | Unlimited symbols |
| Real-time analysis | ✅ | ❌ | Historical in REPLAY |
| 5 active TRADE approaches | ✅ | ✅ | Executor → Analyzer → Validator |
| 2 archived TRADE approaches | ❌ | ❌ | `enabled: false` in executor config |
| 3 ANNOUNCE approaches | ✅ | ✅ | AnnouncementAlerterBase |
| Per-approach resolution (configurable) | ✅ | ✅ | 1m, 5m, 15m, 1h, etc. |
| Auto-recovery | ✅ | ❌ | Supervisor loop in LIVE |
| Email notifications | ✅ | ✅ | Via SMTP — validated |
| Slack notifications | ✅ | ✅ | Via Incoming Webhook (Block Kit) — validated |
| Ntfy web push notifications | ✅ | ✅ | Via Ntfy — validated |
| SMS notifications | ⚠️ | ⚠️ | Not yet validated |
| Env/run-mode footer on all channels | ✅ | ✅ | BaseNotificationChannel._get_run_context_footer() |
| **Live trade execution** | ✅ | ❌ | DEPLOYMENT mode only; daemon thread |
| **DCA ladder orders** | ✅ | ❌ | 7 LIMIT orders, USDT-sized |
| **Dynamic TP/SL bracket** | ✅ | ❌ | Recalculated from avg fill price |
| **Alert expiry guard** | ✅ | ❌ | Skips stale alerts (default 5 min) |
| Performance analysis | ✅ | ✅ | Backtesting available |
| Alert deduplication | ✅ | ✅ | Within monitoring cycle |
| Report generation | ✅ | ✅ | reports/ vs reports_replay/ |
| Scheduled notifications | ✅ | ✅ | NotificationScheduler (close position, reminders) |

---

## 📚 Related Documentation

### System-Wide Architecture
- This file: `SYSTEM_ARCHITECTURE_OVERVIEW.md` (complete system overview)
- `AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_OPERATIONS.md` - Operational perspective
- `AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md` - Developer perspective
- `TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md` - Component-level details

### Executor-Level Architecture (Narrower Scope)
- `TECHNICAL_REFERENCE/EXECUTOR_PATTERN_OVERVIEW.md` - Executor pattern details (approach-level)
- `TECHNICAL_REFERENCE/EXECUTOR_PATTERN_DIAGRAMS.md` - Visual executor component diagrams
- `TECHNICAL_REFERENCE/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md` - ABC design patterns
- `IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md` - How to create executors
- `IMPLEMENTATION_GUIDES/ANALYZER_VALIDATOR_QUICK_REFERENCE.md` - ABC usage guide

### Trade Execution Service (Layer 10) ⚡ NEW
- `TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md` - Trade service architecture theory
- `TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md` - Full BinancePerpetualTrading reference (method map, config, lifecycle diagrams)
- `IMPLEMENTATION_GUIDES/LAYER_10_TRADE_EXECUTION/README.md` - How to extend trade platforms

### Data & Notifications
- `DATA_SERVICES/ARCHITECTURE.md` - Data layer design
- `IMPLEMENTATION_GUIDES/DATA_PROVIDER_EXTENSION_GUIDE.md` - Adding data sources
- `IMPLEMENTATION_GUIDES/NOTIFICATION_CHANNEL_EXTENSION_GUIDE.md` - Adding notification channels

### Implementation & Operations
- `IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md` - Production deployment
- `IMPLEMENTATION_GUIDES/TROUBLESHOOTING_GUIDE.md` - Issue resolution
- `CODE_QUALITY_STANDARDS.md` - Code expectations

---

## 🚀 Quick Start by Role

### For **Developers** (adding new approaches)
1. Read: `TECHNICAL_REFERENCE/EXECUTOR_PATTERN_OVERVIEW.md`
2. Read: `IMPLEMENTATION_GUIDES/EXECUTOR_IMPLEMENTATION_GUIDE.md`
3. Study: Existing approach in `src/stockreports/alert/approach/`
4. Implement: New Executor, Analyzer, Validator

### For **Trade Service** (extending live trading)
1. Read: `TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md`
2. Read: `TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md`
3. Study: `BinancePerpetualTrading` in `…/platforms/binance_perpetual_trading.py`
4. Extend: Add new symbol mapping in `TradingPlatformRegistry` or implement new `BaseTrading` subclass

### For **Data Integration** (adding new data sources)
1. Read: `DATA_SERVICES/ARCHITECTURE.md`
2. Read: `IMPLEMENTATION_GUIDES/DATA_PROVIDER_EXTENSION_GUIDE.md`
3. Implement: New DataProvider class

### For **Operations/DevOps** (deployment & monitoring)
1. Read: `AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_OPERATIONS.md`
2. Read: `IMPLEMENTATION_GUIDES/OPERATIONS_DEPLOYMENT_GUIDE.md`
3. Review: Health checks and monitoring

### For **Architects** (system design decisions)
1. Read: This file (`SYSTEM_ARCHITECTURE_OVERVIEW.md`)
2. Read: `TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md`
3. Read: `AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md`

---

**Status**: Tier 1 - System Orchestration ✅  
**Focus**: Complete end-to-end system architecture  
**Scope**: From SymbolAlertManager through all layers to report generation and live trade execution  
**Last Updated**: May 29, 2026
