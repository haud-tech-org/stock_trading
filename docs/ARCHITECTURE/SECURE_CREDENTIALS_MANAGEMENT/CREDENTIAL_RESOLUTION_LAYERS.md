# Secure Credentials Management - Credential Resolution Layers Architecture

## 🎯 Overview

The system uses a **4-layer priority-based resolution strategy** to fetch credentials from the most secure source available, with graceful fallback to less secure sources.

---

## 📊 The 4 Resolution Layers

```
Request: loader.get_secret("EMAIL_APP_PASSWORD")
│
├─ LAYER 1: Environment Variables (Highest Priority)
│  ├─ Query: os.environ.get("EMAIL_APP_PASSWORD")
│  └─ ✓ Found? RETURN immediately
│
├─ LAYER 2: Secret Management Services
│  ├─ If Azure: Azure Key Vault
│  │  └─ ✓ Found? RETURN immediately
│  │
│  └─ If GCP: Google Secret Manager
│     └─ ✓ Found? RETURN immediately
│
├─ LAYER 3: .env File (Local Development)
│  ├─ Query: Parsed .env file values
│  └─ ✓ Found? RETURN immediately
│
└─ LAYER 4: Default Values (Non-Sensitive Only)
   ├─ Use provided default value
   └─ ✓ Default available? RETURN value
      └─ ✗ No default? Return None (may log warning if required=True)
```

---

## 🔐 Layer 1: Environment Variables

### Purpose
Highest priority - allows runtime configuration without code changes.

### When Used
- **Development:** Environment variables set in shell
- **Docker:** Environment variables passed in docker-compose or docker run
- **Kubernetes:** Secrets mounted as environment variables
- **CI/CD:** Secrets injected by CI/CD platform

### Example
```bash
# Set credential as environment variable
export EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx"

# Application reads it
python app.py
```

### Why Priority 1
✅ Can be set at runtime (before app starts)  
✅ Secure when managed by cloud platforms  
✅ Supports secret rotation without redeployment  
✅ No additional SDK calls needed  

### Code Implementation
```python
def get_secret(self, key: str, ...) -> Any:
    # Layer 1: Check environment variables first
    value = os.environ.get(key)
    if value:
        logger.debug(f"Secret '{key}' found in environment variables")
        return value
```

---

## 🔑 Layer 2: Secret Management Services

### Purpose
Second priority - secure, managed secret storage by cloud providers.

### Supported Services

#### Azure Key Vault
```
When Detected: AZURE_KEYVAULT_URL env var is set
Example URL: https://my-vault.vault.azure.net/
Usage: For Azure deployments (ACI, App Service, VMs, etc.)
```

**How it works:**
```
1. Application detects AZURE environment (AZURE_KEYVAULT_URL set)
2. Azure SDK initialized with Key Vault URL
3. Credentials requested from Key Vault
4. Azure manages encryption, rotation, access control
5. Application receives decrypted credentials
```

#### Google Secret Manager
```
When Detected: GOOGLE_CLOUD_PROJECT env var is set
Example Value: my-project-id
Usage: For Google Cloud deployments (Cloud Run, Compute Engine, etc.)
```

**How it works:**
```
1. Application detects GCP environment (GOOGLE_CLOUD_PROJECT set)
2. Google Cloud SDK initialized
3. Credentials requested from Secret Manager
4. Google Cloud manages encryption, rotation, access control
5. Application receives decrypted credentials
```

### Why Priority 2
✅ Managed by cloud platforms (no manual key management)  
✅ Automatic encryption at rest and in transit  
✅ Audit logging and access control  
✅ Support for secret rotation and versioning  
✅ More secure than environment variables (encrypted)  

### When Used
- **Production Azure:** Secrets stored in Key Vault
- **Production GCP:** Secrets stored in Secret Manager
- **Enterprise:** Required for compliance (SOC 2, ISO 27001, etc.)

### Code Implementation
```python
def _get_from_azure_keyvault(self, key: str) -> Optional[str]:
    """Fetch secret from Azure Key Vault"""
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient
        
        keyvault_url = os.environ.get('AZURE_KEYVAULT_URL')
        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_url, credential=credential)
        secret = client.get_secret(key)
        return secret.value
    except Exception as e:
        logger.debug(f"Could not fetch from Azure Key Vault: {e}")
        return None

def _get_from_google_secret_manager(self, key: str) -> Optional[str]:
    """Fetch secret from Google Secret Manager"""
    try:
        from google.cloud import secretmanager
        
        project_id = os.environ.get('GOOGLE_CLOUD_PROJECT')
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{key}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode('UTF-8')
    except Exception as e:
        logger.debug(f"Could not fetch from Google Secret Manager: {e}")
        return None
```

