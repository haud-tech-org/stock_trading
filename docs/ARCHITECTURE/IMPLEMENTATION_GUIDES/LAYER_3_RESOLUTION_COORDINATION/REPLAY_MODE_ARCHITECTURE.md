# Replay Mode Architecture & Reports Directory Separation

**Location:** `docs/ARCHITECTURE/IMPLEMENTATION_GUIDES/`  
**Purpose:** Operational documentation for replay testing and report generation strategies  
**Audience:** Developers, QA, operations teams

---

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     STOCK TRADING ALERTER SYSTEM                     │
└─────────────────────────────────────────────────────────────────────┘

                          Configuration Layer
                                  │
                    ┌─────────────┴─────────────┐
                    │                           │
         DEBUG_REPLAY_START_TIME             Other Settings
            ▼ (Control Point)                   ▼
         ┌──────────────────────┐            ┌──────┐
         │  None = LIVE MODE    │            │ MODE │
         │  Set = REPLAY MODE   │            │ etc. │
         └──────────┬───────────┘            └──────┘
                    │
                    ▼
      ┌─────────────────────────────┐
      │ get_reports_directory_name()│  ◄─── UTILITY FUNCTION
      │                             │
      │ Returns: "reports" or       │
      │          "reports_replay"   │
      └────────────┬────────────────┘
                   │
         ┌─────────┴─────────┐
         ▼                   ▼
      "reports/"        "reports_replay/"
      (LIVE MODE)       (REPLAY MODE)
         │                   │
         ├─ VN30/           ├─ VN30/
         │  ├─ deployment/  │  ├─ deployment/
         │  │  ├─ vra/      │  │  ├─ vra/
         │  │  └─ ...       │  │  └─ ...
         │  └─ dev/         │  └─ dev/
         │                  │
         └─ VN30F1M/        └─ VN30F1M/
```

---

## Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                    ALERT NOTIFICATION FLOW                            │
└──────────────────────────────────────────────────────────────────────┘

1. ALERT GENERATION
   ────────────────
   SymbolAlerter._run_deployment_mode()
           │
           ▼
   TimeSimulator created
   Check: DEBUG_REPLAY_START_TIME
   │
   ├─ None          ├─ "2026-01-08..."
   │  (LIVE)        │  (REPLAY)
   └─────┬──────────┴─────┐
         │                │
         ▼                ▼
   _perform_monitoring_session()
           │
           ▼
   executor.run() → AlertResult
           │
   ┌───────┴───────┐
   ▼               ▼
LIVE MODE      REPLAY MODE
│               │
├─ Real-time    ├─ Historical
├─ Live API     ├─ Live API (simulated time)
└─ Continuous   └─ Time window


2. ALERT ENRICHMENT
   ────────────────
   NotificationManager.process_and_notify(result, symbol)
           │
           ├─ Extract latest alert
           ├─ Check duplicates
           ├─ Enrich with prices
           └─ Send notifications


3. REPORT PERSISTENCE
   ───────────────────
   save_alert_report(result, symbol, date_str)
           │
           ▼
   ┌──────────────────────┐
   │ get_reports_directory│
   │ _name()              │  ◄─── CHECKS DEBUG_REPLAY_START_TIME
   └──────────┬───────────┘
              │
      ┌───────┴───────┐
      │               │
      ▼               ▼
   reports/      reports_replay/
   (LIVE)        (REPLAY)
      │               │
      ▼               ▼
   {symbol}/     {symbol}/
   {mode}/       {mode}/
   {approach}/   {approach}/
      │               │
      └───────┬───────┘
              ▼
   alert_notification_{date}.json
   (Different directories)
```

---

## Function Call Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│         TOP-LEVEL FUNCTIONS (Using Mode Logic)              │
└─────────────────────────────────────────────────────────────┘
            │
    ┌───────┼───────┬──────────────┐
    │       │       │              │
    ▼       ▼       ▼              ▼
save_alert_ update_ save_prof     get_consol.
report()    summary() itability    _scenario_
                    _report()      directory()
    │       │       │              │
    └───────┼───────┼──────────────┘
            │
    ┌───────▼────────────────────────────┐
    │  get_reports_directory_name()      │  ◄─── CORE FUNCTION
    │                                    │
    │  Checks: settings.                 │
    │          DEBUG_REPLAY_START_TIME   │
    │                                    │
    │  Returns: "reports"     (LIVE)     │
    │        or "reports_replay" (REPLAY)│
    └────────────────────────────────────┘
```

---

## Mode Selection Logic

```
┌──────────────────────────────────────────────────────────────┐
│          CONFIGURATION-DRIVEN MODE SELECTION                 │
└──────────────────────────────────────────────────────────────┘

START
  │
  ▼
Read settings.DEBUG_REPLAY_START_TIME
  │
  ├─────────────┬──────────────────────────────┐
  │             │                              │
  ▼             ▼                              ▼
None         "2026-01-08 09:05:00"          Other values
  │             │                              │
  ▼             ▼                              ▼
LIVE MODE   REPLAY MODE                    REPLAY MODE
  │             │                              │
  ├─────────────┴──────────────────────────────┤
  │                                            │
  ▼                                            ▼
