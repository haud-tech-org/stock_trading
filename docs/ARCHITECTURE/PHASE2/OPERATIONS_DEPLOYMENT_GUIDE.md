# Operations and Deployment Guide - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Codebase Analysis  
**Audience:** DevOps and System Administrators  
**Prerequisites:** Phase 1 architecture understanding  

---

## Overview

This guide documents the ACTUAL deployment infrastructure for the stock alerting system, including Docker configuration, Kubernetes manifests, configuration management, and health monitoring.

---

## Docker Deployment

### Dockerfile

**Location:** `/Dockerfile` (50 lines)

**What it does:**
```dockerfile
FROM python:3.12-slim-bookworm

# System dependencies for scientific computing
RUN apt-get update && apt-get install -y \
    build-essential \
    gfortran \
    libatlas-base-dev

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Key setting: Detect when running in Docker
ENV DOCKER_CONTAINER=true

# Run Flask web API
CMD ["python", "-m", "src.stockreports.web"]
```

**Key Points:**
- Python 3.12 slim image
- Scientific packages: gfortran, libatlas (for numpy, scipy, pandas)
- Credentials are injected at runtime (NOT in image)
- DOCKER_CONTAINER env var enables automatic detection
- Runs Flask web service on startup

### Docker Compose - Development

**File:** `/docker-compose.yml` (113 lines)

**Configuration:**
```yaml
version: '3.8'

services:
  stock-alerter:
    build:
      context: .
      dockerfile: Dockerfile
    
    # Credentials from .env file (local development only)
    env_file:
      - .env
    
    # All 6 settings modules + 3 notification channels
    environment:
      DOCKER_CONTAINER: "true"
      
      # Email (optional)
      EMAIL_ENABLED: "${EMAIL_ENABLED:-false}"
      EMAIL_SENDER: "${EMAIL_SENDER:-}"
      EMAIL_APP_PASSWORD: "${EMAIL_APP_PASSWORD:-}"
      EMAIL_RECEIVERS: "${EMAIL_RECEIVERS:-}"
      
      # SMS via Twilio (optional)
      TWILIO_ENABLED: "${TWILIO_ENABLED:-false}"
      TWILIO_ACCOUNT_SID: "${TWILIO_ACCOUNT_SID:-}"
      TWILIO_AUTH_TOKEN: "${TWILIO_AUTH_TOKEN:-}"
      TWILIO_PHONE_NUMBER: "${TWILIO_PHONE_NUMBER:-}"
      
      # Ntfy notifications (optional)
      NTFY_ENABLED: "${NTFY_ENABLED:-false}"
      NTFY_TOPICS: "${NTFY_TOPICS:-}"
    
    container_name: stock-alerter-app
    restart: unless-stopped
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '8'        # Hard cap
          memory: 4096M    # OOM threshold
        reservations:
          cpus: '4'        # Guaranteed minimum
          memory: 2048M    # Guaranteed minimum
    
    ports:
      - "5000:5000"
    
    volumes:
      - ./src:/app/src      # Hot reload
      - ./logs:/app/logs    # Persistent logs
```

**Resource Allocation Guidance:**
- **Development:** 1 CPU / 512M RAM (1-2 symbols)
- **Staging:** 2 CPUs / 1024M RAM (3-5 symbols)
- **Production:** 4 CPUs / 2048M RAM (5-10 symbols)
- **Enterprise:** 8 CPUs / 4096M RAM (10+ symbols, sharding recommended)

### Docker Compose - Staging/Production

**File:** `/docker-compose.staging.yml` and `/docker-compose.production.yml`

**Key differences:**
```yaml
# Staging: Continuous testing, moderate resources
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1024M
    reservations:
      cpus: '1'
      memory: 512M

# Production: Live trading, maximum reliability
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 2048M
    reservations:
      cpus: '2'
      memory: 1024M

# Credentials via secrets (not .env file)
env_file: []  # Do NOT use .env in production
```

---

## Kubernetes Deployment

### Manifest Structure

**File:** `/kubernetes-manifests.yaml` (420 lines)

**Three Components:**

#### 1. Kubernetes Secret

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: stock-alerter-secrets
  namespace: stock-alerter

type: Opaque

stringData:
  # Email Credentials
  EMAIL_SENDER: "your-email@gmail.com"
  EMAIL_APP_PASSWORD: "xxxx xxxx xxxx xxxx"
  EMAIL_SENDER_DISPLAY_NAME: "Stock Alerter (No-Reply)"
  
  # SMS Credentials (Twilio)
  TWILIO_ACCOUNT_SID: "ACxxxxxxxxxxxxxxxxxx"
  TWILIO_AUTH_TOKEN: "your_auth_token_here"
  TWILIO_PHONE_NUMBER: "+1234567890"
  SMS_RECEIVER_PHONE_NUMBER: "+84983794189"
