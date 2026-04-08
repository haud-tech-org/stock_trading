# Architecture Guide for Developers

**Date:** April 8, 2026  
**Target Audience:** Developer team, software engineers, maintainers, architects  
**Purpose:** Complete technical reference for system design, extension, and maintenance  
**Reading Time:** 40-50 minutes

---

## Executive Summary

This document provides the complete technical architecture of a real-time trading alert system with backtesting capabilities. The system demonstrates:

- **Multi-mode architecture** (LIVE production + REPLAY simulation)
- **Pluggable component design** (6 executors, 3 providers, 3 channels)
- **Resilient orchestration** (supervisor pattern with crash recovery)
- **Flexible configuration** (6 settings modules with runtime customization)
- **Comprehensive testing** (unit, integration, performance testing)

**Key architectural decisions:**
1. **TimeSimulator-based mode control** - Single codebase, two operational modes via configuration
2. **Executor framework** - Standardized interface for extensible alert approaches
3. **Supervisor pattern** - Per-symbol orchestrators with independent failure domains
4. **Channel isolation** - Notification failures don't impact system operation

---

## System Overview

### Architecture Diagram

```
Application Flow:

┌──────────────────────────────────────────────────────────────────┐
│ Entry Point: SymbolAlertManager (Multi-symbol Orchestrator)      │
│ - ThreadPoolExecutor for concurrent symbol processing            │
│ - Manages multiple SymbolAlerter instances                        │
│ - Handles graceful shutdown                                      │
└──────────────────────────────────────────────────────────────────┘
                             ↓
┌──────────────────────────────────────────────────────────────────┐
│ SymbolAlerter (Single-Symbol Supervisor) - Per Symbol            │
│ - Supervisor pattern with automatic restart on failure           │
│ - Coordinates 3 layers for single symbol                         │
│ - Resilience: Restarts up to N times in LIVE mode              │
└──────────────────────────────────────────────────────────────────┘
                             ↓
        ┌────────────────────┼────────────────────┐
        ↓                    ↓                    ↓
┌──────────────────┐ ┌──────────────┐  ┌──────────────────┐
│ Data Layer       │ │ Analysis     │  │ Notification     │
├──────────────────┤ │ Layer        │  │ Layer            │
│ DataService      │ │              │  │                  │
│ Orchestrator     │ │ Executor     │  │ NotificationMgr  │
│                  │ │ Framework    │  │                  │
│ Coordinates:     │ │              │  │ Routes to:       │
│ - Vietstock      │ │ 6 Real:      │  │ - Email          │
│ - Binance API    │ │ • Strong     │  │ - SMS            │
│ - Binance CCXT   │ │   Candle     │  │ - Ntfy           │
│                  │ │ • Momentum   │  │                  │
│ Provides:        │ │ • VRA        │  │ Handles:         │
│ - OHLCV data     │ │ • Ichimoku   │  │ - Route selection│
│ - Caching        │ │ • Volume     │  │ - Retries        │
│ - Normalization  │ │   Spike      │  │ - Failures       │
│                  │ │ • Vol Anchor │  │                  │
└──────────────────┘ └──────────────┘  └──────────────────┘
        ↓                    ↓                    ↓
      Data              Signals                 Sent
    OHLCV[t]        alert_generated         notifications
                    + metadata                 on channels
```

---

## Component Inventory

### 1. Orchestration Layer

#### SymbolAlertManager
**File:** `src/stockreports/alert/symbol_alert_manager.py`  
**Responsibility:** Multi-symbol coordination  
**Pattern:** ThreadPoolExecutor wrapper  
**Key Methods:**
- `monitor_symbols(symbols, settings)` - Main entry point
- `_create_alerter(symbol)` - Create per-symbol supervisor
- `_handle_symbol_errors(symbol, exception)` - Error handling
- Graceful shutdown on SIGTERM

**Threading Model:**
```python
with ThreadPoolExecutor(max_workers=cpu_count()) as executor:
    futures = {
        executor.submit(self._monitor_symbol, sym): sym 
        for sym in symbols
    }
```

#### SymbolAlerter
**File:** `src/stockreports/alert/symbol_alerter.py`  
**Responsibility:** Single-symbol orchestration with resilience  
**Pattern:** Supervisor with crash recovery  
**Key Methods:**
- `alert_single_symbol(symbol, settings)` - Main supervisor loop
- `_get_orchestrator()` - Lazy-load orchestrator
- `_run_alert_cycle()` - Single monitoring iteration
- `_handle_crash_and_restart()` - Recovery logic (LIVE mode)

**Supervisor Loop (Simplified):**
```python
def alert_single_symbol(symbol, settings):
    restart_count = 0
    while restart_count < MAX_RESTARTS:
        try:
            while not stop_event.is_set():
                orchestrator.run_alert_cycle()
        except Exception as e:
            if settings.is_live_mode():
                restart_count += 1
                restart()  # Resume from beginning
            else:
                raise  # REPLAY mode: fail-fast
```

---

### 2. Data Layer

