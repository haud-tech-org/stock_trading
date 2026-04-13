# Layer 9: Operational Support - Tier 2 Reference

**Layer Number**: 9  
**Layer Name**: Operational Support  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding logging, errors, deployment, configuration, and CLI  

---

## 🎯 Layer Responsibility

Layer 9 provides **cross-cutting operational support** - structured logging, error recovery, configuration management, deployment infrastructure, and command-line interface. It spans the entire system.

**Key Concept**: Unified operational framework ensuring system reliability, observability, configurability, and operational excellence across all layers.

---

## 📖 Contents at This Layer

Currently, this layer has **no reference documentation files**. Operational support theory and architecture can be found in the parent Tier 2 directory.

| File | Purpose | Status |
|------|---------|--------|
| (No files) | Operational support cross-cutting concerns | Ready for documentation |

---

## 🏗️ Operational Support Subsystems

Layer 9 comprises **7 integrated operational subsystems**:

### 1️⃣ Web API & Health Checks
- **Purpose**: REST API endpoint for system health monitoring
- **Component**: Flask REST API (`src/stockreports/web.py`)
- **Endpoints**:
  - `GET /health` - System health status
  - Other monitoring endpoints
- **Use**: Integration with monitoring systems, load balancers, orchestrators
- **Monitoring**: Real-time health verification

### 2️⃣ Structured Logging
- **Purpose**: Consistent, contextual logging across all components
- **Component**: Log factory (`src/stockreports/utils/log_factory.py`)
- **Features**:
  - Per-symbol dedicated log files
  - Context-aware logging (symbol, layer, action)
  - Log levels: DEBUG, INFO, WARNING, ERROR
  - Structured format for parsing and analysis
- **Benefits**: Troubleshooting, audit trail, performance monitoring

### 3️⃣ Error Recovery & Resilience
- **Purpose**: Graceful handling of failures with automatic recovery
- **Component**: ThreadPoolExecutor with per-symbol isolation (`symbol_alert_manager.py`)
- **Features**:
  - Per-symbol error containment
  - Auto-restart on transient failures
  - LIVE mode: Indefinite retry with backoff
  - REPLAY mode: Deterministic failure exit
  - Circuit breaker patterns
- **Benefits**: System resilience, graceful degradation

### 4️⃣ Configuration Management
- **Purpose**: Flexible system configuration without code changes
- **Components**:
  - YAML/JSON configuration files
  - Environment variable overrides
  - Symbol-specific settings
  - Approach-resolution mappings
- **Features**:
  - Runtime validation
  - Hot reload capability
  - Per-environment configs (dev, staging, prod)
  - Default fallbacks

### 5️⃣ Deployment Infrastructure
- **Purpose**: Reliable, scalable deployment and infrastructure
- **Components**:
  - Dockerfile (Python 3.12-slim base)
  - Docker Compose (3 configurations)
  - Kubernetes manifests (optional scaling)
  - Procfile (process management)
- **Environments**:
  - Development: Single process, verbose logging
  - Staging: Multi-process, simulated load
  - Production: Scaled deployment, monitoring
- **Features**: Container orchestration, resource limits, auto-restart

### 6️⃣ Mode Switching
- **Purpose**: Support different execution modes (LIVE, REPLAY, etc.)
- **Components**: Mode configuration and control logic
- **Modes**:
  - **DEPLOYMENT (LIVE)**: Continuous production monitoring, indefinite, auto-restart
  - **DEVELOPMENT**: Sequential processing, verbose logging, fast iteration
  - **REPLAY**: Historical backtesting, deterministic, bounded execution
- **Features**: Mode selection via CLI, behavior differences per mode

### 7️⃣ Command-Line Interface (CLI)
- **Purpose**: System control and management from terminal
- **Component**: CLI framework (`src/stockreports/cli.py`)
- **Features**:
  - `--mode`: Select execution mode (DEPLOYMENT, DEVELOPMENT, REPLAY)
  - `--verbose`: Control logging verbosity
  - Symbol selection and filtering
  - Configuration override
