# Quick Reference Guides

**Date:** April 8, 2026  
**Format:** Quick lookup (minimal reading)  
**Total:** 4 quick reference cards

---

## EXECUTOR_QUICK_REFERENCE.md

### Creating a New Executor - 5 Minute Summary

**File Location:** `src/executors/your_executor.py`

**Minimum Code:**

```python
from src.executors.base import Executor, AlertResult, AlertData
import pandas as pd

class YourExecutor(Executor):
    def __init__(self, config, symbol, data_service, logger):
        super().__init__(config, symbol, data_service, logger)
        self._config = config.get("executors", {}).get("your_executor", {})
    
    def execute(self) -> AlertResult:
        ohlcv = self._data_service.get_ohlcv(self.symbol, 20)
        
        if ohlcv is None or len(ohlcv) < 20:
            return AlertResult(self.symbol, self._data_service.get_current_time(), [], {})
        
        # Your logic here
        alerts = []  # Generate alerts
        
        return AlertResult(
            symbol=self.symbol,
            timestamp=self._data_service.get_current_time(),
            confirmed_alerts=alerts,
            candle_data=ohlcv.iloc[-1].to_dict()
        )
    
    def reset(self):
        pass
    
    def get_performance_metrics(self):
        return {"approach": "YourExecutor", "total_alerts": 0}
    
    @property
    def is_enabled(self):
        return True
    
    @property
    def requires_history(self):
        return True
```

**Configuration:**

```yaml
executors:
  your_executor:
    enabled: true
    parameter_1: value
    parameter_2: value
```

**Testing:**

```bash
# Unit test
python -m pytest tests/executors/test_your_executor.py -v

# Integration test
python -m src.main --mode REPLAY --config config/replay_test.yaml
```

**Checklist:**

- [ ] File created at `src/executors/your_executor.py`
- [ ] Extends `Executor` base class
- [ ] `execute()` returns `AlertResult`
- [ ] `reset()` and `get_performance_metrics()` implemented
- [ ] Properties `is_enabled` and `requires_history` implemented
- [ ] Configuration added to `config.yaml`
- [ ] Unit tests written and passing
- [ ] REPLAY mode test passing

**Common Patterns:**

```python
# Get data
ohlcv = self._data_service.get_ohlcv(self.symbol, 20)

# Check if valid
if ohlcv is None or len(ohlcv) < 20:
    return AlertResult(confirmed_alerts=[])

# Get current time (LIVE/REPLAY safe)
now = self._data_service.get_current_time()

# Log information
self._logger.debug(f"Debug info")
self._logger.warning(f"Warning")
self._logger.error(f"Error")

# Create alert
alert = AlertData(
    alert_type="BUY",
    description="Description",
    price=float(ohlcv.iloc[-1]["close"]),
    approach=self.name,
    strength=0.75
)

# Return result
return AlertResult(
    symbol=self.symbol,
    timestamp=now,
    confirmed_alerts=[alert],
    candle_data=ohlcv.iloc[-1].to_dict()
)
```

---

## DATA_PROVIDER_QUICK_REFERENCE.md

### Adding a Data Provider - 5 Minute Summary

**File Location:** `src/data_providers/your_provider.py`

**Minimum Code:**

```python
from src.data_providers.base import DataProvider
import pandas as pd
import requests

class YourProvider(DataProvider):
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self._config = config.get("data_providers", {}).get("providers", {}).get(self.name, {})
        self._endpoint = self._config.get("endpoint", "https://api.example.com")
    
    def fetch_ohlcv(self, symbol: str, lookback_periods: int):
        try:
            # Fetch data
            response = requests.get(f"{self._endpoint}/ohlcv", params={
                "symbol": symbol,
                "periods": lookback_periods
            }, timeout=10)
            
            if response.status_code != 200:
                return None
            
            # Normalize to OHLCV format
            data = response.json()
            df = pd.DataFrame(data)
            df.set_index("time", inplace=True)
            
            # Validate
            if not self._validate(df):
                return None
            
            return df
        
        except Exception as e:
            self._logger.error(f"Error: {str(e)}")
            return None
    
    def _validate(self, df):
        """Validate OHLCV data."""
        return (
            all(col in df.columns for col in ['open', 'high', 'low', 'close', 'volume'])
            and not df.isnull().any().any()
            and (df['high'] >= df['low']).all()
        )
    
    @property
    def name(self):
        return "YourProvider"
    
    @property
    def priority(self):
        return 2  # 1=primary, 2=secondary, 3=tertiary
```

