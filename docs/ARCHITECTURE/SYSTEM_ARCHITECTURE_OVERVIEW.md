# System Architecture Overview - Complete End-to-End

**Status**: ✅ Complete System Reference  
**Purpose**: Understand the entire trading alert system architecture, from entry point to delivery  
**Scope**: **Complete system-wide architecture** (from SymbolAlertManager through all components to report generation)  
**Audience**: All developers, architects, operations, stakeholders  
**Last Updated**: April 10, 2026

---

## 🎯 Executive Summary

The **Stock Trading Alert System** is a real-time market analysis platform that:

1. **Monitors** multiple symbols across different exchanges (Vietstock, Binance, etc.)
2. **Analyzes** price action using 18+ configurable trading approaches
3. **Detects** trading opportunities via multi-resolution analysis (1m, 5m, 15m, 1h candles)
4. **Validates** signals using threshold-based rules
5. **Notifies** users via email, SMS, and web notifications
6. **Records** alerts and generates performance reports

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
│ LAYER 3: RESOLUTION COORDINATION                                           │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ ResolutionCoordinator (Multi-Resolution Approach Mapper)            │  │
│  │ Location: src/stockreports/coordination/resolution_coordinator.py   │  │
│  │ Responsibility: Map trading approaches to specific resolutions      │  │
│  │                                                                     │  │
│  │ Input: Symbol, current candle data                                 │  │
│  │ Process:                                                            │  │
│  │ ├─ Read APPROACH_RESOLUTION_MAPPING configuration                 │  │
│  │ ├─ For each configured resolution (1m, 5m, 15m, 1h):              │  │
│  │ │  ├─ Fetch candle data at that resolution                        │  │
│  │ │  ├─ Get list of approaches for this resolution                  │  │
│  │ │  └─ Yield (resolution, approach_list) tuple                     │  │
│  │ └─ Handle multi-resolution conflicts                               │  │
│  │                                                                     │  │
│  │ Output: Iterator of (resolution, approaches) tuples                │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                    ┌────────────┴────────────┐                            │
│                    │ (For each resolution)   │                            │
│                    ▼                         ▼                            │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│ LAYER 4: APPROACH EXECUTION (18+ Trading Strategies)                       │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  For each APPROACH at current RESOLUTION:                                  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Executor (Trading Strategy Implementation)                         │  │
│  │ Pattern: Executor → Analyzer → Validator                           │  │
│  │ Location: src/stockreports/alert/approach/{APPROACH}/              │  │
│  │ Responsibility: Detect trading signals for this strategy           │  │
│  │                                                                     │  │
│  │ Common Executor Actions (ALL approaches follow this pattern):       │  │
│  │ ├─ Load approach-specific configuration                           │  │
│  │ │  ├─ Thresholds (price, volume, ratio limits)                    │  │
│  │ │  └─ Window sizes (lookback periods)                             │  │
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
│  │ └─ Return AlertResult (alerts or error info)                      │  │
│  │                                                                     │  │
│  │ AVAILABLE APPROACHES (18+):                                        │  │
│  │ • STRONG_CANDLE - Strong candle detection                         │  │
│  │ • VRA - Volume Rate of Change analysis                            │  │
│  │ • ICHIMOKU - Ichimoku cloud analysis                              │  │
│  │ • CONSISTENT_MOMENTUM - Consistent color patterns                 │  │
│  │ • BREAKOUT - Breakout detection                                   │  │
│  │ • REVERSAL - Reversal pattern detection                           │  │
│  │ • VOLATILITY - Volatility-based analysis                          │  │
│  │ • And 11+ more custom strategies                                  │  │
│  │                                                                     │  │
│  │ Key Characteristic: Each approach is INDEPENDENT                  │  │
│  │ ├─ Can use different analyzers and validators                     │  │
│  │ ├─ Can have different thresholds and rules                        │  │
│  │ ├─ Runs in parallel (no blocking between approaches)              │  │
│  │ └─ One failure doesn't affect others                              │  │
│  └──────────────────────────────┬──────────────────────────────────────┘  │
│                                 │                                          │
│                    ┌────────────┴────────────┐                            │
│                    │ (For each approach)     │                            │
│                    ▼                         ▼                            │
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
│  │ ├─ Multi-source support (Vietstock, Binance, CCXT)                │  │
│  │ ├─ Resolution aggregation (convert 1m → 5m, 15m, 1h)              │  │
│  │ ├─ Error handling with fallbacks                                   │  │
│  │ ├─ Data validation                                                 │  │
│  │ └─ Automatic refresh intervals                                     │  │
│  │                                                                     │  │
│  │ Supported Data Providers:                                           │  │
│  │ • Vietstock (Vietnamese stocks/indices)                             │  │
│  │ • Binance API (Cryptocurrencies)                                    │  │
│  │ • Binance CCXT (Alternative integration)                            │  │
│  │ • Custom providers (extensible)                                     │  │
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
│  │ Location: src/stockreports/report/report_utils.py                  │  │
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
│  │ NotificationManager (Multi-Channel Delivery)                        │  │
│  │ Location: src/stockreports/notification/notification_manager.py     │  │
│  │ Responsibility: Deliver alerts through configured channels          │  │
│  │                                                                     │  │
│  │ Delivery Channels:                                                  │  │
│  │ ├─ Email (via SMTP)                                               │  │
│  │ │  ├─ Recipient configuration                                      │  │
│  │ │  ├─ Template-based formatting                                   │  │
│  │ │  ├─ Retry on failure                                            │  │
│  │ │  └─ HTML and plain text formats                                 │  │
│  │ │                                                                   │  │
│  │ ├─ SMS (via Twilio or similar)                                    │  │
│  │ │  ├─ Phone number configuration                                  │  │
│  │ │  ├─ Character limit handling                                    │  │
│  │ │  ├─ Delivery confirmation                                       │  │
│  │ │  └─ Retry on failure                                            │  │
│  │ │                                                                   │  │
│  │ └─ Web Notifications (via ntfy.sh or similar)                      │  │
│  │    ├─ Webhook integration                                          │  │
│  │    ├─ Realtime push to web/mobile                                 │  │
│  │    ├─ No phone number required                                     │  │
│  │    └─ Retry on failure                                            │  │
│  │                                                                     │  │
│  │ Error Handling:                                                     │  │
│  │ ├─ Channel failure isolation (one failure ≠ system failure)        │  │
│  │ ├─ Automatic retry with exponential backoff                        │  │
│  │ ├─ Failed alerts logged for manual review                          │  │
│  │ └─ Alert not lost if delivery fails                                │  │
│  │                                                                     │  │
│  │ Filtering:                                                          │  │
│  │ ├─ Alert type filtering (BUY/SELL/NEUTRAL)                        │  │
│  │ ├─ Symbol filtering                                                │  │
│  │ ├─ Approach filtering                                              │  │
│  │ ├─ Resolution filtering (1m/5m/15m/1h)                           │  │
│  │ └─ Confidence level filtering                                      │  │
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
│  │ Location: src/stockreports/report/trade_report.py                  │  │
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
│  │    • Multi-channel notification support (Email, SMS, Ntfy)          │  │
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
```

---

## 🔄 Data Flow: Complete Journey of an Alert

```
1. START
   └─ Main entry point: SymbolAlertManager
      └─ For each symbol in configuration