#### DataServiceOrchestrator
**File:** `src/data_processing/data_service.py`  
**Responsibility:** Unified data access to 3+ providers  
**Pattern:** Strategy pattern for provider selection  
**Key Methods:**
- `fetch_ohlcv(symbol, timeframe)` - Fetch OHLCV data
- `get_all_ohlcv(symbols, timeframes)` - Bulk fetch
- `validate_data_quality()` - Data sanity checks

**Architecture:**
```
DataServiceOrchestrator
├── VietstockProvider
│   ├── fetch_historical_data()
│   ├── get_latest_prices()
│   └── price_cache
├── BinanceAPIProvider
│   ├── fetch_klines()
│   ├── connection_pool
│   └── rate_limiting
└── BinanceCCXTProvider
    ├── fetch_ohlcv()
    ├── market_data()
    └── symbol_mapping
```

**Provider Interface (Must Implement):**
```python
class BaseDataProvider(ABC):
    @abstractmethod
    def fetch_ohlcv(symbol: str, timeframe: str, 
                    start: datetime, end: datetime) -> DataFrame:
        pass
    
    @abstractmethod
    def get_latest_prices(symbols: List[str]) -> Dict:
        pass
    
    @property
    def is_available(self) -> bool:
        pass
```

**Data Caching Strategy:**
- Time-based cache (5 min default)
- Size-limited (100 entries max)
- Provider-specific cache invalidation

---

### 3. Analysis Layer: Executor Framework

#### Executor Architecture

**Base Class:** `BaseExecutor`  
**File:** `src/analyzer/executor_base.py`  
**Pattern:** Strategy pattern for different signal detection  

**Executor Interface:**
```python
class BaseExecutor(ABC):
    @abstractmethod
    def run(self, symbol: str, data: DataFrame, 
            settings: AlertSettings) -> AlertData:
        """
        Returns:
            AlertData object with:
            - alert_generated (bool)
            - approach_name (str)
            - confidence (0-100)
            - technical_details (dict)
        """
        pass
    
    @property
    @abstractmethod
    def approach_name(self) -> str:
        pass
```

#### 6 Real Executors

| Executor | File | Purpose | Parameters |
|----------|------|---------|------------|
| **StrongCandleExecutor** | `src/analyzer/executors/strong_candle.py` | Candle strength patterns | Min movement %, close ratio |
| **MomentumExecutor** | `src/analyzer/executors/momentum.py` | Momentum changes | Lookback period, threshold |
| **VolumeReactionAreaExecutor** | `src/analyzer/executors/vra.py` | Support/resistance reactions | Area size, touch count |
| **IchimokuExecutor** | `src/analyzer/executors/ichimoku.py` | Cloud breakouts | Cloud period settings |
| **VolumeSpikeExecutor** | `src/analyzer/executors/volume_spike.py` | Unusual volume | Volume multiplier |
| **ConsistentVolumeAnchorExecutor** | `src/analyzer/executors/volume_anchor.py` | Volume anchoring | Consistency ratio |

#### Executor Execution Flow

```python
class ExecutorFramework:
    def __init__(self, executors: List[BaseExecutor]):
        self.executors = executors
    
    def run_all(self, symbol: str, data: DataFrame, 
                settings: AlertSettings) -> List[AlertData]:
        """Run all executors, collect results"""
        results = []
        for executor in self.executors:
            try:
                result = executor.run(symbol, data, settings)
                results.append(result)
            except Exception as e:
                log.error(f"Executor {executor.approach_name} failed: {e}")
                continue
        return results
```

**To Add New Executor:**
1. Create class inheriting `BaseExecutor`
2. Implement `run()` method
3. Implement `approach_name` property
4. Register in executor registry
5. Add configuration in `signal_settings.py`

**Example New Executor:**
```python
class MyCustomExecutor(BaseExecutor):
    @property
    def approach_name(self) -> str:
        return "MyCustomApproach"
    
    def run(self, symbol: str, data: DataFrame, 
            settings: AlertSettings) -> AlertData:
        # Your signal detection logic
        
        return AlertData(
            symbol=symbol,
            approach=self.approach_name,
            alert_generated=signal_detected,
            confidence=confidence_score,
            technical_details={"key": value}
        )
```

---

### 4. Notification Layer

#### NotificationManager
**File:** `src/notification/notification_manager.py`  
**Responsibility:** Route alerts to configured channels  
**Pattern:** Adapter pattern for channel abstraction  

**Manager Interface:**
```python
class NotificationManager:
    def __init__(self, channels: List[BaseChannel]):
        self.channels = channels
    
    def send_alert(self, alert: AlertData) -> NotificationResult:
        """Send to all configured channels"""
        results = {}
        for channel in self.channels:
            try:
                result = channel.send(alert)
                results[channel.name] = result
            except Exception as e:
                results[channel.name] = {"success": False, "error": str(e)}
                log.error(f"Channel {channel.name} failed: {e}")
        return results
```

#### 3 Real Notification Channels

