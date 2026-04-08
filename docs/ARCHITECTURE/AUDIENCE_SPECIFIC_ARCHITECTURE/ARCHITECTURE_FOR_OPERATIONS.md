# Architecture Guide for Operations & Cross-Functional Teams

**Date:** April 8, 2026  
**Target Audience:** QA, BSA, Product, Operations, DevOps  
**Purpose:** Understand system capabilities, deployment, monitoring, and troubleshooting  
**Reading Time:** 20-25 minutes

---

## System Overview

The system is a **real-time trading alert platform** with two operational modes:

```
┌─────────────────────────────────────────────────────────┐
│          TRADING ALERT SYSTEM                           │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  LIVE Mode (Production)    REPLAY Mode (Testing)       │
│  ├─ Real-time monitoring   ├─ Historical simulation    │
│  ├─ Live market data       ├─ Backtest capability      │
│  ├─ Indefinite operation   ├─ Bounded (day-end)        │
│  ├─ Auto-recovery          ├─ Exit on error            │
│  └─ reports/ output        └─ reports_replay/ output   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

Both modes run on the same codebase with different configurations.

---

## System Capabilities Checklist

### ✅ Core Alert Generation
- [ ] Multi-symbol monitoring (unlimited symbols)
- [ ] Real-time price data fetching
- [ ] 6 different alert detection approaches
- [ ] Customizable alert thresholds
- [ ] Time-based scheduled operations
- [ ] Multi-threaded concurrent processing

### ✅ Data Sources
- [ ] Vietstock (Vietnamese stocks/indices)
- [ ] Binance API (Cryptocurrencies)
- [ ] Binance CCXT (Alternative crypto integration)
- [ ] Data caching for performance
- [ ] Automatic data refresh intervals

### ✅ Notification Delivery
- [ ] Email notifications
- [ ] SMS notifications
- [ ] Ntfy web notifications
- [ ] Error isolation (one channel failure doesn't affect others)
- [ ] Retry logic for failed deliveries

### ✅ Performance Analysis
- [ ] Trade simulation and backtesting
- [ ] Multi-scenario testing (20+ profit/loss combinations)
- [ ] Performance metrics generation
- [ ] Optional S/R level detection
- [ ] Optional parameter optimization

### ✅ Operational Features
- [ ] Health check endpoints
- [ ] Structured logging
- [ ] Error recovery and restart
- [ ] Configuration validation
- [ ] Mode switching (LIVE/REPLAY)

---

## System Architecture (High-Level)

```
┌────────────────────────────────────────────────────────────┐
│  ENTRY POINT: SymbolAlertManager                           │
│  (Multi-symbol orchestrator using ThreadPoolExecutor)      │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│  ORCHESTRATOR: SymbolAlerter (per symbol)                  │
│  - Supervisor pattern with crash resilience               │
│  - Restarts on failure in LIVE mode                        │
│  - Single-symbol coordination                              │
└────────────────────────────────────────────────────────────┘
                            ↓
        ┌───────────────────┬───────────────────┐
        ↓                   ↓                   ↓
   ┌─────────┐        ┌──────────┐      ┌────────────┐
   │ Data    │        │ Analysis │      │Notification│
   │ Service │        │ Executors│      │ Manager    │
   └─────────┘        └──────────┘      └────────────┘
        ↓                   ↓                   ↓
   [3 Sources]    [6 Approaches]    [3 Channels]
   ↓              ↓                  ↓
   Vietstock      Strong Candle      Email
   Binance API    Momentum            SMS
   Binance CCXT   Volume Spike        Ntfy
                  VRA
                  Ichimoku
                  Vol Anchor
        ↓
    ┌─────────────┐
    │ Reports out │
    │ reports/ or │
    │ reports_rep │
    └─────────────┘
