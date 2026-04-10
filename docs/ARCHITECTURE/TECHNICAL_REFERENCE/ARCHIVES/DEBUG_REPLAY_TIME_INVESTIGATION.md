# Investigation: DEBUG_REPLAY_START_TIME Configuration Impact

**Date:** April 8, 2026  
**Status:** Complete - Critical Discovery  
**Focus:** Deployment Mode Operation & Time Simulation Logic

---

## Executive Summary

**CRITICAL DISCOVERY:** `DEBUG_REPLAY_START_TIME` is NOT about DEVELOPMENT vs DEPLOYMENT mode selection.

Instead, it controls **TWO DISTINCT OPERATIONAL MODES within DEPLOYMENT mode:**
1. **LIVE MODE** - `DEBUG_REPLAY_START_TIME = None` → Real-time monitoring (indefinite)
2. **REPLAY MODE** - `DEBUG_REPLAY_START_TIME = "timestamp"` → Historical simulation (bounded)

The MODE setting controls DEVELOPMENT vs DEPLOYMENT (different data sources).
The DEBUG_REPLAY_START_TIME controls TIME BEHAVIOR within DEPLOYMENT mode.

---

## Part 1: Configuration Hierarchy

### Level 1: Execution Mode (Outermost)
**Configuration:** `MODE` in `config/settings.py`
**Values:** "DEVELOPMENT" or "DEPLOYMENT"
**Decision Point:** `SymbolAlerter.execute()`

```python
def execute(self):
    self.logger.info(f"Executing alerter for symbol: {self.symbol}...")
    if settings.MODE == "DEVELOPMENT":
        self._run_development_mode()       # ← Data from local files
    elif settings.MODE == "DEPLOYMENT":
        self._run_deployment_mode()        # ← Data from API + time simulator
    self.logger.critical(f"Execution finished for symbol: {self.symbol}.")
```

**Impact:**
- DEVELOPMENT: Uses local historical data files (batch processing)
- DEPLOYMENT: Uses API data with real-time/simulated time (continuous monitoring)

---

### Level 2: Time Behavior (Within DEPLOYMENT mode)
**Configuration:** `DEBUG_REPLAY_START_TIME` in `config/settings.py`
**Values:** `None` (LIVE) or "YYYY-MM-DD HH:MM:SS" (REPLAY)
**Decision Point:** `TimeSimulator.__init__()`

```python
class TimeSimulator:
    def __init__(self, replay_start_str: Optional[str], interval_seconds: int):
        self._is_replay = replay_start_str is not None
        
        if self._is_replay:
            # REPLAY MODE: Use provided timestamp
            self._current_time = pd.to_datetime(replay_start_str).tz_localize(TIMEZONE)
            self.end_of_day = self._get_session_end(self._current_time)
            logging.info(f"TimeSimulator: REPLAY mode. Start: {self._current_time}, End: {self.end_of_day}")
        else:
            # LIVE MODE: Use current system time
            self._current_time = self._get_live_time()
            self.end_of_day = None  # Not fixed in live mode
            logging.info("TimeSimulator: LIVE mode.")
```

---

## Part 2: Time Simulator Deep Dive

### TimeSimulator Class Location
**File:** `src/stockreports/utils/time_utils.py` (lines 35-80)

### Initialization Flow

```
TimeSimulator.__init__(replay_start_str, interval_seconds)
    │
    ├─ IF replay_start_str is None:
    │   └─ LIVE MODE
    │       ├─ _current_time = datetime.now(UTC).astimezone(TIMEZONE)
    │       ├─ end_of_day = None
    │       └─ Runs indefinitely
    │
    └─ IF replay_start_str is "YYYY-MM-DD HH:MM:SS":
        └─ REPLAY MODE
            ├─ _current_time = pd.to_datetime(replay_start_str).tz_localize(TIMEZONE)
            ├─ end_of_day = _get_session_end(_current_time)
            │   └─ Finds last trading session end time for the given date
            └─ Stops at end_of_day
```