**1. EmailChannel**
- File: `src/notification/channels/email_channel.py`
- Protocol: SMTP
- Configuration: Host, port, credentials, from address
- Features: HTML templates, subject customization, retry logic

**2. SMSChannel**
- File: `src/notification/channels/sms_channel.py`
- Protocol: Twilio/provider API
- Configuration: Account SID, auth token, phone numbers
- Features: Message templates, delivery tracking

**3. NtfyChannel**
- File: `src/notification/channels/ntfy_channel.py`
- Protocol: HTTP POST to ntfy.sh
- Configuration: Topic name, base URL
- Features: Web-viewable alerts, no credentials required

#### Channel Interface (For Custom Channels)

```python
class BaseChannel(ABC):
    @abstractmethod
    def send(self, alert: AlertData) -> Dict[str, Any]:
        """
        Send notification through this channel
        Returns dict with:
        - success: bool
        - message_id: str (if successful)
        - error: str (if failed)
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @abstractmethod
    def is_configured(self) -> bool:
        pass
```

**To Add New Channel:**
1. Create class inheriting `BaseChannel`
2. Implement `send()` method
3. Implement `name` and `is_configured` properties
4. Register in notification_settings.py

---

### 5. Time Control Layer

#### TimeSimulator
**File:** `src/time/time_simulator.py`  
**Responsibility:** Dual-mode time abstraction  
**Key Insight:** Single codebase, two time behaviors via configuration

**Modes:**
```
LIVE Mode:
├─ DEBUG_REPLAY_START_TIME = None
├─ Returns actual system time
├─ Unbounded operation (indefinite)
└─ Used in production

REPLAY Mode:
├─ DEBUG_REPLAY_START_TIME = "2026-01-01 09:15:00"
├─ Simulates historical time from that point
├─ Advances based on data availability
├─ Exits at day-end (16:00)
└─ Used for backtesting
```

**Interface:**
```python
class TimeSimulator:
    def __init__(self, debug_replay_start_time: Optional[datetime]):
        self.debug_mode = debug_replay_start_time is not None
        self.current_time = debug_replay_start_time or now()
    
    def get_now(self) -> datetime:
        """Returns actual time or simulated time"""
        return self.current_time
    
    def advance_to(self, time: datetime) -> None:
        """Advance simulated time to this point"""
        if self.debug_mode:
            self.current_time = time
    
    @property
    def should_continue_trading(self) -> bool:
        """Returns False when trading session ends"""
        if self.debug_mode:
            return self.current_time.hour < 16  # Stop at 4 PM
        return True
```

**Critical Architectural Point:**
TimeSimulator enables:
- **Single codebase** for both LIVE and REPLAY
- **No conditional branching** in main logic
- **Clean separation** of concerns
- **Easy testing** via mock TimeSimulator

---

### 6. Report Generation Layer

#### CentralizedReportGenerator
**File:** `src/tools/centralized_report_generator/centralized_report_generator.py`  
**Responsibility:** Backtesting and performance analysis  
**Pattern:** Command pattern for step composition

**Architecture:**

```
CentralizedReportGenerator
├── Base Steps (Always Executed):
│   ├── Step 1: Load historical data
│   └── Step 2: Run alert simulation (backtest)
└── Optional Steps (Configurable):
    ├── Step 3: Support/Resistance detection
    ├── Step 4: Profit/Loss scenario analysis
    └── Step 5: Parameter optimization
```

**Not Fixed 5-Step Process:**

The process is **2 base + 3 optional**, meaning:
```
Minimum Report:
├─ Load data + simulate alerts
└─ Duration: 30-60 seconds

Full Report:
├─ Load data + simulate alerts
├─ Detect S/R levels
├─ Analyze 20+ profit scenarios
├─ Optimize parameters
└─ Duration: 5-15 minutes
```

**Main Function Signature:**
```python
def generate_report(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    executors: List[BaseExecutor],
    # Backtesting parameters
    profit_target: float = 2.0,  # Fixed points
    stop_loss_thresholds: List[float] = None,  
    # [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0] - creates 9 scenarios
    # Optional parameters
    detect_support_resistance: bool = False,
    optimize_parameters: bool = False,
    optimization_bounds: Dict = None,
) -> BacktestReport:
    pass
```

**Report Contents (9 Scenario Analysis):**
```
Symbol: VN30, Date: 2026-04-01 to 2026-04-08

Approach: Strong Candle Detection
─────────────────────────────────────────
Total Alerts: 24

Profit Target: 2.0 points (fixed)
Stop Loss Scenarios:
├─ 2.5 points: 16 wins, 8 losses → 67% win rate
├─ 3.0 points: 18 wins, 6 losses → 75% win rate
├─ 3.5 points: 19 wins, 5 losses → 79% win rate
├─ 4.0 points: 20 wins, 4 losses → 83% win rate
├─ 5.0 points: 21 wins, 3 losses → 88% win rate
├─ 6.0 points: 22 wins, 2 losses → 92% win rate
├─ 7.0 points: 22 wins, 2 losses → 92% win rate
├─ 8.0 points: 23 wins, 1 loss  → 96% win rate
└─ 9.0 points: 23 wins, 1 loss  → 96% win rate

Optimal: 3.0-3.5 points (best risk/reward balance)
```

