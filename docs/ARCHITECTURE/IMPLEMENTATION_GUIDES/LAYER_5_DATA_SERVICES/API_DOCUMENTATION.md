# API Documentation - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Code Analysis  
**Audience:** Developers, API consumers, integration partners  
**Prerequisites:** Technical Reference architecture understanding  

---

## Overview

This documentation covers the PUBLIC APIs exposed by the stock alerting system. All documented types, methods, and signatures are from actual codebase analysis.

---

## AlertData Model

**File:** `/src/stockreports/alert/model/models.py:1-100`

**Purpose:** Standardized data structure for a single alert

### Fields

```python
@dataclass
class AlertData:
    # Required fields
    approach: Approach                          # Which executor generated this alert
    id: str                                     # Unique identifier for alert
    signal: Signal                              # BUY, SELL, NEUTRAL
    alert_price: float                          # Entry price when alert triggered
    alert_time: pd.Timestamp                    # ISO 8601 timestamp when alert triggered
    start_price: float                          # Starting reference price
    start_time: pd.Timestamp                    # ISO 8601 timestamp of start
    
    # Optional fields
    details: Optional[str]                      # Approach-specific details as JSON string
    trend: Optional[Trend]                      # UPTREND, DOWNTREND, SIDEWAYS
    profit_loss: Optional[float]                # Realized P/L in % or points
    period_time: Optional[int]                  # Time period in minutes
    status: Optional[Status]                    # SUCCESS, FAILED, PENDING
    validation_price_time: Optional[pd.Timestamp]  # When validation price reached
    time_to_best_price: Optional[int]           # Minutes to reach best price
    min_expected_profit_loss: Optional[float]   # Minimum expected P/L
    symbol: Optional[str]                       # Stock symbol
    magnitude: Optional[float]                  # Alert strength/magnitude
    structural_suggested_price: Optional[float] # S/R-based suggested entry
    performance_suggested_price: Optional[float] # History-based suggested entry
    suggested_profit_threshold: Optional[float] # Suggested exit at this profit %
```

### Creating AlertData

**From Dictionary:**
```python
alert_dict = {
    'approach': 'ICHIMOKU',
    'id': 'alert_001',
    'signal': 'BUY',
    'alert_price': 1250.50,
    'alert_time': '2026-04-08T14:23:45+00:00',
    'start_price': 1240.00,
    'start_time': '2026-04-08T14:00:00+00:00',
    'trend': 'UPTREND',
    'status': 'SUCCESS'
}

alert = AlertData.from_dict(alert_dict)
```

**Creating Directly:**
```python
from src.stockreports.alert.model.models import AlertData
from src.stockreports.alert.common.constants import Approach, Signal
import pandas as pd

alert = AlertData(
    approach=Approach.ICHIMOKU,
    id='alert_001',
    signal=Signal.BUY,
    alert_price=1250.50,
    alert_time=pd.Timestamp('2026-04-08T14:23:45', tz='UTC'),
    start_price=1240.00,
    start_time=pd.Timestamp('2026-04-08T14:00:00', tz='UTC'),
    trend=Trend.UPTREND,
    status=Status.SUCCESS
)
```

### Converting to Dictionary

```python
# Convert back to dict (for JSON serialization)
alert_dict = alert.to_dict()

# Timestamps are automatically converted to ISO 8601 strings
print(alert_dict['alert_time'])  # '2026-04-08T14:23:45+00:00'
```

### Required vs Optional

**Required fields:**
- `approach` - Always present
- `id` - Always present
- `signal` - Always present
- `alert_price` - Always present
- `alert_time` - Always present (pd.Timestamp, timezone-aware)
- `start_price` - Always present
- `start_time` - Always present (pd.Timestamp, timezone-aware)

**Optional fields:**
- All other fields may be None

---

## AlertResult Model

**File:** `/src/stockreports/alert/model/models.py:135-250`

**Purpose:** Return value from Executor.run()

### Fields

```python
@dataclass
class AlertResult:
    approach_name: str                          # Name of executor (e.g., 'StrongCandle')
    confirmed_alerts: Optional[List[AlertData]] # List of generated alerts (may be empty)
    status: Status                              # SUCCESS or FAILED
    message: str                                # Error message if FAILED
```

### Creating AlertResult