### Key Methods

#### `is_running() -> bool`
Determines if the main monitoring loop should continue:

```python
def is_running(self) -> bool:
    if self._is_replay:
        # REPLAY: Stop if current time has passed end of trading day
        return self._current_time <= self.end_of_day
    return True  # LIVE: Always continues indefinitely
```

**Impact on Main Loop:**
```
LIVE MODE:
    while time_simulator.is_running():
        # Loops forever (until KeyboardInterrupt or crash)
        # Processes current real-world time

REPLAY MODE:
    while time_simulator.is_running():
        # Loops until current_time > end_of_day
        # Process stops automatically after trading hours
```

#### `advance()`
Moves time forward for replay mode:

```python
def advance(self):
    if self._is_replay:
        self._current_time += self._interval  # Advance by MONITORING_INTERVAL_SECONDS
```

**Impact:**
- REPLAY: Each iteration advances time by `MONITORING_INTERVAL_SECONDS`
- LIVE: No effect (real time advances naturally)

#### `is_replay_mode() -> bool`
Returns True if in replay mode, False if live mode.

---

## Part 3: Main Monitoring Loop - Time-Dependent Behavior

**Location:** `SymbolAlerter._perform_monitoring_session()` (lines 244-350)

### Loop Structure with Time Behavior

```python
while time_simulator.is_running():
    current_time = time_simulator.get_current_time()
    
    # 1. Check for scheduled close position notifications
    scheduled_notification = check_and_notify(current_time)
    
    # 2. Check trading hours
    if not is_trading_hours(current_time):
        if time_simulator.is_replay_mode():
            time_simulator.advance()  # Jump forward to next trading window
            continue
        else:
            time.sleep(900)  # Wait 15 minutes before next check
            continue
    
    # 3-5. Process data and alerts (same for both modes)
    
    # 6. Advance time simulator
    time_simulator.advance()
```

### Critical Branching: Outside Trading Hours

```
LIVE MODE (DEBUG_REPLAY_START_TIME = None):
    Outside trading hours?
        ├─ YES → time.sleep(900)  [Wait 15 minutes in real time]
        └─ NO → Process data normally

REPLAY MODE (DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"):
    Outside trading hours?
        ├─ YES → time_simulator.advance()  [Jump to next time slot]
        └─ NO → Process data normally
```

---

## Part 4: Error Handling - Mode-Dependent Resilience

**Location:** `SymbolAlerter._run_deployment_mode()` (lines 216-241)

### Exception Handling Differs by Mode

```python
except Exception as e:
    if settings.DEBUG_REPLAY_START_TIME is None:
        # LIVE MODE: Resilient
        self.logger.info(f"Waiting {MONITORING_INTERVAL_SECONDS}s before restarting...")
        time.sleep(settings.MONITORING_INTERVAL_SECONDS)
        # Continue supervisor loop to restart monitoring session
    else:
        # REPLAY MODE: Stop on error
        self.logger.error("Exiting replay due to critical error.")
        break  # Exit supervisor loop
```

**Impact:**
- LIVE: Crashes are auto-recovered (resilient)
- REPLAY: Crashes are fatal (deterministic)

---

## Part 5: Report Storage - Mode-Driven Separation

**Location:** `src/stockreports/utils/report_utils.py` (lines 30-60)

### Report Directory Selection Logic

```python
def get_reports_directory_name():
    """
    Determines the base reports directory based on time simulator mode.
    """
    if settings.DEBUG_REPLAY_START_TIME is None:
        return "reports"          # LIVE MODE: Standard directory
    else:
        return "reports_replay"   # REPLAY MODE: Separate directory
```

### Directory Structure

