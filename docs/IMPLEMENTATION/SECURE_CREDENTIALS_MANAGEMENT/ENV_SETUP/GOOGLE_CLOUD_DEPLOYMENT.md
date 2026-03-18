# Google Cloud Run Deployment Guide

This guide covers deploying the Stock Alerter application to Google Cloud Run using Google Secret Manager for credential management.

## Prerequisites

- Google Cloud CLI (gcloud) installed and configured
- Active Google Cloud project
- Docker image built and pushed to Google Container Registry
- Appropriate IAM permissions
- Python 3.12+

## Step 1: Set Up Project Variables

Initialize your deployment by setting up project-level variables that will be used throughout all deployment steps.

```bash
# Set your Google Cloud project ID - Replace with your actual project ID
PROJECT_ID="stock-trading-489001"

# Set the region where resources will be deployed
# europe-west1 = Belgium (used for compliance/data residency)
# us-central1 = Iowa (default, cheapest)
# Other options: europe-north1, us-west1, asia-southeast1
REGION="europe-west1"

# Name of the Cloud Run service - This will be part of your service URL
SERVICE_NAME="stock-alerter"

# Set the active project for all subsequent gcloud commands
gcloud config set project $PROJECT_ID
```

**Explanation**:
- `PROJECT_ID`: The GCP project identifier where all resources will be created
- `REGION`: Geographic location for resource deployment (affects latency and compliance)
- `SERVICE_NAME`: Identifier for your Cloud Run service (must be unique within the project)
- `gcloud config set`: Configures gcloud to use your project by default

## Step 2: Enable Required APIs

Enable the Google Cloud APIs needed for running the Stock Alerter service.

```bash
# Enable necessary APIs for Cloud Run and related services
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com
```

**Argument Explanations**:
- `run.googleapis.com`: Cloud Run API - enables serverless container deployment
- `secretmanager.googleapis.com`: Secret Manager API - enables secure credential storage
- `artifactregistry.googleapis.com`: Artifact Registry API - enables container image storage
- `compute.googleapis.com`: Compute Engine API - enables VM and networking resources

## Step 3: Create Secrets in Google Secret Manager

Store sensitive credentials securely in Google Secret Manager instead of environment variables.

```bash
# Store email address used to send alerts
echo -n "your-email@gmail.com" | gcloud secrets create email-sender \
  --data-file=-

# Store Gmail App Password (not your main Gmail password)
# Generate at: https://myaccount.google.com/apppasswords
echo -n "xxxx xxxx xxxx xxxx" | gcloud secrets create email-app-password \
  --data-file=-

# Store the display name for email sender
echo -n "Stock Alerter (No-Reply)" | gcloud secrets create email-sender-display-name \
  --data-file=-

# Store Twilio Account SID (if using SMS alerts)
echo -n "ACxxxxxxxxxxxxxxxxxx" | gcloud secrets create twilio-account-sid \
  --data-file=-

# Store Twilio Auth Token (if using SMS alerts)
echo -n "your_auth_token_here" | gcloud secrets create twilio-auth-token \
  --data-file=-
```

**Argument Explanations**:
- `echo -n`: Outputs text without newline (secrets should not have trailing newlines)
- `--data-file=-`: Reads secret data from stdin (the pipe `|`)
- Secret names must be lowercase alphanumeric with hyphens (no underscores)
- Each secret is versioned; you can create new versions without deleting

**Why use Secret Manager?**
- Secrets are encrypted at rest in Google's vaults
- Access is logged and auditable
- Fine-grained IAM permissions
- No secrets in environment variables or code

## Step 4: Create Service Account

Create a dedicated service account for the Cloud Run service with limited permissions.

```bash
# Create a service account specifically for the Stock Alerter
gcloud iam service-accounts create stock-alerter-sa \
  --display-name="Stock Alerter Service Account" \
  --description="Service account for stock alert generation and notification"

# Store the service account email for later use
SERVICE_ACCOUNT_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Stock Alerter Service Account" \
  --format='value(email)')

# Print the service account email for reference
echo "Service Account Email: $SERVICE_ACCOUNT_EMAIL"
```