---

## 📄 Layer 3: .env File

### Purpose
Third priority - local development convenience without committing secrets.

### When Used
- **Local Development:** Developer testing on laptop
- **Docker Local:** Local docker-compose for testing
- **CI/CD Testing:** Test environments with local .env

### How It Works
```
1. Application looks for .env file in project root
2. Parses file line-by-line (format: KEY=value)
3. Stores values in memory during initialization
4. Subsequent get_secret() calls check parsed values
```

### .env File Format
```bash
# Email Configuration
EMAIL_SENDER=your-email@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_SENDER_DISPLAY_NAME=Stock Alerter

# Twilio Configuration
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_token_here
```

### Why Priority 3
✅ Convenient for local development  
✅ Never committed (in .gitignore)  
✅ Easy to test different configurations  
✅ No dependency on cloud services  
⚠️ Less secure than cloud managers (stored in plain text)  

### When NOT to Use
❌ Production environments (not secure)  
❌ Shared machines (not isolated)  
❌ When Layer 1 or 2 are available  

### Code Implementation
```python
def _find_env_file(self) -> Optional[Path]:
    """Locate .env file in project root or parent directories"""
    current = Path.cwd()
    for _ in range(4):  # Check up to 4 levels
        env_file = current / ".env"
        if env_file.exists():
            logger.info(f"Found .env file at: {env_file}")
            return env_file
        current = current.parent
    return None

def _load_env_file(self) -> None:
    """Load environment variables from .env file"""
    if not self.env_file:
        logger.debug("No .env file found; using environment variables only")
        return

    try:
        with open(self.env_file, 'r') as f:
            for line in f:
                line = line.strip()
                
                # Skip empty lines and comments
                if not line or line.startswith('#'):
                    continue
                
                if '=' not in line:
                    continue
                
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes if present
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
```

---

## 📌 Layer 4: Default Values

### Purpose
Fourth priority - provides sensible defaults for non-sensitive configuration.

### When Used
- **Feature Flags:** `EMAIL_ENABLED=false` (default, no credential needed)
- **Non-Sensitive Config:** Display names, server addresses, etc.
- **Optional Services:** Fallback when service not configured

### Examples
```python
# Sensible defaults (NO credentials)
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'false')  # Safe default
TWILIO_ENABLED = os.getenv('TWILIO_ENABLED', 'false')  # Safe default

# DANGEROUS - Never do this with credentials!
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD', '')  # Empty safe
EMAIL_APP_PASSWORD = os.getenv('EMAIL_APP_PASSWORD', 'debug123')  # DANGER!
```

### Why Priority 4
✅ Provides fallback for optional settings  
✅ Prevents hard-coding configuration  
⚠️ Should NOT contain sensitive values  
⚠️ Should NOT be used for credentials  

### Safety Rule
```
✅ SAFE defaults:
  - Feature flags (true/false)
  - Display names
  - Server addresses
  - Timeout values
  - Log levels

❌ UNSAFE defaults:
  - Passwords
  - API keys
  - Tokens
  - Credentials of any kind
```

### Code Implementation
```python
def get_secret(
    self,
    key: str,
    default: Any = None,
    required: bool = False,
    is_sensitive: bool = True
) -> Any:
    """
    Resolve secret using 4-layer priority resolution.
    """
    # Layers 1-3 checked first...
    
    # Layer 4: Default value
    if default is not None:
        logger.debug(f"Secret '{key}' using default value")
        return default
    
    # No value found anywhere
    if required:
        raise ValueError(f"Required credential '{key}' not found in any source")
    
    return None
```

---

## 🎯 Resolution Decision Tree