2. FETCH DATA
   └─ Symbol monitoring loop (SymbolAlerter)
      └─ Retrieve latest market data for symbol
         └─ From data service (Vietstock, Binance, or CCXT)
            └─ Returns: OHLCV candle data

3. COORDINATE RESOLUTIONS
   └─ Resolution mapping (ResolutionCoordinator)
      └─ For each configured resolution (1m, 5m, 15m, 1h)
         └─ Get list of approaches assigned to this resolution
            └─ Returns: (resolution, approaches) pairs

4. EXECUTE APPROACHES
   └─ For each approach at this resolution
      └─ Execute trading strategy (Executor)
         ├─ ANALYZE: Process data using Analyzer
         │  └─ Generate all necessary market metrics
         ├─ VALIDATE: Check signals using Validator
         │  └─ Apply business rules and thresholds
         └─ CREATE: Generate alert if all validations pass
            └─ AlertData: timestamp, symbol, approach, resolution, signal, confidence

5. AGGREGATE ALERTS
   └─ Collect results from all resolutions/approaches
      └─ Report storage system
         ├─ Combine all alerts from this monitoring cycle
         ├─ Deduplicate overlapping signals (same symbol+approach+resolution within 5min)
         └─ Save to reports/ (LIVE) or reports_replay/ (REPLAY)