```
reports/
├── [symbol]/
│   └── deployment/
│       ├── alert_notification_*.json
│       └── ...
│
reports_replay/  ← Used when DEBUG_REPLAY_START_TIME is set
├── [symbol]/
│   └── deployment/
│       ├── alert_notification_*.json
│       └── ...
```

**Purpose:** Separate real-time monitoring alerts from historical replay simulations.

---

## Part 6: System-Wide Impact Map

### Configuration Detection Points

| Component | Location | Checks | Behavior |
|-----------|----------|--------|----------|
| **TimeSimulator** | `time_utils.py:44` | `is_replay = (replay_start_str is not None)` | Initializes LIVE or REPLAY |
| **Main Loop** | `symbol_alerter.py:260` | `is_running()` | Continues indefinitely (LIVE) or bounded (REPLAY) |
| **Trading Hours Skip** | `symbol_alerter.py:273-282` | `is_replay_mode()` | Jumps time (REPLAY) or sleeps (LIVE) |
| **Error Handling** | `symbol_alerter.py:234-240` | `DEBUG_REPLAY_START_TIME is None` | Restarts (LIVE) or exits (REPLAY) |
| **Report Storage** | `report_utils.py:54` | `DEBUG_REPLAY_START_TIME is None` | reports/ or reports_replay/ |
| **Tools/Utilities** | `update_alert_field.py:43` | Uses `get_reports_directory_name()` | Scans correct directory |

---

## Part 7: Complete Execution Flow - LIVE vs REPLAY

### LIVE MODE Execution
```
MODE = "DEPLOYMENT" + DEBUG_REPLAY_START_TIME = None
    │
    └─ SymbolAlertManager._run_deployment()
        └─ Concurrent execution via ThreadPoolExecutor
            └─ For each symbol:
                └─ SymbolAlerter.execute()
                    └─ _run_deployment_mode()  [Supervisor Loop]
                        └─ _perform_monitoring_session()
                            └─ TimeSimulator(replay_start_str=None, ...)
                                ├─ _is_replay = False
                                ├─ end_of_day = None
                                └─ Monitoring Loop:
                                    while time_simulator.is_running():  # ← True forever
                                        │
                                        ├─ current_time = datetime.now(TIMEZONE)
                                        │
                                        ├─ IF outside trading hours:
                                        │   └─ time.sleep(900)  [Wait 15 min in real time]
                                        │
                                        ├─ ELSE:
                                        │   ├─ Fetch API data for current_time
                                        │   ├─ Process alerts
                                        │   └─ Send notifications
                                        │
                                        └─ advance()  # No effect in LIVE mode
                                        
                                    # Loop continues indefinitely until:
                                    # - KeyboardInterrupt
                                    # - Exception → Caught, restart with sleep
```

### REPLAY MODE Execution
```
MODE = "DEPLOYMENT" + DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"
    │
    └─ SymbolAlertManager._run_deployment()
        └─ Concurrent execution via ThreadPoolExecutor
            └─ For each symbol:
                └─ SymbolAlerter.execute()
                    └─ _run_deployment_mode()  [Supervisor Loop]
                        └─ _perform_monitoring_session()
                            └─ TimeSimulator(replay_start_str="2026-04-08 09:05:00", ...)
                                ├─ _is_replay = True
                                ├─ _current_time = 2026-04-08 09:05:00 (TIMEZONE)
                                ├─ end_of_day = 2026-04-08 14:27:00 (Last session end)
                                └─ Monitoring Loop:
                                    while time_simulator.is_running():  # True until > 14:27
                                        │
                                        ├─ current_time = 2026-04-08 09:05:00
                                        │  (advances each iteration)
                                        │
                                        ├─ IF outside trading hours:
                                        │   └─ time_simulator.advance()  [Jump to next slot]
                                        │       └─ _current_time += 57 seconds
                                        │
                                        ├─ ELSE:
                                        │   ├─ Fetch API data for simulated current_time
                                        │   ├─ Process alerts
                                        │   └─ Send notifications
                                        │
                                        └─ time_simulator.advance()
                                            └─ _current_time += 57 seconds
                                        
                                    # Loop continues until:
                                    # - current_time > end_of_day → Loop exits cleanly
                                    # - Exception → Caught, exits immediately (not restarted)
```

