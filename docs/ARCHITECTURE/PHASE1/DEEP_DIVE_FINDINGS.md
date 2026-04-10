# Phase 1: Deep-Dive Code Investigation - Architecture Findings

**Date:** April 8, 2026  
**Status:** Complete - Ready for Phase 2 Architecture Documentation  
**Investigator:** AI Code Analysis

⚠️ **CRITICAL UPDATE:** See `DEBUG_REPLAY_START_TIME_INVESTIGATION.md` for two sub-modes within DEPLOYMENT.

---

## Executive Summary

✅ **User's Flow Hypothesis: CONFIRMED WITH CLARIFICATIONS**

The end-to-end flow described is **accurate but incomplete**. Investigation revealed additional critical components and nuances.

⚠️ **CRITICAL DISCOVERY:** DEPLOYMENT mode contains TWO time-based sub-modes:
- **LIVE MODE** - `DEBUG_REPLAY_START_TIME = None` → Real-time indefinite monitoring
- **REPLAY MODE** - `DEBUG_REPLAY_START_TIME = "timestamp"` → Historical simulation (bounded)

**Verified Flow:**
```
SymbolAlertManager (Multi-symbol orchestrator)
  └─→ SymbolAlerter (Single-symbol supervisor)
      ├─→ ResolutionCoordinator (Approach-to-resolution mapping)
      │   └─→ APPROACH_RESOLUTION_MAPPING config
      │
      └─→ Monitoring Session (Time-based loop)
          ├─→ DataServiceOrchestrator (Multi-resolution data fetching)
          │   └─→ HistoricalDataManager (Cache hub)
          │       └─→ DataProviderCoordinator (Provider routing)
          │           └─→ 3 Providers (Vietstock, Binance API, Binance CCXT)
          │
          ├─→ PriceMovementAlerter (Price level detection on 1-min resolution)
          │
          ├─→ Executor Framework (6 approach-specific executors)
          │   ├─→ CONSISTENT_MOMENTUM (resolution-specific)
          │   ├─→ STRONG_CANDLE (resolution-specific)
          │   ├─→ VOLUME_SPIKE_CONFIRMATION (resolution-specific)
          │   ├─→ VRA (resolution-specific)
          │   ├─→ CONSISTENT_VOLUME_ANCHOR (resolution-specific)
          │   └─→ ICHIMOKU (resolution-specific)
          │
          └─→ Close Position Scheduler (Time-based position closing)
              └─→ NotificationManager (Multi-channel notifications)
                  ├─→ Email Service
                  ├─→ SMS Service
                  └─→ Ntfy Service
```

---

## Part 1: Component Verification & Details

### 1.1 Entry Point: SymbolAlertManager ✅

**Location:** `src/stockreports/alert/symbol_alert_manager.py`

**Responsibility:**
- Multi-symbol orchestration
- Concurrent execution management via ThreadPoolExecutor
- Thread pool management for parallel symbol processing
- Logging configuration

**Key Methods:**
- `_execute_for_symbol(symbol)` - Instantiates SymbolAlerter for each symbol
- `_run_deployment()` - Concurrent execution via ThreadPoolExecutor

**Configuration:**
- Reads SYMBOLS from settings
- Executes in DEPLOYMENT mode (production monitoring)
- Configurable logging levels

---

### 1.2 Core Orchestrator: SymbolAlerter ✅

**Location:** `src/stockreports/alert/symbol_alerter.py`

**Responsibility:**
- Single-symbol supervision (acts as resilient supervisor)
- **Multi-resolution data management** (stores dataframes per resolution)
- Continuous monitoring with crash resilience
- Data fetching via DataServiceOrchestrator (for multiple resolutions)
- Alert detection via Executors & PriceMovementAlerter
- Notification dispatch

**Architecture:**
```
SymbolAlerter (Deployment Mode)
├─ Supervisor Loop: Catches crashes, restarts session
│   └─ Monitoring Session: Time-based continuous execution
│       ├─ Multi-Resolution Storage: Dict[resolution] → DataFrame
│       │   └─ Resolution 1 (1-min): Always required
│       │   └─ Other resolutions: Per-approach configured
│       │
│       └─ Main Loop: Interval-based operations
```

**Key Methods:**
1. `execute()` - Entry point for deployment mode execution
2. `_run_deployment_mode()` - Supervisor loop with restart capability
3. `_perform_monitoring_session()` - Main monitoring loop
4. `_init_resolution_dataframes()` - Initialize resolution storage
5. `_update_resolution_dataframes(from_dt, to_dt)` - Fetch data for all resolutions
6. `_get_approaches_for_symbol()` - Gets symbol-specific approaches

**Multi-Resolution Storage:**
```python
# In __init__:
self.resolution_coordinator = ResolutionCoordinator()
self._init_resolution_dataframes()  # Dict[int, Optional[DataFrame]]

# Example structure for VN30F1M with multiple approaches:
self._resolution_dataframes = {
    1: None,    # 1-minute (required by PriceMovementAlerter + approaches)
    5: None,    # 5-minute (if any approach configured for 5-min)
    15: None    # 15-minute (if any approach configured for 15-min)
}

# Resolution 1 (1-minute) is ALWAYS included because:
# - PriceMovementAlerter always uses 1-minute data
# - Monitoring loop uses resolution 1 as first-run indicator
```

