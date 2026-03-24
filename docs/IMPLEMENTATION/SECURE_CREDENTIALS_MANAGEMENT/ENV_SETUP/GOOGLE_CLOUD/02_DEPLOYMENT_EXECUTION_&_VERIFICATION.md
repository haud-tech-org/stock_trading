# 🚀 Cloud Deployment Execution & Verification Guide

**Purpose**: Build, push, and deploy Docker image to Cloud Run with verification  
**Audience**: Ready to deploy (after completing setup guide)  
**Time**: ~15-20 minutes  
**Status**: ✅ Ready to Execute  
**Date**: March 24, 2026  
**Last Tested**: March 20, 2026

---

## Prerequisites

✅ **You must complete `01_DEPLOYMENT_SETUP.md` first**

This guide assumes you have:
- APIs enabled
- Secrets created in Secret Manager
- Service account with proper IAM roles
- Project variables set

---

## Quick Start

Run these 3 commands in sequence to build, push, and deploy:

```bash
# 1. Build Docker image
docker buildx build --platform linux/amd64 -t stock-alerter:latest .

# 2. Tag and push to Container Registry
docker tag stock-alerter:latest gcr.io/stock-trading-489001/stock-alerter:latest
gcloud auth configure-docker
docker push gcr.io/stock-trading-489001/stock-alerter:latest

# 3. Deploy to Cloud Run
gcloud run deploy stock-alerter \
  --image gcr.io/stock-trading-489001/stock-alerter:latest \
  --region europe-west1 \
  --service-account stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --no-allow-unauthenticated \
  --memory 16Gi \
  --cpu 8 \
  --no-cpu-throttling \
  --timeout 300 \
  --max-instances 2
```

---

## Step 7: Build Docker Image

Build the Docker image with the correct platform (Linux x86_64 for Cloud Run).

### Set Environment Variables

```bash
export PROJECT_ID="stock-trading-489001"
export REGION="europe-west1"
export SERVICE_NAME="stock-alerter"
export SERVICE_ACCOUNT_EMAIL="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com"

# Verify variables are set
echo "PROJECT_ID: $PROJECT_ID"
echo "REGION: $REGION"
echo "SERVICE_NAME: $SERVICE_NAME"
echo "SERVICE_ACCOUNT_EMAIL: $SERVICE_ACCOUNT_EMAIL"
```

### Build Image

```bash
# Build Docker image for Linux x86_64 architecture
# CRITICAL: Required if building on Apple Silicon (M1/M2/M3) Mac
docker buildx build --platform linux/amd64 -t stock-alerter:latest .
```

**Alternative if buildx is not available** (Intel/AMD machines):
```bash
docker build -t stock-alerter:latest .
```

**If buildx not found, enable it**:
```bash
docker buildx create --use
docker buildx build --platform linux/amd64 -t stock-alerter:latest .
```

### Actual Execution Result (March 20, 2026)

```
[+] Building 8.1s (11/11) FINISHED                                               
 => [internal] load build definition from Dockerfile                        0.0s
 => [internal] load .dockerignore                                           0.0s
 => [internal] load metadata for docker.io/library/python:3.12-slim-bookwo 7.7s
 => [internal] load build context                                           0.2s
 => [1/6] FROM docker.io/library/python:3.12-slim-bookworm@sha256:31c0807d 0.0s
 => CACHED [2/6] RUN apt-get update && apt-get install -y ...             0.0s
 => CACHED [3/6] WORKDIR /app                                              0.0s
 => CACHED [4/6] COPY requirements.txt .                                   0.0s
 => CACHED [5/6] RUN pip install --no-cache-dir -r requirements.txt        0.0s
 => [6/6] COPY . .                                                         0.1s
 => exporting to image                                                     0.1s
 => exporting layers                                                       0.1s
 => writing image sha256:64bcdcd8ec5a71c8b4966e24f8aacddbf06ba54584f53f   0.0s
 => naming to docker.io/library/stock-alerter:latest                      0.0s
```

**Status**: ✅ Build Time: **8.1 seconds** | Platform: **linux/amd64**  
**Image ID**: `sha256:64bcdcd8ec5a71c8b4966e24f8aacddbf06ba54584f53f`

---

## Step 8: Tag and Push to Container Registry

