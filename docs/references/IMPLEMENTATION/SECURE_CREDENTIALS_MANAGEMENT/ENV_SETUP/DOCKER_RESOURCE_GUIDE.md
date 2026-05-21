# Docker Resource Configuration Guide
## Quick Reference for Stock Trading Alert System

**Status:** March 15, 2026  
**Deep Analysis Location:** `DOCKER_RESOURCE_ANALYSIS.md`

---

## 🎯 Quick Decision Matrix

Choose your configuration based on your use case:

| Use Case | CPU | Memory | File | Symbols | Uptime | Cost |
|----------|-----|--------|------|---------|--------|------|
| **Development** | 1 | 512 MB | Current | 1-2 | 95% | $$ |
| **Staging/CI** | 2 | 1 GB | `.staging.yml` | 3-5 | 99.5% | $$$ |
| **Production** | 4 | 2 GB | `.production.yml` | 8-10 | 99.9% | $$$$ |
| **Enterprise** | 8 | 4 GB | Custom | 20+ | 99.95% | $$$$$ |

---

## 🚀 Quick Start

### For Development (Local Testing)

```bash
# Use default configuration
docker-compose up -d

# Monitor resources
docker stats stock-alerter

# View logs
docker-compose logs -f stock-alerter
```

**Expected Resources:**
- CPU: 20-40% utilization
- Memory: 330-350 MB usage
- Safe for: 1-2 symbols

---

### For Staging/CI Testing

```bash
# Use staging override
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Monitor with health check
docker-compose ps
```

**Expected Resources:**
- CPU: 50-70% utilization
- Memory: 450-500 MB usage
- Safe for: 3-5 symbols
- Better for: continuous integration testing

---

### For Production Deployment

```bash
# Use production override
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d

# Monitor system
watch docker stats stock-alerter

# View structured logs
docker-compose logs --tail=100 -f stock-alerter
```

**Expected Resources:**
- CPU: 50-70% utilization
- Memory: 500-600 MB usage
- Safe for: 8-10 symbols
- Recommended for: live trading 24/5

---

## 🔍 Monitoring Commands

### Check Current Resource Usage

```bash
# Real-time resource statistics
docker stats stock-alerter

# Format: CPU% | Memory Usage / Limit | Memory% | Network I/O | Block I/O | PIDs
```

### Check Container Health

```bash
# View health status
docker inspect stock-alerter | grep -A 5 '"Health"'

# Restart unhealthy container
docker-compose restart stock-alerter
```

### View Memory Breakdown

```bash
# Run memory analysis
docker exec stock-alerter python -c "
import psutil
import os
p = psutil.Process(os.getpid())
m = p.memory_info()
print(f'RSS: {m.rss/1024/1024:.1f} MB')
print(f'VMS: {m.vms/1024/1024:.1f} MB')
"
```

### Check Active Threads

```bash
# View thread count
docker exec stock-alerter python -c "
import threading
import logging
logging.basicConfig(level=logging.INFO)
print(f'Active threads: {threading.active_count()}')
for t in threading.enumerate():
    print(f'  - {t.name}')
"
```

---

## ⚠️ Troubleshooting

### Issue: Container exits with OOM

**Symptom:** `docker-compose ps` shows container crashed

**Diagnosis:**
```bash
docker-compose logs | grep -i "oom\|killed\|memory"
```

**Solution:**
- Increase memory limit
- Use production configuration (2 GB instead of 512 MB)
- Reduce number of symbols
- Implement cache limits

### Issue: Slow Alert Processing

**Symptom:** Monitoring cycle takes >5 seconds

**Diagnosis:**
```bash
# Check CPU usage
docker stats --no-stream stock-alerter

# Check thread count
docker exec stock-alerter python -c "import threading; print(threading.active_count())"
```

**Solution:**
- Increase CPU allocation
- Use staging/production configuration
- Reduce logging verbosity
- Profile to find bottleneck

### Issue: High Memory Usage (But No Crash)

**Symptom:** Memory usage approaching limit but container running

**Diagnosis:**
```bash
# Check if cache is growing
docker exec stock-alerter python -c "
from src.stockreports.utils.historical_data_manager import _data_cache
print(f'Cache entries: {len(_data_cache)}')
for key, df in list(_data_cache.items())[:5]:
    print(f'{key}: {len(df)} rows, {df.memory_usage(deep=True).sum()/1024/1024:.1f} MB')
"
```

**Solution:**
- Implement cache size limits (see DOCKER_RESOURCE_ANALYSIS.md)
- Enable garbage collection tuning
- Monitor memory trends

### Issue: Container Fails Health Check

**Symptom:** Health status shows "unhealthy"

**Diagnosis:**
```bash
docker-compose ps
docker-compose logs stock-alerter
```

**Solution:**
- Check environment variables loaded correctly
- Verify credentials are accessible
- Increase health check timeout (production.yml)
- Check for memory pressure

---

## 📊 Resource Allocation Formula

For N symbols, recommended resources:

```
Memory = 250 MB (base) + (3 MB × N) + 150 MB (buffer)
CPU = ceil(N / 2) or 1, whichever is higher

Examples:
- 1 symbol:  ~403 MB memory, 1 CPU
- 3 symbols: ~409 MB memory, 2 CPU
- 5 symbols: ~415 MB memory, 2 CPU
- 10 symbols: ~430 MB memory, 4 CPU
```

---

## 🔧 Configuration Files

### docker-compose.yml (Base)
- **Symbols:** 1-2
- **CPU:** 1 core
- **Memory:** 512 MB
- **Use:** Local development