```python
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Status

# Success case (multiple alerts)
result = AlertResult(
    approach_name='Ichimoku',
    confirmed_alerts=[alert1, alert2, alert3],
    status=Status.SUCCESS,
    message=''
)

# Success case (no alerts found)
result = AlertResult(
    approach_name='Ichimoku',
    confirmed_alerts=[],
    status=Status.SUCCESS,
    message=''
)

# Failure case
result = AlertResult(
    approach_name='Ichimoku',
    confirmed_alerts=None,
    status=Status.FAILED,
    message='Insufficient data for calculation'
)
```

### Using AlertResult

```python
# Check if alerts were generated
if result.has_alerts:
    for alert in result.confirmed_alerts:
        print(f"Alert: {alert.signal} at {alert.alert_price}")

# Check status
if result.status == Status.SUCCESS:
    print("Executor ran successfully")
else:
    print(f"Executor failed: {result.message}")

# Get count of alerts
count = len(result.confirmed_alerts) if result.confirmed_alerts else 0
print(f"Generated {count} alerts")
```

### Validation Rules

```python
# confirmed_alerts validation happens in __post_init__

# ✅ Valid: List of AlertData
result = AlertResult(
    approach_name='Test',
    confirmed_alerts=[alert1, alert2],
    status=Status.SUCCESS
)

# ✅ Valid: Empty list
result = AlertResult(
    approach_name='Test',
    confirmed_alerts=[],
    status=Status.SUCCESS
)

---

## ResolutionCoordinator

**File:** `/src/stockreports/coordination/resolution_coordinator.py` (180 lines)

**Purpose:** Map trading approaches to configured time resolutions

### ResolutionCoordinator API

```python
from src.stockreports.coordination.resolution_coordinator import ResolutionCoordinator
from src.stockreports.alert.common.constants import Approach

# Initialize (loads APPROACH_RESOLUTION_MAPPING from signal_settings.py)
coordinator = ResolutionCoordinator()

# Get resolution for a specific approach
def get_resolutions(approach: str) -> int:
    """
    Get resolution (in minutes) for an approach.
    
    Args:
        approach: Approach constant string (e.g., Approach.ICHIMOKU)
    
    Returns:
        Resolution in minutes: 1, 5, 15, or 60
    
    Raises:
        KeyError: If approach not in APPROACH_RESOLUTION_MAPPING
    
    Example:
        resolution = coordinator.get_resolutions(Approach.ICHIMOKU)
        # Returns: 15 (if configured for 15-minute resolution)
    """
    
# Get all required resolutions for a symbol
def get_required_resolutions(symbol: str) -> list[int]:
    """
    Get list of resolutions needed for a symbol's approaches.
    
    Gets all approaches configured for the symbol from SYMBOL_ALERT_APPROACHES,
    then returns sorted unique resolutions for those approaches.
    Always includes resolution 1 (1-minute).
    
    Args:
        symbol: Stock symbol (e.g., "VN30F1M")
    
    Returns:
        Sorted list of unique resolutions: e.g., [1, 5, 15]
    
    Example:
        resolutions = coordinator.get_required_resolutions("VN30F1M")
        # Returns: [1, 5, 15] if VN30F1M has approaches on 1, 5, 15 min
    """
```

### Usage Examples

**Example 1: Get Resolution for Single Approach**
```python
from src.stockreports.coordination.resolution_coordinator import ResolutionCoordinator
from src.stockreports.alert.common.constants import Approach

coordinator = ResolutionCoordinator()

# Get resolution for ICHIMOKU
ichimoku_res = coordinator.get_resolutions(Approach.ICHIMOKU)
print(f"ICHIMOKU uses {ichimoku_res}-minute data")  # Output: 15-minute data
```

**Example 2: Initialize Multi-Resolution Storage**
```python
from src.stockreports.coordination.resolution_coordinator import ResolutionCoordinator

coordinator = ResolutionCoordinator()
symbol = "VN30F1M"

# Get all required resolutions for this symbol
required_resolutions = coordinator.get_required_resolutions(symbol)
print(f"Required resolutions for {symbol}: {required_resolutions}")

# Initialize storage
resolution_dfs = {
    res: None for res in required_resolutions
}
# Result: {1: None, 5: None, 15: None}
```

**Example 3: In Monitoring Loop**
```python
from src.stockreports.coordination.resolution_coordinator import ResolutionCoordinator

coordinator = ResolutionCoordinator()

# For each approach configured for the symbol
for approach_name in symbol_approaches:
    # Get resolution for this approach
    resolution = coordinator.get_resolutions(approach_name)
    
    # Get data for this resolution (from multi-resolution storage)
    approach_df = resolution_dfs[resolution]
    
    # Run executor on correct resolution data
    executor = get_executor(approach_name)
    result = executor.run(df=approach_df, ...)