---

## Configuration System

### 6 Settings Modules

#### 1. `settings.py` - System Configuration
```python
class SystemSettings:
    # Mode selection
    DEPLOYMENT = "LIVE"  # or "REPLAY"
    DEBUG_REPLAY_START_TIME = None  # or "2026-01-01 09:15:00"
    
    # Threading
    MAX_WORKERS = 4
    
    # Timing
    ALERT_CHECK_INTERVAL = 300  # seconds
    DATA_REFRESH_INTERVAL = 60  # seconds
```

#### 2. `data_provider_settings.py` - Data Sources
```python
class DataProviderSettings:
    ENABLED_PROVIDERS = [
        "vietstock",
        "binance_api",
        "binance_ccxt"
    ]
    
    VIETSTOCK_CONFIG = {...}
    BINANCE_CONFIG = {...}
```

#### 3. `signal_settings.py` - Alert Approaches
```python
class SignalSettings:
    ENABLED_APPROACHES = [
        "strong_candle",
        "momentum",
        "vra",
        "ichimoku",
        "volume_spike",
        "volume_anchor"
    ]
    
    STRONG_CANDLE_PARAMS = {
        "min_movement_percent": 1.5,
        "close_ratio_threshold": 0.8
    }
    # ... other approach configs
```

#### 4. `notification_settings.py` - Channels
```python
class NotificationSettings:
    ENABLED_CHANNELS = ["email", "sms", "ntfy"]
    
    EMAIL_CONFIG = {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "username": env.EMAIL_USER,
        "password": env.EMAIL_PASSWORD,
        "from_address": "alerts@trading.com"
    }
    
    SMS_CONFIG = {
        "account_sid": env.TWILIO_ACCOUNT_SID,
        "auth_token": env.TWILIO_AUTH_TOKEN,
        "from_number": env.SMS_FROM_NUMBER,
        "to_numbers": ["+84901234567"]
    }
    
    NTFY_CONFIG = {
        "base_url": "https://ntfy.sh",
        "topic": "trading_alerts"
    }
```

#### 5. `price_alert_settings.py` - Alert Thresholds
```python
class PriceAlertSettings:
    # Alert validation
    MIN_ALERT_CONFIDENCE = 50  # 0-100
    MAX_ALERTS_PER_HOUR = 100
    
    # Note: Profit/loss targets are configured in validation_settings.py
```

#### 6. `validation_settings.py` - Backtesting Configuration
```python
# Profit/Loss targets for simulation (in points, not percentages)
VALIDATION_PRICE_GAIN_THRESHOLD = 3.0  # Min profit points for success
VALIDATION_PRICE_DROP_THRESHOLD = 3.0  # Min loss points for success
VALIDATION_TIME_WINDOW_MINUTES = 15    # Time to check if targets met

# Per-trade take-profit configuration
VALIDATION_PRICE_THRESHOLD_PROFIT = [2.0]      # Fixed profit target (points)
VALIDATION_MAGNITUDE_PROFIT_FACTOR = 0.7       # Dynamic factor (70% of magnitude)
VALIDATION_MIN_PROFIT_FOR_SUCCESS = 1.5        # Min profit if timeout

# Stop-loss thresholds (tested against each alert)
VALIDATION_PRICE_THRESHOLD_LOSS = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]
# Creates 9 scenarios: 1 profit target × 9 stop-loss levels

# Data source
VALIDATION_DATA_SOURCE = 1  # 1 = local JSON, 0 = live API
VALIDATION_DATE_FILTER = None  # None = all dates, "YYYY-MM-DD" = specific date

# Price adjustment
PRICE_ADJUSTMENT_EXCLUSION_LIST = ["VN30", "VN30F1M", "BTC/USDT"]
```

---

## Data Models

### AlertData
```python
class AlertData:
    symbol: str
    approach: str  # "strong_candle", etc.
    alert_generated: bool
    confidence: int  # 0-100
    timestamp: datetime
    current_price: float
    technical_details: Dict
    
    # Example technical_details:
    # {
    #   "candle_strength": 85,
    #   "volume_ratio": 2.3,
    #   "support_level": 27.5
    # }
```

### BacktestReport
```python
class BacktestReport:
    symbol: str
    date_range: Tuple[datetime, datetime]
    alert_count: int
    win_rate: float  # 0-1
    profit_factor: float
    total_return_percent: float
    alerts: List[AlertData]
    metrics: Dict
```

### NotificationResult
```python
class NotificationResult:
    channel_results: Dict[str, Dict]  # channel_name -> result
    overall_success: bool
    timestamp: datetime
    
    # Example:
    # {
    #   "email": {"success": True, "message_id": "..."},
    #   "sms": {"success": False, "error": "Invalid number"},
    #   "ntfy": {"success": True, "message_id": "..."}
    # }
```

---

## How to Extend the System

### Adding a New Alert Approach (Executor)