"reports" directory            "reports_replay" directory
  │                                            │
  ├─ Live API fetch          ├─ Live API with
  ├─ Real-time monitoring    │  simulated time
  ├─ Continuous operation    ├─ Backtesting
  └─ Production use          └─ Strategy validation
```

---

## Operational Procedures

### LIVE Mode (Production)

**Configuration:**
```python
# In settings.py
DEBUG_REPLAY_START_TIME = None  # Indicates LIVE mode
```

**Behavior:**
1. System uses current system time
2. Reports saved to `reports/` directory
3. Real-time API calls for price data
4. Continuous monitoring during market hours

**Report Structure:**
```
reports/
├── VN30/
│   ├── deployment/
│   │   └── vra/
│   │       └── alert_notification_2026-04-10.json
│   └── dev/
└── VN30F1M/
```

### REPLAY Mode (Testing & Backtesting)

**Configuration:**
```python
# In settings.py
DEBUG_REPLAY_START_TIME = "2026-01-08 09:05:00"  # Historical start time
```

**Behavior:**
1. System uses simulated time (TimeSimulator)
2. Reports saved to `reports_replay/` directory
3. API calls made with historical time context
4. Execution within specified time window

**Report Structure:**
```
reports_replay/
├── VN30/
│   ├── deployment/
│   │   └── vra/
│   │       └── alert_notification_2026-01-08.json
│   └── dev/
└── VN30F1M/
```

---

## Implementation Details

### get_reports_directory_name() Function

**Purpose:** Centralized mode selection logic

**Implementation:**
```python
def get_reports_directory_name() -> str:
    """
    Determine reports directory based on DEBUG_REPLAY_START_TIME setting.
    
    Returns:
        "reports"        if DEBUG_REPLAY_START_TIME is None (LIVE mode)
        "reports_replay" if DEBUG_REPLAY_START_TIME is set (REPLAY mode)
    """
    from src.stockreports.config.settings import DEBUG_REPLAY_START_TIME
    
    if DEBUG_REPLAY_START_TIME is None:
        return "reports"  # LIVE mode
    else:
        return "reports_replay"  # REPLAY mode
```

**Usage in save_alert_report():**
```python
def save_alert_report(result: AlertResult, symbol: str, date_str: str) -> None:
    """Save alert report to appropriate directory based on mode."""
    
    # Get correct directory for current mode
    reports_dir = get_reports_directory_name()
    
    # Build path
    report_path = f"{reports_dir}/{symbol}/deployment/vra/alert_notification_{date_str}.json"
    
    # Save report
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(result.to_dict(), f, indent=2)
```

---

## Testing Scenarios

### Scenario 1: Local Development Testing

**Setup:**
```python
DEBUG_REPLAY_START_TIME = "2026-03-24 09:00:00"  # Test date
```

**Expected Behavior:**
- Reports saved to `reports_replay/` directory
- Alerts generated using historical data
- No interference with live data
- Consistent results across multiple test runs

### Scenario 2: Production Validation

**Setup:**
```python
DEBUG_REPLAY_START_TIME = None  # Live mode
```

**Expected Behavior:**
- Reports saved to `reports/` directory
- Alerts generated in real-time
- Live API data processed continuously
- Results vary with market conditions

### Scenario 3: Historical Backtesting

**Setup:**
```python
DEBUG_REPLAY_START_TIME = "2026-01-15 09:05:00"  # Historical date (e.g., 3 months ago)
```

**Expected Behavior:**
- Reports saved to `reports_replay/` directory
- System simulates time progression
- All executors run with historical context
- Strategy validation against past market data

---

## Troubleshooting

### Issue: Reports going to wrong directory

**Cause:** DEBUG_REPLAY_START_TIME set incorrectly

**Solution:**
```python
# Check current setting
from src.stockreports.config.settings import DEBUG_REPLAY_START_TIME
print(f"Current mode: {DEBUG_REPLAY_START_TIME}")
print(f"Directory: {get_reports_directory_name()}")

# Reset to LIVE mode
# In settings.py:
DEBUG_REPLAY_START_TIME = None
```

### Issue: Replay results inconsistent

**Cause:** Different time values or settings between runs

**Solution:**
1. Verify DEBUG_REPLAY_START_TIME is identical across runs
2. Check TimeSimulator initialization
3. Validate API historical data consistency
4. Ensure time zone handling is consistent

### Issue: Mixed reports (LIVE and REPLAY)

**Cause:** Mode switched during runtime

**Solution:**
1. Never change DEBUG_REPLAY_START_TIME during execution
2. Restart system after mode change
3. Verify setting before starting monitoring
4. Use configuration validation

---

## Cross-References

For more information, see:
- 👉 [OPERATIONS_DEPLOYMENT_GUIDE.md](./OPERATIONS_DEPLOYMENT_GUIDE.md) - Deployment procedures
- 👉 [TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md](../TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md) - Complete system architecture
- 👉 [TECHNICAL_REFERENCE/VISUAL_GUIDE.md](../TECHNICAL_REFERENCE/VISUAL_GUIDE.md) - Architecture diagrams

---

**Version:** 1.0  
**Last Updated:** April 10, 2026  
**Status:** ✅ Complete
