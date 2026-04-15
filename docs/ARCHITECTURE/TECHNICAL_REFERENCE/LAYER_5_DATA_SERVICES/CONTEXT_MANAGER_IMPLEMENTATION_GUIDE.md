# Context Manager Implementation Guide

**Purpose:** Step-by-step guide for implementing context managers in data providers  
**Audience:** Developers adding new data providers or extending existing ones  
**Location:** `docs/ARCHITECTURE/TECHNICAL_REFERENCE/LAYER_5_DATA_SERVICES/`  
**Created:** April 13, 2026  

---

## 📋 Quick Overview

This guide walks you through implementing context managers for data providers to ensure proper resource cleanup. Following this pattern ensures your provider works safely with the monitoring system and prevents connection timeouts.

---

## 🎯 When to Implement Context Managers

Use this guide when:
- ✅ Adding a new data provider (Vietstock, Binance, etc.)
- ✅ Modifying an existing provider
- ✅ Adding persistent resource management (HTTP sessions, exchange connections)
- ✅ Integrating with the coordinator's monitoring loop

**Why:** All providers must support context managers to prevent 1-2 hour connection timeouts in the 57-second monitoring cycle.

---

## 🏗️ Step-by-Step Implementation

### Step 1: Inherit from BaseDataProvider

All providers must inherit from `BaseDataProvider`:

**File:** `src/stockreports/data_services/_internal/providing/_base_provider.py` (lines 157-217)

```python
# ✅ Correct
from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider

class YourNewProvider(BaseDataProvider):
    """Your new data provider"""
    pass

# ❌ Don't do this
class YourNewProvider:
    """Missing context manager support!"""
    pass
```

**Why:** BaseDataProvider provides:
- `__enter__()` - Called when entering `with` block
- `__exit__()` - Called when exiting `with` block (calls `close()`)
- Default `close()` - Safe no-op if you don't need cleanup

---

### Step 2: Determine Your Resource Needs

What persistent resources does your provider use?

**Category 1: Stateless (No Persistent Resources)**

Example: VietstockProvider
- Makes HTTP REST calls (each call opens/closes connection automatically)
- No persistent connection held
- No session management needed

**Action:** Skip steps 3-4, inherit defaults from BaseDataProvider

```python
class VietstockProvider(BaseDataProvider):
    # Inherit __enter__, __exit__, close() defaults
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        # HTTP request handling by requests library
        ...
```

**Category 2: HTTP Session Management**

Example: BinanceAPIProvider
- Creates persistent `requests.Session()` for performance
- Needs explicit cleanup to close HTTP connection
- **Action:** Implement `close()` override (see Step 3)

**Category 3: Exchange Connection Management**

Example: BinanceCCXTProvider
- Creates persistent CCXT exchange object
- May need cleanup for graceful disconnect
- **Action:** Implement `close()` override (see Step 3)

---

### Step 3: Override close() for Persistent Resources

If your provider has persistent resources, override the `close()` method:

**Template:**

```python
class YourProvider(BaseDataProvider):
    def __init__(self, ...):
        # Initialize persistent resource
        self._session = self._create_session()  # Example: HTTP session
        # or
        self._connection = self._create_connection()  # Example: DB connection
    
    def close(self):
        """
        Close any persistent resources.
        
        Called automatically when exiting 'with' block.
        Must handle:
        - Resource already closed (idempotent)
        - Errors during cleanup (catch and log)
        - None/missing resources (check with hasattr)
        """
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
                self._session = None
        except Exception as e:
            logger.error(f"Error closing session: {e}")
            # Don't re-raise - cleanup failure shouldn't crash system
```

**Real Example - BinanceAPIProvider (lines 70-82):**

```python
class BinanceAPIProvider(BaseDataProvider):
    def __init__(self, api_key: str, api_secret: str, timeout: int = 30):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout = timeout
        self._session = self._create_session()  # Create on init
    
    def _create_session(self):
        """Create HTTP session with auth headers"""
        session = requests.Session()
        session.headers.update({
            'X-MBX-APIKEY': self.api_key,
        })
        return session
    
    def close(self):
        """Close HTTP session - CRITICAL for cleanup"""
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        # Use self._session for requests
        response = self._session.get(self.endpoint, params=params)
        ...
```

