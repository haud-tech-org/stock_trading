# Google Cloud Run Deployment Guide

This guide covers deploying the Stock Alerter application to Google Cloud Run using Google Secret Manager for credential management.

## Prerequisites

- Google Cloud CLI (gcloud) installed and configured
- Active Google Cloud # Deploy to Cloud Run with all environment variables and secrets on a single line
# NOTE: Removed --allow-unauthenticated flag to require authentication (requires IAM invoker role)
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/stock-alerter:latest \
  --platform managed \
  --region $REGION \
  --service-account $SERVICE_ACCOUNT_EMAIL \
  --no-allow-unauthenticated \
  --memory 16Gi \
  --cpu 8 \
  --timeout 300 \
  --max-instances 2 \
  --set-env-vars EMAIL_ENABLED=true,EMAIL_SMTP_SERVER=smtp.gmail.com,EMAIL_SMTP_PORT=587,EMAIL_RECEIVERS=haud.fin@gmail.com,EMAIL_BCC_RECEIVERS=haud.fin@gmail.com,NTFY_ENABLED=false,NTFY_TOPICS=vn30_alerts_f8a9b2c1,TWILIO_ENABLED=false,TWILIO_PHONE_NUMBER="",SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets EMAIL_SENDER=email-sender:latest,EMAIL_APP_PASSWORD=email-app-password:latest,EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,TWILIO_ACCOUNT_SID=twilio-account-sid:latest,TWILIO_AUTH_TOKEN=twilio-auth-token:latestker image built and pushed to Google Container Registry
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

Grant the service account all necessary roles for deployment, execution, and Cloud Run management.

```bash
# Define the roles needed for Cloud Run deployment and execution
PROJECT_ID="stock-trading-489001"
SERVICE_ACCOUNT_EMAIL="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com"

# Grant Cloud Run Admin role (full Cloud Run management and deployment)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/run.admin \
  --condition=None

# Grant Service Account User role (allows using service accounts)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/iam.serviceAccountUser \
  --condition=None

# Grant Storage Object Admin role (for Cloud Storage access)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/storage.objectAdmin \
  --condition=None

# Grant Cloud Run Invoker role (allows service invocation and scheduling)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/run.invoker \
  --condition=None

# Grant Artifact Registry Reader role (pull Docker images for deployment)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/artifactregistry.reader \
  --condition=None

# Grant Compute Admin role (manage compute resources)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/compute.admin \
  --condition=None

# Grant Logging Log Writer role (write application logs)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/logging.logWriter \
  --condition=None

# Grant Monitoring Metric Writer role (write metrics)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT_EMAIL \
  --role=roles/monitoring.metricWriter \
  --condition=None
```

**Argument Explanations**:
- `gcloud projects add-iam-policy-binding`: Grants a role at the project level
- `--member=serviceAccount:...`: The service account being granted the role
- `--condition=None`: No conditions on this binding (applies in all contexts)

**Roles Granted and Their Purpose**:
| Role | Purpose |
|------|---------|
| `roles/run.admin` | Full Cloud Run service management and deployment |
| `roles/iam.serviceAccountUser` | Allows using this service account for operations |
| `roles/storage.objectAdmin` | Full read/write access to Cloud Storage buckets |
| `roles/run.invoker` | Invoke Cloud Run services and trigger Cloud Scheduler jobs |
| `roles/artifactregistry.reader` | Pull Docker images from Container Registry for deployment |
| `roles/compute.admin` | Manage compute resources and instances |
| `roles/logging.logWriter` | Write application logs to Cloud Logging |
| `roles/monitoring.metricWriter` | Write metrics to Cloud Monitoring |

**Verify Assigned Roles**:
```bash
# Check all roles assigned to the service account
gcloud projects get-iam-policy $PROJECT_ID --format=json | \
  jq ".bindings[] | select(.members[] | contains(\"$SERVICE_ACCOUNT_EMAIL\")) | .role" | sort
```

**Expected Output**:
```
"roles/artifactregistry.reader"
"roles/compute.admin"
"roles/iam.serviceAccountUser"
"roles/logging.logWriter"
"roles/monitoring.metricWriter"
"roles/run.admin"
"roles/run.invoker"
"roles/secretmanager.secretAccessor"
"roles/storage.objectAdmin"
```

## Step 7: Build and Push Docker Image

Build the Docker image with the correct platform (Linux x86_64 for Cloud Run) and push to Google Container Registry.