- **Benefits**: Operational flexibility, debugging support

---

## 🔗 Layer Connections

Layer 9 is **cross-cutting** - it supports ALL other layers:

| Connected Layer | Purpose |
|-----------------|---------|
| Layer 1-8 | All layers use logging, config, error handling |
| Deployment | Infrastructure for all layers |
| Monitoring | Health checks for system observability |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Add logging, handle errors, use config system
- **Key Learning**: Structured logging and error recovery patterns
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_9 for how-to

### 🏗️ Architects
- **Use Case**: Design operational and deployment strategy
- **Key Learning**: Mode switching, deployment architecture
- **Next Step**: Review deployment infrastructure and scaling

### 🚀 Operations/DevOps
- **Use Case**: Deploy, monitor, and operate the system
- **Key Learning**: Container deployment, health checks, configuration
- **Must Read**: All operational support documentation
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_9 for detailed procedures

---

## 🚀 Quick Navigation by Use Case

### **"How do I start the system in production?"**
→ Use Docker/Kubernetes with DEPLOYMENT mode: `python -m src.stockreports.cli --mode DEPLOYMENT`

### **"Why is symbol X stuck?"**
→ Check structured logs for that symbol: `logs/symbol_X.log`

### **"Can I run the system offline for testing?"**
→ Yes - use REPLAY mode: `python -m src.stockreports.cli --mode REPLAY`

### **"How do I change system behavior?"**
→ Update configuration files (YAML/JSON) or use environment variables

### **"Is the system healthy?"**
→ Call health endpoint: `curl http://localhost:5000/health`

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **All Previous Layers**: Each layer uses operational support
- **Implementation Guide**: [IMPLEMENTATION_GUIDES Layer 9](../../../IMPLEMENTATION_GUIDES/LAYER_9_OPERATIONAL_SUPPORT/README.md)
- **Operations Guide**: [OPERATIONS_DEPLOYMENT_GUIDE.md](../../../IMPLEMENTATION_GUIDES/LAYER_9_OPERATIONAL_SUPPORT/OPERATIONS_DEPLOYMENT_GUIDE.md)
- **Troubleshooting**: [TROUBLESHOOTING_GUIDE.md](../../../IMPLEMENTATION_GUIDES/LAYER_9_OPERATIONAL_SUPPORT/TROUBLESHOOTING_GUIDE.md)

---

## 🔍 Key Concepts

**Structured Logging**: Consistent, contextual, per-symbol logging  
**Error Recovery**: Per-symbol isolation, auto-restart, graceful degradation  
**Configuration Management**: Flexible, validatable, environment-specific config  
**Deployment Infrastructure**: Docker, Kubernetes, scalable deployment  
**Mode Switching**: LIVE/REPLAY/DEVELOPMENT modes with different behaviors  
**Health Monitoring**: REST API health checks for observability  
**CLI Interface**: Terminal-based system control and debugging  

---

## 📖 Operational Subsystems Deep Dive

### Web API & Health Checks
- Flask REST API providing system health endpoint
- Real-time health status for monitoring systems
- Integration with Kubernetes liveness probes
- Extensible for custom health metrics

### Structured Logging
- Factory pattern for consistent log creation
- Per-symbol dedicated log files
- Context tracking (symbol, layer, action)
- Structured format enabling machine parsing

### Error Recovery & Resilience
- ThreadPoolExecutor for concurrent execution
- Per-symbol error isolation
- Auto-restart with exponential backoff (LIVE mode)
- Graceful exit on error (REPLAY mode)

### Configuration Management
- YAML/JSON-based configuration
- Environment variable overrides
- Runtime validation with defaults
- Hot reload without restart

### Deployment Infrastructure
- Container-based deployment (Docker)
- Multi-environment support
- Kubernetes for scaling
- Resource limits and monitoring

### Mode Switching
- CLI-based mode selection
- Behavior differences per mode
- Logging level changes
- Deterministic vs indefinite execution

