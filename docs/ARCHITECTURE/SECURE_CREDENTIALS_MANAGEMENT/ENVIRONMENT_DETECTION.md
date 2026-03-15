# Secure Credentials Management - Environment Detection Architecture

## 🎯 Purpose

This document explains **how** the system automatically detects the deployment environment without requiring manual configuration or environment-specific code branches.

---

## 🌍 Supported Environments

The system recognizes and adapts to these deployment scenarios:

| Environment | Detection Signal | Use Case |
|-------------|------------------|----------|
| **LOCAL** | No cloud signals detected | Development on developer machine |
| **DOCKER** | `/.dockerenv` exists OR `DOCKER_CONTAINER=true` | Docker container deployment |
| **KUBERNETES** | `KUBERNETES_SERVICE_HOST` env var | Kubernetes cluster orchestration |
| **AZURE** | `AZURE_KEYVAULT_URL` env var | Microsoft Azure (ACI, App Service, etc.) |
| **GCP** | `GOOGLE_CLOUD_PROJECT` env var | Google Cloud Platform (Cloud Run, Compute Engine, etc.) |

---

## 🔍 Detection Algorithm

```python
def _detect_environment(self) -> None:
    """
    Automatically detect deployment environment by checking for 
    environment-specific signals in a priority order.
    """
    
    # Step 1: Check for Azure
    if os.getenv('AZURE_KEYVAULT_URL'):
        self.environment_type = EnvironmentType.AZURE
        return
    
    # Step 2: Check for Google Cloud
    if os.getenv('GOOGLE_CLOUD_PROJECT'):
        self.environment_type = EnvironmentType.GCP
        return
    
    # Step 3: Check for Kubernetes
    if os.getenv('KUBERNETES_SERVICE_HOST'):
        self.environment_type = EnvironmentType.KUBERNETES
        return
    
    # Step 4: Check for Docker
    if (Path('/.dockerenv').exists() or 
        os.getenv('DOCKER_CONTAINER') == 'true'):
        self.environment_type = EnvironmentType.DOCKER
        return
    
    # Step 5: Default to Local
    self.environment_type = EnvironmentType.LOCAL
```

---

## 🎯 Detection Signals Explained

### Azure Detection
```bash
Environment Variable: AZURE_KEYVAULT_URL
Example: https://my-vault.vault.azure.net/

Purpose: Points to Azure Key Vault for credential storage
Set By: Azure infrastructure or deployment scripts
When to Use: Azure Container Instances, App Service, Azure VMs
```

**How it works:**
1. Application checks for `AZURE_KEYVAULT_URL` environment variable
2. If present, system initializes Azure SDK
3. Credentials are fetched from Azure Key Vault
4. Application can use credentials for email, SMS, etc.

### Google Cloud Detection
```bash
Environment Variable: GOOGLE_CLOUD_PROJECT
Example: my-project-id

Purpose: Identifies the Google Cloud project for credential access
Set By: Google Cloud infrastructure
When to Use: Cloud Run, Compute Engine, Kubernetes Engine (GKE)
```

**How it works:**
1. Application checks for `GOOGLE_CLOUD_PROJECT` environment variable
2. If present, system initializes Google Cloud SDK
3. Credentials are fetched from Google Secret Manager
4. Application can use credentials for email, SMS, etc.

### Kubernetes Detection
```bash
Environment Variable: KUBERNETES_SERVICE_HOST
Example: 10.0.0.1

Purpose: Service DNS for Kubernetes API server
Set Automatically: By Kubernetes when mounting service account
When to Use: Any Kubernetes cluster deployment
```

**How it works:**
1. Kubernetes automatically injects `KUBERNETES_SERVICE_HOST` into every pod
2. Application detects this variable
3. Credentials come from Kubernetes Secrets (mounted as env vars)
4. Application can use credentials for email, SMS, etc.

### Docker Detection
```bash
File: /.dockerenv
OR
Environment Variable: DOCKER_CONTAINER=true

Purpose: Identifies Docker container environment
Set By: Docker automatically (.dockerenv) or manually (env var)
When to Use: Docker, Docker Compose, Docker Swarm
```