```bash
# Build Docker image for Linux x86_64 architecture (required for Cloud Run)
# This is critical if you're building on Apple Silicon (M1/M2/M3) Mac
docker buildx build --platform linux/amd64 -t stock-alerter:latest .

# Alternative if buildx is not available (for Intel/AMD machines):
# docker build -t stock-alerter:latest .

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

# Check image details
gcloud container images describe gcr.io/$PROJECT_ID/stock-alerter:latest
```

**Argument Explanations**:
- `docker buildx build --platform linux/amd64`: Builds image for Linux x86_64 architecture
  - `--platform linux/amd64`: Specifies target architecture (required for Cloud Run, which runs on Linux x86_64)
  - This ensures compatibility if building on Apple Silicon Macs
  - If you get "buildx" not found, enable Docker Desktop experimental features or use regular `docker build`
- `-t {image-name}:{tag}`: Tag (name and version) for the image
- `.`: Build context (uses Dockerfile in current directory)
- `docker tag {source} {target}`: Creates a new tag pointing to an existing image
- `gcloud auth configure-docker`: Authenticates Docker with GCP credentials
- `docker push {image}`: Uploads image to the registry

**Important: Platform Compatibility**

If you're building on an Apple Silicon Mac and get error: `failed to load /usr/local/bin/python: exec format error`

This means the image was built for ARM64 (Mac architecture) instead of x86_64 (Cloud Run architecture).

**Solution**:
```bash
# Build with correct platform flag
docker buildx build --platform linux/amd64 -t stock-alerter:latest .

# If buildx is unavailable, enable it:
docker buildx create --use
docker buildx build --platform linux/amd64 -t stock-alerter:latest .
```

**Alternative: Use Cloud Build** (builds on GCP infrastructure, avoiding architecture issues):
```bash
gcloud builds submit --region=$REGION \
  --tag=gcr.io/$PROJECT_ID/stock-alerter:latest
```

**Advantage of Cloud Build**:
- No need to push from your machine
- Uses GCP's infrastructure (avoids local architecture issues)
- Automatically builds for correct Linux x86_64 architecture
- Integrated with GCP ecosystem
- Better for CI/CD pipelines

## Step 8: Deploy to Cloud Run

Deploy the Docker image to Cloud Run with environment variables and secrets.

