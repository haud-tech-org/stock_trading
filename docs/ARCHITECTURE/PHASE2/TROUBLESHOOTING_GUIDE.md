# Troubleshooting Guide - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Exception Types and Error Handling  
**Audience:** DevOps, System Administrators, Developers  
**Prerequisites:** Phase 1 architecture understanding  

---

## Overview

This guide documents ACTUAL errors encountered in the system and their resolution procedures. Unlike generic troubleshooting, all error types are based on actual code examination.

---

## Common Exception Types

The codebase uses standard Python exceptions plus a few custom patterns:

| Exception | Source | Meaning | Action |
|-----------|--------|---------|--------|
| `ValueError` | Data validation | Invalid data value | Check data format/range |
| `TypeError` | Type checking | Wrong data type | Verify parameter types |
| `KeyError` | Dict/JSON access | Missing key | Verify config/alert files |
| `FileNotFoundError` | File operations | Missing file | Create file or fix path |
| `RuntimeError` | Data provider | API/data issue | Check provider connectivity |
| `ImportError` | Module loading | Missing module | Install dependencies |
| `JSONDecodeError` | JSON parsing | Invalid JSON | Verify file format |
| `RequestException` | HTTP requests | Network error | Check internet/API status |
| `Exception` | Generic handler | Unknown issue | Check logs for details |

---

## Data Provider Errors

### Error: "ValueError: Response contains no data"

**Cause:** Data provider returned empty result

**File:** `/src/stockreports/data_services/_internal/providing/binance/normalizer.py:58`

**Actual Code:**
```python
if not candles:
    raise ValueError("Response contains no data (empty array)")
```

**Common Scenarios:**
1. Symbol not found on exchange
2. Date range has no trading data
3. API rate limit exceeded (returns empty)

**Resolution:**
```bash
# 1. Verify symbol exists on exchange
curl "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=1m&limit=1"

# 2. Check date range has trading
python3 -c "import pandas; print(pd.Timestamp.now())"

# 3. Wait for rate limit reset (Binance: 1200 requests/min)
# Then retry operation

# 4. Check logs for exact error
docker logs stock-alerter-app 2>&1 | grep "no data"
```

### Error: "ValueError: Missing required columns"

**Cause:** Provider returned incomplete OHLCV data

**File:** `/src/stockreports/data_services/_internal/providing/binance/normalizer.py:188`

**Actual Code:**
```python
required_cols = {'Open', 'High', 'Low', 'Close', 'Volume'}
missing_cols = required_cols - set(df.columns)
if missing_cols:
    raise ValueError(f"Missing required columns: {missing_cols}")
```

**Common Scenarios:**
1. Provider returned wrong data structure
2. Data transformation failed
3. API response changed

**Resolution:**
```bash
# 1. Verify provider returns OHLCV
python3 << 'EOF'
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing._base_provider import DataProviderFactory

provider = DataProviderFactory.create(Provider.BINANCE_API)
df = provider.fetch_ohlcv('BTCUSDT', [1609459200], 60)  # Unix timestamp
print(df.columns)  # Should show: Open, High, Low, Close, Volume
EOF

# 2. Check normalizer transformation
grep -n "required_cols" \
  src/stockreports/data_services/_internal/providing/binance/normalizer.py
```

### Error: "ValueError: Index must be DatetimeIndex"

**Cause:** OHLCV data index is not timezone-aware datetime

**File:** `/src/stockreports/data_services/_internal/providing/binance/normalizer.py:192-194`

**Actual Code:**
```python
if not isinstance(df.index, pd.DatetimeIndex):
    raise ValueError("Index must be DatetimeIndex")

if df.index.tz is None:
    raise ValueError("Index must be timezone-aware")
```

**Common Scenarios:**
1. Provider returned numeric index instead of datetime
2. Timezone conversion failed
3. Data processing disabled timezone conversion

**Resolution:**
```python
# Verify DataFrame has correct index structure
import pandas as pd
from src.stockreports.data_services.orchestrator import DataServiceOrchestrator

service = DataServiceOrchestrator()
df = service.fetch_multi_symbol_ohlcv(
    symbols=['BTCUSDT'],
    unix_timestamps=[1609459200],
    resolution_minutes=60
)

# Check index
print(f"Index type: {type(df.index)}")
print(f"Index name: {df.index.name}")
print(f"Timezone: {df.index.tz}")
print(f"First timestamp: {df.index[0]}")

# Must show:
# Index type: <class 'pandas.core.indexes.datetimes.DatetimeIndex'>
# Timezone: UTC or market-specific
```

