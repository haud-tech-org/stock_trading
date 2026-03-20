# Secret Manager Integration Guide

**Updated**: March 18, 2026  
**Python Version**: 3.12.12  
**Status**: ✅ Ready for Production

---

## Overview

The project now supports multiple credential management systems:

1. **Google Cloud Secret Manager** ✅
2. **Azure Key Vault** ✅
3. **Environment Variables** ✅
4. **.env Files** ✅

This guide explains the integration and how to use each service.

---

## Installed Packages

### Requirements Added to `requirements.txt`

```
# Google Cloud Secret Manager
google-cloud-secret-manager==2.26.0
google-cloud-core==2.5.0  (dependency)
google-cloud-storage==3.9.0  (already existed)

# Azure Key Vault
azure-identity==1.25.3
azure-keyvault-secrets==4.10.0
azure-core==1.38.3  (dependency)
```

### Installation Status

```bash
✅ google-cloud-secret-manager==2.26.0
✅ azure-identity==1.25.3
✅ azure-keyvault-secrets==4.10.0
✅ All dependencies resolved
```

---

## Architecture: Credential Resolution Layers

The `SecretsLoader` class implements a **priority-based credential resolution system**:

```
┌─────────────────────────────────────────────────────┐
│  get_secret(key, default, required, is_sensitive)  │
└─────────────────────┬───────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────────┐
         │ Layer 1: Cache Check       │
         │ (In-memory cache)          │
         └─────────┬──────────────────┘
                   │ (miss)
                   ▼
         ┌────────────────────────────┐
         │ Layer 2: Environment Vars  │
         │ (os.getenv + loaded .env)  │
         └─────────┬──────────────────┘
                   │ (not found)
                   ▼
         ┌────────────────────────────┐
         │ Layer 3: Secret Manager    │
         │ ┌──────────────────────┐   │
         │ │ GCP Secret Manager   │   │
         │ │ or                   │   │
         │ │ Azure Key Vault      │   │
         │ └──────────────────────┘   │
         └─────────┬──────────────────┘
                   │ (not found)
                   ▼
         ┌────────────────────────────┐
         │ Layer 4: Default Value     │
         │ (if provided)              │
         └─────────┬──────────────────┘
                   │ (not found)
                   ▼
         ┌────────────────────────────┐
         │ Handle Missing Secret      │
         │ ├─ required=True → Raise   │
         │ └─ required=False → None   │
         └────────────────────────────┘
```

---

## Environment Detection

The system automatically detects the deployment environment:

```python
from src.stockreports.config.secrets_loader import SecretsLoader

loader = SecretsLoader()

# Check environment
if loader.is_gcp:
    print("Running on Google Cloud Platform")
elif loader.is_azure:
    print("Running on Azure")
elif loader.is_kubernetes:
    print("Running on Kubernetes")
elif loader.is_docker:
    print("Running in Docker")
else:
    print("Running locally")
```

### Environment Detection Logic

| Environment | Detected By | Flag |
|-------------|------------|------|
| **GCP** | `GOOGLE_CLOUD_PROJECT` env var | `loader.is_gcp` |
| **Azure** | `AZURE_KEYVAULT_URL` env var | `loader.is_azure` |
| **Kubernetes** | `KUBERNETES_SERVICE_HOST` env var | `loader.is_kubernetes` |
| **Docker** | `/.dockerenv` file or `DOCKER_CONTAINER=true` | `loader.is_docker` |
| **Local** | None of the above | `loader.is_local` |

---

## 1. Google Cloud Secret Manager

### Setup

#### Step 1: Create GCP Project and Secret

```bash
# Set your GCP project
export PROJECT_ID="your-project-id"
export GOOGLE_CLOUD_PROJECT="$PROJECT_ID"

# Create a secret
gcloud secrets create EMAIL_APP_PASSWORD --data-file=- <<< "your-app-password"

# Verify
gcloud secrets list
gcloud secrets versions access latest --secret="EMAIL_APP_PASSWORD"
```

#### Step 2: Set Environment Variable

```bash
# Add to .env or export
export GOOGLE_CLOUD_PROJECT="your-project-id"
```

#### Step 3: Authentication Options

**Option A: Application Default Credentials (Recommended)**

```bash
# Use existing ADC
gcloud auth application-default login
```

**Option B: Service Account Key**

