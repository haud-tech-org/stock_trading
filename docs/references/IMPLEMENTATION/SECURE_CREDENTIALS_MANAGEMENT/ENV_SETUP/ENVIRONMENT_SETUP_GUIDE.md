# Environment Setup Guide - Step-by-Step Configuration

Complete step-by-step instructions for setting up secure credentials in each deployment environment. Follow the guide for your specific environment.

---

## 📋 Quick Reference

| Environment | Configuration Method | Difficulty | Time |
|-------------|----------------------|-----------|------|
| **Local Development** | .env file | Easy | 5 min |
| **Docker (Compose)** | docker-compose.yml | Easy | 10 min |
| **Google Cloud Run** | Secret Manager + Env vars | Medium | 15 min |
| **Azure Container Instances** | Key Vault + Environment variables | Medium | 20 min |
| **Kubernetes** | ConfigMap/Secrets + Pod env | Medium | 15 min |

---

## 1️⃣ LOCAL DEVELOPMENT

### Overview
- **Location:** Your laptop/workstation
- **Credentials Source:** `.env` file
- **Best For:** Development, testing, debugging
- **Security:** File is in `.gitignore` (never committed)

### Step-by-Step Setup

#### Step 1: Create .env file from template
```bash
cd /Users/tech/dev/development/trending_and_summary
cp .env.example .env
```

**Result:** You now have a `.env` file in the project root

#### Step 2: Get your credentials
You need:
- **EMAIL_SENDER** - Your Gmail address (e.g., `haud.tech@gmail.com`)
- **EMAIL_APP_PASSWORD** - Gmail app-specific password (16 characters with spaces)
- **TWILIO_ACCOUNT_SID** - From Twilio dashboard (starts with AC)
- **TWILIO_AUTH_TOKEN** - From Twilio dashboard
- **TWILIO_PHONE_NUMBER** - Your Twilio phone number (format: +1234567890)

#### Step 3: Edit .env file
```bash
nano .env
```

**Add these values:**
```bash
# Email Configuration
EMAIL_ENABLED=true
EMAIL_SENDER=haud.tech@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_SENDER_DISPLAY_NAME=Stock Alerter (No-Reply)
EMAIL_RECEIVERS=your-email@example.com
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587

# Twilio SMS (optional)
TWILIO_ENABLED=false
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_PHONE_NUMBER=+1234567890

# ntfy (optional)
NTFY_TOPICS=stock-alerts
```

**Save:** Press `Ctrl+X`, then `Y`, then `Enter`

#### Step 4: Verify credentials loaded
```bash
cd /Users/tech/dev/development/trending_and_summary
source venv/bin/activate
python -c "from src.stockreports.config.secrets_loader import SecretsLoader; loader = SecretsLoader(); print('✅ Credentials loaded successfully!')"
```

**Expected output:**
```
✅ Credentials loaded successfully!
```

#### Step 5: Run application
```bash
python -m src.stockreports.cli alerts
```

### Troubleshooting

**Problem:** `KeyError: 'EMAIL_SENDER'`
- **Cause:** .env file missing or not found
- **Solution:** Run Step 1 again, ensure file is in project root

**Problem:** `FileNotFoundError: .env`
- **Cause:** Working directory is wrong
- **Solution:** Run `pwd` and ensure you're in `/Users/tech/dev/development/trending_and_summary`

**Problem:** Credentials not being read
- **Cause:** .env file not loaded
- **Solution:** Run `source venv/bin/activate` first

---

## 2️⃣ DOCKER (Local Compose)

### Overview
- **Location:** Your laptop via Docker
- **Credentials Source:** `.env` file + `docker-compose.yml`
- **Best For:** Testing containerized deployments locally
- **Security:** Uses environment variable injection

### Step-by-Step Setup

#### Step 1: Prepare .env file (same as Local Development)
```bash
cp .env.example .env
nano .env
# Edit with your credentials (same as Step 3 above)
```

#### Step 2: Verify docker-compose.yml
```bash
cat docker-compose.yml
```

**Check for:**
```yaml
services:
  stock-alerter:
    environment:
      EMAIL_ENABLED: "true"
      EMAIL_SENDER: ${EMAIL_SENDER}
      EMAIL_APP_PASSWORD: ${EMAIL_APP_PASSWORD}
    env_file:
      - .env
```

#### Step 3: Build Docker image
```bash
cd /Users/tech/dev/development/trending_and_summary
docker-compose build
```

**Expected output:**
```
Building stock-alerter
Step 1/10 : FROM python:3.11-slim
...
Successfully tagged stock-alerter:latest
```

#### Step 4: Run Docker container
```bash
docker-compose up -d
```

**Expected output:**
```
Creating stock-alerter ... done
```