```

### Configuration: APPROACH_RESOLUTION_MAPPING

Located in: `src/stockreports/config/signal_settings.py`

```python
APPROACH_RESOLUTION_MAPPING = {
    "CONSISTENT_MOMENTUM": 1,      # 1-minute resolution
    "ICHIMOKU": 1,                # 1-minute resolution
    "STRONG_CANDLE": 1,            # 1-minute resolution
    "VRA": 1,                      # 1-minute resolution
    "VOLUME_SPIKE_CONFIRMATION": 1,  # 1-minute resolution
    "CONSISTENT_VOLUME_ANCHOR": 1   # 1-minute resolution
}
```

**To Change Resolution:**
```python
# Before:
APPROACH_RESOLUTION_MAPPING = {
    "ICHIMOKU": 1,  # Was 1-minute
}

# After:
APPROACH_RESOLUTION_MAPPING = {
    "ICHIMOKU": 15,  # Now 15-minute
}

# No code changes needed! ResolutionCoordinator will auto-detect.
```

### Validation Rules

ResolutionCoordinator validates configuration at initialization:

1. **Approach exists:** All keys must be valid Approach constants
   - Error: `ValueError: Approach 'INVALID_APPROACH' not found in Approach class`

2. **Resolution is integer:** All values must be `int` type
   - Error: `TypeError: Approach 'ICHIMOKU' resolution must be int, got str: '15'`

3. **Resolution is supported:** Must be in {1, 5, 15, 60}
   - Error: `ValueError: Approach 'ICHIMOKU' uses unsupported resolution 7`

---

## Executor Framework

**File:** `/src/stockreports/alert/executor.py` (Base class - 345 lines)

### Base Executor

```python
from src.stockreports.alert.executor import Executor

class Executor:
    """Base class for all alert executors."""
    
    def __init__(self, mode: str, symbol: str, alert_sources: list[str]):
        """
        Initialize executor.
        
        Args:
            mode: 'deployment' (str, not Mode enum)
                  Note: 'development' mode being removed in Phase 3
            symbol: Stock symbol to analyze
            alert_sources: List of symbols that trigger alerts
        """
    
    def run(self, alert_data: list[AlertData]) -> AlertResult:
        """
        Generate alerts from alert data.
        
        Args:
            alert_data: List of AlertData objects
            
        Returns:
            AlertResult with confirmed_alerts list
            
        Raises:
            Exception: On critical errors (caught and logged)
        """
    
    def _find_alerts(self, alert_data: list[AlertData]) -> list[AlertData]:
        """
        Find alerts (implemented by subclasses).
        
        Must be implemented by each executor.
        
        Args:
            alert_data: List of input alerts
            
        Returns:
            List of AlertData objects that passed executor's criteria
        """
        raise NotImplementedError
```

### Actual Executors

**6 Real Executors:**

1. **StrongCandleExecutor**
   - File: `/src/stockreports/alert/approach/strong_candle/executor.py`
   - Criteria: Strong candle patterns

2. **ConsistentMomentumExecutor**
   - File: `/src/stockreports/alert/approach/consistent_momentum/executor.py`
   - Criteria: Consistent price momentum

3. **VRAExecutor**
   - File: `/src/stockreports/alert/approach/vra/executor.py`
   - Criteria: Volume-price analysis

4. **IchimokuExecutor**
   - File: `/src/stockreports/alert/approach/ichimoku/executor.py`
   - Criteria: Ichimoku cloud signals

5. **VolumeSpikeExecutor**
   - File: `/src/stockreports/alert/approach/volume_spike/executor.py`
   - Criteria: Volume anomalies

6. **ConsistentVolumeAnchorExecutor**
   - File: `/src/stockreports/alert/approach/consistent_volume_anchor/executor.py`
   - Criteria: Volume and price anchoring

### Using an Executor

```python
from src.stockreports.alert.approach.strong_candle.executor import StrongCandleExecutor
from src.stockreports.alert.model.models import AlertData, AlertResult
import pandas as pd

# Create executor
executor = StrongCandleExecutor(
    mode='deployment',
    symbol='VN30F1M',
    alert_sources=['VN30', 'VN30F1M']
)

# Create some alerts to analyze
alerts = [
    AlertData(
        approach='STRONG_CANDLE',
        id='alert_001',
        signal='BUY',
        alert_price=1250.50,
        alert_time=pd.Timestamp('2026-04-08T14:23:45', tz='UTC'),
        start_price=1240.00,
        start_time=pd.Timestamp('2026-04-08T14:00:00', tz='UTC')
    )
]