**Data Flow in Main Loop:**
```python
while time_simulator.is_running():
    # 1. Check for scheduled close position notifications
    scheduled_notification = check_and_notify(current_time)
    
    # 2. Check trading hours
    if not is_trading_hours(current_time): continue
    
    # 3. UPDATE ALL RESOLUTION DATAFRAMES (multi-resolution support)
    has_data = self._update_resolution_dataframes(from_dt, to_dt)
    if not has_data: continue
    
    # 4. Price Movement Detection (always on 1-min resolution)
    price_df = self._resolution_dataframes.get(1)
    price_alerter = PriceMovementAlerter(self.symbol)
    price_result = price_alerter.execute(price_df)
    
    # 5. Executor-based Approaches (each on configured resolution)
    for approach_name in approaches_to_run:
        resolution = resolution_coordinator.get_resolutions(approach_name)
        approach_df = self._resolution_dataframes.get(resolution)
        
        executor = get_approach_executor(approach_name)
        result = executor.run(df=approach_df)
    
    # 6. Advance time simulator
    time_simulator.advance()
```

**Key Changes from Previous Architecture:**
- ✅ **Before:** Single `master_df` for all approaches
- ✅ **Now:** Per-resolution dataframes (`_resolution_dataframes` dict)
- ✅ **Before:** All approaches ran on same resolution
- ✅ **Now:** Each approach configured for specific resolution
- ✅ **Before:** Redundant data fetching
- ✅ **Now:** Efficient multi-resolution fetch once per cycle
    
    # 4. Price Movement Detection
    price_alerter = PriceMovementAlerter(self.symbol)
    price_result = price_alerter.execute(master_df)
    if price_result.has_alerts:
        notification_manager.process_and_notify(price_result)
    
    # 5. Executor-based Approaches
    for approach in approaches:
        executor = get_approach_executor(approach)
        result = executor.run(df=master_df)
        if result.has_alerts:
            notification_manager.process_and_notify(result)
    
    # 6. Advance time simulator
    time_simulator.advance()
```

---

### 1.3 Resolution Coordinator ✅

**Location:** `src/stockreports/coordination/resolution_coordinator.py`

**Responsibility:**
- **Maps each approach to its configured resolution** (1, 5, 15, or 60 minutes)
- Validates configuration at initialization
- Provides approach-to-resolution lookups
- Returns required resolutions for a symbol

**Pattern:** Facade - Simple interface for approach-to-resolution mappings

**Key Concept:**
Each trading approach runs on a specific time resolution (intraday chart timeframe):
- `ICHIMOKU` → 15-minute resolution
- `VRA` → 5-minute resolution  
- `STRONG_CANDLE` → 1-minute resolution
- etc.

This allows different approaches to run on different timeframes simultaneously.

**Configuration (APPROACH_RESOLUTION_MAPPING in signal_settings.py):**
```python
APPROACH_RESOLUTION_MAPPING = {
    "CONSISTENT_MOMENTUM": 1,      # 1-minute charts
    "ICHIMOKU": 1,                # 1-minute charts
    "STRONG_CANDLE": 1,            # 1-minute charts
    "VRA": 1,                      # 1-minute charts
    "VOLUME_SPIKE_CONFIRMATION": 1,  # 1-minute charts
    "CONSISTENT_VOLUME_ANCHOR": 1   # 1-minute charts
}
```

**Public Methods:**

```python
def get_resolutions(approach: str) -> int:
    """
    Get resolution for an approach.
    
    Args:
        approach: Approach constant (e.g., Approach.ICHIMOKU)
    
    Returns:
        Resolution in minutes (1, 5, 15, or 60)
    
    Raises:
        KeyError: If approach not found in APPROACH_RESOLUTION_MAPPING
    
    Example:
        coordinator.get_resolutions(Approach.ICHIMOKU)  # Returns 15
    """

def get_required_resolutions(symbol: str) -> list[int]:
    """
    Get list of required resolutions for a symbol.
    
    Gets all approaches configured for the symbol, then collects
    unique resolutions needed. Always includes resolution 1.
    
    Args:
        symbol: Stock symbol (e.g., "VN30F1M")
    
    Returns:
        Sorted list of unique resolutions [1, 5, 15]
    
    Example:
        coordinator.get_required_resolutions("VN30F1M")  # [1, 5, 15]
    """
```

**Validation:**
- ✅ All approaches exist in Approach class
- ✅ All resolutions are numeric integers
- ✅ All resolutions in supported set: {1, 5, 15, 60}
- Raises ValueError/TypeError if validation fails

**Integration with SymbolAlerter:**
```python
# In SymbolAlerter.__init__:
self.resolution_coordinator = ResolutionCoordinator()
self._init_resolution_dataframes()