---

### Step 4: Use in Coordinator (No Changes Needed!)

The coordinator automatically uses context managers correctly:

**File:** `src/stockreports/data_services/_internal/providing/_coordinator.py` (lines 168-174)

```python
def fetch_ohlcv(self, symbol, from_timestamp, to_timestamp, resolution):
    """Get OHLCV data with resource safety"""
    provider = self._get_provider(symbol)
    
    with provider:  # ← Automatically calls __enter__
        ohlcv = provider.fetch_ohlcv(
            symbol, from_timestamp, to_timestamp, resolution
        )
        # Your close() is called here on __exit__ (guaranteed)
    
    return ohlcv
```

**Nothing to do here** - the coordinator handles everything! Your job is just to:
1. Inherit from BaseDataProvider ✅
2. Override `close()` if needed ✅
3. Trust that `with provider:` will call your `close()` ✅

---

### Step 5: Add Exception Handling

Always handle exceptions in `close()` gracefully:

**Pattern:**

```python
def close(self):
    """Close with proper exception handling"""
    try:
        if hasattr(self, '_resource') and self._resource:
            self._resource.close()  # Might raise exception
    except Exception as e:
        # Log but don't re-raise
        logger.error(f"Error closing resource: {e}", exc_info=True)
        # Context manager still continues normally
```

**Why:**
- Closing might fail (already closed, network error, etc.)
- Failure in cleanup shouldn't crash the system
- Failure shouldn't prevent other cleanup operations
- Must log for debugging

**Example - What Could Go Wrong:**

```python
def close(self):
    # ❌ DON'T do this (will crash if socket already closed)
    self._session.close()  # Might raise exception!
    
    # ✅ DO this instead
    try:
        if hasattr(self, '_session') and self._session:
            self._session.close()
    except Exception as e:
        logger.error(f"Error closing session: {e}")
```

---

### Step 6: Implement fetch_ohlcv() with Proper Resource Usage

Your provider's `fetch_ohlcv()` should use the managed resources:

```python
class YourProvider(BaseDataProvider):
    def __init__(self):
        self._session = requests.Session()
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        """Fetch OHLCV using persistent session"""
        
        # Use the managed resource
        response = self._session.get(
            self.base_url,
            params={
                'symbol': symbol,
                'startTime': from_ts,
                'endTime': to_ts,
                'interval': self._resolution_to_interval(resolution)
            },
            timeout=self.timeout
        )
        
        response.raise_for_status()
        
        # Process response to OHLCV format
        ohlcv = self._normalize(response.json())
        
        return ohlcv
    
    def close(self):
        """Clean up session when done"""
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")
```

---

## 🧪 Testing Your Implementation

### Test 1: Verify Context Manager Works

```python
def test_provider_context_manager():
    """Verify provider can be used with context manager"""
    provider = YourProvider()
    
    # Should not raise exception
    with provider:
        data = provider.fetch_ohlcv('SYMBOL', ts1, ts2, resolution)
        assert data is not None
```

### Test 2: Verify close() is Called

```python
def test_close_called_on_exit():
    """Verify close() is called when exiting with block"""
    
    provider = YourProvider()
    close_called = False
    
    # Monkey-patch close() to track calls
    original_close = provider.close
    def tracked_close():
        nonlocal close_called
        close_called = True
        original_close()
    
    provider.close = tracked_close
    
    with provider:
        pass  # Do nothing
    
    assert close_called, "close() should be called on exit"
```

### Test 3: Verify close() Called on Exception

```python
def test_close_called_on_exception():
    """Verify close() is called even if exception in with block"""
    
    provider = YourProvider()
    close_called = False
    
    # Track close() calls
    original_close = provider.close
    def tracked_close():
        nonlocal close_called
        close_called = True
        original_close()
    
    provider.close = tracked_close
    
    try:
        with provider:
            raise ValueError("Test error")
    except ValueError:
        pass
    
    assert close_called, "close() should be called even on exception"
```