```bash
# Create service account
gcloud iam service-accounts create stock-trading-app

# Create key
gcloud iam service-accounts keys create key.json \
  --iam-account=stock-trading-app@${PROJECT_ID}.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"

# Give permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
  --member=serviceAccount:stock-trading-app@${PROJECT_ID}.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

**Option C: Docker/Kubernetes (Workload Identity)**

```yaml
# Kubernetes ServiceAccount
apiVersion: v1
kind: ServiceAccount
metadata:
  name: stock-trading
  namespace: default
  annotations:
    iam.gke.io/gcp-service-account: stock-trading@PROJECT_ID.iam.gserviceaccount.com
```

### Usage Example

```python
from src.stockreports.config.secrets_loader import SecretsLoader

# Initialize loader
secrets = SecretsLoader()

# Retrieve secret
email_password = secrets.get_secret(
    key="EMAIL_APP_PASSWORD",
    required=True,
    is_sensitive=True
)

# Use in code
send_email(password=email_password)
```

### Code Implementation

The `_get_from_google_secret_manager` method in `secrets_loader.py`:

```python
def _get_from_google_secret_manager(self, key: str) -> Optional[str]:
    """
    Retrieve secret from Google Secret Manager.
    
    Requires:
    - GOOGLE_CLOUD_PROJECT environment variable
    - Google Cloud credentials (ADC or GOOGLE_APPLICATION_CREDENTIALS)
    - google-cloud-secret-manager package
    
    Args:
        key: Secret key name
        
    Returns:
        Secret value or None if not found
    """
    try:
        from google.cloud import secretmanager

        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            logger.debug("GOOGLE_CLOUD_PROJECT not set; skipping Google Secret Manager")
            return None

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{key}/versions/latest"
        
        try:
            response = client.access_secret_version(request={"name": name})
            secret_value = response.payload.data.decode("UTF-8")
            logger.debug(f"Retrieved '{key}' from Google Secret Manager")
            return secret_value
        except Exception as e:
            logger.debug(f"Secret '{key}' not found in Google Secret Manager: {e}")
            return None
            
    except ImportError:
        logger.debug("Google Cloud SDK not installed (google-cloud-secret-manager); "
                    "skipping Google Secret Manager")
        return None
    except Exception as e:
        logger.warning(f"Error accessing Google Secret Manager: {e}")
        return None
```

### GCP Command Reference

```bash
# List all secrets
gcloud secrets list

# Create secret
gcloud secrets create EMAIL_APP_PASSWORD --data-file=- <<< "password"

# View secret (latest version)
gcloud secrets versions access latest --secret="EMAIL_APP_PASSWORD"

# Update secret (creates new version)
gcloud secrets versions add EMAIL_APP_PASSWORD --data-file=- <<< "new-password"

# Delete secret
gcloud secrets delete EMAIL_APP_PASSWORD

# Grant access to service account
gcloud secrets add-iam-policy-binding EMAIL_APP_PASSWORD \
  --member=serviceAccount:stock-trading@PROJECT_ID.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# View secret versions
gcloud secrets versions list EMAIL_APP_PASSWORD
```

---

## 2. Azure Key Vault

### Setup

#### Step 1: Create Azure Key Vault

```bash
# Create resource group
az group create --name stock-trading-rg --location eastus

# Create Key Vault
az keyvault create \
  --name stock-trading-kv \
  --resource-group stock-trading-rg \
  --location eastus

# Set environment variable
export AZURE_KEYVAULT_URL="https://stock-trading-kv.vault.azure.net/"
```

#### Step 2: Add Secrets

```bash
# Create secret (key uses hyphens, not underscores)
az keyvault secret set \
  --vault-name stock-trading-kv \
  --name email-app-password \
  --value "your-app-password"

# Verify
az keyvault secret show \
  --vault-name stock-trading-kv \
  --name email-app-password
```

#### Step 3: Authentication Options

**Option A: Azure CLI (Development)**

```bash
# Login with Azure CLI
az login

# Login interactively
az login --interactive
```

**Option B: Service Principal (Production)**

```bash
# Create service principal
az ad sp create-for-rbac \
  --name stock-trading-app \
  --role Contributor

# Set environment variables
export AZURE_CLIENT_ID="<client-id>"
export AZURE_CLIENT_SECRET="<client-secret>"
export AZURE_TENANT_ID="<tenant-id>"

# Grant Key Vault access
az keyvault set-policy \
  --name stock-trading-kv \
  --spn ${AZURE_CLIENT_ID} \
  --secret-permissions get list