**Argument Explanations**:
- `gcloud iam service-accounts create`: Creates a new service account
- `--display-name`: Human-readable name (visible in Cloud Console)
- `--description`: Purpose of the service account (best practice)
- `--filter`: Finds services matching criteria
- `--format='value(email)'`: Outputs only the email address

**Why use Service Accounts?**
- Provides identity for the Cloud Run service
- Enables fine-grained permissions (least privilege principle)
- Audit trail of actions performed by the service
- Prevents accidental exposure of your personal credentials

## Step 5: Grant Secret Access Permissions

Grant the service account permission to access the secrets created in Step 3.

```bash
# For each secret, grant the service account read-only access
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token; do
  gcloud secrets add-iam-policy-binding $secret \
    --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
    --role=roles/secretmanager.secretAccessor
done
```

**Argument Explanations**:
- `gcloud secrets add-iam-policy-binding`: Adds an IAM binding to a secret
- `$secret`: The name of the secret to grant access to
- `--member=serviceAccount:$SERVICE_ACCOUNT_EMAIL`: The service account getting access
- `--role=roles/secretmanager.secretAccessor`: Pre-defined role for reading secrets (no create/delete)

**Why this permission?**
- `secretAccessor` allows reading secret values but not modifying them
- Service account can only access secrets you explicitly grant
- Follows the principle of least privilege

## Step 6: Grant Additional Permissions

Grant the service account additional roles needed for the application to function.

```bash
# Grant Storage Object Admin role (for Cloud Storage access)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/storage.objectAdmin \
  --condition=None

# Grant Cloud Run Invoker role (allows execution)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/run.invoker \
  --condition=None
```

**Argument Explanations**:
- `gcloud projects add-iam-policy-binding`: Grants a role at the project level
- `--member=serviceAccount:...`: The service account being granted the role
- `roles/storage.objectAdmin`: Allows full read/write access to Cloud Storage buckets
- `roles/run.invoker`: Allows the service account to invoke Cloud Run services
- `--condition=None`: No conditions on this binding (applies in all contexts)

**Permissions Granted**:
- `storage.objectAdmin`: Access to stored alert data and reports
- `run.invoker`: Ability to trigger scheduled executions via Cloud Scheduler

## Step 7: Build and Push Docker Image

Build the Docker image locally and push to Google Container Registry.

```bash
# Build Docker image from Dockerfile in current directory
docker build -t stock-alerter:latest .

# Tag image for Google Container Registry
# Format: gcr.io/{project-id}/{image-name}:{tag}
docker tag stock-alerter:latest gcr.io/$PROJECT_ID/stock-alerter:latest

# Configure Docker to authenticate with GCP
gcloud auth configure-docker

# Push image to Google Container Registry
# This uploads the image so Cloud Run can pull it for deployment
docker push gcr.io/$PROJECT_ID/stock-alerter:latest

# Verify image was pushed successfully
gcloud container images list --repository=gcr.io/$PROJECT_ID
```

**Argument Explanations**:
- `docker build -t {image-name}:{tag} .`: Builds image from Dockerfile in current directory
  - `-t`: Tag (name and version) for the image
  - `.`: Build context (uses Dockerfile in current directory)
- `docker tag {source} {target}`: Creates a new tag pointing to an existing image
- `gcloud auth configure-docker`: Authenticates Docker with GCP credentials
- `docker push {image}`: Uploads image to the registry

**Alternative: Use Cloud Build** (builds on GCP infrastructure instead of locally):
```bash
gcloud builds submit --region=$REGION \
  --tag=gcr.io/$PROJECT_ID/stock-alerter:latest
```

**Advantage of Cloud Build**:
- No need to push from your machine
- Uses GCP's infrastructure (faster for large images)
- Integrated with GCP ecosystem

## Step 8: Deploy to Cloud Run

Deploy the Docker image to Cloud Run with environment variables and secrets.

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
  --set-env-vars \
    EMAIL_ENABLED=true,\
    EMAIL_SMTP_SERVER="smtp.gmail.com",\
    EMAIL_SMTP_PORT="587",\
    EMAIL_RECEIVERS="haud.fin@gmail.com",\
    EMAIL_BCC_RECEIVERS="haud.fin@gmail.com",\
    NTFY_ENABLED=false,\
    NTFY_TOPICS="vn30_alerts_f8a9b2c1",\
    TWILIO_ENABLED=false,\
    TWILIO_PHONE_NUMBER="",\
    SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets \
    EMAIL_SENDER=email-sender:latest,\
    EMAIL_APP_PASSWORD=email-app-password:latest,\
    EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,\
    TWILIO_ACCOUNT_SID=twilio-account-sid:latest,\
    TWILIO_AUTH_TOKEN=twilio-auth-token:latest \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --allow-unauthenticated \
  --memory 16Gi \
  --cpu 8 \
  --timeout 600 \
  --max-instances 2