### Test 4: Verify Resource Actually Closes

```python
def test_session_closes():
    """Verify HTTP session actually closes"""
    
    provider = BinanceAPIProvider(key, secret)
    
    session_before = provider._session
    assert not session_before.closed
    
    with provider:
        data = provider.fetch_ohlcv('BTCUSDT', ts1, ts2, 60)
    
    # After exiting, session should be closed
    assert session_before.closed
```

### Test 5: Multiple Cycles (Stress Test)

```python
def test_multiple_cycles():
    """Verify resource cleanup works across multiple cycles"""
    
    for i in range(100):
        provider = YourProvider()
        
        with provider:
            data = provider.fetch_ohlcv('SYMBOL', ts1, ts2, resolution)
            assert data is not None
    
    # Should complete without errors
    # No resource leaks after 100 cycles
```

---

## 📋 Validation Checklist

Before considering your implementation complete:

- [ ] Class inherits from `BaseDataProvider`
- [ ] `close()` method defined (if resource cleanup needed)
- [ ] `close()` handles exceptions gracefully
- [ ] `close()` is idempotent (safe to call multiple times)
- [ ] `close()` checks `hasattr()` before accessing resources
- [ ] All persistent resources initialized in `__init__`
- [ ] `fetch_ohlcv()` uses managed resources
- [ ] Test 1: Context manager works ✅
- [ ] Test 2: close() called on exit ✅
- [ ] Test 3: close() called on exception ✅
- [ ] Test 4: Resource actually closes ✅
- [ ] Test 5: Multiple cycles work ✅
- [ ] Provider works with 57-second monitoring loop
- [ ] No resource leaks after extended operation (24+ hours)
- [ ] Logs show normal operation (no timeout errors)

---

## 🔍 Common Issues & Solutions

### Issue 1: "close() called multiple times"

**Symptom:** Error like "Session already closed" when close() runs twice

**Cause:** Your close() doesn't check if already closed

**Solution:**
```python
def close(self):
    # ✅ Correct: Check before closing
    if hasattr(self, '_session') and self._session:
        try:
            self._session.close()
        except Exception as e:
            logger.error(f"Error: {e}")
```

### Issue 2: "Context manager never called"

**Symptom:** Resources not cleaned up, connection timeouts after 1-2 hours

**Cause:** Code uses provider without `with` statement

**Solution:**
```python
# ❌ Wrong - no cleanup!
provider = get_provider(symbol)
data = provider.fetch_ohlcv(symbol, ...)

# ✅ Right - with guarantees cleanup
provider = get_provider(symbol)
with provider:
    data = provider.fetch_ohlcv(symbol, ...)
```

### Issue 3: "AttributeError: '_session' not found"

**Symptom:** `close()` crashes trying to access session

**Cause:** Forgot to initialize in `__init__` or used wrong attribute name

**Solution:**
```python
class YourProvider(BaseDataProvider):
    def __init__(self):
        self._session = None  # Initialize! ← Important
        # or
        self._session = self._create_session()
    
    def close(self):
        if hasattr(self, '_session') and self._session:  # Check first!
            self._session.close()
```

### Issue 4: "Resource leak: 1000+ open connections"

**Symptom:** Memory grows constantly, `netstat` shows many connections

**Cause:** close() not being called (probably not using `with`)

**Solution:** Ensure all provider usage is wrapped in `with provider:`

---

## 🎓 Design Patterns

### Pattern 1: Minimal Implementation (No Resources)

**For:** Stateless providers that don't hold persistent resources

```python
class SimpleProvider(BaseDataProvider):
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        # No persistent resources - just make call
        response = self._make_api_call(symbol, from_ts, to_ts)
        return self._normalize(response)
    
    # Inherit close(), __enter__(), __exit__() from base
    # close() is no-op (safe)
```

**When to use:** RESTful providers without sessions

---

### Pattern 2: Session Management Implementation