### docker-compose.staging.yml
- **Symbols:** 3-5
- **CPU:** 2 cores
- **Memory:** 1 GB
- **Use:** CI/CD, testing
- **Apply:** `-f docker-compose.staging.yml`

### docker-compose.production.yml
- **Symbols:** 8-10
- **CPU:** 4 cores
- **Memory:** 2 GB
- **Use:** Live trading
- **Apply:** `-f docker-compose.production.yml`

---

## 🎬 Deployment Examples

### Development Setup

```bash
# Terminal 1: Start container
docker-compose up

# Terminal 2: Monitor resources
watch docker stats stock-alerter

# Test with single symbol
docker-compose exec stock-alerter \
  python -m src.stockreports.cli --symbols AAPL --mode backtest
```

### Staging Setup

```bash
# Build and start with staging config
docker-compose -f docker-compose.yml -f docker-compose.staging.yml build
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d

# Run integration tests
docker-compose exec stock-alerter pytest tests/ -v

# Monitor
docker-compose logs -f stock-alerter
```

### Production Deployment

```bash
# Deploy with production config
docker-compose -f docker-compose.yml -f docker-compose.production.yml up -d

# Verify health
docker-compose exec stock-alerter \
  python -c "from src.stockreports.config.secrets_loader import SecretsLoader; \
  loader = SecretsLoader(); \
  print(f'Environment: {loader.env_type}')"

# Monitor continuously
docker stats stock-alerter
```

---

## 📈 Scaling Guidelines

### Horizontal Scaling (Multiple Containers)

If you need more than 10 symbols:

```yaml
# docker-compose.large-scale.yml
version: '3.8'

services:
  stock-alerter-1:
    # symbols: AAPL, GOOGL, MSFT (3 symbols)
    # resources: 2 CPU, 1 GB
    
  stock-alerter-2:
    # symbols: AMZN, TSLA, META (3 symbols)
    # resources: 2 CPU, 1 GB
    
  stock-alerter-3:
    # symbols: NVDA, AMD, INTC (3 symbols)
    # resources: 2 CPU, 1 GB
    
  notification-service:
    # Central notification aggregator
    # resources: 1 CPU, 512 MB
```

**Benefits:**
- Distribute load across containers
- Isolate symbol processing
- Better fault isolation
- Easier to scale individual clusters

### Kubernetes Deployment

For containerized production:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-alerter
spec:
  replicas: 3  # Run 3 instances for HA
  selector:
    matchLabels:
      app: stock-alerter
  template:
    metadata:
      labels:
        app: stock-alerter
    spec:
      containers:
      - name: stock-alerter
        image: stock-alerter:latest
        resources:
          requests:
            memory: "1Gi"
            cpu: "2"
          limits:
            memory: "2Gi"
            cpu: "4"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "from src.stockreports.config.secrets_loader import SecretsLoader; SecretsLoader()"
          initialDelaySeconds: 60
          periodSeconds: 30
```

---

## 📋 Resource Limits Explanation

### CPU Limits vs Reservations

```yaml
deploy:
  resources:
    limits:
      cpus: '4'        # Hard cap - container never uses more
    reservations:
      cpus: '2'        # Soft guarantee - system tries to reserve
```

- **Limit:** Maximum allowed CPU (hard stop)
- **Reservation:** Minimum guaranteed CPU (soft requirement)

### Memory Limits vs Reservations

```yaml
deploy:
  resources:
    limits:
      memory: 2048M    # Hard cap - OOM kill if exceeded
    reservations:
      memory: 1024M    # Soft guarantee - system tries to reserve
```

- **Limit:** Maximum allowed memory (process killed if exceeded)
- **Reservation:** Minimum guaranteed memory (system reserves)

---

## 🎓 Capacity Planning

### Calculate Resources for Your Symbols

1. **Count your symbols:** How many stocks to monitor?
   ```
   N = ____ symbols
   ```

2. **Apply formula:**
   ```
   Memory = 250 + (3 × N) + 150 MB
   CPU = ceil(N / 2) or 1
   ```

3. **Round up for safety:**
   ```
   Memory: Round up to nearest 512 MB
   CPU: Round up to nearest 0.5 cores
   ```

4. **Example: 7 symbols**
   ```
   Memory = 250 + (3 × 7) + 150 = 521 MB → 1 GB
   CPU = ceil(7 / 2) = 4 → 4 cores
   → Allocate: 4 CPU, 1-2 GB
   ```

---

## 📞 Support & Documentation

- **Detailed Analysis:** See `DOCKER_RESOURCE_ANALYSIS.md`
- **System Architecture:** See `docs/ARCHITECTURE/`
- **Environment Setup:** See `docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENVIRONMENT_SETUP_GUIDE.md`
- **Credentials:** See `docs/SECURE_CREDENTIALS_MANAGEMENT.md`

---

## ✅ Checklist for Deployment

### Before Going to Production

- [ ] Read `DOCKER_RESOURCE_ANALYSIS.md` for detailed analysis
- [ ] Test with staging config for 1 week
- [ ] Monitor memory trends over time
- [ ] Verify all credentials load correctly
- [ ] Test with production symbol count
- [ ] Set up monitoring/alerting
- [ ] Document your symbol configuration
- [ ] Plan scaling strategy if symbols grow

### Regular Monitoring

- [ ] Check `docker stats` daily
- [ ] Review logs for errors/warnings
- [ ] Monitor memory usage trends
- [ ] Verify all alerts sending successfully
- [ ] Test failover/restart scenarios
- [ ] Update documentation as you scale

---

**Questions?** Review `DOCKER_RESOURCE_ANALYSIS.md` for comprehensive technical details.