# In _init_resolution_dataframes():
resolutions = self.resolution_coordinator.get_required_resolutions(self.symbol)
self._resolution_dataframes = {resolution: None for resolution in resolutions}

# In monitoring loop:
resolution = self.resolution_coordinator.get_resolutions(approach_name)
approach_df = self._resolution_dataframes.get(resolution)
executor.run(df=approach_df)
```

---

### 1.4 Data Services: DataServiceOrchestrator ✅

**Location:** `src/stockreports/data_services/orchestrator.py`

**Responsibility:**
- **Single Public API** for all data operations (Facade Pattern)
- Data fetching with intelligent caching
- Provider coordination & auto-detection
- Data processing (timezone conversion, price adjustments)

**Public Method:**
```python
def fetch_and_process(
    symbol: str,
    start_time: pd.Timestamp,
    end_time: pd.Timestamp,
    resolution: Optional[int] = None
) -> Optional[pd.DataFrame]
```

**Internal Architecture:**
```
DataServiceOrchestrator (Public Facade)
└─ HistoricalDataManager (Cache Hub)
   ├─ Cache Key: (symbol, resolution)
   ├─ Cache Logic: HIT / MISS / PARTIAL detection
   └─ Coordinator Interface:
       └─ DataProviderCoordinator (Provider Routing)
           ├─ Auto-detect provider from symbol config
           ├─ Route to appropriate provider
           └─ 3 Providers:
               ├─ VietstockProvider
               ├─ BinanceAPIProvider
               └─ BinanceCCXTProvider
```

**Data Format (Standardized):**
- Index: `pd.DatetimeIndex` named 'time' (with timezone)
- Columns: ['open', 'high', 'low', 'close', 'volume']
- All numeric columns: float64

---

### 1.5 Price Movement Detection: PriceMovementAlerter ✅

**Location:** `src/stockreports/alert/price_movement_alerter.py`

**Responsibility:**
- Detect price level crossings (support/resistance)
- Self-contained level tracking per symbol
- Cooldown-based repeated alert prevention
- Time-based expiration for triggered levels

**Key Features:**
- Configuration: `PRICE_ALERTS` in settings (per-symbol levels)
- State: Class-level dict tracking triggered levels today
- Cooldown: Configurable via `LEVEL_ALERT_COOLDOWN_MINUTES`
- Returns: `AlertResult` with `confirmed_alerts` (AlertData list)

**Public Method:**
```python
def execute(df: pd.DataFrame) -> AlertResult
```

**Approach Name:** `Approach.PRICE_MOVEMENT`

---

### 1.6 Executor Framework ✅

**Location:** `src/stockreports/alert/executor.py` (base), `src/stockreports/alert/approach/[NAME]/executor.py` (implementations)

**Responsibility:**
- Approach-specific alert detection
- Validation step tracking & logging
- Alert details construction
- Standardized AlertResult generation

**Base Class: Executor (ABC)**
- Abstract method: `_find_alerts(df, new_candle_count)` - Implementation-specific
- Public method: `run(df, new_candle_count)` - Entry point
- Returns: `AlertResult` with `confirmed_alerts` list

**6 Implemented Approaches:**

| # | Approach | Location | Purpose |
|---|----------|----------|---------|
| 1 | CONSISTENT_MOMENTUM | `approach/CONSISTENT_MOMENTUM/executor.py` | Momentum consistency detection |
| 2 | STRONG_CANDLE | `approach/STRONG_CANDLE/executor.py` | Strong candle pattern detection |
| 3 | VOLUME_SPIKE_CONFIRMATION | `approach/VOLUME_SPIKE_CONFIRMATION/executor.py` | Volume spike with trend confirmation |
| 4 | VRA | `approach/VRA/executor.py` | Volume Reversal Analysis |
| 5 | CONSISTENT_VOLUME_ANCHOR | `approach/CONSISTENT_VOLUME_ANCHOR/executor.py` | Volume anchor consistency |
| 6 | ICHIMOKU | `approach/ICHIMOKU/executor.py` | Ichimoku cloud indicators |

**Executor Hierarchy:**
```
Executor (Abstract Base)
├─ Provides: run(), validation tracking, details builder, cooldown check
├─ Requires: _find_alerts() implementation
└─ 6 Subclasses (one per approach)
```

**Configuration:**
- `SYMBOL_ALERT_APPROACHES`: Per-symbol approach lists
- `ALERT_APPROACHES_DEFAULT`: Default approaches
- Falls back to legacy `ALERT_APPROACHES` for backward compatibility

---

### 1.7 Close Position Scheduler ✅

**Location:** `src/stockreports/notification/unified_scheduler.py`

**Responsibility:**
- **Unified scheduler** handling BOTH order reminders and position closing
- Dictionary-based state tracking pending BUY/SELL signals
- Time-based notification scheduling with multiple delays
- State management (module-level with structured dictionary)

**Key Features:**
- Module-level state: `_scheduled_state` (dictionary with 'alert' and 'sent' keys)
- Dictionary tracks what's been sent: `{'order_reminder': bool, 'close_position': bool}`
- Triggered on delay expiry for each notification type independently
- Only tracks BUY/SELL signals (ignores others)
- Auto-resets state when both notifications sent
- Generates up to 2 notifications per signal: ORDER REMINDER + CLOSE POSITION

**State Structure:**
```python
_scheduled_state = {
    'alert': AlertNotification,  # Current BUY/SELL signal being tracked
    'sent': {
        'order_reminder': False,      # Has order reminder been sent?
        'close_position': False       # Has close position been sent?
    }
}
```

**Public Functions:**
```python
def update_latest_signal(notification: AlertNotification) -> None
    # Called by NotificationManager after new BUY/SELL alert sent
    # Resets both 'sent' flags when new signal arrives