```

**Option C: Managed Identity (Azure Container Instances, App Service)**

```bash
# Enable Managed Identity on resource
# (done through Azure Portal or CLI during resource creation)

# Grant access to Key Vault
az keyvault set-policy \
  --name stock-trading-kv \
  --object-id <managed-identity-object-id> \
  --secret-permissions get list
```

### Usage Example

```python
from src.stockreports.config.secrets_loader import SecretsLoader

# Initialize loader (auto-detects Azure)
secrets = SecretsLoader()

# Retrieve secret
email_password = secrets.get_secret(
    key="EMAIL_APP_PASSWORD",
    required=True,
    is_sensitive=True
)
```

### Code Implementation

The `_get_from_azure_keyvault` method in `secrets_loader.py`:

```python
def _get_from_azure_keyvault(self, key: str) -> Optional[str]:
    """
    Retrieve secret from Azure Key Vault.
    
    Requires:
    - AZURE_KEYVAULT_URL environment variable
    - Azure credentials (DefaultAzureCredential)
    - azure-identity and azure-keyvault-secrets packages
    
    Args:
        key: Secret key name (converted to Azure format with hyphens)
        
    Returns:
        Secret value or None if not found
    """
    try:
        from azure.identity import DefaultAzureCredential
        from azure.keyvault.secrets import SecretClient

        keyvault_url = os.getenv("AZURE_KEYVAULT_URL")
        if not keyvault_url:
            logger.debug("AZURE_KEYVAULT_URL not set; skipping Azure Key Vault lookup")
            return None

        credential = DefaultAzureCredential()
        client = SecretClient(vault_url=keyvault_url, credential=credential)
        
        # Azure Key Vault uses hyphens instead of underscores
        azure_key = key.lower().replace("_", "-")
        
        try:
            secret = client.get_secret(azure_key)
            logger.debug(f"Retrieved '{key}' from Azure Key Vault")
            return secret.value
        except Exception as e:
            logger.debug(f"Secret '{azure_key}' not found in Azure Key Vault: {e}")
            return None
            
    except ImportError:
        logger.debug("Azure SDK not installed (azure-identity, azure-keyvault-secrets); "
                    "skipping Azure Key Vault")
        return None
    except Exception as e:
        logger.warning(f"Error accessing Azure Key Vault: {e}")
        return None
```

### Azure CLI Command Reference

```bash
# Create Key Vault
az keyvault create --name MyKeyVault --resource-group MyRG

# Create secret (key format: lowercase with hyphens)
az keyvault secret set --vault-name MyKeyVault --name email-app-password --value "password"

# View secret
az keyvault secret show --vault-name MyKeyVault --name email-app-password

# Update secret
az keyvault secret set --vault-name MyKeyVault --name email-app-password --value "new-password"

# Delete secret
az keyvault secret delete --vault-name MyKeyVault --name email-app-password

# List secrets
az keyvault secret list --vault-name MyKeyVault

# Grant access to service principal
az keyvault set-policy --vault-name MyKeyVault \
  --spn <app-id> \
  --secret-permissions get list set delete
```

---

## 3. Local Development (.env File)

### Setup

Create `.env` file in project root:

```bash
# Email Configuration
EMAIL_APP_PASSWORD=your-app-password
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587

# Google Cloud
GOOGLE_CLOUD_PROJECT=your-project-id
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json  # Optional

# Azure
# AZURE_KEYVAULT_URL=https://your-vault.vault.azure.net/

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/stock_trading

# API Keys
API_KEY=your-api-key
```

### Usage Example

```python
from src.stockreports.config.secrets_loader import SecretsLoader

# Initialize loader (auto-loads .env)
secrets = SecretsLoader()

# Retrieve secrets
email_password = secrets.get_secret("EMAIL_APP_PASSWORD", required=True)
smtp_server = secrets.get_secret("SMTP_SERVER", default="smtp.gmail.com")
```

---

## Complete Usage Example

```python
from src.stockreports.config.secrets_loader import SecretsLoader
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize SecretsLoader
secrets = SecretsLoader()

# Log environment info (non-sensitive)
secrets.log_environment_info()

# Retrieve required secrets
try:
    email_password = secrets.get_secret(
        key="EMAIL_APP_PASSWORD",
        required=True,
        is_sensitive=True
    )
    
    smtp_server = secrets.get_secret(
        key="SMTP_SERVER",
        default="smtp.gmail.com",
        is_sensitive=False
    )
    
    api_key = secrets.get_secret(
        key="API_KEY",
        required=True,
        is_sensitive=True
    )
    
    # Use secrets in application
    send_email(
        smtp_server=smtp_server,
        password=email_password,
        api_key=api_key
    )
    