```bash
# Export variables for the deployment command
export PROJECT_ID="stock-trading-489001"
export REGION="europe-west1"
export SERVICE_NAME="stock-alerter"
export SERVICE_ACCOUNT_EMAIL="stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com"

# Deploy to Cloud Run with all environment variables and secrets on a single line
# NOTE: Production configuration with complete feature set:
# - Memory: 16Gi (maximum) for optimal performance
# - CPU: 8 cores (maximum) for parallel processing
# - Billing: Instance-based with --no-cpu-throttling (always pay for CPU, not just when handling requests)
# - CPU Boost: Enabled for faster startup
# - Min Instances: 1 (always keep 1 instance warm for instant responses)
# - Max Instances: 2 for cost control with high-resource allocation
# - Authentication: --no-allow-unauthenticated for secure production
# - Cloud Storage: GCS bucket mounted at /mnt via GCSFUSE
# - Environment: Gen2 with 5-minute timeout
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

**Core Arguments Explanation**:
- `gcloud run deploy`: Deploys a service to Cloud Run
- `$SERVICE_NAME`: Name of the service (stock-alerter)
- `--image`: Container image to deploy from Container Registry
- `--platform managed`: Use Cloud Run fully managed (serverless, no infrastructure management)
- `--region`: Geographic region for the service (europe-west1 for compliance/data residency)
- `--service-account`: Service account with necessary permissions for secrets and storage access
- `--no-allow-unauthenticated`: Require authentication to invoke the service
  - Access is controlled by IAM permissions (IAM invoker role required)
  - Only authorized users/service accounts can access the service
  - More secure for production deployments
  - Cloud Scheduler jobs can still invoke using service account authentication
  - To allow public access, use `--allow-unauthenticated` flag instead
- `--memory 16Gi`: Memory allocation for each instance
  - Minimum: 256Mi, Maximum: 16Gi
  - 16Gi provides optimal performance for complex stock alert computations
  - Higher memory allows faster data processing and caching
  - Paired with 8 CPU cores for maximum performance
- `--cpu 8`: CPU allocation for each instance
  - Minimum: 1, Maximum: 8 cores (maximum)
  - 8 cores (maximum) enables parallel processing and fast execution
  - Optimal for concurrent alert generation and data analysis
  - Matched with 16Gi memory for maximum performance
  - **Billing Model**: Instance-based (see section below)
- `--no-cpu-throttling`: Disable CPU throttling to enable instance-based billing
  - By default, CPU is throttled when not actively serving requests (request-based billing)
  - Using `--no-cpu-throttling` enables instance-based billing (always pay for CPU)
  - Ensures full CPU power is available at all times (no throttling between requests)
  - Better for performance-critical applications like stock alert generation
  - Cost: You pay for the instance's full CPU lifetime, not just active request time
  - **Alternative**: Remove this flag to use request-based billing (pay only when serving requests, but CPU may be throttled)
- `--cpu-boost`: Enable startup CPU boost for faster container initialization
  - Allocates extra CPU during container startup
  - Reduces startup time significantly
  - Important for `--min-instances 1` to ensure fast cold start when traffic arrives
  - Automatically disabled after startup completes
- `--timeout 300`: Maximum execution time in seconds (5 minutes)
  - Must be 60-3600 seconds
  - 300 seconds provides enough time for complete alert generation cycle
  - For long-running alerts, can increase to 600 (10 minutes)
  - Increase if alert generation takes longer than timeout
- `--max-instances 2`: Maximum number of concurrent instances
  - Controls cost and resource usage
  - Auto-scales based on request load up to this limit
  - Limited to 2 instances for cost control with high-resource (16Gi/8CPU) configuration
  - Prevents runaway costs while maintaining availability
- `--min-instances 1`: Minimum number of instances to keep running
  - **Billing Model**: Instance-based (charged for full lifetime of instances)
  - With min-instances=1, you pay for at least 1 full instance at all times
  - Provides instant response times (no cold starts) when requests arrive
  - Ensures service is always warm and ready to process alerts
  - Useful for time-sensitive stock alert generation
  - Cost: Instance-based billing charges continuously (even with 0 requests)
  - Alternative: Use min-instances=0 for request-based billing (only pay when handling requests)
- `--execution-environment gen2`: Use Cloud Run 2nd generation runtime
  - Better performance and flexibility compared to gen1
  - Supports longer timeouts and larger memory allocations
  - Default for new deployments, recommended for production
- `--add-volume=name=gcs-1,type=cloud-storage,bucket=stock-trading-2`: Mount GCS bucket as volume
  - `name=gcs-1`: Volume identifier name
  - `type=cloud-storage`: Use Google Cloud Storage FUSE mount
  - `bucket=stock-trading-2`: GCS bucket to mount
  - Provides persistent access to reports and data files
  - Mounted at `/mnt` path (see next flag)
- `--add-volume-mount=volume=gcs-1,mount-path=/mnt`: Mount volume to container path
  - `volume=gcs-1`: Reference to volume defined above
  - `mount-path=/mnt`: Container path where bucket is accessible
  - Application can read/write files at `/mnt` → stored in `gs://stock-trading-2/`

**Environment Variables** (`--set-env-vars`) - All on one line with comma separation:
- `EMAIL_ENABLED=true`: Enable email notifications
- `EMAIL_SMTP_SERVER=smtp.gmail.com`: Gmail SMTP server
- `EMAIL_SMTP_PORT=587`: SMTP port for TLS encryption
- `EMAIL_RECEIVERS=haud.fin@gmail.com`: Primary recipient email
- `EMAIL_BCC_RECEIVERS=haud.fin@gmail.com`: BCC recipient (for auditing/backup)
- `NTFY_ENABLED=false`: Disable ntfy.sh push notifications (set `true` to enable)
- `NTFY_TOPICS=vn30_alerts_f8a9b2c1`: ntfy.sh topic for notifications
- `TWILIO_ENABLED=false`: Disable SMS notifications (set `true` to enable)
- `TWILIO_PHONE_NUMBER=""`: Sender phone number (leave empty if SMS disabled)
- `SMS_RECEIVER_PHONE_NUMBER=""`: Recipient phone number (leave empty if SMS disabled)