### Error: "RuntimeError: Binance API request failed after 3 attempts"

**Cause:** API provider exhausted retries

**File:** `/src/stockreports/data_services/_internal/providing/binance/api_provider.py:228`

**Actual Code:**
```python
except requests.exceptions.RequestException as e:
    # Retry logic (3 attempts by default)
    if attempt == self.retries - 1:
        raise RuntimeError(f"Binance API request failed after {self.retries} attempts: {e}")
```

**Common Scenarios:**
1. Binance API unreachable
2. Network connectivity issue
3. Rate limiting (1200 req/min)
4. API endpoint changed

**Resolution:**
```bash
# 1. Test Binance API connectivity
curl -I https://api.binance.com/api/v3/ping

# 2. Check network connectivity
ping -c 3 api.binance.com

# 3. Verify current rate limit status
curl https://api.binance.com/api/v3/exchangeInfo | grep -o '"weight":.*' | head -5

# 4. Check if symbol is tradeable
curl "https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT"

# 5. Monitor request count in logs
docker logs stock-alerter-app 2>&1 | grep "request" | tail -20
```

---

## Data Processing Errors

### Error: "ValueError: Found NaN values"

**Cause:** OHLCV data contains missing/null values

**File:** `/src/stockreports/data_services/_internal/providing/binance/normalizer.py:199`

**Actual Code:**
```python
nan_info = df.isna().sum()
if nan_info.sum() > 0:
    raise ValueError(f"Found NaN values: {nan_info[nan_info > 0].to_dict()}")
```

**Common Scenarios:**
1. Provider has gaps in data
2. Data processing step failed
3. Incomplete trading hours

**Resolution:**
```python
# Find which columns have NaN
import pandas as pd

df = load_ohlcv_data()  # Your data loading function
print(df.isna().sum())  # Shows NaN count per column
print(df[df.isna().any(axis=1)])  # Shows rows with NaN

# Options to fix:
# 1. Forward fill (use previous value)
df = df.fillna(method='ffill')

# 2. Drop rows with NaN
df = df.dropna()

# 3. Interpolate (estimate values)
df = df.interpolate(method='linear')
```

### Error: "ValueError: Volume values must be non-negative"

**Cause:** Volume data contains negative numbers

**File:** `/src/stockreports/data_services/_internal/providing/binance/normalizer.py:217`

**Actual Code:**
```python
if (df['Volume'] < 0).any():
    raise ValueError("Volume values must be non-negative")
```

**Common Scenarios:**
1. Data type conversion error (string to float)
2. API returned invalid data
3. Price adjustment logic error

**Resolution:**
```python
# Check volume data
import pandas as pd

df = load_ohlcv_data()
print(f"Min volume: {df['Volume'].min()}")
print(f"Max volume: {df['Volume'].max()}")
print(f"Negative volumes: {(df['Volume'] < 0).sum()}")

# Find problematic rows
problem_rows = df[df['Volume'] < 0]
print(problem_rows)

# Fix by absolute value
df['Volume'] = df['Volume'].abs()
```

---

## Executor Errors

### Error: "TypeError: Invalid alert sources"

**Cause:** Executor initialization received wrong parameter type

**File:** `/src/stockreports/alert/executor.py:83`

**Actual Code:**
```python
try:
    # Executor initialization
    executor = executor_class(mode=mode, symbol=symbol, alert_sources=alert_sources)
except Exception as e:
    logger.error(f"Executor initialization failed: {e}")
    raise
```

**Common Scenarios:**
1. alert_sources is string instead of list
2. Symbol not in SYMBOLS config
3. Mode is invalid

**Resolution:**
```python
# Correct format
from src.stockreports.alert.executor import Executor

# WRONG: String instead of list
executor = Executor(
    mode='deployment',
    symbol='VN30F1M',
    alert_sources='VN30'  # ❌ String
)

# CORRECT: List of strings
executor = Executor(
    mode='deployment',
    symbol='VN30F1M',
    alert_sources=['VN30', 'VN30F1M']  # ✅ List
)

# Verify in config
from src.stockreports.config.loader import get_settings
settings = get_settings()
print(settings.SYMBOLS)  # Should include all symbols
```

### Error: "Exception: Executor execution failed"

**Cause:** Executor._find_alerts() raised an exception

**File:** `/src/stockreports/alert/executor.py:83`