### Tag Image

```bash
# Tag the locally built image for Google Container Registry
docker tag stock-alerter:latest gcr.io/$PROJECT_ID/stock-alerter:latest

# Verify image exists locally
docker images | grep stock-alerter
```

**Actual Execution Result (March 20, 2026)**:
```
✓ Image tagged as: gcr.io/stock-trading-489001/stock-alerter:latest
```

**Status**: ✅ Image successfully tagged

### Authenticate Docker

```bash
# Configure Docker to authenticate with GCP
gcloud auth configure-docker

# This updates ~/.docker/config.json with GCP credentials
# Verify authentication worked:
cat ~/.docker/config.json | grep -A 5 "gcr.io"
```

**Actual Execution Result (March 20, 2026)**:
```
WARNING: Your config file at [/Users/haudo/.docker/config.json] contains these credential helper entries:
{
  "credHelpers": {
    "us.gcr.io": "gcloud",
    "asia.gcr.io": "gcloud",
    "marketplace.gcr.io": "gcloud",
    "gcr.io": "gcloud",
    "eu.gcr.io": "gcloud",
    "staging-k8s.gcr.io": "gcloud"
  }
}
Adding credentials for all GCR repositories.
WARNING: A long list of credential helpers may cause delays running 'docker build'.
gcloud credential helpers already registered correctly.
✓ Docker is now authenticated with GCP
```

**Status**: ✅ Docker authentication configured

### Push to Registry

```bash
# Push the image to GCP Container Registry
docker push gcr.io/$PROJECT_ID/stock-alerter:latest

# Watch the upload progress (shows layer digest and push confirmation)
# Takes 2-5 minutes depending on image size and connection

# Verify image was pushed successfully
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Check image details
gcloud container images describe gcr.io/$PROJECT_ID/stock-alerter:latest
```

**Actual Execution Result (March 20, 2026)**:
```
The push refers to repository [gcr.io/stock-trading-489001/stock-alerter]
20eb0acb092c: Pushed
3f1c1d92bb7e: Pushed
e0fdf4f6d38c: Pushed
...
latest: digest: sha256:a3c6f776aa49a93065a05bcc794106dac89e61fcacf04f5b926d72ab6e09e266 size: 2847
```

**Status**: ✅ Image pushed successfully  
**Image Digest**: `sha256:a3c6f776aa49a93065a05bcc794106dac89e61fcacf04f5b926d72ab6e09e266`

---

## Step 9: Deploy to Cloud Run

Deploy the Docker image to Cloud Run with environment variables and secrets.

### Deployment Command

```bash
# Export variables for the deployment command
export PROJECT_ID="stock-trading-489001"
export REGION="europe-west1"
export SERVICE_NAME="stock-alerter"
export SERVICE_ACCOUNT_EMAIL="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com"

# Deploy to Cloud Run
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --no-allow-unauthenticated \
  --memory 16Gi \
  --cpu 8 \
  --no-cpu-throttling \
  --cpu-boost \
  --timeout 300 \
  --min-instances 1 \
  --max-instances 2 \
  --execution-environment gen2 \
  --set-env-vars EMAIL_ENABLED=true,EMAIL_SMTP_SERVER=smtp.gmail.com,EMAIL_SMTP_PORT=587,EMAIL_RECEIVERS=haud.fin@gmail.com,EMAIL_BCC_RECEIVERS=haud.fin@gmail.com,NTFY_ENABLED=false,NTFY_TOPICS=vn30_alerts_f8a9b2c1,TWILIO_ENABLED=false,TWILIO_PHONE_NUMBER="",SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets EMAIL_SENDER=email-sender:latest,EMAIL_APP_PASSWORD=email-app-password:latest,EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest
```

### Key Deployment Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| `--memory` | 16Gi | Maximum for optimal performance |
| `--cpu` | 8 cores | Maximum for parallel processing |
| `--no-cpu-throttling` | Set | Instance-based billing (always available CPU) |
| `--cpu-boost` | Set | Faster container startup |
| `--timeout` | 300s | 5 minutes for complete alert cycle |
| `--max-instances` | 2 | Cost control with high-resource config |
| `--no-allow-unauthenticated` | Set | Secure production (requires IAM) |
| `--execution-environment` | gen2 | 2nd generation runtime (better performance) |