```

**Core Arguments**:
- `--image`: Container image to deploy (from Container Registry)
- `--platform managed`: Use Cloud Run fully managed (serverless)
- `--region`: Geographic region for the service
- `--service-account`: Service account with necessary permissions

**Environment Variables** (`--set-env-vars`):
- `EMAIL_ENABLED=true`: Enable email notifications
- `EMAIL_SMTP_SERVER="smtp.gmail.com"`: Gmail SMTP server address
- `EMAIL_SMTP_PORT="587"`: SMTP port (TLS)
- `EMAIL_RECEIVERS`: Comma-separated list of recipient emails
- `EMAIL_BCC_RECEIVERS`: Comma-separated list of BCC recipients
- `NTFY_ENABLED=false`: Disable ntfy.sh notifications (set `true` to enable)
- `NTFY_TOPICS`: Topic ID for ntfy.sh notifications
- `TWILIO_ENABLED=false`: Disable SMS notifications (set `true` to enable)
- `TWILIO_PHONE_NUMBER`: Sender phone number (if SMS enabled)
- `SMS_RECEIVER_PHONE_NUMBER`: Recipient phone number (if SMS enabled)

**Secrets** (`--set-secrets`):
- Format: `ENV_VAR_NAME=secret-name:version`
- `latest`: Always use the latest version of the secret
- Secrets are injected as environment variables at runtime
- Values are never visible in Cloud Console or logs

**Resource Specifications**:
- `--memory 16Gi`: Memory allocation (16 GB)
  - Minimum: 256Mi
  - Maximum: 16Gi
  - More memory = faster startup, higher cost
- `--cpu 8`: CPU allocation (8 cores)
  - Minimum: 1 (with 256Mi-3.5Gi memory)
  - Maximum: 8 (with 4Gi-16Gi memory)
- `--timeout 600`: Maximum execution time in seconds (10 minutes)
  - Must be 60-3600 seconds
  - Longer timeouts wait longer before health check failure
- `--max-instances 2`: Maximum number of concurrent service instances
  - Limits cost and resource usage
  - Auto-scales based on request load up to this limit
- `--allow-unauthenticated`: Allow public access (no authentication required)
  - Remove this flag to require authentication

# Deploy to Cloud Run with secret references
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --set-env-vars \
    GOOGLE_CLOUD_PROJECT=$PROJECT_ID,\
    EMAIL_ENABLED=true,\
    EMAIL_SMTP_SERVER="smtp.gmail.com",\
    EMAIL_SMTP_PORT="587",\
    EMAIL_RECEIVERS="recipient@example.com",\
    EMAIL_BCC_RECEIVERS="admin@example.com",\
    EMAIL_SENDER_DISPLAY_NAME="[GC] Stock Alerter (No-Reply)",\
    NTFY_ENABLED=false,\
    NTFY_TOPICS="vn30_alerts_f8a9b2c1",\
    TWILIO_ENABLED=false,\
    TWILIO_PHONE_NUMBER="",\
    SMS_RECEIVER_PHONE_NUMBER="" \
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

## Step 9: Verify Deployment

Verify that the Cloud Run service has been deployed successfully and is responding to requests.

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test the health endpoint
curl $SERVICE_URL/health

# Expected response:
# {"status": "ok"}
```

**Explanation**:
- Retrieves the auto-generated HTTPS URL for your Cloud Run service
- Tests the `/health` endpoint to verify the service is running
- Health endpoint responds immediately (no background tasks)

```bash
# View recent deployment logs
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --limit 50
```

**Argument Explanations**:
- `--limit 50`: Shows the last 50 log entries
- Logs include container startup, environment variable loading, errors

## Step 10: Update Secrets

To update a secret without redeploying the entire service.