def check_and_notify(current_time: datetime) -> List[AlertNotification]
    # Called in main loop, returns list of notifications (0-2 items)
    # Checks: 1) Order Reminder (5 min), 2) Close Position (10 min)
    # Returns: Notifications due at current time

def get_state() -> dict
    # Returns copy of current state (for debugging/testing)

def reset_state() -> None
    # Manually resets state (for emergency reset/testing)
```

**Configuration:**
- `SCHEDULED_REMINDER_ORDER_DELAY_MINUTES = 5` (order reminder timing)
- `SCHEDULED_REMINDER_CLOSE_DELAY_MINUTES = 10` (close position timing)
- Can be set to `None` to disable either notification type

**Check Order:**
1. **First:** Order Reminder (e.g., 5 minutes after BUY/SELL)
2. **Second:** Close Position (e.g., 10 minutes after BUY/SELL)
3. **Auto-reset:** When both sent, state resets for next signal

**Flow:**
1. NotificationManager sends BUY/SELL → calls `update_latest_signal(notification)`
   - Stores notification in state
   - Resets both 'sent' flags to False
2. Main loop calls `check_and_notify(current_time)` each iteration
   - Checks if order reminder is due
   - Checks if close position is due
   - Returns list of due notifications
3. SymbolAlerter sends each notification via NotificationManager
4. When both sent, state auto-resets for next signal

**Extensibility:**
To add new notification type (e.g., "weekly_review"):
1. Add key to 'sent' dict: `'weekly_review': False`
2. Add configuration: `SCHEDULED_REMINDER_REVIEW_DELAY_MINUTES = 10080` (7 days)
3. Add check in `check_and_notify()` for new notification type
4. Update tests and documentation

**Backward Compatibility:**
- Old file `close_position_scheduler.py` maintained as deprecated wrapper
- Imports still work but emit deprecation warnings
- Migration path: Update imports to point to `unified_scheduler`

---

### 1.8 Notification Service: NotificationManager ✅

**Location:** `src/stockreports/notification/notification_manager.py`

**Responsibility:**
- **Separate service** for multi-channel notifications
- Deduplication (prevents same alert being sent twice)
- Session-level tracking of sent alerts
- Delegates to channel-specific utilities

**Supported Channels:**
✅ **Email** - `src.stockreports.utils.notification.email_utils`
✅ **SMS** - `src.stockreports.utils.notification.sms_utils`
✅ **Ntfy** - `src.stockreports.utils.notification.ntfy_utils`

**Public Methods:**
```python
def process_and_notify(result: AlertResult, symbol: str)
    # Main entry point: Processes latest alert, sends if not duplicated

def _send_alert(notification: AlertNotification)
    # Sends through all enabled channels
```

**Configuration:**
- `ENABLED_NOTIFICATION_CHANNELS`: List of active channels
- Channel-specific settings per channel
- Deduplication key: `(approach_name, alert_time)`

---

### 1.9 Supporting Components ✅

#### Analyzer (Abstract Base)
**Location:** `src/stockreports/alert/analyzer.py`

Provides shared calculation methods:
- `calculate_body_ratio()` - Candle body ratio
- `calculate_body_size()` - Body size calculation
- `get_candle_color()` - GREEN/RED/NEUTRAL detection
- Other pure calculation methods

Each approach subclasses to inherit calculations.

#### Validator
**Location:** `src/stockreports/alert/validator.py`

Validation step tracking and logging.

---

## Part 2: Data Models

### AlertResult
```python
class AlertResult:
    approach_name: str
    confirmed_alerts: List[AlertData]  # Empty if no alerts
    status: Status  # SUCCESS or FAILED
    message: Optional[str]
    
    @property
    def has_alerts(self) -> bool:
        return len(self.confirmed_alerts) > 0
```

### AlertData
```python
class AlertData:
    alert_time: pd.Timestamp
    signal: Signal  # BUY, SELL, CLOSE POSITION, etc
    alert_price: float
    approach: str
    details: Dict (JSON)
    suggested_profit_threshold: Optional[float]
    performance_suggested_price: Optional[float]
    structural_suggested_price: Optional[float]