### Command-Line Interface
- Python Click/Argparse-based CLI
- Mode selection (DEPLOYMENT, DEVELOPMENT, REPLAY)
- Verbosity control
- Symbol filtering and configuration

---

## � Provider Resource Management (Monitoring Integration)

**Layer 5 → Layer 9 Integration:** Data providers use context managers to ensure reliable operation within the monitoring system.

### Connection Lifecycle Management

**Problem Solved:** Connection timeouts in 57-second monitoring cycle
- **Before:** Connections reused indefinitely → 1-2 hour timeout ❌
- **After:** Fresh connection every cycle → 24+ hour reliability ✅

### Context Manager Pattern

All data providers implement Python's context manager protocol:

```python
with provider:
    # Fresh connection on entry
    data = provider.fetch_ohlcv(symbol, ...)
# Automatic cleanup on exit - guaranteed! ✅
```

**Operational Benefits:**
1. **Reliability**: No connection timeouts after extended operation
2. **Resource Safety**: No accumulated open connections (no memory leak)
3. **Error Resilience**: Cleanup happens even if exception occurs
4. **Monitoring Loop**: 57-second cycle with fresh connections proven for 24+ hours

### Resource Monitoring

**What to Monitor:**
- Active connections count (should spike/drop with each cycle)
- Memory usage (should remain stable, not grow)
- Provider error logs (should be clean, no timeout errors)
- Connection state (should show cycles of open/close)

**Healthy Indicators:**
- ✅ Connections: 0 → 1 → 0 every 57 seconds
- ✅ Memory: ±5MB variance (no growth trend)
- ✅ Logs: No "Connection reset" or "Broken pipe" after 1+ hour
- ✅ Operation: 24+ hours without timeout

**Operational Commands:**
```bash
# Monitor active connections
watch -n 1 "netstat -an | grep ESTABLISHED | grep -E ':(443|8080)' | wc -l"

# Check memory usage
ps aux | grep stockreports

# Check logs for provider issues
tail -f logs/symbol_*.log | grep -i "connection\|timeout\|error"
```

### Troubleshooting Provider Resource Issues

**Symptom:** System times out after 1-2 hours

**Root Cause:** Providers not using context managers properly

**Check:**
```python
# ❌ Wrong - no context manager
provider = get_provider(symbol)
data = provider.fetch_ohlcv(symbol, ...)

# ✅ Correct - with context manager
provider = get_provider(symbol)
with provider:
    data = provider.fetch_ohlcv(symbol, ...)
```

**Solution:** Ensure all provider usage wraps in `with provider:` block

**Symptom:** Growing connection count, memory leak

**Root Cause:** Context managers not calling close() properly

**Check:**
- Provider's `close()` method implemented
- `__exit__()` calls `close()` (should inherit from BaseDataProvider)
- Exception handling in `close()` (shouldn't crash if already closed)

**Solution:** Review provider's close() implementation against CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md

### Related Documentation

For detailed information on provider resource management:
- **Architecture**: [LAYER_5_DATA_SERVICES/DATA_LAYER_ARCHITECTURE.md](../LAYER_5_DATA_SERVICES/DATA_LAYER_ARCHITECTURE.md) - Resource Management section
- **Implementation**: [LAYER_5_DATA_SERVICES/CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md](../LAYER_5_DATA_SERVICES/CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md) - Step-by-step implementation
- **Operations**: [LAYER_5_DATA_SERVICES/PROVIDER_RESOURCE_LIFECYCLE.md](../LAYER_5_DATA_SERVICES/PROVIDER_RESOURCE_LIFECYCLE.md) - Comprehensive operational guide

---

## �📞 Need More Information?

- **How to add logging**: See IMPLEMENTATION_GUIDES/LAYER_9
- **Error handling patterns**: See IMPLEMENTATION_GUIDES/LAYER_9
- **Configuration system**: See IMPLEMENTATION_GUIDES/LAYER_9
- **Deployment procedures**: See OPERATIONS_DEPLOYMENT_GUIDE.md
- **Troubleshooting issues**: See TROUBLESHOOTING_GUIDE.md
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 10, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