```bash
# Update an existing secret with a new value
echo -n "new_password_here" | gcloud secrets versions add email-app-password \
  --data-file=-

# Cloud Run automatically picks up the new version on next invocation
# For immediate effect with service redeploy:
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --region $REGION \
  --update-secrets EMAIL_APP_PASSWORD=email-app-password:latest
```

**Argument Explanations**:
- `gcloud secrets versions add`: Creates a new version of an existing secret
- `--update-secrets`: Updates which secret versions the service uses
- `latest`: Always references the most recent version

**Important**: Secret updates take effect on the next service invocation. To force immediate update, redeploy the service or wait for the next scheduled execution.

## Step 11: Set Up Scheduled Execution (Optional)

Configure Cloud Scheduler to trigger the alert generation on a schedule (e.g., every hour, every 4 hours).

```bash
# Create a Cloud Scheduler job to trigger alerts periodically
gcloud scheduler jobs create http $SERVICE_NAME-scheduler \
  --location=$REGION \
  --schedule="*/60 * * * *" \
  --uri="$SERVICE_URL/run-alerts" \
  --http-method=POST \
  --oidc-service-account-email=$SERVICE_ACCOUNT_EMAIL \
  --oidc-token-audience=$SERVICE_URL
```

**Argument Explanations**:
- `gcloud scheduler jobs create http`: Creates an HTTP-based scheduled job
- `--location`: Region for the scheduler (must match Cloud Run region)
- `--schedule`: Cron expression for when to run
  - `*/60 * * * *`: Every 60 minutes (hourly)
  - `0 */4 * * *`: Every 4 hours at 0 minutes
  - `0 9-17 * * MON-FRI`: 9 AM to 5 PM weekdays
  - `0 */1 * * *`: Every minute (for frequent updates)
- `--uri`: The endpoint to call (`/run-alerts` endpoint)
- `--http-method=POST`: HTTP method to use
- `--oidc-service-account-email`: Service account for authentication
- `--oidc-token-audience`: Target service for the OIDC token

**Update a scheduled job**:
```bash
# Modify the schedule
gcloud scheduler jobs update http $SERVICE_NAME-scheduler \
  --location=$REGION \
  --schedule="0 */4 * * *"  # Change to every 4 hours

# View job details
gcloud scheduler jobs describe $SERVICE_NAME-scheduler --location=$REGION

# Trigger job manually (for testing)
gcloud scheduler jobs run $SERVICE_NAME-scheduler --location=$REGION

# View job execution history
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=$SERVICE_NAME-scheduler" \
  --limit=10 \
  --format=json
```

**Cron Expression Reference**:
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6, Sunday=0)
│ │ │ │ │
│ │ │ │ │
* * * * *

Examples:
0 */1 * * *     Every hour at minute 0
*/15 * * * *    Every 15 minutes
0 9 * * *       Daily at 9 AM
0 */4 * * *     Every 4 hours
0 9-17 * * 1-5  Weekdays 9 AM to 5 PM
```

## Step 12: Monitor and Troubleshoot

Monitor the Cloud Run service for errors and performance issues.

```bash
# View real-time logs (streaming)
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --stream \
  --limit 50
```

**Arguments**:
- `--stream`: Continuously shows new log entries (like `tail -f`)
- `--limit 50`: Initial number of historical entries to show

```bash
# View detailed service information
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format=json

# Check if service is running and responsive
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format='value(status.conditions[].message)'
```

**Troubleshoot Common Issues**:

### Service Not Starting

```bash
# Check detailed error messages
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --limit=20 \
  --format=json

# Check container startup logs
gcloud logging read "resource.type=cloud_run_revision" \
  --order=desc \
  --limit=50
```

### Secret Access Denied

```bash
# Verify service account has secret access
gcloud secrets get-iam-policy email-sender