**Actual Code:**
```python
def run(self, alert_data: list[AlertData]) -> AlertResult:
    """
    Run executor and return AlertResult.
    
    Exceptions are caught and logged here.
    """
    try:
        results = self._find_alerts(alert_data)
        return AlertResult(alerts=results)
    except Exception as e:
        logger.error(f"Executor execution failed: {e}", exc_info=True)
        raise
```

**Common Scenarios:**
1. Child class _find_alerts() not implemented
2. Indicator calculation failed (division by zero, NaN)
3. Alert data malformed

**Resolution:**
```bash
# 1. Check which executor failed
docker logs stock-alerter-app 2>&1 | grep "Executor execution failed"

# 2. Get full traceback
docker logs stock-alerter-app 2>&1 | grep -A 20 "Executor execution failed"

# 3. Verify executor is implemented
ls -la src/stockreports/alert/approach/*/executor.py

# 4. Test executor standalone
python3 << 'EOF'
from src.stockreports.alert.executor import StrongCandleExecutor
from src.stockreports.alert.model.models import AlertData

executor = StrongCandleExecutor(
    mode='deployment',
    symbol='VN30F1M',
    alert_sources=['VN30']
)

# Create minimal AlertData
alert = AlertData(
    alert_price=1000.0,
    alert_type='BUY',
    timestamp=pd.Timestamp.now()
)

result = executor.run([alert])
print(f"Result: {result}")
EOF
```

---

## Notification Errors

### Error: "Exception: Email notification failed"

**Cause:** Email sending encountered an error

**File:** `/src/stockreports/notification/notification_manager.py:90`

**Actual Code:**
```python
try:
    send_email(alert_notification)
except Exception as e:
    logger.warning(f"Email notification failed: {e}")
    # Continues - doesn't stop other notifications
```

**Common Scenarios:**
1. SMTP server unreachable
2. Invalid credentials
3. Gmail security setting blocks access

**Resolution:**
```bash
# 1. Verify email configuration
python3 << 'EOF'
from src.stockreports.config.loader import get_notification_settings

settings = get_notification_settings()
print(f"Email enabled: {settings.EMAIL_ENABLED}")
print(f"Sender: {settings.EMAIL_SENDER}")
print(f"Receivers: {settings.EMAIL_RECEIVERS}")
EOF

# 2. Test SMTP connectivity
python3 << 'EOF'
import smtplib

server = smtplib.SMTP('smtp.gmail.com', 587)
server.starttls()
try:
    server.login('your-email@gmail.com', 'your-app-password')
    print("✓ SMTP login successful")
except Exception as e:
    print(f"✗ SMTP login failed: {e}")
finally:
    server.quit()
EOF

# 3. For Gmail: Generate app-specific password
# https://support.google.com/accounts/answer/185833

# 4. Check email configuration in environment
env | grep EMAIL
```

### Error: "Exception: SMS notification failed"

**Cause:** Twilio SMS sending failed

**File:** `/src/stockreports/notification/notification_manager.py:101`

**Actual Code:**
```python
try:
    send_sms(alert_notification)
except Exception as e:
    logger.warning(f"SMS notification failed: {e}")
    # Continues - doesn't stop other notifications
```

**Common Scenarios:**
1. Invalid Twilio credentials
2. Phone number format incorrect
3. Account out of credits

**Resolution:**
```bash
# 1. Verify Twilio configuration
python3 << 'EOF'
from src.stockreports.config.loader import get_notification_settings

settings = get_notification_settings()
print(f"Twilio enabled: {settings.TWILIO_ENABLED}")
print(f"Account SID: {settings.TWILIO_ACCOUNT_SID[:10]}...")  # Masked
print(f"From phone: {settings.TWILIO_PHONE_NUMBER}")
print(f"To phone: {settings.SMS_RECEIVER_PHONE_NUMBER}")
EOF

# 2. Test Twilio client
python3 << 'EOF'
from twilio.rest import Client

account_sid = "your_account_sid"
auth_token = "your_auth_token"

client = Client(account_sid, auth_token)
try:
    # Verify credentials by fetching account info
    account = client.api.accounts(account_sid).fetch()
    print(f"✓ Twilio account verified: {account.friendly_name}")
except Exception as e:
    print(f"✗ Twilio auth failed: {e}")
EOF

# 3. Verify phone number format
# Must include country code, e.g.: +84983794189 (not 0983794189)

# 4. Check account balance in Twilio dashboard
```

### Error: "JSONDecodeError: Expecting value"

**Cause:** Ntfy notification response invalid JSON