**Step 1: Create Executor Class**
```python
# File: src/analyzer/executors/my_approach.py

from src.analyzer.executor_base import BaseExecutor, AlertData

class MyApproachExecutor(BaseExecutor):
    @property
    def approach_name(self) -> str:
        return "my_approach"
    
    def run(self, symbol: str, data: DataFrame, 
            settings: AlertSettings) -> AlertData:
        # Your signal detection logic
        alert_generated = self._detect_signal(data)
        confidence = self._calculate_confidence(data)
        
        return AlertData(
            symbol=symbol,
            approach=self.approach_name,
            alert_generated=alert_generated,
            confidence=confidence,
            technical_details={
                "key_metric": value,
                "other_metric": other_value
            }
        )
    
    def _detect_signal(self, data: DataFrame) -> bool:
        # Implementation
        pass
    
    def _calculate_confidence(self, data: DataFrame) -> int:
        # Implementation
        return 0  # 0-100
```

**Step 2: Register in ExecutorFramework**
```python
# In executor registry or factory

from src.analyzer.executors.my_approach import MyApproachExecutor

def get_executor(approach_name: str) -> BaseExecutor:
    executors = {
        "strong_candle": StrongCandleExecutor(),
        "momentum": MomentumExecutor(),
        # ... other executors
        "my_approach": MyApproachExecutor(),  # Add here
    }
    return executors[approach_name]
```

**Step 3: Add Configuration**
```python
# In signal_settings.py

class SignalSettings:
    ENABLED_APPROACHES = [
        "strong_candle",
        "momentum",
        # ... other approaches
        "my_approach",  # Add here
    ]
    
    MY_APPROACH_PARAMS = {
        "parameter1": value1,
        "parameter2": value2,
        # Your executor's configuration
    }
```

**Step 4: Write Tests**
```python
# File: tests/analyzer/executors/test_my_approach.py

import pytest
from src.analyzer.executors.my_approach import MyApproachExecutor

class TestMyApproachExecutor:
    def test_signal_generation(self):
        # Test setup
        executor = MyApproachExecutor()
        data = create_test_data()
        settings = create_test_settings()
        
        # Execute
        result = executor.run("TEST", data, settings)
        
        # Verify
        assert isinstance(result, AlertData)
        assert 0 <= result.confidence <= 100
```

### Adding a New Notification Channel

**Step 1: Create Channel Class**
```python
# File: src/notification/channels/my_channel.py

from src.notification.base_channel import BaseChannel
from src.models import AlertData

class MyChannel(BaseChannel):
    @property
    def name(self) -> str:
        return "my_channel"
    
    def is_configured(self) -> bool:
        return bool(os.getenv("MY_CHANNEL_API_KEY"))
    
    def send(self, alert: AlertData) -> Dict[str, Any]:
        try:
            message = self._format_alert(alert)
            response = self._send_via_api(message)
            
            return {
                "success": True,
                "message_id": response.get("id"),
                "timestamp": datetime.now()
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_alert(self, alert: AlertData) -> str:
        return f"{alert.symbol} Alert: {alert.approach}"
    
    def _send_via_api(self, message: str) -> Dict:
        # API call implementation
        pass
```

**Step 2: Register in NotificationManager**
```python
# In notification_manager.py

from src.notification.channels.my_channel import MyChannel

class NotificationManager:
    def __init__(self, settings: NotificationSettings):
        self.channels = []
        
        if "email" in settings.ENABLED_CHANNELS:
            self.channels.append(EmailChannel(settings))
        if "sms" in settings.ENABLED_CHANNELS:
            self.channels.append(SMSChannel(settings))
        if "ntfy" in settings.ENABLED_CHANNELS:
            self.channels.append(NtfyChannel(settings))
        if "my_channel" in settings.ENABLED_CHANNELS:  # Add here
            self.channels.append(MyChannel(settings))
```

**Step 3: Add Configuration**
```python
# In notification_settings.py

MY_CHANNEL_CONFIG = {
    "api_key": env.MY_CHANNEL_API_KEY,
    "api_url": "https://api.my-service.com",
    "webhook_url": "https://webhook.my-service.com/alerts",
    # Your channel's configuration
}
```

### Adding a New Data Provider

**Step 1: Create Provider Class**
```python
# File: src/data_processing/providers/my_provider.py

from src.data_processing.base_provider import BaseDataProvider
from pandas import DataFrame
from datetime import datetime
from typing import Dict, List

class MyProvider(BaseDataProvider):
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config.get("api_key")
        self.base_url = config.get("api_url")
    
    def fetch_ohlcv(self, symbol: str, timeframe: str,
                    start: datetime, end: datetime) -> DataFrame:
        """Fetch OHLCV data from my data source"""
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "start_time": start.isoformat(),
            "end_time": end.isoformat()
        }
        
        response = self._api_call("/ohlcv", params)
        data = self._parse_response(response)
        return self._normalize_to_dataframe(data)
    
    def get_latest_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get latest prices for symbols"""
        response = self._api_call("/latest_prices", {"symbols": symbols})
        return response
    
    @property
    def is_available(self) -> bool:
        """Check if provider is reachable"""
        try:
            self._api_call("/health")
            return True
        except:
            return False
    
    def _api_call(self, endpoint: str, params: Dict) -> Dict:
        # API implementation
        pass
    
    def _parse_response(self, response: Dict) -> List[Dict]:
        # Parse response into list of OHLCV dicts
        pass
    
    def _normalize_to_dataframe(self, data: List[Dict]) -> DataFrame:
        # Convert to standard OHLCV DataFrame format
        pass
```