**Configuration:**

```yaml
data_providers:
  primary: "YourProvider"
  providers:
    YourProvider:
      enabled: true
      endpoint: "https://api.example.com"
      timeout: 10
      priority: 1
```

**Testing:**

```bash
# Test directly
python -c "
from src.data_providers.your_provider import YourProvider
provider = YourProvider(config, logger)
ohlcv = provider.fetch_ohlcv('BNBUSDT', 20)
print(f'Data shape: {ohlcv.shape if ohlcv is not None else None}')
"

# Unit tests
python -m pytest tests/data_providers/test_your_provider.py -v
```

**Checklist:**

- [ ] File created at `src/data_providers/your_provider.py`
- [ ] Extends `DataProvider` base class
- [ ] `fetch_ohlcv()` returns DataFrame or None
- [ ] Data normalized to [open, high, low, close, volume]
- [ ] `name` and `priority` properties implemented
- [ ] Validation logic implemented
- [ ] Configuration added to `config.yaml`
- [ ] Unit tests written and passing

**Key Points:**

```python
# Return format: pandas DataFrame
DataFrame columns: [open, high, low, close, volume]
Index: datetime (time)

# Return None on error (triggers fallback)
if error:
    self._logger.error("...")
    return None

# Validate all data
if (df['high'] < df['low']).any():
    return None  # Invalid

# Use configuration values
timeout = self._config.get("timeout", 10)
endpoint = self._config.get("endpoint", "...")
```

---

## NOTIFICATION_QUICK_REFERENCE.md

### Adding Notification Channel - 5 Minute Summary

**File Location:** `src/notification_channels/your_channel.py`

**Minimum Code:**

```python
from src.notification_channels.base import NotificationChannel, AlertData
import requests

class YourChannel(NotificationChannel):
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self._config = config.get("notifications", {}).get("channels", {}).get(self.name, {})
        self._api_key = self._config.get("api_key")
        self._enabled = self._config.get("enabled", False)
    
    def send(self, alert: AlertData, context: dict) -> bool:
        if not self._enabled:
            return False
        
        try:
            # Format message
            message = {
                "type": alert.alert_type,
                "description": alert.description,
                "price": alert.price,
                "symbol": context.get("symbol")
            }
            
            # Send via API
            response = requests.post(
                "https://api.example.com/send",
                json=message,
                headers={"Authorization": f"Bearer {self._api_key}"},
                timeout=10
            )
            
            return response.status_code in [200, 201, 204]
        
        except Exception as e:
            self._logger.error(f"Send error: {str(e)}")
            return False
    
    @property
    def name(self):
        return "YourChannel"
    
    def is_enabled(self):
        return self._enabled
```

**Configuration:**

```yaml
notifications:
  enabled: true
  channels:
    your_channel:
      enabled: true
      api_key: "${YOUR_API_KEY}"
      endpoint: "https://api.example.com"
      timeout: 10
```

**Testing:**

```bash
# Test directly
python -c "
from src.notification_channels.your_channel import YourChannel
from src.notification_channels.base import AlertData

channel = YourChannel(config, logger)
alert = AlertData('BUY', 'Test', 100.0, 'Test', 0.8)
success = channel.send(alert, {'symbol': 'BNBUSDT'})
print(f'Sent: {success}')
"
```

**Checklist:**

- [ ] File created at `src/notification_channels/your_channel.py`
- [ ] Extends `NotificationChannel` base class
- [ ] `send()` returns bool
- [ ] Returns False when disabled (never crashes)
- [ ] Returns False on error (graceful handling)
- [ ] `name` property and `is_enabled()` implemented
- [ ] Configuration added to `config.yaml`
- [ ] Unit tests written and passing

**Key Points:**

```python
# Always return bool (never raise exceptions)
return True   # Success
return False  # Failure

# Check enabled status first
if not self._enabled:
    return False

# Handle errors gracefully
try:
    # Send
except Exception as e:
    self._logger.error(f"Error: {str(e)}")
    return False

# Use configuration
api_key = self._config.get("api_key")
endpoint = self._config.get("endpoint", "...")
```

---

## CONFIGURATION_QUICK_REFERENCE.md

### Configuration Options - Complete Reference

**File:** `config.yaml`

**Core Settings:**