**How it works:**
1. Application checks for `/.dockerenv` file
2. Alternative: Check for `DOCKER_CONTAINER=true` environment variable
3. Credentials come from environment variables or .env file
4. Application can use credentials for email, SMS, etc.

### Local Detection (Default)
```bash
Trigger: No other detection signals found

Purpose: Development environment on developer machine
Set By: Automatic default fallback
When to Use: Developer laptops and local testing
```

**How it works:**
1. No cloud signals detected
2. System assumes local development
3. Credentials loaded from .env file
4. Great for debugging and local testing

---

## 📊 Detection Priority Flow

```
Check Environment Signals (Priority Order)
│
├─ 1. AZURE_KEYVAULT_URL?
│     └─ YES → AZURE ✓
│
├─ 2. GOOGLE_CLOUD_PROJECT?
│     └─ YES → GCP ✓
│
├─ 3. KUBERNETES_SERVICE_HOST?
│     └─ YES → KUBERNETES ✓
│
├─ 4. /.dockerenv OR DOCKER_CONTAINER=true?
│     └─ YES → DOCKER ✓
│
└─ 5. No signals found?
     └─ DEFAULT → LOCAL ✓
```

---

## 🔄 Environment Switching Example

### Same Code, Different Environments

```python
# YOUR CODE (Never needs to change!)
from src.stockreports.config.secrets_loader import SecretsLoader

loader = SecretsLoader()
email_password = loader.get_secret("EMAIL_APP_PASSWORD")
```

**Automatic Behavior:**

| Deployment | No Code Change | Credentials Loaded From |
|------------|----------------|------------------------|
| Local Machine | ✓ | .env file |
| Docker Container | ✓ | Environment variables |
| Kubernetes | ✓ | Kubernetes Secrets (as env vars) |
| Azure | ✓ | Azure Key Vault |
| Google Cloud | ✓ | Google Secret Manager |

**No if-statements needed!** The same code works everywhere.

---

## 🛠️ Implementation Details

### Where Detection Happens
```
File: src/stockreports/config/secrets_loader.py

class SecretsLoader:
    def __init__(self, env_file: Optional[str] = None):
        """Initialize and detect environment"""
        self.env_file = env_file or self._find_env_file()
        self.secrets_cache: Dict[str, Any] = {}
        self._load_env_file()
        self._detect_environment()  # <-- Detection happens here
```

### When Detection Happens
```
Timing: At SecretsLoader initialization

Sequence:
1. Application starts
2. NotificationSettings module is imported
3. _secrets_loader = SecretsLoader() is executed
4. _detect_environment() is called
5. Environment type is stored in self.environment_type
6. Credentials can now be loaded appropriately
```

### How to Access Detected Environment
```python
from src.stockreports.config.secrets_loader import SecretsLoader

loader = SecretsLoader()
env_type = loader.env_type  # Returns EnvironmentType constant
# e.g., "AZURE", "GCP", "KUBERNETES", "DOCKER", or "LOCAL"
```

---

## 🧪 Testing Detection (Manually)

### Test Local Detection
```bash
# Unset any cloud environment variables
unset AZURE_KEYVAULT_URL
unset GOOGLE_CLOUD_PROJECT
unset KUBERNETES_SERVICE_HOST
unset DOCKER_CONTAINER

# Run code - should detect LOCAL
python -c "from src.stockreports.config.secrets_loader import SecretsLoader; \
           loader = SecretsLoader(); \
           print(f'Detected: {loader.env_type}')"
# Output: Detected: LOCAL
```

### Test Docker Detection
```bash
# Set Docker container flag
export DOCKER_CONTAINER=true

# Run code - should detect DOCKER
python -c "from src.stockreports.config.secrets_loader import SecretsLoader; \
           loader = SecretsLoader(); \
           print(f'Detected: {loader.env_type}')"
# Output: Detected: DOCKER
```

### Test GCP Detection
```bash
# Set GCP environment variable
export GOOGLE_CLOUD_PROJECT=my-project-id

# Run code - should detect GCP
python -c "from src.stockreports.config.secrets_loader import SecretsLoader; \
           loader = SecretsLoader(); \
           print(f'Detected: {loader.env_type}')"
# Output: Detected: GCP
```