**Step 2: Register in DataServiceOrchestrator**
```python
# In data_service.py

from src.data_processing.providers.my_provider import MyProvider

class DataServiceOrchestrator:
    def __init__(self, settings: DataProviderSettings):
        self.providers = {}
        
        if "vietstock" in settings.ENABLED_PROVIDERS:
            self.providers["vietstock"] = VietstockProvider(...)
        if "binance_api" in settings.ENABLED_PROVIDERS:
            self.providers["binance_api"] = BinanceAPIProvider(...)
        if "my_provider" in settings.ENABLED_PROVIDERS:  # Add here
            self.providers["my_provider"] = MyProvider(settings.MY_PROVIDER_CONFIG)
```

---

## Testing Strategy

### Unit Testing

**Test Structure:**
```
tests/
├── analyzer/
│   ├── test_executor_base.py
│   ├── executors/
│   │   ├── test_strong_candle.py
│   │   ├── test_momentum.py
│   │   └── test_vra.py
├── data_processing/
│   ├── test_data_service.py
│   ├── providers/
│   │   ├── test_vietstock.py
│   │   ├── test_binance_api.py
├── notification/
│   ├── test_notification_manager.py
│   ├── channels/
│   │   ├── test_email.py
│   │   ├── test_sms.py
└── time/
    └── test_time_simulator.py
```

**Example Unit Test:**
```python
import pytest
from src.analyzer.executors.strong_candle import StrongCandleExecutor
from src.models import AlertData

class TestStrongCandleExecutor:
    @pytest.fixture
    def executor(self):
        return StrongCandleExecutor()
    
    @pytest.fixture
    def sample_data(self):
        # Create sample OHLCV DataFrame
        import pandas as pd
        return pd.DataFrame({
            "open": [100, 101, 102],
            "high": [102, 103, 104],
            "low": [99, 100, 101],
            "close": [102, 102.5, 104],
            "volume": [1000, 1200, 1500]
        })
    
    def test_signal_generated_on_strong_candle(self, executor, sample_data):
        result = executor.run("TEST", sample_data, {})
        
        assert isinstance(result, AlertData)
        assert result.alert_generated == True
        assert 0 <= result.confidence <= 100
    
    def test_confidence_score_calculation(self, executor, sample_data):
        result = executor.run("TEST", sample_data, {})
        
        # Confidence should increase with stronger candle
        assert result.confidence > 50
```

### Integration Testing

**Scenario 1: Full Alert Generation Pipeline**
```python
def test_alert_generation_to_notification():
    # Setup
    symbol = "VN30"
    data = fetch_test_data(symbol, "2026-01-01", "2026-01-31")
    executors = [StrongCandleExecutor(), MomentumExecutor()]
    
    # Execute
    alerter = SymbolAlerter(symbol, data, executors)
    alerts = alerter.run()
    
    # Verify
    assert len(alerts) > 0
    for alert in alerts:
        assert alert.symbol == symbol
        assert alert.confidence > 0
```

**Scenario 2: REPLAY Mode Time Simulation**
```python
def test_replay_mode_time_simulation():
    # Setup
    settings = {
        "DEBUG_REPLAY_START_TIME": "2026-01-01 09:15:00"
    }
    
    # Execute
    time_sim = TimeSimulator(settings["DEBUG_REPLAY_START_TIME"])
    
    # Verify
    assert time_sim.get_now() == "2026-01-01 09:15:00"
    time_sim.advance_to("2026-01-01 16:00:00")
    assert time_sim.should_continue_trading == False
```

### Performance Testing

**Load Test:**
```python
def test_concurrent_symbol_processing():
    import time
    
    symbols = [f"SYMBOL{i}" for i in range(100)]
    start = time.time()
    
    manager = SymbolAlertManager()
    results = manager.monitor_symbols(symbols, settings)
    
    elapsed = time.time() - start
    
    # Verify performance
    assert elapsed < 120  # Should complete in 2 minutes
    assert len(results) == 100
```

---

## File Organization