```

---

## Operational Architecture

### Configuration Tiers

**Tier 1: System Configuration** (`settings.py`)
- Mode selection (LIVE/REPLAY)
- System-wide parameters
- Data refresh intervals
- Threading configuration

**Tier 2: Feature-Specific Configuration**
- `data_provider_settings.py` - Which data sources to use
- `signal_settings.py` - Which alert approaches to use
- `notification_settings.py` - Notification preferences
- `price_alert_settings.py` - Alert thresholds
- `validation_settings.py` - Validation rules and thresholds

**Tier 3: Runtime Configuration**
- Command-line arguments
- Environment variables
- Configuration overrides

### Data Flow

```
Input: Symbol list + Configuration
   ↓
Fetch OHLCV Data (1-min, 5-min, etc.)
   ↓
Analyze via 6+ Executors
   ↓
Generate Alerts (when conditions match)
   ↓
Send via Notification Channels
   ↓
Store in Reports Directory
   ↓
Optional: Backtest Analysis
```

---

## Testing & QA Coverage

### Unit Testing Areas

| Component | Coverage | Notes |
|-----------|----------|-------|
| DataServiceOrchestrator | ✅ High | Data fetching, caching |
| Executor Framework | ✅ High | Each executor tested individually |
| NotificationManager | ✅ High | Each channel tested separately |
| TimeSimulator | ✅ High | LIVE/REPLAY mode testing |
| AlertData Model | ✅ Complete | Data structure validation |

### Integration Testing Scenarios

#### Scenario 1: LIVE Mode - Single Symbol
```
1. Start monitoring single symbol
2. Fetch real market data
3. Generate alerts on real prices
4. Send notifications
5. Continue indefinitely until stopped
6. Verify auto-recovery on error
```

#### Scenario 2: LIVE Mode - Multiple Symbols
```
1. Start monitoring 3+ symbols concurrently
2. Verify independent data fetching for each
3. Verify alerts don't interfere
4. Test thread safety
5. Verify concurrent notifications
```

#### Scenario 3: REPLAY Mode - Backtesting
```
1. Set DEBUG_REPLAY_START_TIME = "2026-01-01 09:15:00"
2. Run with historical data
3. Verify time simulator bounds loop to trading hours
4. Verify exits at day end automatically
5. Generate backtest report
```

#### Scenario 4: Mode Switching
```
1. Start in LIVE mode
2. Switch configuration to REPLAY mode
3. Verify new session uses simulated time
4. Switch back to LIVE
5. Verify reconnection works
```

#### Scenario 5: Error Recovery
```
1. Start monitoring
2. Simulate data provider failure
3. Verify system logs error
4. Verify auto-recovery attempts
5. Verify notification on recovery
```

#### Scenario 6: Notification Failure Isolation
```
1. Start monitoring with 3 channels configured
2. Disable one notification channel
3. Verify alerts still send via other channels
4. Verify failure doesn't crash system
5. Verify logging of failure
```

### Performance Testing

| Test | Target | Method |
|------|--------|--------|
| Alert Latency | < 5 seconds | Measure time from data fetch to notification |
| Concurrent Symbols | 100+ | Load test with multiple symbols |
| Data Fetch Throughput | 1,000 rows/sec | Measure data ingestion rate |
| Notification Delivery | 99.9% success | Send 1,000 notifications, count failures |
| Report Generation | < 1 min per day | Backtest and measure generation time |

---

## Monitoring & Health Checks

### Available Health Endpoints

#### 1. System Health Check
```
GET /health
Response: {
  "status": "healthy",
  "timestamp": "2026-04-08T10:30:00Z",
  "uptime_seconds": 3600,
  "mode": "LIVE"
}
```

#### 2. Component Status
```
GET /health/components
Response: {
  "data_provider": "healthy",
  "notifications": "healthy", 
  "execution_engine": "healthy",
  "storage": "healthy"
}
```

#### 3. Alert Status
```
GET /alerts/status
Response: {
  "monitoring_symbols": ["VN30", "BTC", "ETH"],
  "active_executors": 6,
  "alerts_generated": 152,
  "last_alert": "2026-04-08T10:25:15Z"
}
```

### Key Metrics to Monitor

| Metric | Alert Threshold | Frequency |
|--------|-----------------|-----------|
| System Uptime | < 99.5% | Continuous |
| Alert Latency | > 10 seconds | Per alert |
| Data Fetch Errors | > 5% | Per 5 minutes |
| Notification Failures | > 1% | Per batch |
| Report Generation Time | > 5 minutes | Per report |
| Disk Usage (reports) | > 80% | Hourly |

### Logging Configuration

**Log Levels:**
- ERROR: System failures, exceptions
- WARN: Recoverable issues, retries
- INFO: Operational events, alerts triggered
- DEBUG: Detailed execution flow

**Log Locations:**
- `/var/log/trading_alert_system.log` - Main system log
- `/var/log/alerts/` - Alert generation logs
- `reports/` - Alert output files
- `reports_replay/` - Backtest output files

---

## Deployment Architecture

### Deployment Modes

#### LIVE Deployment
```
┌─────────────────────────────────────┐
│ Production Server                   │
├─────────────────────────────────────┤
│ Environment: production             │
│ Mode: LIVE                          │
│ DEBUG_REPLAY_START_TIME: None       │
│ Data: Real market data              │
│ Operation: 24/7 monitoring          │
│ Error Handling: Auto-recovery       │
│ Output: reports/ directory          │
└─────────────────────────────────────┘
```

#### REPLAY Deployment
```
┌─────────────────────────────────────┐
│ Testing Server                      │
├─────────────────────────────────────┤
│ Environment: testing                │
│ Mode: REPLAY                        │
│ DEBUG_REPLAY_START_TIME: timestamp  │
│ Data: Historical data               │
│ Operation: Bounded (day-end exit)   │
│ Error Handling: Fail-fast           │
│ Output: reports_replay/ directory   │
└─────────────────────────────────────┘
```

### Configuration Validation Checklist

Before deployment, verify:

- [ ] All required data sources configured
- [ ] All notification channels working
- [ ] Alert thresholds set appropriately
- [ ] Profit targets sensible (1-5%)
- [ ] Stop losses sensible (0.5-3%)
- [ ] Output directories writable
- [ ] Time synchronization correct
- [ ] Resource limits appropriate

### Deployment Steps

1. **Install Dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Validate Configuration**
   ```
   python -m src.config.validator
   ```

3. **Test Data Connections**
   ```
   python -m src.data.connection_test
   ```

4. **Test Notifications**
   ```
   python -m src.notification.test_channels
   ```

5. **Start System**
   ```
   python -m src.stockreports.alert.symbol_alert_manager
   ```

6. **Verify Health**
   ```
   curl http://localhost:8000/health
   ```

---

## Troubleshooting Guide

### Common Issues & Solutions

#### Issue 1: No Alerts Generating

**Check 1: Data Fetching**
```
- Verify data provider is reachable
- Check network connectivity
- Review data provider logs
- Test with curl: curl https://data-provider-api/
```

**Check 2: Alert Configuration**
```
- Verify alert thresholds make sense (not 0%)
- Check approaches are enabled
- Verify symbols are in configuration
```

**Check 3: Time Synchronization**
```
- Compare server time with market time
- Verify not outside trading hours
- Check TimeSimulator configuration
```

#### Issue 2: Notification Failures

**Check 1: Channel Configuration**
```
- Verify SMTP settings for email
- Verify phone number for SMS
- Verify Ntfy endpoint URL
```

**Check 2: Channel Health**
```
- Test email: Send test email
- Test SMS: Send test SMS
- Test Ntfy: Curl to endpoint
```

**Check 3: Error Logs**
```
- Review notification error logs
- Check for rate limiting errors
- Check for authentication failures
```

#### Issue 3: High Latency (Slow Alerts)

**Check 1: Data Fetching**
```
- Measure time to fetch latest data
- Check network latency to data provider
- Look for data provider throttling
```

**Check 2: Analysis Processing**
```
- Profile executor performance
- Check for lock contention
- Verify executor algorithms efficient
```

**Check 3: System Resources**
```
- Check CPU utilization
- Check memory usage
- Check disk I/O
- Look for excessive context switching
```

#### Issue 4: System Crashes/Restarts

**Check 1: Memory**
```
- Monitor memory usage over time
- Check for memory leaks
- Look for unbounded data structures
```

**Check 2: Exceptions**
```
- Review exception logs for patterns
- Check for null pointer exceptions
- Look for timeout errors
```

**Check 3: Resource Limits**
```
- Check file descriptor limits
- Check disk space
- Check database connections
```

---

## Performance & Scalability

### Single Symbol Performance
- **Data Fetch:** 100-500ms per interval
- **Analysis:** 50-200ms for all approaches
- **Notification:** 100-1000ms (depends on channel)
- **Total Latency:** 300-1700ms (typically < 1 second)

### Multi-Symbol Scaling
- **1 Symbol:** 1x baseline latency
- **5 Symbols:** 1.2x baseline (parallelization helps)
- **20 Symbols:** 1.5-2x baseline
- **100 Symbols:** 2-3x baseline (thread pool limit reached)

### Bottleneck Analysis

1. **Data Fetching** (40% of time)
   - Network round-trip to data provider
   - Data parsing and normalization
   - Solutions: Caching, connection pooling

2. **Analysis/Execution** (30% of time)
   - Running 6+ alert approaches
   - Computing indicators and values
   - Solutions: Algorithm optimization, parallelization

3. **Notification** (20% of time)
   - Network calls to email/SMS providers
   - Solutions: Batching, connection pooling, async

4. **System Overhead** (10% of time)
   - Thread management, logging, file I/O

---

## Disaster Recovery

### Backup Strategy

- **Alert Files:** Backed up hourly
- **Configuration:** Version controlled in Git
- **Databases:** Daily incremental backups
- **Logs:** Archived daily, retained 30 days

### Recovery Time Objectives (RTO)

| Failure Type | Recovery Time |
|--------------|---------------|
| Single symbol failure | < 1 minute |
| Data provider failure | < 5 minutes (retry) |
| Notification channel failure | < 10 minutes |
| Complete system failure | < 30 minutes |
| Data loss | < 24 hours (from backup) |

### Failover Procedure

1. **Detect Failure**
   - Health check returns unhealthy
   - Manual monitoring alerts

2. **Stop Primary**
   ```
   kill -15 <process_id>
   ```

3. **Verify Backup Ready**
   - Check backup system status
   - Verify recent snapshot exists

4. **Switch Downstream Clients**
   - Redirect data to backup system
   - Update DNS if applicable

5. **Restart Primary**
   - Resolve issue
   - Restart monitoring
   - Verify health

---

## Compliance & Security

### Data Privacy
- Alert data stored locally in reports/
- No external data retention
- GDPR compliant (no personal data beyond email)

### Access Control
- Environment variable secrets (not in code)
- Role-based access to logs
- Audit trail of configuration changes

### Error Handling
- No sensitive data in error messages
- Safe exception logging
- Graceful degradation on failure

---

## FAQ - Operations Team

**Q: How do I add a new symbol?**
A: Add to symbols list in settings, restart monitoring.

**Q: How do I change alert thresholds?**
A: Modify price_alert_settings.py, changes apply to new alerts.

**Q: What if data provider is down?**
A: System retries automatically. Backups can be configured.

**Q: How do I test a new approach?**
A: Run in REPLAY mode first, then promote to LIVE.

**Q: Can I run multiple systems?**
A: Yes, with different symbol lists and output directories.

---

## Support & Escalation

- **Level 1:** Self-service troubleshooting (check logs, restart)
- **Level 2:** Health check analysis and configuration validation
- **Level 3:** Code review and performance optimization
- **Critical:** Immediate restart, notify on-call engineer