```

### AlertNotification
```python
class AlertNotification:
    symbol: str
    signal: Signal
    alert_price: float
    alert_time: pd.Timestamp
    approach: str
    details: Dict
    suggested_price: Optional[float]
    suggested_profit_threshold: Optional[float]
```

---

## Part 3: Critical Flow Details

### Main Monitoring Loop Sequence

```
1. CHECK SCHEDULED NOTIFICATIONS
   ├─ Scheduler checks if delay elapsed since BUY/SELL
   └─ If expired → generates "CLOSE POSITION" notification
      └─ Sent via NotificationManager

2. CHECK TRADING HOURS
   └─ Skip non-trading periods

3. FETCH DATA
   └─ DataServiceOrchestrator.fetch_and_process()
      ├─ Uses HistoricalDataManager (handles caching)
      ├─ Auto-detects provider from symbol
      ├─ Applies timezone conversion & price adjustments
      └─ Returns standardized DataFrame

4. DETECT PRICE MOVEMENTS
   └─ PriceMovementAlerter.execute(master_df)
      └─ Checks configured price levels
      └─ Returns AlertResult
      └─ If has_alerts → NotificationManager.process_and_notify()

5. RUN APPROACH EXECUTORS
   └─ For each approach in symbol's approach list:
      └─ executor.run(df=master_df, new_candle_count)
         ├─ Performs approach-specific analysis
         ├─ Generates AlertResult with confirmed_alerts
         └─ If has_alerts → NotificationManager.process_and_notify()

6. ADVANCE TIME
   └─ time_simulator.advance()
       └─ Next iteration at MONITORING_INTERVAL_SECONDS
```

### Notification Deduplication
```
Alert Generated → NotificationManager.process_and_notify()
                    ↓
                 Create (approach, alert_time) key
                    ↓
                 Check in session set: alerts_sent_in_session
                    ↓
            Yes (duplicate) → Skip, log & return
                    ↓
            No (new alert)  → Create AlertNotification
                            ↓
                        Scheduler Update: update_latest_signal()
                            ↓
                        Send via channels: _send_alert()
                            ↓
                        Add to sent set
```

---

## Part 4: Configuration Points

### Critical Settings
| Setting | Location | Purpose |
|---------|----------|---------|
| `SYMBOLS` | config/settings.py | List of symbols to monitor |
| `SYMBOL_ALERT_APPROACHES` | config/settings.py | Per-symbol approach list |
| `ALERT_APPROACHES_DEFAULT` | config/settings.py | Default approaches |
| `ENABLED_DATA_PROVIDERS` | config/data_provider_settings.py | Active data providers |
| `PRICE_ALERTS` | config/settings.py | Price level configurations |
| `CLOSE_POSITION_DELAY_MINUTES` | config/signal_settings.py | Close position delay |
| `ENABLED_NOTIFICATION_CHANNELS` | config/notification_settings.py | Active notification channels |
| `MONITORING_INTERVAL_SECONDS` | config/settings.py | Main loop interval |
| `MONITORING_DATA_RESOLUTION_MINUTES` | config/data_provider_settings.py | Candle resolution |

---

## Part 5: Clarifications & Corrections

### ✅ Clarification 1: Downstream Components
**Status:** Separate Services (CONFIRMED) → Now Unified in v2

- **Unified Scheduler:** SINGLE SERVICE (consolidates order reminders + position closing)
  - Location: `src/stockreports/notification/unified_scheduler.py`
  - State: Module-level dict tracking pending signals + sent status
  - Responsibility: Time-based order reminders + position closing logic
  - Note: Old `close_position_scheduler.py` kept as deprecated wrapper
  
- **Price Movement Alerter:** SEPARATE SERVICE (not just handler)
  - Location: `src/stockreports/alert/price_movement_alerter.py`
  - State: Class-level dict tracking triggered levels
  - Responsibility: Price level crossing detection

- **Notification Manager:** SEPARATE SERVICE
  - Location: `src/stockreports/notification/notification_manager.py`
  - Channels: Email, SMS, Ntfy
  - Responsibility: Multi-channel notification dispatch

**Important:** Downstream components are **independent analysis services**, not just handlers triggered by alerts. They're called in parallel with executor-based approaches.

---

### ✅ Clarification 2: Executor Architecture
**Status:** Framework with 6 Implementations (CONFIRMED)

**Executor is NOT part of SymbolAlert:**
- Executor is an **abstract framework** for approach-specific implementations
- SymbolAlerter **uses/instantiates** Executors dynamically via `_get_approach_executor()`
- Each approach has its own Executor subclass

**Hierarchy:**
```
Executor (Abstract Base Class)
├─ Defines: run(), validation tracking, alerts structure
└─ 6 Subclasses (one per approach)
    ├─ ConsistentMomentumExecutor
    ├─ StrongCandleExecutor
    ├─ VolumeSpikeCongfirmationExecutor
    ├─ VraExecutor
    ├─ ConsistentVolumeAnchorExecutor
    └─ IchimokuExecutor