#### Step 5: Verify container is running
```bash
docker-compose ps
```

**Expected output:**
```
NAME        STATUS
stock-alerter  Up 2 seconds
```

#### Step 6: Check logs
```bash
docker-compose logs -f stock-alerter
```

**Look for:**
```
✅ Credentials loaded successfully!
Detected environment: Docker
```

#### Step 7: Stop container
```bash
docker-compose down
```

### Troubleshooting

**Problem:** `docker: command not found`
- **Solution:** Install Docker Desktop

**Problem:** `Cannot find .env file`
- **Solution:** Run `ls -la .env` in project root

**Problem:** Container exits immediately
- **Solution:** Check logs: `docker-compose logs stock-alerter`

**Problem:** Port already in use
- **Solution:** Stop other services: `docker-compose down`

---

## 3️⃣ GOOGLE CLOUD RUN

### Overview
- **Location:** Google Cloud Platform
- **Credentials Source:** Google Secret Manager
- **Environment Detection:** Automatic (checks GOOGLE_CLOUD_PROJECT)
- **Best For:** Serverless production deployments

### Prerequisites
- Google Cloud account
- `gcloud` CLI installed
- Project created in GCP
- Docker installed

### Step-by-Step Setup

#### Step 1: Set up Google Cloud credentials
```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

**Replace:** `YOUR_PROJECT_ID` with your actual GCP project ID

#### Step 2: Create secrets in Secret Manager
```bash
# Email credentials
gcloud secrets create email-sender \
  --data-file=- <<< "haud.tech@gmail.com"

gcloud secrets create email-app-password \
  --data-file=- <<< "xxxx xxxx xxxx xxxx"

# Twilio credentials (optional)
gcloud secrets create twilio-account-sid \
  --data-file=- <<< "ACxxxxxxxxxxxxxxxxxx"

gcloud secrets create twilio-auth-token \
  --data-file=- <<< "your_auth_token_here"
```

**Expected output:**
```
Created secret [email-sender]
Created secret [email-app-password]
...
```

#### Step 3: Verify secrets were created
```bash
gcloud secrets list
```

**Expected output:**
```
NAME                    CREATED
email-sender            2026-03-15T10:00:00Z
email-app-password      2026-03-15T10:00:00Z
twilio-account-sid      2026-03-15T10:00:00Z
twilio-auth-token       2026-03-15T10:00:00Z
```

#### Step 4: Build and push Docker image
```bash
# Set image name
export IMAGE_NAME=gcr.io/YOUR_PROJECT_ID/stock-alerter

# Build locally
docker build -t $IMAGE_NAME .

# Push to Google Container Registry
docker push $IMAGE_NAME
```

**Expected output:**
```
Pushing gcr.io/YOUR_PROJECT_ID/stock-alerter:latest...
...
Successfully pushed
```

#### Step 5: Deploy to Cloud Run
```bash
gcloud run deploy stock-alerter \
  --image $IMAGE_NAME \
  --platform managed \
  --region us-central1 \
  --update-secrets EMAIL_SENDER=email-sender:latest \
  --update-secrets EMAIL_APP_PASSWORD=email-app-password:latest \
  --update-secrets TWILIO_ACCOUNT_SID=twilio-account-sid:latest \
  --update-secrets TWILIO_AUTH_TOKEN=twilio-auth-token:latest \
  --set-env-vars GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID \
  --memory 512Mi \
  --timeout 300
```

**Expected output:**
```
Deploying container to Cloud Run service [stock-alerter]
✓ Deploying...
✓ Creating Revision...
✓ Routing traffic...
Done.
Service URL: https://stock-alerter-xxxxx-uc.a.run.app
```

#### Step 6: Test the deployment
```bash
# View logs
gcloud run services describe stock-alerter --region=us-central1

# Check logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=stock-alerter" \
  --limit 50 \
  --format=json
```

### Troubleshooting

**Problem:** `gcloud: command not found`
- **Solution:** Install Google Cloud SDK

**Problem:** Authentication fails
- **Solution:** Run `gcloud auth login` again

**Problem:** Secrets not accessible
- **Solution:** Check IAM permissions on service account

**Problem:** Container exits on Cloud Run
- **Solution:** Check logs: `gcloud logging read ...`

---

## 4️⃣ AZURE CONTAINER INSTANCES

### Overview
- **Location:** Microsoft Azure
- **Credentials Source:** Azure Key Vault
- **Environment Detection:** Automatic (checks AZURE_KEYVAULT_URL)
- **Best For:** Enterprise Azure deployments

### Prerequisites
- Azure account
- `az` CLI installed
- Resource group created
- Container Registry set up

### Step-by-Step Setup

#### Step 1: Set up Azure credentials
```bash
az login
az account set --subscription YOUR_SUBSCRIPTION_ID
```

**Replace:** `YOUR_SUBSCRIPTION_ID` with your Azure subscription ID

#### Step 2: Create Key Vault
```bash
# Set variables
VAULT_NAME="stock-alerter-vault"
RESOURCE_GROUP="your-resource-group"
LOCATION="eastus"