6. NOTIFY
   └─ Send alerts to users (NotificationManager)
      ├─ Email channel (SMTP)
      ├─ SMS channel (Twilio or similar)
      └─ Web notification channel (ntfy.sh or similar)
         └─ All channels send independently
            └─ One channel failure doesn't block others

7. ANALYSIS (Optional)
   └─ Trade performance analysis engine (Trade Simulation)
      └─ Offline backtesting with generated alerts
         └─ Generate performance reports and metrics

8. END
   └─ Sleep until next monitoring interval
      └─ Return to FETCH DATA (loop continues)
```

---

## 🔌 Component Dependencies

```
SymbolAlertManager
├─ SymbolAlerter
│  ├─ ResolutionCoordinator
│  │  └─ DataServiceOrchestrator
│  │     ├─ VietStockProvider
│  │     ├─ BinanceAPIProvider
│  │     └─ BinanceCCXTProvider
│  │
│  └─ 18+ Executors (selected by ResolutionCoordinator)
│     ├─ StrongCandleExecutor
│     │  ├─ StrongCandleAnalyzer
│     │  │  └─ Analyzer (base class)
│     │  └─ StrongCandleValidator
│     │     └─ Validator (base class)
│     ├─ VRAExecutor
│     │  ├─ VRAAnalyzer
│     │  │  └─ Analyzer (base class)
│     │  └─ VRAValidator
│     │     └─ Validator (base class)
│     └─ ... (16 more approaches)
│
├─ Report Generation System
│  ├─ Alert storage
│  └─ Deduplication logic
│
├─ NotificationManager
│  ├─ EmailChannel
│  ├─ SMSChannel
│  └─ WebNotificationChannel
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

The system analyzes the same symbol across multiple timeframes **simultaneously**:

```
Symbol: VN30

Resolution 1m:
├─ STRONG_CANDLE approach → Alert (if triggered)
├─ VRA approach → Alert (if triggered)
└─ VOLATILITY approach → No alert

Resolution 5m:
├─ ICHIMOKU approach → Alert (if triggered)
├─ BREAKOUT approach → No alert
└─ MOMENTUM approach → Alert (if triggered)

Resolution 15m:
├─ REVERSAL approach → No alert
└─ CONSISTENT_MOMENTUM approach → Alert (if triggered)

Resolution 1h:
├─ MACD approach → No alert
└─ (other 1h-specific approaches)

FINAL RESULT: Multiple alerts, one for each triggered (resolution, approach) pair
```

**Benefit**: Avoid false signals by confirming signals across multiple timeframes

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
| 18+ trading approaches | ✅ | ✅ | All approaches available |
| Multi-resolution (1m/5m/15m/1h) | ✅ | ✅ | Simultaneous analysis |
| Auto-recovery | ✅ | ❌ | Supervisor loop in LIVE |
| Email notifications | ✅ | ✅ | Via SMTP |
| SMS notifications | ✅ | ✅ | Via Twilio/similar |
| Web notifications | ✅ | ✅ | Via ntfy.sh |
| Performance analysis | ✅ | ✅ | Backtesting available |
| Alert deduplication | ✅ | ✅ | Within 5 min window |
| Report generation | ✅ | ✅ | CSV format |
| Support/Resistance detection | ✅ | ✅ | Optional feature |
| Parameter optimization | ✅ | ✅ | Optional feature |

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
**Scope**: From SymbolAlertManager through all layers to report generation  
**Last Updated**: April 10, 2026