```
project_root/
├── src/
│   ├── __init__.py
│   ├── stockreports/
│   │   └── alert/
│   │       ├── symbol_alert_manager.py       (Multi-symbol entry point)
│   │       └── symbol_alerter.py             (Single-symbol supervisor)
│   ├── data_processing/
│   │   ├── data_service.py                   (Orchestrator)
│   │   └── providers/
│   │       ├── base_provider.py              (Interface)
│   │       ├── vietstock.py                  (Provider 1)
│   │       ├── binance_api.py                (Provider 2)
│   │       └── binance_ccxt.py               (Provider 3)
│   ├── analyzer/
│   │   ├── executor_base.py                  (Interface)
│   │   └── executors/
│   │       ├── strong_candle.py              (Executor 1)
│   │       ├── momentum.py                   (Executor 2)
│   │       ├── vra.py                        (Executor 3)
│   │       ├── ichimoku.py                   (Executor 4)
│   │       ├── volume_spike.py               (Executor 5)
│   │       └── volume_anchor.py              (Executor 6)
│   ├── notification/
│   │   ├── notification_manager.py           (Router)
│   │   ├── base_channel.py                   (Interface)
│   │   └── channels/
│   │       ├── email_channel.py              (Channel 1)
│   │       ├── sms_channel.py                (Channel 2)
│   │       └── ntfy_channel.py               (Channel 3)
│   ├── time/
│   │   └── time_simulator.py                 (Time abstraction)
│   ├── tools/
│   │   └── centralized_report_generator/
│   │       └── centralized_report_generator.py (Backtesting)
│   ├── models/
│   │   └── alert_data.py                     (Data models)
│   └── config/
│       ├── settings.py                       (System config)
│       ├── data_provider_settings.py         (Data config)
│       ├── signal_settings.py                (Signal config)
│       ├── notification_settings.py          (Notification config)
│       ├── price_alert_settings.py           (Alert config)
│       └── validation_settings.py            (Validation config)
│
├── tests/
│   ├── __init__.py
│   ├── analyzer/
│   │   ├── test_executor_base.py
│   │   └── executors/
│   │       ├── test_strong_candle.py
│   │       └── ... (other executor tests)
│   ├── data_processing/
│   │   ├── test_data_service.py
│   │   └── providers/
│   │       └── ... (provider tests)
│   ├── notification/
│   │   ├── test_notification_manager.py
│   │   └── channels/
│   │       └── ... (channel tests)
│   └── time/
│       └── test_time_simulator.py
│
├── reports/                                   (LIVE mode outputs)
├── reports_replay/                            (REPLAY mode outputs)
├── logs/                                      (System logs)
├── requirements.txt
├── README.md
└── .env.example
```

---

## Critical Design Patterns

### 1. Strategy Pattern (Executors & Providers)

**Problem:** Multiple alert approaches and data sources need pluggable behavior  
**Solution:** Define interface, implement multiple strategies, select at runtime

```python
# Interface
class BaseExecutor(ABC):
    def run(...) -> AlertData: pass

# Implementations
class StrongCandleExecutor(BaseExecutor): ...
class MomentumExecutor(BaseExecutor): ...
# ... others

# Selection at runtime
executors = [
    get_executor("strong_candle"),
    get_executor("momentum"),
    # ... selected based on configuration
]
```

### 2. Supervisor Pattern (SymbolAlerter)

**Problem:** Single-symbol monitoring can crash, need automatic recovery  
**Solution:** Supervisor loop with restart capability

```python
def alert_single_symbol(symbol):
    restart_count = 0
    while restart_count < MAX_RESTARTS:
        try:
            while not stop:
                run_one_cycle()
        except Exception:
            restart_count += 1
            # Restart supervisor loop
```

### 3. Adapter Pattern (NotificationManager)

**Problem:** Different notification channels have different APIs  
**Solution:** Adapt all channels to common interface

```python
class NotificationManager:
    def send(self, alert):
        for channel in self.channels:
            result = channel.send(alert)  # Common interface
```

### 4. Command Pattern (Report Generator)

**Problem:** Backtesting has variable steps (base + optional)  
**Solution:** Compose steps as commands

```python
class ReportGenerator:
    def __init__(self, steps: List[Command]):
        self.steps = steps
    
    def generate(self):
        for step in self.steps:
            step.execute()
```

### 5. Facade Pattern (SymbolAlertManager)

**Problem:** Complex coordination of multiple components  
**Solution:** Provide simple interface hiding complexity

```python
# Simple interface
manager = SymbolAlertManager()
manager.monitor_symbols(symbols, settings)

# Hides complexity of:
# - ThreadPoolExecutor setup
# - Per-symbol orchestrators
# - Error handling
# - Graceful shutdown
```

---

## Key Architectural Decisions

### Decision 1: TimeSimulator-Based Mode Control

**Question:** How to support both LIVE production and REPLAY backtesting?

**Options Considered:**
1. Separate code paths for LIVE vs REPLAY (DRY violation)
2. Conditional branching throughout code (maintainability issue)
3. Abstract time behind TimeSimulator interface ✅ CHOSEN

**Implementation:**
- Single codebase
- No conditional branching in main logic
- Configuration determines time behavior
- Clean separation of concerns

**Benefit:**
- One code path tested
- Easier to maintain
- Less regression risk

---

### Decision 2: Executor Framework

**Question:** How to support multiple alert approaches?

**Options Considered:**
1. Hardcode all approaches in main loop (inflexible)
2. Plugin system with dynamic loading (complex)
3. Strategy pattern with registered executors ✅ CHOSEN