# Create Key Vault
az keyvault create \
  --name $VAULT_NAME \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Get Vault URI (you'll need this later)
VAULT_URI=$(az keyvault show --name $VAULT_NAME --query properties.vaultUri -o tsv)
echo $VAULT_URI
```

**Expected output:**
```
https://stock-alerter-vault.vault.azure.net/
```

#### Step 3: Add secrets to Key Vault
```bash
# Email credentials
az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name EmailSender \
  --value "haud.tech@gmail.com"

az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name EmailAppPassword \
  --value "xxxx xxxx xxxx xxxx"

# Twilio credentials (optional)
az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name TwilioAccountSid \
  --value "ACxxxxxxxxxxxxxxxxxx"

az keyvault secret set \
  --vault-name $VAULT_NAME \
  --name TwilioAuthToken \
  --value "your_auth_token_here"
```

**Expected output:**
```
{
  "id": "https://stock-alerter-vault.vault.azure.net/secrets/EmailSender/xxxxxxxx",
  ...
}
```

#### Step 4: Verify secrets were created
```bash
az keyvault secret list --vault-name $VAULT_NAME
```

**Expected output:**
```
[
  {
    "id": ".../secrets/EmailSender/...",
    "name": "EmailSender"
  },
  ...
]
```

#### Step 5: Create Container Registry
```bash
REGISTRY_NAME="stockalertregistry"

az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $REGISTRY_NAME \
  --sku Basic
```

**Expected output:**
```
{
  "id": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.ContainerRegistry/registries/xxx",
  "loginServer": "stockalertregistry.azurecr.io"
}
```

#### Step 6: Build and push image
```bash
az acr build \
  --registry $REGISTRY_NAME \
  --image stock-alerter:latest \
  .
```

**Expected output:**
```
Build complete
Image: stockalertregistry.azurecr.io/stock-alerter:latest
```

#### Step 7: Deploy to Container Instances
```bash
az container create \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter \
  --image stockalertregistry.azurecr.io/stock-alerter:latest \
  --cpu 1 \
  --memory 1 \
  --environment-variables \
    AZURE_KEYVAULT_URL=$VAULT_URI \
  --secure-environment-variables \
    AZURE_SUBSCRIPTION_ID=$AZURE_SUBSCRIPTION_ID \
    AZURE_TENANT_ID=$AZURE_TENANT_ID \
    AZURE_CLIENT_ID=$AZURE_CLIENT_ID \
    AZURE_CLIENT_SECRET=$AZURE_CLIENT_SECRET
```

**Expected output:**
```
{
  "id": "/subscriptions/xxx/resourceGroups/xxx/providers/Microsoft.ContainerInstance/containerGroups/stock-alerter",
  "state": "Running"
}
```

#### Step 8: Check logs
```bash
az container logs \
  --resource-group $RESOURCE_GROUP \
  --name stock-alerter
```

### Troubleshooting

**Problem:** `az: command not found`
- **Solution:** Install Azure CLI

**Problem:** Authentication fails
- **Solution:** Run `az login` again

**Problem:** Key Vault permissions denied
- **Solution:** Check IAM role assignments on Key Vault

**Problem:** Container fails to start
- **Solution:** Check logs: `az container logs ...`

---

## 5️⃣ KUBERNETES

### Overview
- **Location:** Any Kubernetes cluster (AWS EKS, GCP GKE, Azure AKS, or local minikube)
- **Credentials Source:** Kubernetes Secrets
- **Environment Detection:** Automatic (checks KUBERNETES_SERVICE_HOST)
- **Best For:** Enterprise multi-cluster deployments

### Prerequisites
- Kubernetes cluster running
- `kubectl` configured
- Docker image in registry accessible to cluster

### Step-by-Step Setup

#### Step 1: Create namespace
```bash
kubectl create namespace stock-alerter
```

**Expected output:**
```
namespace/stock-alerter created
```

#### Step 2: Create Kubernetes secrets
```bash
# Create secret with all credentials
kubectl create secret generic stock-alerter-secrets \
  --from-literal=EMAIL_SENDER="haud.tech@gmail.com" \
  --from-literal=EMAIL_APP_PASSWORD="xxxx xxxx xxxx xxxx" \
  --from-literal=TWILIO_ACCOUNT_SID="ACxxxxxxxxxxxxxxxxxx" \
  --from-literal=TWILIO_AUTH_TOKEN="your_auth_token_here" \
  --namespace=stock-alerter
```

**Expected output:**
```
secret/stock-alerter-secrets created
```

#### Step 3: Verify secrets were created
```bash
kubectl get secrets --namespace=stock-alerter
```

**Expected output:**
```
NAME                    TYPE      DATA
stock-alerter-secrets   Opaque    4
```

#### Step 4: Create deployment manifest
**File:** `kubernetes-manifests.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: stock-alerter
  namespace: stock-alerter
spec:
  replicas: 1
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
        image: gcr.io/YOUR_PROJECT_ID/stock-alerter:latest
        env:
        # Regular environment variables
        - name: EMAIL_ENABLED
          value: "true"
        - name: TWILIO_ENABLED
          value: "false"
        # Credentials from secrets
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
        - name: TWILIO_ACCOUNT_SID
          valueFrom:
            secretKeyRef:
              name: stock-alerter-secrets
              key: TWILIO_ACCOUNT_SID
        - name: TWILIO_AUTH_TOKEN
          valueFrom:
            secretKeyRef:
              name: stock-alerter-secrets
              key: TWILIO_AUTH_TOKEN
        # Kubernetes detection
        - name: KUBERNETES_SERVICE_HOST
          value: "true"
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
```

#### Step 5: Deploy to Kubernetes
```bash
kubectl apply -f kubernetes-manifests.yaml
```

**Expected output:**
```
deployment.apps/stock-alerter created
```

#### Step 6: Verify deployment
```bash
kubectl get deployments --namespace=stock-alerter
```

**Expected output:**
```
NAME            READY   UP-TO-DATE   AVAILABLE
stock-alerter   1/1     1            1
```

#### Step 7: Check pod logs
```bash
kubectl logs -n stock-alerter -l app=stock-alerter -f
```

**Expected output:**
```
✅ Detected environment: Kubernetes
✅ Credentials loaded from Kubernetes Secrets
Starting alerter...
```

### Troubleshooting

**Problem:** `kubectl: command not found`
- **Solution:** Install kubectl

**Problem:** Pod stuck in pending
- **Solution:** Check resources: `kubectl describe pod -n stock-alerter`

**Problem:** Secret not found
- **Solution:** Verify secret exists: `kubectl get secrets -n stock-alerter`

**Problem:** Image pull errors
- **Solution:** Check image is accessible: `kubectl describe pod -n stock-alerter`

---

## 🔍 Verification Checklist

After setup in any environment, verify:

- [ ] Credentials are loaded without errors
- [ ] Application starts successfully
- [ ] Environment is correctly detected
- [ ] No credentials appear in logs
- [ ] Application can connect to services (email, SMS)

### Verification Command (All Environments)
```bash
python -c "
from src.stockreports.config.secrets_loader import SecretsLoader
from src.stockreports.alert.common.environment import EnvironmentType

loader = SecretsLoader()
print(f'✅ Environment detected: {EnvironmentType.get_display_name(loader.env_type)}')
print(f'✅ EMAIL_SENDER: {loader.get_secret(\"EMAIL_SENDER\", default=\"<not set>\")}')
print(f'✅ All credentials loaded successfully!')
"
```

---

## ⚠️ Security Checklist

- [ ] .env file is in .gitignore (Local Development)
- [ ] Never commit .env file (Local Development)
- [ ] Never hardcode credentials in code
- [ ] Never log credentials
- [ ] Use environment-specific secrets management
- [ ] Rotate credentials regularly
- [ ] Monitor secret access in cloud platforms
- [ ] Use least-privilege IAM roles

---

## 🆘 Common Issues & Solutions

### Issue: "Credential not found" error

**Check:**
```bash
# Local Development
cat .env | grep EMAIL_SENDER

# Docker
docker-compose config | grep EMAIL_SENDER

# GCP
gcloud secrets describe email-sender

# Azure
az keyvault secret show --vault-name $VAULT_NAME --name EmailSender

# Kubernetes
kubectl get secret stock-alerter-secrets -o yaml
```

### Issue: Wrong environment detected

**Debug:**
```bash
python -c "
from src.stockreports.config.secrets_loader import SecretsLoader
loader = SecretsLoader()
print(f'Detected: {loader.env_type}')
print(f'is_azure: {loader.is_azure}')
print(f'is_gcp: {loader.is_gcp}')
print(f'is_kubernetes: {loader.is_kubernetes}')
print(f'is_docker: {loader.is_docker}')
"
```

### Issue: Credentials work locally but not in cloud

**Check:**
1. Are IAM permissions set correctly?
2. Does the service have access to secrets?
3. Are secret names correct in deployment?
4. Are credentials properly formatted?

---

**Last Updated:** March 15, 2026  
**Version:** 1.0