---

## Part 8: Configuration Examples

### Example 1: Production Live Monitoring
```python
# config/settings.py
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = None
MONITORING_INTERVAL_SECONDS = 57

# Result:
# - Runs indefinitely in real time
# - Checks market every 57 seconds
# - Waits 15 minutes during non-trading hours
# - Auto-restarts on crashes
# - Saves alerts to reports/ directory
```

### Example 2: Historical Replay Simulation
```python
# config/settings.py
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = "2026-04-03 09:05:00"
MONITORING_INTERVAL_SECONDS = 57

# Result:
# - Simulates trading day starting at 09:05 on April 3
# - Stops at end of trading day (14:27)
# - Advances simulated time by 57 seconds each iteration
# - Skips non-trading hours instantly (no sleep)
# - Exits immediately on crash
# - Saves alerts to reports_replay/ directory
```

### Example 3: Development with Local Data
```python
# config/settings.py
MODE = "DEVELOPMENT"
DEBUG_REPLAY_START_TIME = (ignored)

# Result:
# - Loads data from local JSON files
# - Processes each date sequentially
# - DEBUG_REPLAY_START_TIME is ignored
# - Different execution path entirely
```

---

## Part 9: Critical Insights

### Insight 1: Two Independent Configuration Axes
```
┌─────────────────────────────────────────────────┐
│           MODE = DEVELOPMENT/DEPLOYMENT         │
│  (Controls data source: Files vs API)           │
├─────────────────────────────────────────────────┤
│ DEVELOPMENT:                 │  DEPLOYMENT:    │
│ - Load from local files      │ - Fetch from API│
│ - Batch process dates        │ - Time-based    │
│ - Date-driven loop           │ - Continuous    │
└─────────────────────────────────────────────────┘
                      ↓
     ┌────────────────────────────────────────────┐
     │  DEBUG_REPLAY_START_TIME = None or String  │
     │  (Only matters in DEPLOYMENT mode)         │
     ├────────────────────────────────────────────┤
     │ None: LIVE Mode              │ String: REPLAY Mode   │
     │ - Current system time        │ - Simulated time      │
     │ - Indefinite loop            │ - Bounded by end_of_day|
     │ - Sleep during non-hours     │ - Jump during non-hours|
     │ - Auto-restart on crash      │ - Exit on crash       │
     │ - reports/ storage           │ - reports_replay/ storage │
     └────────────────────────────────────────────┘
```

### Insight 2: Time Simulator is the Core Mechanism
The `TimeSimulator` class is the **central switch** that controls:
- How current time is obtained (system time vs simulated)
- When the loop should stop (`is_running()`)
- How to handle non-trading hours (sleep vs jump)
- Error recovery behavior

### Insight 3: Report Separation is Intentional
Replay and Live alerts are stored separately to:
- Prevent live monitoring data from being polluted with historical replays
- Allow independent analysis of real-time vs simulated performance
- Enable easy cleanup of replay data without affecting production alerts

### Insight 4: DEPLOYMENT Mode is Flexible
Both LIVE and REPLAY use the same core code path:
- Same executor framework
- Same data processing
- Same notification logic
- Only differs in time behavior and reporting

---

## Part 10: Code Paths Summary

### Configuration Check Locations (All in DEPLOYMENT mode)

**Location 1: TimeSimulator Initialization**
```python
# src/stockreports/utils/time_utils.py:44
self._is_replay = replay_start_str is not None
```

**Location 2: Main Loop Continuation**
```python
# src/stockreports/utils/time_utils.py:78
def is_running(self) -> bool:
    if self._is_replay:
        return self._current_time <= self.end_of_day
    return True
```