**Secrets** (`--set-secrets`) - Format: `ENV_VAR_NAME=secret-name:version`
- `EMAIL_SENDER=email-sender:latest`: Gmail address (from Secret Manager)
- `EMAIL_APP_PASSWORD=email-app-password:latest`: Gmail App Password (from Secret Manager)
- `EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest`: Display name for emails
- `TWILIO_ACCOUNT_SID=twilio-account-sid:latest`: Twilio account ID (if SMS enabled)
- `TWILIO_AUTH_TOKEN=twilio-auth-token:latest`: Twilio authentication token (if SMS enabled)

**Important Notes**:
- All environment variables must be on a single comma-separated line after `--set-env-vars`
- All secrets must be on a single comma-separated line after `--set-secrets`
- No line breaks within the variable/secret lists (this causes command parsing errors)
- `:latest` always uses the most recent version of each secret
- Secrets are never visible in Cloud Console or logs (encrypted transmission)

### Billing Model Configuration

**Current Configuration**: **Instance-Based Billing**

The service is configured with instance-based billing, which means:

```json
{
  "run.googleapis.com/cpu-throttling": "false",
  "run.googleapis.com/startup-cpu-boost": "true"
}
```

**Instance-Based Billing Details**:
- **Cost Model**: Charged for the entire lifecycle of each instance
- **CPU Availability**: Full CPU (8 cores) available at all times, not throttled
- **Concurrency**: 640 concurrent requests per instance (containerConcurrency: 640)
- **Cost per Month** (Approximate):
  - 8 CPU cores × $0.0000317 per CPU-second × 2,592,000 seconds/month = ~$655/month per active instance
  - Max 2 instances = ~$1,310/month for full month operation
  - Scales with actual instance uptime

**Why Instance-Based Instead of Request-Based?**
1. **Better for Always-On Services**: Stock alerter runs continuously checking market data
2. **Better for High-Concurrency**: 640 concurrent requests per instance is high throughput
3. **Better for Predictable Performance**: No CPU throttling between requests
4. **Guaranteed CPU**: Full 8 cores always available for parallel alert processing

**Comparison: Request-Based vs Instance-Based**

| Feature | Request-Based | Instance-Based (Current) |
|---------|---------------|------------------------|
| **Billing** | Only when processing requests | Entire instance lifecycle |
| **CPU Availability** | Limited outside requests | Full 8 cores always |
| **Cost Model** | Pay-per-request | Pay-per-instance-second |
| **Best For** | Sporadic, low-latency requests | Always-on, high-throughput services |
| **Startup** | Slower (cold starts) | Faster (always warm) |
| **Concurrency** | Lower | Higher (640 in your config) |

**To Switch Billing Models** (if needed):

```bash
# Switch to REQUEST-BASED billing (CPU throttled between requests)
# This would reduce costs but increase latency
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --cpu-throttling  # Enables request-based billing (CPU throttled)

# Keep INSTANCE-BASED billing (current configuration)
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --no-cpu-throttling  # Disables CPU throttling (instance-based billing)
```

**Performance Implications**:

With instance-based billing and 8 CPU cores:
- ✅ Stock alerts are processed in parallel
- ✅ Multiple data streams can be analyzed simultaneously
- ✅ No CPU throttling delays between requests
- ✅ Constant availability for incoming requests
- ❌ Higher cost (~$655/month per active instance)

**Cost Optimization Options**:

1. **Reduce CPU Cores** (switch to request-based):
   ```bash
   gcloud run deploy stock-alerter \
     --cpu=4 \
     --cpu-throttling  # Request-based billing
   ```
   **Savings**: ~$330/month per instance, but slower processing

2. **Reduce Max Instances**:
   ```bash
   gcloud run deploy stock-alerter \
     --max-instances=1  # Only 1 instance instead of 2
   ```
   **Savings**: ~$655/month, but limits concurrent capacity