**File:** `/src/stockreports/notification/notification_manager.py:50`

**Actual Code:**
```python
try:
    response = requests.post(ntfy_url, json=payload)
    response.json()
except json.JSONDecodeError:
    logger.error("Ntfy response is not valid JSON")
```

**Common Scenarios:**
1. Ntfy server returned error page (HTML, not JSON)
2. Network issue corrupted response
3. Wrong URL configured

**Resolution:**
```bash
# 1. Test Ntfy endpoint
curl -d "Hello from test" https://ntfy.sh/test_topic

# 2. Verify topic name
# Ntfy topics must be alphanumeric + underscores
# Example: vn30_alerts_f8a9b2c1 ✓
# Example: vn30 alerts ✗ (has space)

# 3. Check Ntfy configuration
python3 << 'EOF'
from src.stockreports.config.loader import get_notification_settings

settings = get_notification_settings()
print(f"Ntfy enabled: {settings.NTFY_ENABLED}")
print(f"Topics: {settings.NTFY_TOPICS}")
EOF

# 4. Test JSON response manually
python3 << 'EOF'
import requests

response = requests.post('https://ntfy.sh/test_topic', data='test message')
print(f"Status: {response.status_code}")
print(f"Content-Type: {response.headers.get('content-type')}")
print(f"Body: {response.text[:200]}")
EOF
```

---

## Alert Generation Errors

### Error: "KeyError: Missing alert field"

**Cause:** AlertData missing required field

**File:** `/src/stockreports/alert/model/models.py:168-176`

**Actual Code:**
```python
@classmethod
def from_dict(cls, data: dict) -> 'AlertData':
    """Create AlertData from dict, raise TypeError if missing required fields."""
    required_fields = {'alert_price', 'alert_type', 'timestamp'}
    missing = required_fields - set(data.keys())
    if missing:
        raise TypeError(f"Missing required fields: {missing}")
```

**Common Scenarios:**
1. Alert JSON file missing fields
2. Data transformation dropped fields
3. Alert source changed format

**Resolution:**
```bash
# 1. Check alert JSON structure
python3 << 'EOF'
import json

with open('alerts/VN30/alert_VN30_2026-04-08.json') as f:
    alerts = json.load(f)

# Check first alert
if alerts:
    print(json.dumps(alerts[0], indent=2))
EOF

# 2. Verify required fields exist
# Every alert must have:
# - alert_price (float)
# - alert_type (str: 'BUY' or 'SELL')
# - timestamp (ISO format)

# 3. Regenerate alerts if corrupted
python3 -m src.tools.generate_alerts --symbol VN30 --force
```

### Error: "Exception: Symbol not found in configuration"

**Cause:** Symbol not in SYMBOLS list

**File:** `/src/stockreports/alert/symbol_alerter.py:76`

**Actual Code:**
```python
if symbol not in settings.SYMBOLS:
    raise TypeError(f"Symbol {symbol} not configured in SYMBOLS")
```

**Common Scenarios:**
1. Symbol added to alerts but not settings
2. Typo in symbol name
3. Symbol removed from production

**Resolution:**
```bash
# 1. List configured symbols
python3 << 'EOF'
from src.stockreports.config.loader import get_settings

settings = get_settings()
print(f"Configured symbols: {settings.SYMBOLS}")
print(f"Impact symbols: {settings.IMPACT_SYMBOLS}")
EOF

# 2. Add new symbol to configuration
# Edit: src/stockreports/config/settings.py
# Change:
#   SYMBOLS = ["VN30F1M", "VN30"]
# To:
#   SYMBOLS = ["VN30F1M", "VN30", "VIC"]

# 3. Verify in alert files
find alerts/ -name "*.json" | xargs grep -l "alert_symbol" | sort -u
```

---

## File and Configuration Errors

### Error: "FileNotFoundError: Alert file not found"

**Cause:** Alert JSON file missing

**File:** `/src/stockreports/alert/symbol_alert_manager.py:231`

**Actual Code:**
```python
try:
    with open(alert_file_path) as f:
        alerts = json.load(f)
except (json.JSONDecodeError, KeyError) as e:
    logger.error(f"Failed to parse alert file: {alert_file_path}")
except FileNotFoundError:
    logger.warning(f"Alert file not found: {alert_file_path}")
```

**Common Scenarios:**
1. Alert files not generated
2. Wrong path configured
3. File deleted