```

**Approach Resolution:**
1. Try symbol-specific approaches: `SYMBOL_ALERT_APPROACHES[symbol]`
2. Fallback to default: `ALERT_APPROACHES_DEFAULT`
3. Fallback to legacy: `ALERT_APPROACHES`
4. Hard fallback: `[DEFAULT_APPROACH]` (VRA)

---

### ✅ Clarification 3: Data Services Integration
**Status:** Centralized Orchestrator (CONFIRMED)

Previously:
- `src.stockreports.utils.historical_data_manager` (deprecated)
- `src.stockreports.data_processor` (deprecated)
- `src.stockreports.data_provider` (old structure)

Now:
- **Single Entry Point:** `from src.stockreports.data_services import DataServiceOrchestrator`
- **Internal Modules:** All hidden under `_internal/` (not for direct import)
- **Facade Pattern:** Clean public API, complex internals hidden

**Data Services Components:**
1. HistoricalDataManager (Cache hub)
2. DataProviderCoordinator (Provider routing)
3. DataProcessor (Data transformations)
4. 3 Providers (Vietstock, Binance API, Binance CCXT)

---

## Part 6: Verified Data Flow - Complete Picture

### End-to-End Request Flow
```
SymbolAlerter.execute()
    └─ Call orchestrator.fetch_and_process(symbol, start, end, resolution)
       ├─ HistoricalDataManager.get_with_resolution()
       │  ├─ Check cache: (symbol, resolution) hit/miss/partial
       │  └─ If miss → Call coordinator
       │     └─ DataProviderCoordinator.fetch_ohlcv()
       │        ├─ Auto-detect provider from symbol
       │        ├─ Route to appropriate provider
       │        └─ Provider.fetch_ohlcv()
       │           ├─ Call external API (HTTP)
       │           ├─ Normalize response format
       │           └─ Return DataFrame: 'time' index + OHLCV
       │
       ├─ Cache result in HistoricalDataManager
       │
       └─ DataProcessor: Apply transformations
          ├─ Timezone conversion (if enabled)
          ├─ Price adjustment (if enabled)
          └─ Return processed DataFrame
```

### End-to-End Alert Flow
```
FOR each symbol in SYMBOLS:
    FOR each analysis method:
        Executor.run() OR PriceMovementAlerter.execute()
            └─ Generate AlertResult with confirmed_alerts[]
                └─ IF has_alerts:
                    └─ NotificationManager.process_and_notify()
                        ├─ Check dedup: (approach, alert_time)
                        ├─ Create AlertNotification
                        ├─ Scheduler.update_latest_signal() [if BUY/SELL]
                        └─ Send via channels: Email, SMS, Ntfy

FOR each iteration in main loop:
    Scheduler.check_and_notify(current_time)
        └─ IF delay elapsed for pending BUY/SELL:
            └─ Generate "CLOSE POSITION" AlertNotification
                └─ NotificationManager._send_alert()
                    └─ Send via all enabled channels
```

---

## Part 7: Identified Gaps & Omissions (None)

✅ **No gaps identified.** User's conceptual model is complete and accurate.

**Potential Enhancement Opportunities (Not issues):**
1. More detailed executor-level documentation (approach-specific logic)
2. Configuration management documentation
3. Channel-specific sending logic details

---

## Part 8: Deployment Mode Architecture (with Time Sub-Modes)

### Execution Model
The system operates in **DEPLOYMENT mode** with two time-behavior sub-modes controlled by `DEBUG_REPLAY_START_TIME`:

```
SymbolAlertManager._run_deployment()
    ├─ Creates ThreadPoolExecutor
    ├─ Submits _execute_for_symbol(symbol) for each symbol
    ├─ Manages concurrent execution of all symbols
    └─ For each symbol thread:
        └─ SymbolAlerter.execute() [DEPLOYMENT Mode]
            └─ _run_deployment_mode() [Supervisor Loop]
                ├─ Catches exceptions, logs, restarts/exits (mode-dependent)
                └─ _perform_monitoring_session() [Main Loop]
                    └─ TimeSimulator Controls Time Behavior:
                        ├─ LIVE MODE (DEBUG_REPLAY_START_TIME = None)
                        │   ├─ Uses real system time
                        │   ├─ Loop continues indefinitely
                        │   ├─ Auto-recovers from crashes
                        │   └─ Saves alerts to reports/
                        │
                        └─ REPLAY MODE (DEBUG_REPLAY_START_TIME = "timestamp")
                            ├─ Uses simulated time
                            ├─ Loop stops at end_of_day
                            ├─ Exits immediately on crash
                            └─ Saves alerts to reports_replay/