# Run executor
result: AlertResult = executor.run(alerts)

# Use result
if result.has_alerts:
    for alert in result.confirmed_alerts:
        print(f"Confirmed: {alert.signal} at {alert.alert_price}")
```

---

## Data Provider Framework

**File:** `/src/stockreports/data_services/_internal/providing/_base_provider.py` (196 lines)

### Interface

```python
from src.stockreports.data_services._internal.providing._base_provider import DataProvider

class DataProvider:
    """Base interface for all data providers."""
    
    def fetch_ohlcv(
        self,
        symbol: str,
        unix_timestamps: list[int],
        resolution: int
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data for specific timestamps.
        
        Args:
            symbol: Stock symbol (e.g., 'BTCUSDT')
            unix_timestamps: List of Unix timestamps (seconds since epoch)
            resolution: Candle resolution in minutes
            
        Returns:
            DataFrame with columns [Open, High, Low, Close, Volume]
            Index: DatetimeIndex (timezone-aware, UTC)
            
        Raises:
            ValueError: If data invalid
            RuntimeError: If API error
        """
```

### Using DataServiceOrchestrator (Recommended)

**File:** `/src/stockreports/data_services/orchestrator.py`

```python
from src.stockreports.data_services.orchestrator import DataServiceOrchestrator
import pandas as pd

# Create orchestrator (public API)
orchestrator = DataServiceOrchestrator()

# Fetch data (automatic provider selection)
df = orchestrator.fetch_and_process(
    symbol='VCB',
    start_time=pd.Timestamp('2026-04-01', tz='UTC'),
    end_time=pd.Timestamp('2026-04-08', tz='UTC'),
    resolution=1
)

# Use DataFrame
print(df.head())
# Output:
#                      Open   High    Low  Close    Volume
# 2026-04-01 09:00:00  1250  1255  1248  1252   50000
# 2026-04-01 09:01:00  1252  1258  1250  1256   65000
```

### Available Providers

**3 Actual Providers:**

1. **Vietstock Provider**
   - Symbol range: Vietnamese stocks (VN30, VCB, etc.)
   - API: https://api.vietstock.vn/tvnew/history
   - Resolution: Supports 1m, 5m, 15m, 1h, 1d

2. **Binance API Provider**
   - Symbol range: Cryptocurrency (BTCUSDT, ETHUSDT, etc.)
   - API: https://api.binance.com/api/v3/klines
   - Resolution: Supports 1m, 5m, 15m, 30m, 1h, 4h, 1d

3. **Binance CCXT Provider**
   - Symbol range: Multiple exchanges via CCXT
   - API: CCXT unified API
   - Resolution: Exchange-specific

### Data Format Guarantee

All providers return normalized DataFrame:

```python
# All providers return this structure:
df = orchestrator.fetch_and_process(symbol='VCB', ...)

# Properties:
print(f"Index type: {type(df.index)}")  # DatetimeIndex
print(f"Index tz: {df.index.tz}")       # UTC
print(f"Columns: {list(df.columns)}")   # ['Open', 'High', 'Low', 'Close', 'Volume']
print(f"Data types: {df.dtypes}")       # All float64 except Volume (int64)

# Example row:
# alert_time: 2026-04-08 14:23:00+00:00
# Open:       1250.50
# High:       1255.75
# Low:        1248.00
# Close:      1252.25
# Volume:     125000
```

---

## Constants and Enums

**File:** `/src/stockreports/alert/common/constants.py`

### Approach Enum

```python
class Approach(str, Enum):
    """All alert approach types."""
    STRONG_CANDLE = 'STRONG_CANDLE'
    CONSISTENT_MOMENTUM = 'CONSISTENT_MOMENTUM'
    VRA = 'VRA'
    ICHIMOKU = 'ICHIMOKU'
    VOLUME_SPIKE = 'VOLUME_SPIKE'
    CONSISTENT_VOLUME_ANCHOR = 'CONSISTENT_VOLUME_ANCHOR'
```

### Signal Enum

```python
class Signal(str, Enum):
    """Alert direction."""
    BUY = 'BUY'
    SELL = 'SELL'
    NEUTRAL = 'NEUTRAL'
```

### Status Enum

```python
class Status(str, Enum):
    """Execution status."""
    SUCCESS = 'SUCCESS'
    FAILED = 'FAILED'
    PENDING = 'PENDING'
```

### Trend Enum

```python
class Trend(str, Enum):
    """Market trend."""
    UPTREND = 'UPTREND'
    DOWNTREND = 'DOWNTREND'
    SIDEWAYS = 'SIDEWAYS'
```

### Mode Values

⚠️ **CRITICAL:** DEVELOPMENT mode being removed in Phase 3!

**Valid modes (strings):**

```python
# Currently supported:
DEPLOYMENT = 'deployment'

# Being removed in Phase 3:
# DEVELOPMENT = 'development'  # Implementation Guides only, removed in Phase 3

# Usage (Implementation Guides):
executor = StrongCandleExecutor(
    mode='deployment',  # String, not enum
    symbol='VN30F1M',
    alert_sources=['VN30']
)

# REPLAY is NOT a mode
# REPLAY is a TimeSimulator feature used with DEPLOYMENT mode
# See: CRITICAL_ARCHITECTURAL_DECISION.md
```

---

## Timestamp Handling

### Expected Format

**pd.Timestamp (timezone-aware, UTC):**

```python
# Correct - UTC timezone aware
alert.alert_time = pd.Timestamp('2026-04-08T14:23:45', tz='UTC')

# Correct - ISO 8601 string
'2026-04-08T14:23:45+00:00'

# Incorrect - naive timestamp (no timezone)
pd.Timestamp('2026-04-08T14:23:45')  # ❌ Missing tz='UTC'

# Incorrect - wrong format
'2026-04-08 14:23:45'  # ❌ No timezone info
```

### Conversion Examples

```python
import pandas as pd
from dateutil import parser as date_parser

# From string
iso_string = '2026-04-08T14:23:45+00:00'
ts = date_parser.isoparse(iso_string)  # Parses ISO 8601

# From Unix timestamp
unix_ts = 1712595825  # Seconds since epoch
ts = pd.Timestamp(unix_ts, unit='s', tz='UTC')

# From datetime
from datetime import datetime
dt = datetime(2026, 4, 8, 14, 23, 45)
ts = pd.Timestamp(dt, tz='UTC')

# To ISO 8601 string
iso_str = ts.isoformat()  # '2026-04-08T14:23:45+00:00'

# To Unix timestamp
unix_ts = ts.timestamp()  # 1712595825.0
```

---

## Error Handling

### Standard Exception Types

| Type | Cause | Recovery |
|------|-------|----------|
| `ValueError` | Invalid data (NaN, wrong format) | Validate input |
| `TypeError` | Wrong parameter type | Check types |
| `KeyError` | Missing config/field | Verify settings |
| `RuntimeError` | API failure | Check connectivity |
| `FileNotFoundError` | Missing alert file | Generate file |
| `ImportError` | Module not found | Install package |

### Example Error Handling

```python
from src.stockreports.alert.model.models import AlertData

try:
    alert = AlertData.from_dict(alert_dict)
    if alert is None:
        print("Failed to parse alert")
except Exception as e:
    print(f"Error: {e}")

# If parsing fails, from_dict returns None (doesn't raise)
```

---

## Configuration Access

**File:** `/src/stockreports/config/loader.py`

```python
from src.stockreports.config.loader import (
    load_config,
    get_settings,
    get_signal_settings,
    get_notification_settings,
    get_validation_settings,
    get_price_alert_settings,
    get_data_provider_settings
)

# Load all config modules at startup
load_config()

# Get specific settings module
settings = get_settings()
print(settings.SYMBOLS)  # ['VN30F1M', 'VN30']
print(settings.MONITORING_INTERVAL_SECONDS)  # 57

signal_settings = get_signal_settings()
# Use signal_settings config

notification_settings = get_notification_settings()
print(notification_settings.EMAIL_ENABLED)  # True/False
```

---

## Summary

| Component | Type | Location | Purpose |
|-----------|------|----------|---------|
| **AlertData** | Dataclass | models.py | Single alert record |
| **AlertResult** | Dataclass | models.py | Executor return value |
| **Executor** | Base class | executor.py | Alert generation base |
| **6 Executors** | Implementation | approach/*/executor.py | Real alert strategies |
| **DataProvider** | Interface | _base_provider.py | Data fetching interface |
| **Orchestrator** | Facade | orchestrator.py | Public data API |
| **Constants** | Enums | constants.py | Types and values |
| **Config Loader** | Module | loader.py | Settings access |

---

**Status:** Documented from Actual Code  
**Date:** April 8, 2026  
**Executors:** 6 real (not hypothetical)  
**Providers:** 3 real (not hypothetical)  
**Timestamps:** Always UTC, timezone-aware  
**Ready:** Yes