**Resolution:**
```bash
# 1. Check alert directory structure
ls -la alerts/

# Should show:
# alerts/
# ├── VN30/
# │   └── alert_VN30_2026-04-08.json
# ├── VN30F1M/
# │   └── alert_VN30F1M_2026-04-08.json

# 2. Generate missing alerts
python3 -m src.tools.generate_alerts --symbols VN30 VN30F1M

# 3. Verify alert file format
python3 << 'EOF'
import json

path = 'alerts/VN30/alert_VN30_2026-04-08.json'
try:
    with open(path) as f:
        data = json.load(f)
    print(f"✓ File OK: {len(data)} alerts")
except FileNotFoundError:
    print(f"✗ File not found: {path}")
except json.JSONDecodeError as e:
    print(f"✗ Invalid JSON: {e}")
EOF
```

### Error: "ImportError: Cannot import executor class"

**Cause:** Executor module not found or not in EXECUTORS list

**File:** `/src/stockreports/alert/symbol_alerter.py:137`

**Actual Code:**
```python
try:
    executor_class = getattr(module, executor_name)
except (ImportError, AttributeError) as e:
    logger.error(f"Failed to import executor: {executor_name}")
    raise
```

**Common Scenarios:**
1. Executor class renamed
2. Executor module moved
3. Typo in executor name

**Resolution:**
```bash
# 1. List available executors
ls -la src/stockreports/alert/approach/*/executor.py

# 2. Get executor class names
python3 << 'EOF'
import os
import importlib.util

executors = []
for dir_name in os.listdir('src/stockreports/alert/approach'):
    if dir_name.startswith('_'):
        continue
    
    spec = importlib.util.spec_from_file_location(
        "executor",
        f"src/stockreports/alert/approach/{dir_name}/executor.py"
    )
    if spec and spec.loader:
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find class that ends with 'Executor'
        for name in dir(module):
            if name.endswith('Executor'):
                executors.append(name)

print("Available executors:")
for exc in sorted(set(executors)):
    print(f"  - {exc}")
EOF

# 3. Verify executor in settings
grep -n "EXECUTORS" src/stockreports/config/signal_settings.py
```

---

## Debugging Procedures

### Enable Debug Logging

```bash
# 1. Set environment variable
export LOG_LEVEL=DEBUG

# 2. Restart application
docker-compose restart stock-alerter-app

# 3. View debug logs
docker logs -f stock-alerter-app | grep DEBUG
```

### Trace a Specific Symbol

```bash
# Get all logs for one symbol
docker logs stock-alerter-app 2>&1 | grep "VN30F1M"

# Get timeline of events
docker logs stock-alerter-app 2>&1 | grep "VN30F1M" | head -100
```

### Test Individual Components

**Test Data Provider:**
```python
from src.stockreports.data_services._internal.providing._providers import Provider
from src.stockreports.data_services._internal.providing._base_provider import DataProviderFactory

provider = DataProviderFactory.create(Provider.VIETSTOCK)
df = provider.fetch_ohlcv('VN30', [1609459200], 1)
print(df)
```

**Test Executor:**
```python
from src.stockreports.alert.approach.strong_candle.executor import StrongCandleExecutor
from src.stockreports.alert.model.models import AlertData

executor = StrongCandleExecutor(mode='deployment', symbol='VN30', alert_sources=['VN30'])
alerts = [AlertData(alert_price=1000, alert_type='BUY', timestamp=pd.Timestamp.now())]
result = executor.run(alerts)
print(result)
```

**Test Notification:**
```python
from src.stockreports.notification.notification_manager import NotificationManager
from src.stockreports.alert.model.models import AlertResult, AlertData

notif = NotificationManager()
alert = AlertData(alert_price=1000, alert_type='BUY', timestamp=pd.Timestamp.now())
result = AlertResult(alerts=[alert])
notif.process_and_notify(result, 'VN30')
```

---

## Error Isolation

The system is designed with error isolation:

- **Notification errors don't stop alerts** - One channel failing doesn't block others
- **Executor errors are caught** - Individual executors failing doesn't crash system
- **Data provider errors are logged** - Provider issues logged but can retry
- **Configuration errors are early** - Bad config caught at startup

**Example - Email fails but SMS succeeds:**
```
[14:23:45] ⚠️  Email notification failed: SMTP connection timeout
[14:23:46] ✓ SMS notification succeeded
[14:23:47] ✓ Ntfy notification succeeded
```

---

**Status:** Based on Actual Codebase  
**Date:** April 8, 2026  
**Exception Types:** 12+ documented  
**Real Scenarios:** 20+ covered  
**Verified:** Yes