```

**Create with:**
```bash
kubectl create secret generic stock-alerter-secrets \
  --from-literal=EMAIL_SENDER="haud.tech@gmail.com" \
  --from-literal=EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" \
  -n stock-alerter
```

#### 2. Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: stock-alerter-config
  namespace: stock-alerter

data:
  # Non-sensitive configuration
  EMAIL_ENABLED: "true"
  EMAIL_RECEIVERS: "recipient@example.com"
  
  NTFY_ENABLED: "false"
  NTFY_TOPICS: "vn30_alerts_f8a9b2c1"
  
  TWILIO_ENABLED: "false"
```

#### 3. Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-alerter
  namespace: stock-alerter

spec:
  replicas: 1
  
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  
  template:
    spec:
      containers:
      - name: stock-alerter
        image: stock-alerter:latest
        
        # Port: Flask web service
        ports:
        - name: web
          containerPort: 5000
        
        # ConfigMap: non-sensitive values
        envFrom:
        - configMapRef:
            name: stock-alerter-config
        
        # Secret: sensitive credentials via secretKeyRef
        env:
        - name: EMAIL_SENDER
          valueFrom:
            secretKeyRef:
              name: stock-alerter-secrets
              key: EMAIL_SENDER
        
        - name: EMAIL_APP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: stock-alerter-secrets
              key: EMAIL_APP_PASSWORD
        
        # ... (all other secret fields)
        
        # Health checks
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        
        readinessProbe:
          httpGet:
            path: /ready
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
        
        # Resource requests and limits
        resources:
          requests:
            cpu: 2
            memory: 1024Mi
          limits:
            cpu: 4
            memory: 2048Mi
```

### Deploying to Kubernetes

```bash
# 1. Create namespace
kubectl create namespace stock-alerter

# 2. Create secrets
kubectl create secret generic stock-alerter-secrets \
  --from-literal=EMAIL_SENDER="your-email@gmail.com" \
  --from-literal=EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" \
  -n stock-alerter

# 3. Apply manifests
kubectl apply -f kubernetes-manifests.yaml

# 4. Check deployment
kubectl get pods -n stock-alerter
kubectl logs -f deployment/stock-alerter -n stock-alerter

# 5. Expose service
kubectl expose deployment stock-alerter \
  --type=LoadBalancer \
  --port=5000 \
  -n stock-alerter
```

---

## Configuration System

### Architecture

**File:** `/src/stockreports/config/loader.py` (50 lines)

**What it does:**
```python
def load_config():
    """Dynamically reloads all settings modules at startup."""
    importlib.reload(settings_module)
    importlib.reload(signal_settings_module)
    importlib.reload(notification_settings_module)
    importlib.reload(validation_settings_module)
    importlib.reload(price_alert_settings_module)
    importlib.reload(data_provider_settings_module)

def get_settings():
    """Returns the currently loaded settings module."""
    return settings_module

def get_signal_settings():
    """Returns the currently loaded signal settings module."""
    return signal_settings_module

# ... (getters for each settings module)
```

### 6 Settings Modules

All loaded in `/src/stockreports/config/`:

#### 1. `settings.py` - Main Configuration
```python
# Symbol configuration
SYMBOLS = ["VN30F1M", "VN30"]
IMPACT_SYMBOLS = ["VIC", "VHM"]

# API configuration
API_BASE_URL = "https://api.vietstock.vn/tvnew/history"
API_PARAMS = {"resolution": "1"}

# Monitoring
MONITORING_INTERVAL_SECONDS = 57

# Data processing features
DATA_PROCESSING = {
    "timezone_conversion": True,
    "price_adjustment": True,
}
```

#### 2. `signal_settings.py` - Alert Configuration
```python
# Alert strategy configuration
# Defines thresholds for various alert types
# Loaded by approach executors
```

#### 3. `notification_settings.py` - Notification Configuration
```python
# Email setup
EMAIL_ENABLED = True
EMAIL_SENDER = "your-email@gmail.com"
EMAIL_APP_PASSWORD = "xxxx xxxx xxxx xxxx"
EMAIL_RECEIVERS = ["recipient@example.com"]

# SMS setup (Twilio)
TWILIO_ENABLED = False
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token_here"
TWILIO_PHONE_NUMBER = "+1234567890"

# Ntfy setup
NTFY_ENABLED = False
NTFY_TOPICS = ["vn30_alerts"]
```

#### 4. `validation_settings.py` - Threshold Configuration
```python
# Profit/loss thresholds for scenario testing
VALIDATION_PRICE_THRESHOLD_PROFIT = [1.0, 1.5, 2.0, 2.5, 3.0]
VALIDATION_PRICE_THRESHOLD_LOSS = [-0.5, -1.0, -1.5, -2.0]
```

#### 5. `price_alert_settings.py` - Price Level Configuration
```python
# Price level monitoring settings
# Used by PriceMovementAlerter
```

#### 6. `data_provider_settings.py` - Data Source Configuration
```python
# Which data providers to use
# Configuration for Vietstock, Binance, etc.
```

### Loading Configuration at Startup

```python
# In main application startup
from src.stockreports.config.loader import load_config, get_settings