except ValueError as e:
    logger.error(f"Missing required credential: {e}")
    exit(1)
```

---

## Credential Priority (Example)

When retrieving `EMAIL_APP_PASSWORD`:

```
1. Check in-memory cache
   └─ Not found
   
2. Check environment variables
   ├─ os.getenv("EMAIL_APP_PASSWORD")
   ├─ Also checks .env values (pre-loaded into os.environ)
   └─ Found → Return it
   
If environment variable not found:

3. Check Secret Manager (based on environment)
   ├─ If GCP:
   │  └─ Query Google Secret Manager
   ├─ If Azure:
   │  └─ Query Azure Key Vault
   └─ Not found
   
4. Use default value
   └─ If provided in function call
   
5. Handle missing credential
   ├─ If required=True → Raise ValueError
   └─ If required=False → Return None
```

---

## Environment-Specific Configuration

### Local Development

```bash
# .env file
EMAIL_APP_PASSWORD=local-test-password
GOOGLE_CLOUD_PROJECT=  # Empty or omitted
AZURE_KEYVAULT_URL=    # Empty or omitted
```

### GCP Production

```bash
# Docker container environment
GOOGLE_CLOUD_PROJECT=stock-trading-prod
DOCKER_CONTAINER=true
# Credentials from: Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS
```

### Azure Production

```bash
# Docker container or App Service environment
AZURE_KEYVAULT_URL=https://stock-trading-prod.vault.azure.net/
DOCKER_CONTAINER=true
# Credentials from: DefaultAzureCredential (Managed Identity)
```

### Kubernetes

```bash
# values.yaml or secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: app-secrets
type: Opaque
stringData:
  GOOGLE_CLOUD_PROJECT: stock-trading-prod
  KUBERNETES_SERVICE_HOST: kubernetes.default  # Auto-set
```

---

## Security Best Practices

✅ **Do**:
- Store secrets in dedicated services (Google Secret Manager, Azure Key Vault)
- Use service accounts with minimal permissions
- Rotate secrets regularly
- Enable audit logging
- Use environment variables in production
- Add `.env` to `.gitignore`
- Use `is_sensitive=True` when retrieving passwords

❌ **Don't**:
- Hardcode secrets in code
- Commit `.env` files to Git
- Use weak credentials
- Grant excessive permissions
- Log sensitive values
- Store secrets in Docker images
- Use the same secret across environments

---

## Troubleshooting

### GCP: "No credentials found"

```bash
# Solution: Setup ADC
gcloud auth application-default login

# Or: Set service account key path
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
```

### Azure: "Unauthorized"

```bash
# Solution: Login with Azure CLI
az login

# Or: Set service principal credentials
export AZURE_CLIENT_ID="..."
export AZURE_CLIENT_SECRET="..."
export AZURE_TENANT_ID="..."
```

### Secret Not Found

```python
# Check with required=False first
value = secrets.get_secret("KEY_NAME", required=False)
if value is None:
    print(f"Secret not found in any source")
    print(f"Checked: env vars, secret manager, defaults")
```

### Import Error

```bash
# Verify packages installed
pip list | grep -E "google-cloud-secret|azure"

# Reinstall if missing
pip install -r requirements.txt
```

---

## Installed Package Versions

```
google-cloud-secret-manager==2.26.0
google-cloud-core==2.5.0
google-cloud-storage==3.9.0
azure-identity==1.25.3
azure-keyvault-secrets==4.10.0
azure-core==1.38.3
```

---

## Next Steps

1. **For GCP**: Setup Google Cloud Project and secrets
   - Create project
   - Enable Secret Manager API
   - Create service account
   - Add secrets

2. **For Azure**: Setup Azure Key Vault
   - Create resource group
   - Create Key Vault
   - Add secrets
   - Configure authentication

3. **For Local Development**: Create `.env` file
   - Add credentials
   - Don't commit to Git
   - Test credential loading

4. **Test in Application**:
   - Initialize `SecretsLoader()`
   - Retrieve secrets
   - Verify authentication works

---

**Status**: ✅ All packages installed and ready  
**Last Updated**: March 18, 2026  
**Maintained By**: Development Team