**Implementation:**
- BaseExecutor interface
- 6 implementations
- Runtime selection via registry
- Isolated testing per executor

**Benefit:**
- Easy to add new approaches
- Isolated changes
- Pluggable behavior

---

### Decision 3: Supervisor Pattern for Resilience

**Question:** How to handle crashes in single-symbol monitoring?

**Options Considered:**
1. System-wide restart on any error (too disruptive)
2. Per-component error handling (scattered logic)
3. SymbolAlerter supervisor with independent restarts ✅ CHOSEN

**Implementation:**
- Per-symbol orchestrator
- Supervisor loop with crash recovery
- LIVE mode: auto-restart
- REPLAY mode: fail-fast
- Independent failure domains

**Benefit:**
- One symbol crash doesn't affect others
- Automatic recovery in production
- Clean error semantics in testing

---

## Performance Considerations

### Latency Budget

```
Total: ~1 second target

Data Fetch:     300-500ms (network latency)
Analysis:        200-400ms (6 executors in parallel)
Notification:    100-200ms (async)
System Overhead: 50-100ms  (queuing, logging)
```

### Optimization Strategies

1. **Data Caching**
   - Cache OHLCV data (5 min TTL)
   - Reduce repeated fetches

2. **Parallel Execution**
   - Run executors concurrently
   - ThreadPoolExecutor for symbols

3. **Async Notifications**
   - Don't block on notification send
   - Queue notifications

4. **Connection Pooling**
   - Reuse HTTP connections
   - Database connection pools

---

## Security Considerations

### Credential Management

```python
# ✅ CORRECT: Use environment variables
api_key = os.getenv("BINANCE_API_KEY")

# ❌ WRONG: Hardcode credentials
api_key = "xyzabc123..."
```

### Data Validation

```python
# Validate all inputs
def fetch_ohlcv(symbol: str, timeframe: str):
    # Validate symbol exists
    if symbol not in VALID_SYMBOLS:
        raise ValueError(f"Invalid symbol: {symbol}")
    
    # Validate timeframe
    if timeframe not in ["1m", "5m", "1h", "1d"]:
        raise ValueError(f"Invalid timeframe: {timeframe}")
```

### Error Handling

```python
# Don't leak sensitive information
try:
    api_call()
except Exception as e:
    # ❌ WRONG: Logs entire exception with credentials
    log.error(f"API failed: {e}")
    
    # ✅ CORRECT: Log safe error message
    log.error(f"API call failed: {type(e).__name__}")
```

---

## Troubleshooting for Developers

### Issue: Executor Not Running

**Debug Steps:**
1. Check executor is registered in executor_settings.py
2. Check executor returns AlertData object
3. Check executor doesn't raise unhandled exceptions
4. Check executor is enabled in configuration

### Issue: Notification Not Sending

**Debug Steps:**
1. Check channel is configured in notification_settings.py
2. Check credentials are valid (in .env)
3. Check channel.is_configured() returns True
4. Test channel directly: `channel.send(test_alert)`

### Issue: Data Not Fetching

**Debug Steps:**
1. Check provider is enabled in data_provider_settings.py
2. Check API credentials are valid
3. Check network connectivity: `curl https://api-endpoint`
4. Check symbol exists in provider's market

---

## Future Extensions

### Planned Enhancements

1. **Machine Learning Executor**
   - Train models on historical data
   - Predict price movements
   - Implement as new executor

2. **Multi-Timeframe Analysis**
   - Combine signals from multiple timeframes
   - Add higher-level executor

3. **Portfolio Optimization**
   - Optimize weights across multiple symbols
   - Enhanced backtesting

4. **Real-Time Risk Management**
   - Live position tracking
   - Correlation analysis
   - Dynamic stop-loss adjustment

---

## API Reference

### Main Entry Points

**SymbolAlertManager.monitor_symbols()**
```python
def monitor_symbols(
    symbols: List[str],
    settings: Dict[str, Any]
) -> None:
    """Monitor symbols for alerts"""
    # Returns None, runs indefinitely until stop
```

**CentralizedReportGenerator.generate_report()**
```python
def generate_report(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    executors: List[BaseExecutor],
    **kwargs
) -> BacktestReport:
    """Generate backtest report for symbol"""
```

**NotificationManager.send_alert()**
```python
def send_alert(
    alert: AlertData
) -> NotificationResult:
    """Send alert through all configured channels"""
```

---

## Glossary

| Term | Definition |
|------|-----------|
| **Alert** | A signal generated when market conditions match criteria |
| **Executor** | Strategy for detecting specific market patterns |
| **Provider** | Data source (Vietstock, Binance, etc.) |
| **Channel** | Notification destination (Email, SMS, Ntfy) |
| **LIVE Mode** | Real-time production monitoring |
| **REPLAY Mode** | Historical simulation/backtesting |
| **TimeSimulator** | Abstraction enabling both modes with same code |
| **Supervisor** | Error handling pattern with automatic restart |
| **Backtest** | Historical simulation of strategy performance |

