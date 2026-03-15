# Google Cloud Run Deployment Guide

This guide covers deploying the Stock Alerter application to Google Cloud Run using Google Secret Manager for credential management.

## Prerequisites

- Google Cloud CLI (gcloud) installed and configured
- Active Google Cloud project
- Docker image built and pushed to Google Container Registry
- Appropriate IAM permissions

## Step 1: Set Up Project Variables

```bash
# Set your project ID
PROJECT_ID="your-gcp-project-id"
REGION="us-central1"  # Change as needed
SERVICE_NAME="stock-alerter"

# Set active project
gcloud config set project $PROJECT_ID
```

## Step 2: Enable Required APIs

```bash
# Enable necessary APIs
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com
```

## Step 3: Create Secrets in Google Secret Manager

```bash
# Create email credentials
echo -n "your-email@gmail.com" | gcloud secrets create email-sender \
  --data-file=-

echo -n "xxxx xxxx xxxx xxxx" | gcloud secrets create email-app-password \
  --data-file=-

echo -n "Stock Alerter (No-Reply)" | gcloud secrets create email-sender-display-name \
  --data-file=-

# Create Twilio credentials (if using SMS)
echo -n "ACxxxxxxxxxxxxxxxxxx" | gcloud secrets create twilio-account-sid \
  --data-file=-

echo -n "your_auth_token_here" | gcloud secrets create twilio-auth-token \
  --data-file=-
```

## Step 4: Create Service Account

```bash
# Create service account
gcloud iam service-accounts create stock-alerter-sa \
  --display-name="Stock Alerter Service Account"

# Get service account email
SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Stock Alerter Service Account" \
  --format='value(email)')

echo "Service Account: $SERVICE_ACCOUNT_EMAIL"
```

## Step 5: Grant Secret Access Permissions

```bash
# Grant the service account permission to access secrets
for secret in email-sender email-app-password email-sender-display-name twilio-account-sid twilio-auth-token; do
  gcloud secrets add-iam-policy-binding $secret \
    --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
    --role=roles/secretmanager.secretAccessor
done
```

## Step 6: Build and Push Docker Image

```bash
# Build Docker image
docker build -t stock-alerter:latest .

# Tag image for Google Container Registry
docker tag stock-alerter:latest gcr.io/$PROJECT_ID/stock-alerter:latest

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/stock-alerter:latest

# Alternative: Use Cloud Build
gcloud builds submit --tag gcr.io/$PROJECT_ID/stock-alerter:latest
```

## Step 7: Deploy to Cloud Run

```bash
# Deploy to Cloud Run with secret references
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars \
    GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
    EMAIL_ENABLED=true,\
    EMAIL_RECEIVERS="recipient@example.com",\
    EMAIL_BCC_RECEIVERS="admin@example.com",\
    NTFY_ENABLED=false,\
    TWILIO_ENABLED=false \
  --set-secrets \
    EMAIL_SENDER=email-sender:latest,\
    EMAIL_APP_PASSWORD=email-app-password:latest,\
    EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,\
    TWILIO_ACCOUNT_SID=twilio-account-sid:latest,\
    TWILIO_AUTH_TOKEN=twilio-auth-token:latest \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300 \
  --max-instances 10
```

## Step 8: Verify Deployment

```bash
# Get service URL
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format='value(status.url)'

# View logs
gcloud run services logs read $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --limit 50

# Test the service
curl $(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format='value(status.url)')/health
```

## Step 9: Update Secrets

To update a secret without redeploying the entire service:

```bash
# Update the secret
echo -n "new_password_here" | gcloud secrets versions add email-app-password \
  --data-file=-

# The Cloud Run service will automatically pick up the new version on next invocation
# For immediate effect, redeploy:
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --update-secrets EMAIL_APP_PASSWORD=email-app-password:latest
```

## Step 10: Set Up Scheduled Execution (Optional)

If you want to run the alerter on a schedule:

```bash
# Create Cloud Scheduler job
gcloud scheduler jobs create http stock-alerter-scheduler \
  --location=$REGION \
  --schedule="0 */4 * * *" \
  --uri=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format='value(status.url)')/run \
  --http-method=POST \
  --oidc-service-account-email=$SERVICE_ACCOUNT_EMAIL \
  --oidc-token-audience=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format='value(status.url)')

# Update job
gcloud scheduler jobs update http stock-alerter-scheduler \
  --location=$REGION \
  --schedule="0 */4 * * *"

# View job
gcloud scheduler jobs describe stock-alerter-scheduler --location=$REGION

# Trigger job manually
gcloud scheduler jobs run stock-alerter-scheduler --location=$REGION

# View job history/logs
gcloud scheduler jobs run stock-alerter-scheduler --location=$REGION
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=stock-alerter-scheduler" --limit=10
```

## Step 11: Monitor and Troubleshoot

```bash
# View real-time logs
gcloud run services logs read $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --stream

# View metrics
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "Stock Alerter Dashboard",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Request Count",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_count\" resource.type=\"cloud_run_revision\"",
                  "aggregation": {
                    "alignmentPeriod": "60s"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
EOF

# Check service quota
gcloud compute project-info describe --project=$PROJECT_ID \
  --format='value(quotas[].limit)'
```

## Step 12: Cleanup

```bash
# Delete Cloud Run service
gcloud run services delete $SERVICE_NAME \
  --platform managed \
  --region $REGION

# Delete secrets
for secret in email-sender email-app-password email-sender-display-name twilio-account-sid twilio-auth-token; do
  gcloud secrets delete $secret
done

# Delete service account
gcloud iam service-accounts delete $SERVICE_ACCOUNT_EMAIL
```

## Cost Optimization

- **Cloud Run Free Tier**: 2M requests/month, 400k GB-seconds/month
- **Secret Manager**: 6 active secret versions free, then $0.06/version/month
- **Cloud Scheduler**: 3 free jobs, then $0.10/job/month
- **Cloud Logging**: 50GB/month free, then charged per GB

## Troubleshooting

### Secret Access Error

If you see "Permission denied" errors:

```bash
# Verify service account has secret access
gcloud secrets get-iam-policy email-sender

# Re-grant permissions if needed
gcloud secrets add-iam-policy-binding email-sender \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor
```

### Service Not Starting

```bash
# Check detailed error logs
gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION

# View full deployment logs
gcloud logging read "resource.type=cloud_run_revision" --limit=50
```

### GOOGLE_CLOUD_PROJECT Environment Variable

The `GOOGLE_CLOUD_PROJECT` environment variable is automatically set by Cloud Run. If not appearing:

```bash
# Explicitly set it
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --set-env-vars GOOGLE_CLOUD_PROJECT=$PROJECT_ID
```

## Security Best Practices

1. **Use Service Accounts**: Never use default compute service account
2. **Least Privilege**: Grant only required permissions
3. **Network Security**: Use VPC connectors for private databases
4. **Monitoring**: Enable Cloud Logging and set up alerts
5. **Secret Rotation**: Implement automatic secret rotation
6. **IAM Audit Logs**: Enable Cloud Audit Logs for compliance

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)