**For:** Providers with HTTP sessions

```python
class SessionProvider(BaseDataProvider):
    def __init__(self):
        self._session = requests.Session()
    
    def close(self):
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
        except Exception as e:
            logger.error(f"Error closing session: {e}")
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        response = self._session.get(...)  # Use session
        return self._normalize(response.json())
```

**When to use:** Providers using persistent HTTP connections (Binance API)

---

### Pattern 3: Complex Resource Management

**For:** Providers with multiple resources or initialization

```python
class ComplexProvider(BaseDataProvider):
    def __init__(self):
        self._session = None
        self._cache = {}
        self._is_connected = False
        self._initialize()
    
    def _initialize(self):
        """Initialize resources"""
        self._session = self._create_session()
        self._is_connected = True
    
    def close(self):
        """Clean up all resources"""
        try:
            # Clean up session
            if hasattr(self, '_session') and self._session:
                self._session.close()
            
            # Clear cache
            if hasattr(self, '_cache'):
                self._cache.clear()
            
            self._is_connected = False
        except Exception as e:
            logger.error(f"Error closing resources: {e}")
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        if not self._is_connected:
            raise RuntimeError("Provider not connected")
        
        # Use resources
        response = self._session.get(...)
        # ...
```

**When to use:** Complex providers with multiple resources

---

## 📞 Related Documentation

- **Resource Lifecycle Guide:** [PROVIDER_RESOURCE_LIFECYCLE.md](./PROVIDER_RESOURCE_LIFECYCLE.md)
- **Architecture Overview:** [DATA_LAYER_ARCHITECTURE.md](./DATA_LAYER_ARCHITECTURE.md)
- **Extension Guide:** [../IMPLEMENTATION_GUIDES/LAYER_5_DATA_SERVICES/DATA_PROVIDER_EXTENSION_GUIDE.md](../IMPLEMENTATION_GUIDES/LAYER_5_DATA_SERVICES/DATA_PROVIDER_EXTENSION_GUIDE.md)
- **Coordinator Code:** `src/stockreports/data_services/_internal/providing/_coordinator.py`
- **Base Provider Code:** `src/stockreports/data_services/_internal/providing/_base_provider.py`
- **Example - BinanceAPIProvider:** `src/stockreports/data_services/_internal/providing/binance/api_provider.py`

---

## ❓ FAQ

**Q: Do I have to implement context managers?**  
A: Yes, all providers must inherit from BaseDataProvider which provides context manager support.

**Q: What if I don't need cleanup?**  
A: Just inherit the defaults - close() is a no-op by default (safe).

**Q: Can I call close() manually?**  
A: Yes, it's safe: `provider.close()`. Context manager will call it again (no harm).

**Q: What if close() fails?**  
A: Log the error and continue. Don't let cleanup failure crash the system.

**Q: How do I debug cleanup issues?**  
A: Add logging to close(), monitor connections with netstat, check memory usage over time.

**Q: Does this work with pytest?**  
A: Yes, context managers work perfectly with pytest fixtures and tests.

---

## 🚀 Summary

**Minimum Implementation:**

```python
from src.stockreports.data_services._internal.providing._base_provider import BaseDataProvider

class MyProvider(BaseDataProvider):
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        # Your implementation
        pass
```

**With Session Management:**

```python
class MyProvider(BaseDataProvider):
    def __init__(self):
        self._session = requests.Session()
    
    def close(self):
        try:
            if hasattr(self, '_session') and self._session:
                self._session.close()
        except Exception as e:
            logger.error(f"Error: {e}")
    
    def fetch_ohlcv(self, symbol, from_ts, to_ts, resolution):
        response = self._session.get(...)
        return self._normalize(response.json())
```

**Usage in Coordinator (Already Implemented):**

```python
provider = get_provider(symbol)
with provider:  # Automatically calls your close() on exit!
    data = provider.fetch_ohlcv(symbol, ...)
```

---

**Version:** 1.0  
**Created:** April 13, 2026  
**Status:** ✅ Complete  
**Last Updated:** April 13, 2026