# Re-grant if needed
gcloud secrets add-iam-policy-binding email-sender \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor
```

### High Memory Usage

```bash
# View memory and CPU metrics
gcloud monitoring dashboards create --config-from-file=- <<EOF
{
  "displayName": "Stock Alerter Metrics",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "Memory Usage",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "metric.type=\"run.googleapis.com/request_latencies\" resource.type=\"cloud_run_revision\" resource.labels.service_name=\"$SERVICE_NAME\""
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
```

## Step 13: Cleanup Resources

Remove all deployed resources when no longer needed.

```bash
# Delete Cloud Run service
gcloud run services delete $SERVICE_NAME \
  --region $REGION \
  --quiet

# Delete Cloud Scheduler job (if created)
gcloud scheduler jobs delete $SERVICE_NAME-scheduler \
  --location=$REGION \
  --quiet

# Delete all secrets
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token; do
  gcloud secrets delete $secret --quiet
done

# Delete service account
gcloud iam service-accounts delete $SERVICE_ACCOUNT_EMAIL \
  --quiet

# Delete container images (optional)
gcloud container images delete gcr.io/$PROJECT_ID/stock-alerter:latest \
  --quiet
```

**Arguments**:
- `--quiet`: Skips confirmation prompts (use with caution)
- Deleting is permanent; backups are recommended for important data



## Cost Optimization Tips

Understanding Cloud Run pricing to manage deployment costs:

```bash
# Check current usage and costs
gcloud billing budgets list
gcloud compute project-info describe --project=$PROJECT_ID
```

**Free Tier Limits** (per month):
- **Cloud Run**: 
  - 2 million requests
  - 400,000 GB-seconds of compute
  - Enough for ~50 hours per month with 1GB allocation
- **Secret Manager**: 
  - 6 active secret versions (free)
  - Additional versions: $0.06/version/month
- **Cloud Scheduler**: 
  - 3 free jobs
  - Additional jobs: $0.10/job/month
- **Cloud Logging**: 
  - 50GB/month free
  - Additional logs: $0.50/GB

**Cost Optimization Strategies**:

1. **Reduce Memory/CPU if Possible**
   ```bash
   # Reduce from 16Gi to 4Gi for development/testing
   gcloud run deploy $SERVICE_NAME \
     --image gcr.io/$PROJECT_ID/stock-alerter:latest \
     --memory 4Gi \
     --cpu 2
   ```

2. **Set Lower Max Instances**
   ```bash
   # Limit concurrent instances to control costs
   gcloud run deploy $SERVICE_NAME \
     --max-instances 1  # Only 1 instance at a time
   ```

3. **Schedule Execution Only During Market Hours**
   ```bash
   # Run only during trading hours (9 AM - 4 PM, weekdays)
   gcloud scheduler jobs update http $SERVICE_NAME-scheduler \
     --location=$REGION \
     --schedule="*/15 9-16 * * 1-5"  # Every 15 min, 9-4 PM weekdays
   ```

## Security Best Practices

### 1. Service Account Principle of Least Privilege

```bash
# Only grant specific permissions needed
# DON'T use the default Compute Engine service account
# DO create a dedicated service account with minimal roles

# Audit what roles a service account has
gcloud iam service-accounts get-iam-policy $SERVICE_ACCOUNT_EMAIL
```

### 2. Secret Rotation

```bash
# Create a new version of a secret (automatic rotation)
echo -n "new_secure_password_12345" | gcloud secrets versions add email-app-password \
  --data-file=-

# Cloud Run automatically uses the :latest version
# Old versions are retained for audit purposes
gcloud secrets versions list email-app-password

# Access a specific version (if needed for rollback)
gcloud secrets versions access {VERSION_ID} --secret=email-app-password
```

### 3. Network Security

For additional security, restrict Cloud Run service to VPC:

```bash
# Create VPC connector (if using private databases)
gcloud compute networks vpc-access connectors create stock-alerter-connector \
  --region $REGION \
  --subnet projects/$PROJECT_ID/global/networks/default

# Deploy with VPC connector
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --vpc-connector=stock-alerter-connector \
  --region $REGION
```

### 4. Enable Cloud Audit Logs

```bash
# Enable audit logging for compliance
gcloud logging sinks create cloud-audit-logging \
  logging.googleapis.com/projects/$PROJECT_ID/logs/cloudaudit.googleapis.com \
  --log-filter='protoPayload.methodName="storage.objects.get"'
```

### 5. IAM Conditions (Advanced)

```bash
# Grant secret access only from a specific service
gcloud secrets add-iam-policy-binding email-app-password \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor \
  --condition='resource.name.startsWith("projects/12345/secrets/email")'
```

## Troubleshooting Guide

### Issue: "Container failed to start and listen on PORT=8080"

**Causes**:
1. Application doesn't bind to port 8080
2. Application crashes during startup
3. Startup takes longer than timeout

**Solutions**:
```bash
# Increase timeout to 600 seconds
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --timeout 600  # 10 minutes

# Check logs for startup errors
gcloud run services logs read $SERVICE_NAME \
  --region $REGION \
  --stream

# Verify application starts locally
docker run -e PORT=8080 gcr.io/$PROJECT_ID/stock-alerter:latest
```

### Issue: "Permission denied" accessing secrets

**Cause**: Service account lacks `secretmanager.secretAccessor` role

**Solution**:
```bash
# Re-grant secret access
gcloud secrets add-iam-policy-binding email-app-password \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/secretmanager.secretAccessor

# Verify permission was granted
gcloud secrets get-iam-policy email-app-password
```

### Issue: "Service account does not have the necessary permissions"

**Causes**:
1. Service account missing required roles
2. Cloud Run not using correct service account

**Solutions**:
```bash
# Check which service account Cloud Run is using
gcloud run services describe $SERVICE_NAME \
  --region $REGION \
  --format='value(spec.template.spec.serviceAccountName)'

# Grant necessary roles if missing
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/run.invoker

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/storage.objectAdmin
```

### Issue: "The user-provided container image could not be pulled"

**Causes**:
1. Image doesn't exist in Container Registry
2. Authentication failed
3. Wrong project ID or image name

**Solutions**:
```bash
# Verify image exists
gcloud container images list --repository=gcr.io/$PROJECT_ID

# Check image details
gcloud container images describe gcr.io/$PROJECT_ID/stock-alerter:latest

# Re-push image if needed
docker push gcr.io/$PROJECT_ID/stock-alerter:latest
```

### Issue: Scheduler job not triggering Cloud Run service

**Causes**:
1. Service account lacks `run.invoker` role
2. Service not allowing unauthenticated access
3. OIDC token audience mismatch

**Solutions**:
```bash
# Grant run.invoker role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/run.invoker

# Allow unauthenticated access
gcloud run services add-iam-policy-binding $SERVICE_NAME \
  --region $REGION \
  --member=allUsers \
  --role=roles/run.invoker

# Test scheduler job manually
gcloud scheduler jobs run $SERVICE_NAME-scheduler --location=$REGION
```

## Deployment Checklist

Use this checklist to ensure all steps are completed:

- [ ] Project variables set (`PROJECT_ID`, `REGION`, `SERVICE_NAME`)
- [ ] APIs enabled (Cloud Run, Secret Manager, Artifact Registry)
- [ ] All 5 secrets created in Secret Manager
- [ ] Service account created
- [ ] Service account has `secretmanager.secretAccessor` role for all secrets
- [ ] Service account has `storage.objectAdmin` role (if using Cloud Storage)
- [ ] Service account has `run.invoker` role (for scheduler)
- [ ] Docker image built locally
- [ ] Docker authenticated with GCP (`gcloud auth configure-docker`)
- [ ] Docker image pushed to Container Registry
- [ ] Cloud Run service deployed successfully
- [ ] Health endpoint responds (`curl $SERVICE_URL/health`)
- [ ] Cloud Scheduler job created (if needed)
- [ ] Scheduler job tested manually
- [ ] Logs reviewed for errors
- [ ] Cost budget set up
- [ ] Audit logging enabled

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)
- [Securing Cloud Run](https://cloud.google.com/run/docs/securing/managing-access)

## Quick Reference Commands

```bash
# View service details
gcloud run services describe $SERVICE_NAME --region=$REGION

# Update service image
gcloud run deploy $SERVICE_NAME --image=gcr.io/$PROJECT_ID/stock-alerter:latest --region=$REGION

# View recent logs
gcloud run services logs read $SERVICE_NAME --region=$REGION --limit=50

# Update environment variable
gcloud run deploy $SERVICE_NAME --set-env-vars KEY=value --region=$REGION

# Update secret
echo -n "new_value" | gcloud secrets versions add secret-name --data-file=-

# Delete service
gcloud run services delete $SERVICE_NAME --region=$REGION

# List all services
gcloud run services list --region=$REGION

# Export service configuration
gcloud run services describe $SERVICE_NAME --region=$REGION --format=json > service-config.json
```