### Actual Execution Result (March 20, 2026)

```
Deploying service [stock-alerter] in region [europe-west1]
✓ Deploying new service... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.

Service [stock-alerter] revision [stock-alerter-00002-wz8] has been deployed and is serving 100 percent of traffic.
Service URL: https://stock-alerter-717776322217.europe-west1.run.app
```

**Status**: ✅ Deployment successful  
**Service URL**: `https://stock-alerter-717776322217.europe-west1.run.app`  
**Revision**: `stock-alerter-00002-wz8`

---

## Step 10: Verify Deployment

Verify that the Cloud Run service has been deployed successfully and is responding to requests.

### Get Service URL

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"
```

### Test Health Endpoint

```bash
# Test the health endpoint (requires authentication)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $SERVICE_URL/health
```

**Actual Execution Result (March 20, 2026)**:
```json
{"status": "ok"}
```

**Status**: ✅ Service responding correctly

### View Deployment Logs

```bash
# View recent deployment logs
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --limit 50

# View live logs (streaming)
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --stream
```

### View Service Details

```bash
# Get complete service details
gcloud run services describe $SERVICE_NAME --region=$REGION

# Get JSON format for scripting
gcloud run services describe $SERVICE_NAME \
  --region=$REGION \
  --format=json
```

---

## ✅ Deployment Verification Checklist

- [ ] Docker image built successfully (8.1s or similar)
- [ ] Image tagged for Container Registry
- [ ] Docker authenticated with GCP
- [ ] Image pushed to Container Registry
- [ ] Image digest captured
- [ ] Cloud Run deployment command executed
- [ ] Service URL generated and noted
- [ ] Revision ID captured (format: `stock-alerter-00002-xxx`)
- [ ] Health endpoint responds with `{"status": "ok"}`
- [ ] Recent logs show no errors
- [ ] Service traffic shows 100%

---

## 🚀 Next Steps

After successful deployment:

1. **Operations**: Proceed to `03_OPERATIONS_&_REFERENCE.md` for daily operations
2. **Monitoring**: Set up monitoring and alerts (in operations guide)
3. **Scheduler**: Configure Cloud Scheduler for automated execution (in operations guide)

---

## 🔗 Related Guides

- **Setup Guide**: `01_DEPLOYMENT_SETUP.md`
- **Operations & Reference**: `03_OPERATIONS_&_REFERENCE.md`
- **Execution Log (Reference)**: `DEPLOYMENT_EXECUTION_LOG_20260320.md`
- **Full Original Guide**: `GOOGLE_CLOUD_DEPLOYMENT.md`

---

## ⚠️ Troubleshooting

### Error: "failed to load /usr/local/bin/python: exec format error"

**Cause**: Image built for ARM64 (Mac) instead of x86_64 (Cloud Run)

**Solution**:
```bash
# Build with correct platform
docker buildx build --platform linux/amd64 -t stock-alerter:latest .

# Enable buildx if needed
docker buildx create --use
```

### Error: "The user-provided container image could not be pulled"

**Cause**: Image doesn't exist or wrong project ID

**Solution**:
```bash
# Verify image exists
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Verify image details
gcloud container images describe gcr.io/$PROJECT_ID/stock-alerter:latest

# Re-push if needed
docker push gcr.io/$PROJECT_ID/stock-alerter:latest
```

### Error: "Permission denied" when pushing image

**Cause**: Docker not authenticated with GCP

**Solution**:
```bash
# Re-authenticate Docker
gcloud auth configure-docker

# Clear Docker credentials if needed
rm ~/.docker/config.json
gcloud auth configure-docker
```

### Service not starting (Container failed to start)

**Cause**: Application doesn't bind to port 8080 or crashes on startup

**Solution**:
```bash
# Check container startup logs
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --limit=20 \
  --format=json

# Increase timeout if app takes longer to start
gcloud run deploy stock-alerter \
  --region=$REGION \
  --timeout=600  # 10 minutes
```

### Service is running but health check fails

**Cause**: Application doesn't have `/health` endpoint or authentication issue

**Solution**:
```bash
# Test with authentication token
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  $SERVICE_URL/health

# Check if service requires different endpoint
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format=json | grep -i "error\|404\|endpoint"
```
