# 🚀 Quick Deploy Reference - Stock Alerter Service

**Last Updated**: March 27, 2026  
**Status**: ✅ Verified & Working

## One-Command Full Deployment

```bash
# Complete deployment in 3 steps
cd /Users/tech/dev/stock_trading && \
export PROJECT_ID="stock-trading-489001" REGION="europe-west1" SERVICE_NAME="stock-alerter" SERVICE_ACCOUNT="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com" && \
docker buildx build --platform linux/amd64 -t stock-alerter:latest . && \
docker tag stock-alerter:latest gcr.io/$PROJECT_ID/stock-alerter:latest && \
gcloud auth configure-docker && \
docker push gcr.io/$PROJECT_ID/stock-alerter:latest && \
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT \
  --no-allow-unauthenticated \
  --memory 16Gi --cpu 8 --no-cpu-throttling --cpu-boost \
  --timeout 300 --min-instances 1 --max-instances 2 \
  --execution-environment gen2 \
  --add-volume=name=gcs-1,type=cloud-storage,bucket=stock-trading-2 \
  --add-volume-mount=volume=gcs-1,mount-path=/mnt \
  --set-env-vars EMAIL_ENABLED=true,EMAIL_SMTP_SERVER=smtp.gmail.com,EMAIL_SMTP_PORT=587,EMAIL_RECEIVERS=haud.fin@gmail.com,EMAIL_BCC_RECEIVERS=haud.fin@gmail.com,NTFY_ENABLED=false,NTFY_TOPICS=vn30_alerts_f8a9b2c1,TWILIO_ENABLED=false,TWILIO_PHONE_NUMBER="",SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets EMAIL_SENDER=email-sender:latest,EMAIL_APP_PASSWORD=email-app-password:latest,EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest
```

## Step-by-Step Commands

### 1. Build Image
```bash
cd /Users/tech/dev/stock_trading
docker buildx build --platform linux/amd64 -t stock-alerter:latest .
```

### 2. Tag & Push
```bash
docker tag stock-alerter:latest gcr.io/stock-trading-489001/stock-alerter:latest
gcloud auth configure-docker
docker push gcr.io/stock-trading-489001/stock-alerter:latest
```

### 3. Deploy
```bash
export PROJECT_ID="stock-trading-489001"
export REGION="europe-west1"
export SERVICE_NAME="stock-alerter"
export SERVICE_ACCOUNT_EMAIL="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com"

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
  --add-volume=name=gcs-1,type=cloud-storage,bucket=stock-trading-2 \
  --add-volume-mount=volume=gcs-1,mount-path=/mnt \
  --set-env-vars EMAIL_ENABLED=true,EMAIL_SMTP_SERVER=smtp.gmail.com,EMAIL_SMTP_PORT=587,EMAIL_RECEIVERS=haud.fin@gmail.com,EMAIL_BCC_RECEIVERS=haud.fin@gmail.com,NTFY_ENABLED=false,NTFY_TOPICS=vn30_alerts_f8a9b2c1,TWILIO_ENABLED=false,TWILIO_PHONE_NUMBER="",SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets EMAIL_SENDER=email-sender:latest,EMAIL_APP_PASSWORD=email-app-password:latest,EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latest
```

## Verification Commands

### Get Service URL
```bash
gcloud run services describe stock-alerter --region=europe-west1 --format='value(status.url)'
```

### Test Health Endpoint
```bash
SERVICE_URL=$(gcloud run services describe stock-alerter --region=europe-west1 --format='value(status.url)')
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" "$SERVICE_URL/health"
```

### View Logs
```bash
gcloud run services logs read stock-alerter --region=europe-west1 --limit 50
```

### Get Service Details
```bash
gcloud run services describe stock-alerter --region=europe-west1
```

### View Real-time Logs
```bash
gcloud run services logs read stock-alerter --region=europe-west1 --stream
```

## Service URLs

**Production URL**: `https://stock-alerter-717776322217.europe-west1.run.app`

## Configuration Summary

| Component | Value |
|-----------|-------|
| Service Name | stock-alerter |
| Image | gcr.io/stock-trading-489001/stock-alerter:latest |
| Region | europe-west1 |
| Memory | 16Gi |
| CPU | 8 cores (always allocated) |
| Timeout | 300 seconds |
| Min Instances | 1 |
| Max Instances | 2 |
| Execution Environment | Gen2 |
| Service Account | stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com |
| GCS Bucket | stock-trading-2 (/mnt) |
| Authentication | Required |

## Troubleshooting

### Docker not running
```bash
open -a Docker
```

### Clean and rebuild
```bash
docker buildx prune -a
docker buildx build --platform linux/amd64 -t stock-alerter:latest . --no-cache
```

### Push failed - re-authenticate
```bash
rm ~/.docker/config.json
gcloud auth configure-docker
docker push gcr.io/stock-trading-489001/stock-alerter:latest
```

### View deployment errors
```bash
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=stock-alerter AND severity=ERROR" --limit=20 --format=json
```

## Last Deployment

**Date**: March 27, 2026  
**Status**: ✅ Success  
**Revision**: stock-alerter-00002-pv4  
**Build Time**: 7.7 seconds  
**Image Digest**: sha256:eb08b5c7e02423b5b1f3e8559f051902822caebc689d55a749315c4f90c02ee4