# Load all modules once
load_config()

# Access settings throughout application
settings = get_settings()
print(settings.SYMBOLS)  # ["VN30F1M", "VN30"]
```

### Credentials Management

**Three Levels of Priority:**

1. **Environment Variables** (highest)
   ```bash
   export EMAIL_SENDER="user@example.com"
   export EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"
   ```

2. **Kubernetes Secrets** (via secretKeyRef)
   ```yaml
   env:
   - name: EMAIL_SENDER
     valueFrom:
       secretKeyRef:
         name: stock-alerter-secrets
         key: EMAIL_SENDER
   ```

3. **Docker .env file** (lowest - development only)
   ```bash
   EMAIL_SENDER=user@example.com
   EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
   ```

**File:** `/src/stockreports/config/secrets_loader.py`
```python
def load_secrets():
    """Load secrets from environment (Docker, K8s, or system)."""
    email_sender = os.getenv('EMAIL_SENDER')
    email_password = os.getenv('EMAIL_APP_PASSWORD')
    
    # Secrets are loaded from:
    # - Kubernetes secretKeyRef (production)
    # - Docker environment (staging)
    # - .env file (development)
```

---

## Health Checks

### Web Service Health Endpoints

**File:** `/src/stockreports/web/` (Flask application)

```python
@app.route('/health')
def health():
    """
    Liveness probe - Is the service running?
    
    Returns 200 if service is alive, regardless of dependencies.
    """
    return {"status": "alive"}, 200

@app.route('/ready')
def ready():
    """
    Readiness probe - Is the service ready to handle requests?
    
    Checks:
    - Database connectivity
    - Data provider connectivity
    - Configuration loaded
    - Required credentials available
    
    Returns 200 if all dependencies are ready.
    """
    checks = {
        "config": check_config_loaded(),
        "data_provider": check_data_provider_connected(),
        "notifications": check_notification_config(),
    }
    
    if all(checks.values()):
        return {"status": "ready", "checks": checks}, 200
    else:
        return {"status": "not_ready", "checks": checks}, 503
```

### Kubernetes Probes Configuration

```yaml
containers:
- name: stock-alerter
  
  # Liveness Probe: Is container alive?
  livenessProbe:
    httpGet:
      path: /health
      port: 5000
    initialDelaySeconds: 30    # Wait 30s before first check
    periodSeconds: 10          # Check every 10s
    timeoutSeconds: 5          # Timeout after 5s
    failureThreshold: 3        # Kill after 3 failures
  
  # Readiness Probe: Can it handle traffic?
  readinessProbe:
    httpGet:
      path: /ready
      port: 5000
    initialDelaySeconds: 10    # Wait 10s before first check
    periodSeconds: 5           # Check every 5s
    timeoutSeconds: 3          # Timeout after 3s
    failureThreshold: 2        # Remove from LB after 2 failures