3. **Schedule Execution** (if alerts don't need continuous availability):
   ```bash
   # Only run during market hours
   gcloud scheduler jobs update http stock-alerter-scheduler \
     --schedule="*/15 9-16 * * 1-5"  # Every 15 min, 9 AM-4 PM weekdays
   ```
   **Savings**: ~70% reduction in instance uptime

## Additional Configuration Details (via Google Cloud Console)

### Cloud Storage Volume Mount
The service has a Cloud Storage bucket mounted at `/mnt` path:
```json
{
  "volumes": [
    {
      "name": "gcs-1",
      "csi": {
        "driver": "gcsfuse.run.googleapis.com",
        "volumeAttributes": {
          "bucketName": "stock-trading-2"
        }
      }
    }
  ],
  "volumeMounts": [
    {
      "name": "gcs-1",
      "mountPath": "/mnt"
    }
  ]
}
```

**Purpose**: Provides persistent storage access to Google Cloud Storage bucket `stock-trading-2` for reports and data files.

**Access within application**:
```python
# Files in /mnt are stored in gs://stock-trading-2/
# Example: /mnt/reports/alert.csv → gs://stock-trading-2/reports/alert.csv
```

### Startup Probe Configuration
The service includes a TCP startup probe for robust health checking:
```json
{
  "startupProbe": {
    "tcpSocket": {
      "port": 8080
    },
    "initialDelaySeconds": 0,
    "periodSeconds": 240,
    "timeoutSeconds": 240,
    "failureThreshold": 1
  }
}
```

**Purpose**: Ensures the service has fully started before receiving traffic.

**Parameters**:
- `port 8080`: Checks if port 8080 is listening
- `periodSeconds 240`: Check every 4 minutes
- `timeoutSeconds 240`: Wait up to 4 minutes for response
- `failureThreshold 1`: Single failure triggers restart

### Startup CPU Boost
The service has startup CPU boost enabled:
```
"run.googleapis.com/startup-cpu-boost": "true"
```

**Purpose**: Provides maximum CPU during container startup phase
- Accelerates application initialization
- Reduces time to first request handling
- Uses full 8 CPU cores during startup (no throttling)
- Automatically normalizes after startup completes

### Container Concurrency Setting
```
containerConcurrency: 640
```

**Purpose**: Maximum number of concurrent requests per instance (640 requests per container).

### Execution Environment
```
--execution-environment gen2
```

**Features**:
- 2nd generation Cloud Run runtime
- Faster startup times
- Better resource efficiency
- Supports longer timeouts (up to 3600 seconds)
- Larger memory allocations (up to 16Gi)

**Alternative Command Format** (if you need to split across lines for readability):

Save this as a shell script file `deploy.sh`:

```bash
#!/bin/bash
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
  --timeout 300 \
  --max-instances 2 \
  --set-env-vars \
    EMAIL_ENABLED=true,\
    EMAIL_SMTP_SERVER=smtp.gmail.com,\
    EMAIL_SMTP_PORT=587,\
    EMAIL_RECEIVERS=haud.fin@gmail.com,\
    EMAIL_BCC_RECEIVERS=haud.fin@gmail.com,\
    NTFY_ENABLED=false,\
    NTFY_TOPICS=vn30_alerts_f8a9b2c1,\
    TWILIO_ENABLED=false,\
    TWILIO_PHONE_NUMBER="",\
    SMS_RECEIVER_PHONE_NUMBER="" \
  --set-secrets \
    EMAIL_SENDER=email-sender:latest,\
    EMAIL_APP_PASSWORD=email-app-password:latest,\
    EMAIL_SENDER_DISPLAY_NAME=email-sender-display-name:latest,\
    TWILIO_ACCOUNT_SID=twilio-account-sid:latest,\
    TWILIO_AUTH_TOKEN=twilio-auth-token:latest
```

Then run it:
```bash
chmod +x deploy.sh
./deploy.sh
```

**Troubleshooting Deployment**:

If you get argument parsing errors:
1. Ensure all environment variables are on ONE line with commas (no line breaks)
2. Ensure all secrets are on ONE line with commas (no line breaks)
3. Remove any trailing backslashes on the last variable/secret line
4. Use the script file approach if you need multiple lines for readability

## Step 9: Verify Deployment

Verify that the Cloud Run service has been deployed successfully and is responding to requests.

```bash
# Get the service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --format='value(status.url)')

echo "Service URL: $SERVICE_URL"

# Current production service URL:
# https://stock-alerter-717776322217.europe-west1.run.app

# Test the health endpoint (requires authentication since --no-allow-unauthenticated)
# For authenticated requests, use the service account credentials or valid OAuth token
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://stock-alerter-717776322217.europe-west1.run.app/health

# Expected response (when authenticated):
# {"status": "ok"}

# Note: The service requires authentication because it was deployed with --no-allow-unauthenticated
# This is more secure for production deployments
```

**Explanation**:
- Retrieves the auto-generated HTTPS URL for your Cloud Run service
- Tests the `/health` endpoint to verify the service is running
- Health endpoint responds immediately (no background tasks)
- Authentication is required for all requests (uses IAM permissions)

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