**Location 3: Trading Hours Handling**
```python
# src/stockreports/alert/symbol_alerter.py:273
if time_simulator.is_replay_mode():
    time_simulator.advance()  # REPLAY
else:
    time.sleep(900)  # LIVE
```

**Location 4: Error Recovery**
```python
# src/stockreports/alert/symbol_alerter.py:234
if settings.DEBUG_REPLAY_START_TIME is None:
    # LIVE: Restart with sleep
else:
    # REPLAY: Exit immediately
```

**Location 5: Report Storage**
```python
# src/stockreports/utils/report_utils.py:54
if settings.DEBUG_REPLAY_START_TIME is None:
    return "reports"  # LIVE
else:
    return "reports_replay"  # REPLAY
```

---

## Part 11: Updated Technical Reference Understanding

### CRITICAL UPDATE TO PREVIOUS TECHNICAL REFERENCE DOCUMENTATION

The Technical Reference document stated: "DEPLOYMENT mode only"

**Correction:** DEPLOYMENT mode contains TWO sub-modes:

1. **LIVE DEPLOYMENT** - Real-time monitoring indefinitely
   - `MODE = "DEPLOYMENT"` + `DEBUG_REPLAY_START_TIME = None`
   - Uses real system time
   - Runs indefinitely
   - Auto-recovers from crashes
   - Reports → `reports/`

2. **REPLAY DEPLOYMENT** - Historical simulation with bounded time
   - `MODE = "DEPLOYMENT"` + `DEBUG_REPLAY_START_TIME = "YYYY-MM-DD HH:MM:SS"`
   - Uses simulated time
   - Stops at end of trading day
   - Exits on crashes
   - Reports → `reports_replay/`

Both use the same core monitoring logic but differ in **time behavior** and **error handling**.

---

## Part 12: Current Configuration Status

**Current Settings (as of 2026-04-08):**
```python
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"
MONITORING_INTERVAL_SECONDS = 57
```

**Current Execution Mode:** REPLAY DEPLOYMENT

**What This Means:**
- System will simulate trading day starting at 09:05 on April 8, 2026
- Will process 57-second intervals
- Will stop at 14:27 (end of last trading session)
- Will not restart on crashes
- Alerts saved to `reports_replay/`

---

## Summary of Key Findings

✅ **DEBUG_REPLAY_START_TIME is NOT about DEVELOPMENT vs DEPLOYMENT**

✅ **It controls TIME BEHAVIOR within DEPLOYMENT mode**

✅ **Two distinct modes exist within DEPLOYMENT:**
- LIVE (None) = Real-time indefinite monitoring with auto-recovery
- REPLAY (timestamp) = Simulated bounded monitoring that exits cleanly

✅ **TimeSimulator is the control mechanism**
- Determines loop continuation
- Controls time advancement
- Handles non-trading hours differently
- Affects error recovery strategy

✅ **Report separation is intentional**
- `reports/` for real-time LIVE monitoring
- `reports_replay/` for historical REPLAY simulation

✅ **Current configuration uses REPLAY mode**
- Starting at 2026-04-08 09:05:00
- Will complete when trading day ends
- Separate alert storage for analysis isolation

---

## Next Steps for Implementation Guides Documentation

This investigation should be integrated into Technical Reference findings:

1. **Update SymbolAlerter section** - Clarify LIVE vs REPLAY sub-modes
2. **Update TimeSimulator section** - Document is_running() behavior
3. **Add Time Behavior section** - Explain trading hours handling
4. **Add Error Recovery section** - Document mode-dependent resilience
5. **Add Report Storage section** - Explain directory separation logic

The system is more sophisticated than a simple DEVELOPMENT/DEPLOYMENT split. It's a **three-tier configuration hierarchy:**
1. MODE (Data source)
2. DEBUG_REPLAY_START_TIME (Time behavior)
3. Approach selection (Analysis logic)