```

---

## Logging System

### Log Factory

**File:** `/src/stockreports/utils/log_factory.py`

```python
class LogFactory:
    """Create configured loggers for application components."""
    
    @staticmethod
    def create_logger(name: str) -> logging.Logger:
        """
        Create a logger with:
        - Console output (development)
        - File rotation (production)
        - Structured format
        - Component-based filtering
        """
        logger = logging.getLogger(name)
        
        # Handler: Console (stdout)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # Handler: File rotation (production)
        if os.getenv('DOCKER_CONTAINER'):
            file_handler = RotatingFileHandler(
                'logs/app.log',
                maxBytes=10485760,    # 10MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
        
        logger.addHandler(console_handler)
        return logger
```

### Logging Output

```bash
# Console format
2026-04-08 14:23:45,123 | INFO | SymbolAlerter | VN30F1M alert detected

# File rotation
logs/app.log               # Current log
logs/app.log.1             # First rotation
logs/app.log.2             # Second rotation
```

### Enable Debug Logging

```python
# In settings
LOG_LEVEL = "DEBUG"

# Or via environment
export LOG_LEVEL=DEBUG
```

---

## Environment Variables Reference

### All Settings

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `DOCKER_CONTAINER` | No | False | Detect Docker environment |
| `SYMBOLS` | Yes | None | Stock symbols to monitor |
| `IMPACT_SYMBOLS` | No | [] | High-impact symbols |
| `API_BASE_URL` | Yes | vietstock.vn | Data source URL |
| `MONITORING_INTERVAL_SECONDS` | No | 57 | Check frequency |
| `EMAIL_ENABLED` | No | false | Enable email notifications |
| `EMAIL_SENDER` | If EMAIL | None | Sender email address |
| `EMAIL_APP_PASSWORD` | If EMAIL | None | Gmail app password |
| `EMAIL_RECEIVERS` | If EMAIL | None | Recipient emails |
| `TWILIO_ENABLED` | No | false | Enable SMS notifications |
| `TWILIO_ACCOUNT_SID` | If SMS | None | Twilio account ID |
| `TWILIO_AUTH_TOKEN` | If SMS | None | Twilio token |
| `TWILIO_PHONE_NUMBER` | If SMS | None | Sender phone |
| `SMS_RECEIVER_PHONE_NUMBER` | If SMS | None | Recipient phone |
| `NTFY_ENABLED` | No | false | Enable Ntfy notifications |
| `NTFY_TOPICS` | If NTFY | None | Ntfy topics |

### Setting Priority

**Docker Compose (Development):**
1. Environment variables (highest)
2. `.env` file
3. Hardcoded defaults in settings.py

**Kubernetes (Production):**
1. secretKeyRef (Kubernetes Secrets)
2. configMapRef (ConfigMap)
3. Hardcoded defaults

---

## Deployment Checklist

### Pre-Deployment

- [ ] Configure all required settings files
- [ ] Set notification credentials
- [ ] Set data provider API URLs
- [ ] Configure monitoring interval
- [ ] Set profit/loss thresholds
- [ ] Review resource allocations
- [ ] Verify Docker image builds
- [ ] Test locally with docker-compose

### Docker Deployment

```bash
# 1. Build image
docker build -t stock-alerter:latest .

# 2. Start with Docker Compose
docker-compose -f docker-compose.production.yml up -d

# 3. Monitor logs
docker logs -f stock-alerter-app

# 4. Verify health
curl http://localhost:5000/health
curl http://localhost:5000/ready
```

### Kubernetes Deployment

```bash
# 1. Create namespace
kubectl create namespace stock-alerter

# 2. Create secrets
kubectl create secret generic stock-alerter-secrets \
  --from-literal=EMAIL_SENDER="..." \
  -n stock-alerter

# 3. Apply manifests
kubectl apply -f kubernetes-manifests.yaml

# 4. Verify deployment
kubectl get pods -n stock-alerter
kubectl describe pod stock-alerter -n stock-alerter

# 5. Monitor logs
kubectl logs -f deployment/stock-alerter -n stock-alerter

# 6. Check readiness
kubectl exec stock-alerter-xxx -- curl http://localhost:5000/ready
```

### Post-Deployment

- [ ] Verify health endpoints responding
- [ ] Check logs for errors
- [ ] Test alert generation
- [ ] Verify notifications working
- [ ] Monitor resource usage
- [ ] Check data provider connectivity
- [ ] Confirm all symbols loading

---

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs stock-alerter-app

# Common issues:
# 1. Missing required credentials
docker-compose config | grep EMAIL_SENDER

# 2. Port already in use
sudo lsof -i :5000

# 3. Insufficient resources
docker stats stock-alerter-app
```

### Health Check Failing

```bash
# Check readiness
curl -v http://localhost:5000/ready

# Check configuration loaded
docker exec stock-alerter-app python3 -c \
  "from src.stockreports.config.loader import load_config; load_config(); print('OK')"
```

### Kubernetes Pod CrashLooping

```bash
# Check events
kubectl describe pod stock-alerter-xxx -n stock-alerter

# Check logs
kubectl logs -p stock-alerter-xxx -n stock-alerter

# Common issues:
# 1. Secret not found
kubectl get secrets -n stock-alerter

# 2. Image pull error
kubectl describe pod stock-alerter-xxx | grep -i pull

# 3. Resource quota exceeded
kubectl describe quota -n stock-alerter
```

---

## Scaling Considerations

### Vertical Scaling (More Resources)

For more symbols, increase container resources:

```yaml
# Production: 5-10 symbols
resources:
  requests:
    cpu: 4
    memory: 2048Mi
  limits:
    cpu: 8
    memory: 4096Mi

# Enterprise: 10+ symbols
resources:
  requests:
    cpu: 8
    memory: 4096Mi
  limits:
    cpu: 16
    memory: 8192Mi
```

### Horizontal Scaling (Multiple Instances)

For very high volume, consider sharding:

```yaml
# Shard 1: Symbols A-M
replicas: 2
env:
  SYMBOLS: ["VN30F1M", "VN30", "VIC"]

# Shard 2: Symbols N-Z
replicas: 2
env:
  SYMBOLS: ["VHM", "KDH"]

# Each shard runs independently
```

---

**Status:** Based on Actual Codebase  
**Date:** April 8, 2026  
**Verified:** Docker (50 lines), K8s (420 lines), Config (6 modules)  
**Ready:** Yes