```yaml
# Application mode
mode: LIVE              # LIVE or REPLAY

# LIVE settings (if mode: LIVE)
live:
  update_frequency_seconds: 60
  auto_recovery:
    enabled: true
    max_retries: 5
    backoff_seconds: 30

# REPLAY settings (if mode: REPLAY)
replay:
  start_date: "2026-03-01"
  end_date: "2026-04-01"
  speed: 1.0
```

**Symbols:**

```yaml
symbols:
  - symbol: "BNBUSDT"         # Trading pair
    enabled: true             # Monitor this symbol
    executors:                # Executors to use
      - momentum_executor
      - ma_executor
    position_size: 0.01       # 1% of capital per trade
    stop_loss_pct: 2.0        # 2% stop loss
    take_profit_pct: 5.0      # 5% take profit
    max_positions: 3          # Max concurrent positions
```

**Data Providers:**

```yaml
data_providers:
  primary: "BinanceAPI"       # First try
  secondary: "BinanceCCXT"    # Fallback 1
  tertiary: "Vietstock"       # Fallback 2 (optional)
  
  providers:
    BinanceAPI:
      enabled: true
      timeout: 10
      retry_attempts: 5
    
    BinanceCCXT:
      enabled: true
      timeout: 15
      retry_attempts: 3
```

**Executors:**

```yaml
executors:
  momentum_executor:
    enabled: true
    threshold: 0.02           # 2% threshold
    ma_period: 20             # 20-period MA
    lookback_periods: 50
  
  ma_executor:
    enabled: true
    fast_period: 5
    slow_period: 20
    lookback_periods: 50
```

**Notifications:**

```yaml
notifications:
  enabled: true
  throttle_seconds: 60        # Min 60s between alerts
  
  channels:
    telegram:
      enabled: true
      bot_token: "${TELEGRAM_TOKEN}"    # From environment
      chat_id: "${TELEGRAM_CHAT_ID}"
      format: "detailed"      # simple or detailed
    
    slack:
      enabled: false
      webhook_url: "${SLACK_WEBHOOK}"
      format: "json"
```

**Logging:**

```yaml
logging:
  level: INFO                 # DEBUG, INFO, WARNING, ERROR
  file: logs/trading.log
  max_size_mb: 500           # Rotate at 500MB
  backup_count: 10           # Keep 10 backups
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

**Metrics:**

```yaml
metrics:
  enabled: true
  interval_seconds: 300      # Report every 5 min
  output_file: results/metrics.json
```

**Environment Variables:**

```bash
# Required
export TELEGRAM_TOKEN="your_token"
export TELEGRAM_CHAT_ID="your_chat_id"

# Optional
export SLACK_WEBHOOK="your_webhook"
export LOG_LEVEL="DEBUG"
```

**Common Configurations:**

```yaml
# Production LIVE
mode: LIVE
live:
  update_frequency_seconds: 60
  auto_recovery:
    enabled: true
symbols:
  - symbol: "BNBUSDT"
    executors: [momentum_executor, ma_executor]
logging:
  level: INFO

# Testing REPLAY
mode: REPLAY
replay:
  start_date: "2026-03-01"
  end_date: "2026-04-01"
symbols:
  - symbol: "BNBUSDT"
    executors: [momentum_executor]
logging:
  level: DEBUG
```

**Validation:**

```bash
# Validate configuration
python -m src.config.validator config.yaml

# Check YAML syntax
python -m yaml config.yaml

# Check environment variables
echo $TELEGRAM_TOKEN
echo $TELEGRAM_CHAT_ID
```

**Quick Checklist:**

- [ ] Mode set (LIVE or REPLAY)
- [ ] At least one symbol configured
- [ ] At least one executor enabled
- [ ] At least one data provider enabled
- [ ] Notification channels configured
- [ ] API tokens in environment (not config file)
- [ ] Logging level appropriate
- [ ] Configuration validated
- [ ] Permissions correct (read-only)

---

## Summary

**Executor Creation:** ~30 lines minimum  
**Data Provider Creation:** ~40 lines minimum  
**Notification Channel:** ~35 lines minimum  
**Configuration:** ~50 lines minimum

**Testing:**
- Write unit tests
- Run REPLAY mode test
- Verify configuration

**Integration:**
- Add to configuration
- Verify in startup logs
- Monitor for errors

*For complete guides, see implementation guides and API documentation.*