---

## 🚀 Practical Deployment Examples

### Example 1: Docker Compose

```yaml
version: '3.8'
services:
  stock-alerter:
    build: .
    environment:
      DOCKER_CONTAINER: "true"  # Triggers Docker detection
      EMAIL_SENDER: ${EMAIL_SENDER}
      EMAIL_APP_PASSWORD: ${EMAIL_APP_PASSWORD}
```

**What happens:**
1. Docker Compose sets `DOCKER_CONTAINER=true`
2. SecretsLoader detects DOCKER environment
3. Credentials loaded from environment variables
4. Application sends emails successfully

### Example 2: Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-alerter
spec:
  template:
    spec:
      containers:
      - name: alerter
        image: stock-alerter:latest
        env:
        - name: EMAIL_SENDER
          valueFrom:
            secretKeyRef:
              name: email-creds
              key: sender
        - name: EMAIL_APP_PASSWORD
          valueFrom:
            secretKeyRef:
              name: email-creds
              key: password
```

**What happens:**
1. Kubernetes automatically injects `KUBERNETES_SERVICE_HOST`
2. SecretsLoader detects KUBERNETES environment
3. Credentials loaded from environment variables (from secrets)
4. Application sends emails successfully

### Example 3: Azure Container Instance

```bash
az container create \
  --resource-group mygroup \
  --name stock-alerter \
  --image stock-alerter:latest \
  --environment-variables \
    AZURE_KEYVAULT_URL=https://my-vault.vault.azure.net/
```

**What happens:**
1. Azure sets `AZURE_KEYVAULT_URL` environment variable
2. SecretsLoader detects AZURE environment
3. Credentials fetched from Azure Key Vault
4. Application sends emails successfully

### Example 4: Google Cloud Run

```bash
gcloud run deploy stock-alerter \
  --set-env-vars GOOGLE_CLOUD_PROJECT=my-project-id
```

**What happens:**
1. Google Cloud sets `GOOGLE_CLOUD_PROJECT` environment variable
2. SecretsLoader detects GCP environment
3. Credentials fetched from Google Secret Manager
4. Application sends emails successfully

---

## ⚠️ Troubleshooting Detection

### Problem: Wrong environment detected
**Solution:** Check environment variables
```bash
echo "AZURE: $AZURE_KEYVAULT_URL"
echo "GCP: $GOOGLE_CLOUD_PROJECT"
echo "K8S: $KUBERNETES_SERVICE_HOST"
echo "DOCKER: $DOCKER_CONTAINER"
echo "CHECK: [ -f /.dockerenv ] && echo 'Has .dockerenv' || echo 'No .dockerenv'"
```

### Problem: Can't load credentials
**Solution:** Verify environment detection
```python
from src.stockreports.config.secrets_loader import SecretsLoader
loader = SecretsLoader()
print(f"Detected environment: {loader.env_type}")
```

### Problem: Need to force environment
**Solution:** Manually set environment variable before app starts
```bash
# Force Azure detection for testing
export AZURE_KEYVAULT_URL=https://test-vault.vault.azure.net/
python your_app.py
```

---

## 🎯 Design Benefits

✅ **Zero Configuration:** Environment auto-detected automatically  
✅ **No Code Changes:** Same code works everywhere  
✅ **Easy Testing:** Can simulate different environments  
✅ **Clear Intent:** Environment signals are self-documenting  
✅ **Extensible:** Easy to add new environment types  
✅ **Graceful Fallback:** Defaults to LOCAL if no signals found  

---

## 🔗 Related Documentation

- **DESIGN_OVERVIEW.md** - High-level architecture overview
- **CREDENTIAL_RESOLUTION_LAYERS.md** - How credentials are resolved
- **CLOUD_PLATFORM_INTEGRATION.md** - Cloud-specific setup
- **Implementation Guide** - See `docs/IMPLEMENTATION/` for operational details

---

**Last Updated:** March 15, 2026  
**Status:** ✅ Production Ready