```

### Critical: TimeSimulator Control

**Location:** `src/stockreports/utils/time_utils.py` - `TimeSimulator` class (lines 35-80)

The `TimeSimulator` class determines:
1. **Time Source:** System time (LIVE) vs Simulated time (REPLAY)
2. **Loop Duration:** Indefinite (LIVE) vs Bounded by end_of_day (REPLAY)
3. **Non-trading Hours:** Sleep 15min (LIVE) vs Jump forward (REPLAY)
4. **Error Handling:** Restart (LIVE) vs Exit (REPLAY)

**Configuration Driver:** `DEBUG_REPLAY_START_TIME` in `config/settings.py`

### Sub-Mode Comparison Table

| Aspect | LIVE Mode | REPLAY Mode |
|--------|-----------|------------|
| Configuration | `DEBUG_REPLAY_START_TIME = None` | `DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"` |
| Time Source | `datetime.now(TIMEZONE)` | Simulated from timestamp |
| Loop Termination | Indefinite (KeyboardInterrupt only) | Stops at end_of_day |
| Non-Trading Hours | `time.sleep(900)` (wait 15 min) | `time_simulator.advance()` (jump) |
| Error Recovery | Auto-restart with sleep | Exit immediately |
| Report Directory | `reports/` | `reports_replay/` |
| Use Case | Production monitoring | Testing/validation |
| See Details | → Part 9 | → Part 9 |

### Execution Flow
- **Concurrent:** Each symbol monitored in separate thread
- **Resilient (LIVE):** Supervisor auto-restarts on crashes
- **Deterministic (REPLAY):** Exits cleanly on completion or error
- **Time-aware:** Respects trading hours via TimeSimulator

### Key Properties (DEPLOYMENT mode)
- No batch/historical processing mode
- No date-based iteration (unlike DEVELOPMENT)
- Pure event-driven monitoring based on time simulator
- Two execution paths: Production (LIVE) vs Testing (REPLAY)

---

## Part 9: Time Simulator Deep Dive

### TimeSimulator Initialization
**Location:** `src/stockreports/utils/time_utils.py:35-53`

```python
class TimeSimulator:
    def __init__(self, replay_start_str: Optional[str], interval_seconds: int):
        self._is_replay = replay_start_str is not None
        self._interval = timedelta(seconds=interval_seconds)
        
        if self._is_replay:
            # REPLAY: Use provided timestamp
            self._current_time = pd.to_datetime(replay_start_str).tz_localize(TIMEZONE)
            self.end_of_day = self._get_session_end(self._current_time)
            # Returns end time of last trading session (e.g., 14:27 for Vietnam)
        else:
            # LIVE: Use current system time
            self._current_time = self._get_live_time()
            self.end_of_day = None  # Undefined in live mode
```

### Critical Methods

#### `is_running() -> bool`
**Purpose:** Controls main loop continuation

**REPLAY Mode:**
```python
if self._is_replay:
    return self._current_time <= self.end_of_day  # Stop at end of trading
```

**LIVE Mode:**
```python
return True  # Continue indefinitely
```

**Impact on Main Loop:**
```
REPLAY: Loop exits automatically when current_time exceeds end_of_day
LIVE:   Loop only exits via KeyboardInterrupt or exception
```

#### `advance()`
**Purpose:** Move time forward (REPLAY) or no-op (LIVE)

**REPLAY Mode:**
```python
self._current_time += self._interval  # Jump by MONITORING_INTERVAL_SECONDS
```

**LIVE Mode:**
```python
# No-op: Real time advances naturally
```

#### `is_replay_mode() -> bool`
**Purpose:** Used throughout system for branching logic

**Called from:**
- `SymbolAlerter._perform_monitoring_session()` line 273 (trading hours)
- Error handling checks throughout

### Trading Hours Handling - Mode-Dependent

**Location:** `SymbolAlerter._perform_monitoring_session()` lines 273-282

```python
if not is_trading_hours(current_time):
    self.logger.info(f"Outside trading hours. Waiting for next interval.")
    if time_simulator.is_replay_mode():
        # REPLAY: Jump to next time slot instantly
        time_simulator.advance()
        continue
    else:
        # LIVE: Wait 15 minutes in real time
        time.sleep(900)
        continue
```

**Impact:**
- REPLAY: Simulations process data faster (no real-time waiting)
- LIVE: Monitoring respects actual time intervals
- Both: Skip non-trading hours appropriately

### Error Recovery - Mode-Dependent

**Location:** `SymbolAlerter._run_deployment_mode()` lines 234-240

```python
except Exception as e:
    if settings.DEBUG_REPLAY_START_TIME is None:
        # LIVE MODE: Resilient
        self.logger.info(f"Waiting {MONITORING_INTERVAL_SECONDS}s before restarting...")
        time.sleep(settings.MONITORING_INTERVAL_SECONDS)
        # Loop continues to restart session
    else:
        # REPLAY MODE: Deterministic
        self.logger.error("Exiting replay due to critical error.")
        break  # Exit supervisor loop
```

**Impact:**
- LIVE: 24/7 reliability through automatic recovery
- REPLAY: Deterministic state for test reproducibility

### Report Storage - Mode-Driven Separation

**Location:** `src/stockreports/utils/report_utils.py` lines 54-60