```
get_secret("EMAIL_APP_PASSWORD", required=True)
│
├─ Environment Variable Set?
│  └─ YES → Return env var value ✓
│
├─ Cloud Secret Manager Available?
│  ├─ Azure Key Vault available?
│  │  └─ YES → Return from Key Vault ✓
│  │
│  └─ Google Secret Manager available?
│     └─ YES → Return from Secret Manager ✓
│
├─ .env File Loaded?
│  └─ YES → Return from .env ✓
│
├─ Default Value Provided?
│  └─ YES → Return default value ✓
│
└─ No Value Found
   ├─ Required=True?
   │  └─ YES → Raise ValueError ✗
   │
   └─ Required=False?
      └─ YES → Return None
```

---

## 📊 Comparison of Resolution Layers

| Layer | Source | Speed | Security | When Available | Use Case |
|-------|--------|-------|----------|---------------|-----------| 
| 1 | Environment Variables | ⚡ Fastest | 🔒 Good | Always | Development, Docker, K8s |
| 2 | Secret Managers | 🚗 Medium | 🔐 Excellent | Cloud only | Production, Enterprise |
| 3 | .env File | 🚂 Slow | ⚠️ Basic | Local only | Development |
| 4 | Defaults | ⚡ Instant | N/A | Always | Non-sensitive config |

---

## 🔄 Real-World Example

### Scenario: Get email password

```python
password = loader.get_secret("EMAIL_APP_PASSWORD", required=True)
```

#### Path 1: Azure Production
```
1. Check os.environ.get("EMAIL_APP_PASSWORD") → NOT SET
2. Detect AZURE environment (AZURE_KEYVAULT_URL set)
3. Check Azure Key Vault for "EMAIL_APP_PASSWORD" → FOUND
4. RETURN from Key Vault ✓
```

#### Path 2: Docker Local
```
1. Check os.environ.get("EMAIL_APP_PASSWORD") → FOUND in docker-compose
2. RETURN from environment variable ✓
```

#### Path 3: Developer Laptop
```
1. Check os.environ.get("EMAIL_APP_PASSWORD") → NOT SET
2. Detect LOCAL environment
3. Check .env file for "EMAIL_APP_PASSWORD" → FOUND
4. RETURN from .env ✓
```

#### Path 4: Missing Credential
```
1. Check os.environ.get("EMAIL_APP_PASSWORD") → NOT SET
2. No secret manager available (LOCAL environment)
3. Check .env file → NOT SET
4. No default provided
5. required=True → RAISE ERROR ✗
```

---

## 💾 Credential Caching

To avoid repeated queries to cloud services, credentials are cached after first retrieval:

```python
class SecretsLoader:
    def __init__(self):
        self.secrets_cache: Dict[str, Any] = {}
    
    def get_secret(self, key: str, ...) -> Any:
        # Check cache first
        if key in self.secrets_cache:
            return self.secrets_cache[key]
        
        # Resolve credential (Layers 1-4)
        value = self._resolve(key)
        
        # Cache for future calls
        self.secrets_cache[key] = value
        return value
```

**Performance Impact:**
- First call: ~100ms (may hit cloud service)
- Subsequent calls: ~1ms (cached in memory)

---

## ⚠️ Security Considerations

### What Happens When Credential is Found
```
FOUND: Credential is cached in memory
├─ ✅ Encrypted in transit (if from cloud service)
├─ ⚠️ Unencrypted in memory (but only accessible to process)
└─ ❌ Never logged (even in debug mode for sensitive values)
```

### What Happens When Credential is NOT Found
```
NOT FOUND: Behavior depends on 'required' flag

If required=True:
└─ Raises clear error message
   "Required credential 'EMAIL_APP_PASSWORD' not found"

If required=False:
└─ Returns None
   └─ Application should handle gracefully
```

### Never Log Sensitive Values
```python
# ❌ BAD - Exposes password in logs
logger.info(f"Password is: {password}")

# ✅ GOOD - Only logs that credential was found
logger.info(f"Credential 'EMAIL_APP_PASSWORD' loaded successfully")

# ✅ GOOD - Logs masked value
logger.info(f"Email app password: {password[:5]}****")
```

---

## 🔗 Related Documentation

- **DESIGN_OVERVIEW.md** - High-level architecture
- **ENVIRONMENT_DETECTION.md** - Environment detection logic
- **CLOUD_PLATFORM_INTEGRATION.md** - Cloud-specific setup
- **Implementation Guides** - See `docs/IMPLEMENTATION/` for setup instructions

---

**Last Updated:** March 15, 2026  
**Status:** ✅ Production Ready