```python
def get_reports_directory_name():
    if settings.DEBUG_REPLAY_START_TIME is None:
        return "reports"          # LIVE MODE
    else:
        return "reports_replay"   # REPLAY MODE
```

**Directory Structure:**
```
reports/              ← LIVE monitoring alerts
├── [symbol]/
│   └── deployment/
│       └── alert_notification_*.json
│
reports_replay/       ← REPLAY simulation alerts
├── [symbol]/
│   └── deployment/
│       └── alert_notification_*.json
```

**Purpose:** Separate production alerts from test simulations for independent analysis.

---

## Part 10: Scope for Architecture Versions (Deployment Only)

### Scope Boundaries Established

**Version 1 - End Users/Clients (Business):**
- Alert Services (core functionality for trading)
- Data Services (how data is fetched & cached)
- Notification Channels (how they receive alerts)
- NOT: Report generators, simulators, other tools

**Version 2 - Cross-Functional Teams (QA/BSA/Product):**
- All services above
- Integration points & dependencies
- Configuration system
- Error handling & recovery (crash resilience)
- NOT: Internal implementation details

**Version 3 - Developers (Technical):**
- All services above
- Full internal architecture
- Executor framework & implementations
- Provider architecture
- Extension points & patterns
- Maintenance guidelines
- Deployment mode execution flow
- INCLUDES: Report generators, simulators (part of broader system)

---

## Part 10: Scope for Architecture Versions (Deployment Only)

### Scope Boundaries Established

**Version 1 - End Users/Clients (Business):**
- Alert Services (core functionality for trading)
- Data Services (how data is fetched & cached)
- Notification Channels (how they receive alerts)
- Time behavior modes (LIVE vs REPLAY for testing)
- NOT: Report generators, simulators, other tools

**Version 2 - Cross-Functional Teams (QA/BSA/Product):**
- All services above
- Integration points & dependencies
- Configuration system
- Error handling & recovery (crash resilience, mode-dependent)
- Time simulator impact on monitoring loop
- NOT: Internal implementation details

**Version 3 - Developers (Technical):**
- All services above
- Full internal architecture
- Executor framework & implementations
- Provider architecture
- Extension points & patterns
- Maintenance guidelines
- Deployment mode execution flow (LIVE vs REPLAY sub-modes)
- TimeSimulator internals
- INCLUDES: Report generators, simulators (part of broader system)

---

## Phase 1 Complete ✅ (Updated with Time Sub-Modes)

**Focus:** Deployment Mode (with LIVE vs REPLAY sub-modes controlled by DEBUG_REPLAY_START_TIME)

**Critical Discovery:** DEBUG_REPLAY_START_TIME controls time behavior, NOT DEVELOPMENT/DEPLOYMENT distinction

**See Also:** `DEBUG_REPLAY_START_TIME_INVESTIGATION.md` for detailed analysis

**Ready for:** Phase 2 - Create Unified Architecture Documentation

All findings verified through code inspection with exact file locations and code references.

---

## Phase 2 Additions (Report Generation Layer)

⚠️ **NOTE:** Phase 1 documents the core alert and monitoring system. Phase 2 introduces a new report generation layer for backtesting analysis:

**Phase 2 Components (Not in Phase 1 scope):**
- **CentralizedReportGenerator** - Orchestrates backtesting and trade simulation
- **IndividualTradeSimulator** - Simulates daily trades with profit/loss analysis
- **ConsolidateReports** - Aggregates daily results into summary reports
- **SupportResistanceDetector** - Detects support/resistance levels (optional enhancement)
- **PerformanceAnalyzer** - Analyzes overall performance metrics (optional enhancement)

**Phase 2 Configuration Additions:**
- **notification_settings.py** - Notification channel configuration (Phase 2)
- **validation_settings.py** - Profit/loss validation thresholds (Phase 2)

These components extend the base architecture for performance analysis and backtesting scenarios. See `PHASE1_PHASE2_ALIGNMENT.md` and Phase 2 documentation (PERFORMANCE_METRICS_EXTENSION_GUIDE.md) for complete details.

---

## Quick Reference: File Locations

| Component | File | LOC |
|-----------|------|-----|
| SymbolAlertManager | `alert/symbol_alert_manager.py` | 312 |
| SymbolAlerter | `alert/symbol_alerter.py` | 491 |
| DataServiceOrchestrator | `data_services/orchestrator.py` | ~100 |
| HistoricalDataManager | `data_services/_internal/fetching/_manager.py` | ~400 |
| DataProviderCoordinator | `data_services/_internal/providing/_coordinator.py` | ~300 |
| Executor (Base) | `alert/executor.py` | 345 |
| 6 Approach Executors | `alert/approach/[NAME]/executor.py` | Varies |
| PriceMovementAlerter | `alert/price_movement_alerter.py` | 252 |
| NotificationManager | `notification/notification_manager.py` | 113 |
| UnifiedScheduler | `notification/unified_scheduler.py` | 260 |
| Analyzer (Base) | `alert/analyzer.py` | 421 |
| Data Models | `alert/model/models.py` | ~300 |
