# Google Cloud Run Deployment - UI Step-by-Step Guide

This guide provides detailed UI instructions for deploying the Stock Alerter to Google Cloud Run using the Google Cloud Console (web interface).

---

## Prerequisites

✅ Active Google Cloud project  
✅ Google Cloud CLI (gcloud) installed (for Docker push only)  
✅ Docker image built locally (`stock-alerter:latest`)  
✅ Appropriate IAM permissions (Project Editor or Owner role)

---

## Step 1: Set Up Google Cloud Project Variables

### Via Google Cloud Console:

1. **Open Google Cloud Console**: https://console.cloud.google.com/
2. **At the top, click the Project Dropdown** (shows current project name)
3. **Select or Create Project**:
   - Click "NEW PROJECT"
   - Project Name: `stock-trading-alerter`
   - Organization: Leave default
   - Click "CREATE"
   - Wait for project to initialize (1-2 minutes)
4. **Note your Project ID** (appears in the sidebar or at the top as a hyphenated ID like `stock-trading-alerter-123456`)

### Set as Active Project via CLI (required for Docker push):

```bash
export PROJECT_ID="your-actual-gcp-project-id"
export REGION="us-central1"  # Change if needed
export SERVICE_NAME="stock-alerter"

# Set as active project
gcloud config set project $PROJECT_ID
gcloud config get-value project  # Verify
```

---

## Step 2: Enable Required APIs

### Via Google Cloud Console:

1. **Navigate to APIs & Services**:
   - In left sidebar, click **"APIs & Services"**
   - Click **"Library"**

2. **Enable Cloud Run API**:
   - Search: `Cloud Run API`
   - Click the first result
   - Click **"ENABLE"** button
   - Wait for it to complete (green checkmark)

3. **Enable Secret Manager API**:
   - Click **"← Back to APIs & Services Library"**
   - Search: `Secret Manager API`
   - Click the result
   - Click **"ENABLE"**

4. **Enable Artifact Registry API**:
   - Click **"← Back to APIs & Services Library"**
   - Search: `Artifact Registry API`
   - Click the result
   - Click **"ENABLE"**

5. **Enable Compute Engine API**:
   - Click **"← Back to APIs & Services Library"**
   - Search: `Compute Engine API`
   - Click the result
   - Click **"ENABLE"**

**All 4 APIs should now show as "Enabled" (check mark)**

---

## Step 3: Create Secrets in Google Secret Manager

### Via Google Cloud Console:

1. **Navigate to Secret Manager**:
   - Click left sidebar **≡ (Menu)**
   - Search: `Secret Manager`
   - Click **"Secret Manager"** under "Security"

2. **Create Email Sender Secret**:
   - Click **"+ CREATE SECRET"** button (top)
   - Name: `email-sender`
   - Secret value: `your-email@gmail.com`
   - Replication: Keep default "Automatic"
   - Click **"CREATE SECRET"**
   - ✅ Secret created

3. **Create Email App Password Secret**:
   - Click **"+ CREATE SECRET"**
   - Name: `email-app-password`
   - Secret value: `xxxx xxxx xxxx xxxx` (16-digit app password)
   - Replication: Keep default
   - Click **"CREATE SECRET"**
   - ✅ Secret created

4. **Create Email Display Name Secret**:
   - Click **"+ CREATE SECRET"**
   - Name: `email-sender-display-name`
   - Secret value: `Stock Alerter (No-Reply)`
   - Replication: Keep default
   - Click **"CREATE SECRET"**
   - ✅ Secret created

5. **Create Twilio Account SID Secret** (if using SMS):
   - Click **"+ CREATE SECRET"**
   - Name: `twilio-account-sid`
   - Secret value: `ACxxxxxxxxxxxxxxxxxx`
   - Replication: Keep default
   - Click **"CREATE SECRET"**
   - ✅ Secret created

6. **Create Twilio Auth Token Secret** (if using SMS):
   - Click **"+ CREATE SECRET"**
   - Name: `twilio-auth-token`
   - Secret value: `your_auth_token_here`
   - Replication: Keep default
   - Click **"CREATE SECRET"**
   - ✅ Secret created

**You should now have 5 secrets in Secret Manager** (or 3 if not using Twilio)

---

## Step 4: Create Service Account

### Via Google Cloud Console:

1. **Navigate to Service Accounts**:
   - Click left sidebar **≡ (Menu)**
   - Click **"APIs & Services"** → **"Credentials"**
   - Click **"+ CREATE CREDENTIALS"** dropdown
   - Select **"Service Account"**

2. **Fill in Service Account Details**:
   - Service account name: `stock-alerter-sa`
   - Service account ID: Auto-fills as `stock-alerter-sa`
   - Description: `Service account for Stock Alerter Cloud Run deployment`
   - Click **"CREATE AND CONTINUE"**

3. **Grant Roles**:
   - Click **"+ GRANT ROLES"** button
   - Select roles:
     - Search and select: **"Secret Manager Secret Accessor"**
     - Search and select: **"Cloud Run Developer"** (optional, for future deployments)
   - Click **"CONTINUE"**

4. **Finish**:
   - You can skip "Create a key" for now
   - Click **"DONE"**

**Note the Service Account Email** (format: `stock-alerter-sa@PROJECT_ID.iam.gserviceaccount.com`)

---

## Step 5: Grant Secret Access Permissions

### Via Google Cloud Console:

1. **Navigate back to Secret Manager**:
   - Click left sidebar **≡ (Menu)**
   - Search: `Secret Manager`
   - Click **"Secret Manager"**

2. **For each secret**, grant access to service account:

   **For `email-sender` secret**:
   - Click the secret name: `email-sender`
   - Click **"PERMISSIONS"** tab at top
   - Click **"GRANT ACCESS"** button
   - New principals: `stock-alerter-sa@PROJECT_ID.iam.gserviceaccount.com`
   - Role: Select **"Secret Manager Secret Accessor"**
   - Click **"SAVE"**

   **Repeat for all other secrets**:
   - `email-app-password`
   - `email-sender-display-name`
   - `twilio-account-sid` (if created)
   - `twilio-auth-token` (if created)

**Each secret should now show the service account in its Permissions tab**

---

## Step 6: Build and Push Docker Image

### Via Terminal (using gcloud CLI):

```bash
# Navigate to project directory
cd /Users/tech/dev/development/stock_trading

# Configure Docker authentication
gcloud auth configure-docker

# Build Docker image locally
docker build -t stock-alerter:latest .

# Tag for Google Container Registry
docker tag stock-alerter:latest gcr.io/$PROJECT_ID/stock-alerter:latest

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/stock-alerter:latest

# Verify image is in registry (optional)
gcloud container images list
gcloud container images list-tags gcr.io/$PROJECT_ID/stock-alerter
```

**Wait for push to complete** (should show "Pushed ... status: image: digest: sha256:...")

---

## Step 7: Deploy to Cloud Run

### Via Google Cloud Console:

1. **Navigate to Cloud Run**:
   - Click left sidebar **≡ (Menu)**
   - Search: `Cloud Run`
   - Click **"Cloud Run"** under "Compute"

2. **Create New Service**:
   - Click **"CREATE SERVICE"** button

3. **Configure Service - Deployment Settings**:
   - **Container image URL**: Click "SELECT"
     - Find: `gcr.io/PROJECT_ID/stock-alerter:latest`
     - Click to select it
   - **Service name**: `stock-alerter`
   - **Region**: Select `us-central1` (or your preferred region)
   - **Authentication**: Select **"Allow unauthenticated invocations"** ✅
   - Click **"NEXT"** or skip to container settings

4. **Configure Service - Container**:
   - Click **"Container"** tab or scroll down
   - **Memory**: Select `512 MB`
   - **CPU**: Select `1`
   - **Timeout**: Set to `300` seconds (5 minutes)
   - **Maximum instances**: Set to `10`
   - **Service account**: Select `stock-alerter-sa@PROJECT_ID.iam.gserviceaccount.com`
   - Click **"SHOW ADVANCED SETTINGS"** or **"RUNTIME SETTINGS"**

5. **Set Environment Variables**:
   - **GOOGLE_CLOUD_PROJECT**: `PROJECT_ID` (your actual project ID)
   - **EMAIL_ENABLED**: `true`
   - **EMAIL_SMTP_SERVER**: `smtp.gmail.com`
   - **EMAIL_SMTP_PORT**: `587`
   - **EMAIL_RECEIVERS**: `recipient@example.com`
   - **EMAIL_BCC_RECEIVERS**: `admin@example.com`
   - **EMAIL_SENDER_DISPLAY_NAME**: `Stock Alerter (No-Reply)`
   - **NTFY_ENABLED**: `false`
   - **NTFY_TOPICS**: `vn30_alerts_f8a9b2c1`
   - **TWILIO_ENABLED**: `false` (or `true` if using)
   - **TWILIO_PHONE_NUMBER**: `` (empty if not using, or your Twilio number)
   - **SMS_RECEIVER_PHONE_NUMBER**: `` (empty if not using, or receiver phone)
   
   For each variable:
   - Click **"+ ADD VARIABLE"**
   - Name: (from above)
   - Value: (from above)
   - Click **"+"** to add

6. **Set Secrets**:
   - Scroll to find **"Secrets"** section or **"Secret Manager"** field
   - Click **"+ ADD SECRET"** for each:
   
   **Add Secret 1: EMAIL_SENDER**
   - Click **"+ ADD SECRET"**
   - Name: `EMAIL_SENDER`
   - Select secret: `email-sender`
   - Version: Select **"latest"**
   - Click **"+"** to add
   
   **Add Secret 2: EMAIL_APP_PASSWORD**
   - Click **"+ ADD SECRET"**
   - Name: `EMAIL_APP_PASSWORD`
   - Select secret: `email-app-password`
   - Version: Select **"latest"**
   - Click **"+"** to add
   
   **Add Secret 3: EMAIL_SENDER_DISPLAY_NAME**
   - Click **"+ ADD SECRET"**
   - Name: `EMAIL_SENDER_DISPLAY_NAME`
   - Select secret: `email-sender-display-name`
   - Version: Select **"latest"**
   - Click **"+"** to add
   
   **Add Secret 4: TWILIO_ACCOUNT_SID** (if using)
   - Click **"+ ADD SECRET"**
   - Name: `TWILIO_ACCOUNT_SID`
   - Select secret: `twilio-account-sid`
   - Version: Select **"latest"**
   - Click **"+"** to add
   
   **Add Secret 5: TWILIO_AUTH_TOKEN** (if using)
   - Click **"+ ADD SECRET"**
   - Name: `TWILIO_AUTH_TOKEN`
   - Select secret: `twilio-auth-token`
   - Version: Select **"latest"**
   - Click **"+"** to add

7. **Deploy**:
   - Click **"CREATE"** button at bottom right
   - Wait for deployment to complete (2-5 minutes)
   - Status shows: **"Deployment in progress..."** → **"✓ Service deployed successfully"**
   - Green checkmark appears next to service name

**You now have Cloud Run service running!** ✅

---

## Step 8: Verify Deployment

### Via Google Cloud Console:

1. **View Service Details**:
   - Cloud Run service `stock-alerter` is now listed
   - Click the service name to open details
   - **Service URL** appears at top (e.g., `https://stock-alerter-xxxxx.run.app`)

2. **Test the Service**:
   - Copy the Service URL
   - Append `/health` to it: `https://stock-alerter-xxxxx.run.app/health`
   - Open in browser or curl:
     ```bash
     curl https://stock-alerter-xxxxx.run.app/health
     ```
   - Should return: `{"status": "healthy"}` or similar

3. **View Logs**:
   - In the service details page, click **"LOGS"** tab
   - Recent logs appear
   - Look for deployment logs and any errors
   - Click **"Show resources"** to see more details

4. **Monitor Metrics**:
   - Click **"METRICS"** tab
   - View Request count, Latency, Error rate, etc.
   - All should show healthy status

**Deployment is successful!** ✅

---

## Step 9: Update Secrets (Without Redeploying)

### When you need to update a secret (e.g., password expires):

#### Via Google Cloud Console:

1. **Navigate to Secret Manager**:
   - Click left sidebar **≡ (Menu)**
   - Search: `Secret Manager`
   - Click **"Secret Manager"**

2. **Update the Secret**:
   - Click the secret name you want to update (e.g., `email-app-password`)
   - Click **"+ NEW VERSION"** button (top right)
   - Paste new secret value
   - Click **"ADD NEW VERSION"**
   - New version is now **"latest"**

3. **Cloud Run Automatically Uses New Secret**:
   - On the next request/invocation, Cloud Run automatically retrieves the latest version
   - **No redeployment needed!**
   - Existing running instances will use the new secret on their next internal reference

4. **Optional - Force Immediate Refresh** (if needed):
   - Go back to Cloud Run service
   - Click the service name
   - Click **"REVISIONS"** tab
   - Click the current revision name
   - The service will automatically restart and use the new secret

**Secret updated without downtime!** ✅

---

## Step 10: Set Up Scheduled Execution (Optional)

### If you want to run the alerter automatically on a schedule:

#### Via Google Cloud Console:

1. **Navigate to Cloud Scheduler**:
   - Click left sidebar **≡ (Menu)**
   - Search: `Cloud Scheduler`
   - Click **"Cloud Scheduler"** under "Tools"
   - If first time: Click **"ENABLE"** to enable the API
   - Wait for API to enable

2. **Create Scheduled Job**:
   - Click **"+ CREATE JOB"** button

3. **Fill in Job Details**:
   - **Name**: `stock-alerter-scheduler`
   - **Description**: `Runs Stock Alerter every 4 hours`
   - **Frequency**: `0 */4 * * *` (every 4 hours)
   - **Timezone**: Select your timezone
   - Click **"CONTINUE"**

4. **Configure Execution**:
   - **Execution type**: Select **"HTTP"** (pre-selected)
   - **URL**: Paste your Cloud Run service URL with `/run` endpoint:
     ```
     https://stock-alerter-xxxxx.run.app/run
     ```
   - **HTTP method**: Select **"POST"**
   - **Authentication**: Select **"Add OIDC token"**
   - **Service account**: Select `stock-alerter-sa@PROJECT_ID.iam.gserviceaccount.com`
   - Click **"CREATE"**

5. **Test the Job**:
   - In Cloud Scheduler, find your job: `stock-alerter-scheduler`
   - Click **"⋮"** (three dots) → **"Force run"**
   - Status shows: **"PENDING"** → **"SUCCESS"** ✅
   - Check Cloud Run logs to verify execution

6. **View Job History**:
   - Click the job name: `stock-alerter-scheduler`
   - Click **"EXECUTION HISTORY"** tab
   - See all past runs with timestamps and status
   - Click any run to see detailed logs

7. **Update Job Schedule** (if needed later):
   - In Cloud Scheduler, click the job name
   - Click **"EDIT"** button
   - Change frequency/settings
   - Click **"UPDATE"**

**Scheduled execution is now active!** The alerter will run automatically every 4 hours. ✅

---

## Cost Optimization Tips

Understanding Cloud Run pricing and free tier limits helps manage deployment costs:

### Free Tier Limits (per month)

- **Cloud Run**: 
  - 2 million requests
  - 400,000 GB-seconds of compute
  - Approximately 50 hours per month with 512MB allocation
  - Approximately 12 hours per month with 4GB allocation
- **Secret Manager**: 
  - 6 active secret versions (free tier)
  - Additional secret versions cost $0.06/version/month
- **Cloud Scheduler**: 
  - 3 free jobs
  - Additional jobs cost $0.10/job/month
- **Cloud Logging**: 
  - 50GB of ingested logs per month (free tier)
  - Additional logs cost $0.50/GB

### Cost Optimization Strategies

**Strategy 1: Reduce Memory/CPU for Development**

If your alerter doesn't need high resources during testing:

1. Go to Cloud Run service: `stock-alerter`
2. Click **"EDIT & DEPLOY NEW REVISION"**
3. Change **Memory** to `256 MB` (smaller for testing)
4. Change **CPU** to `1` (minimum)
5. Click **"DEPLOY"**
6. Monitor performance - increase if needed

**Strategy 2: Set Maximum Instances Limit**

Prevent unexpected scaling costs:

1. Go to Cloud Run service details
2. Click **"EDIT & DEPLOY NEW REVISION"**
3. Scroll to **"Maximum instances"**: Set to `1` or `2` (prevents uncontrolled scaling)
4. Click **"DEPLOY"**

**Strategy 3: Schedule Execution Only During Business Hours**

If alerts only needed during market hours:

1. Go to Cloud Scheduler job: `stock-alerter-scheduler`
2. Click **"EDIT"**
3. Change **Frequency** to: `*/15 9-16 * * 1-5`
   - This runs every 15 minutes, 9 AM to 4 PM, Monday-Friday only
   - Saves cost by avoiding weekend/night executions
4. Click **"UPDATE"**

**Strategy 4: Use Regional Infrastructure**

Some regions have lower pricing:

1. When deploying, select region: `us-central1` (usually cheapest)
2. Avoid premium regions like `europe-west1` for testing
3. For production, choose based on compliance needs, not just cost

### Estimated Monthly Cost Examples

| Scenario | Monthly Cost |
|----------|---|
| Development (256MB, 1 CPU, business hours only) | $0 (free tier) |
| Production (512MB, 1 CPU, 10 requests/day) | $0-2 (mostly free tier) |
| Production (512MB, 1 CPU, 100 requests/day) | $2-5 (slightly above free) |
| Production (4GB, 4 CPU, 1000 requests/day) | $30-50 (sustained use) |

---

## Security Best Practices

### 1. Service Account Principle of Least Privilege

The service account should have **only** the permissions it needs:

✅ **CORRECT** - Specific roles for Stock Alerter:
- Secret Manager Secret Accessor (read secrets)
- Cloud Run Developer (optional, for deployments)
- Storage Object Admin (if using Cloud Storage)

❌ **WRONG** - Don't use:
- Editor (too powerful)
- Owner (too powerful)
- Default Compute Engine service account (shared, risky)

### 2. Secret Rotation for Security

**When to rotate secrets**:
- Employee leaves the company
- Password/token suspected compromised
- Regular security policy (e.g., quarterly)

**How to rotate without downtime**:

1. Go to **Secret Manager**
2. Find the secret to update (e.g., `email-app-password`)
3. Click **"+ NEW VERSION"** button
4. Paste the new secret value
5. Click **"ADD NEW VERSION"**
6. **Automatic!** Cloud Run uses the new `:latest` version on next invocation
7. Old versions are retained for audit purposes

**To verify old versions**:

1. Click the secret name
2. Click **"VERSIONS"** tab
3. See all versions with timestamps
4. Old versions show state as "Disabled" or "Destroyed" after rotation

### 3. Network Security (Advanced)

For maximum security, restrict Cloud Run to private VPC:

1. Go to Cloud Run service details
2. Click **"EDIT & DEPLOY NEW REVISION"**
3. Scroll to **"Networking"** section
4. Toggle **"VPC Connector"** to ON
5. Select or create VPC connector in your region
6. Click **"DEPLOY"**

This ensures Cloud Run can only access resources within your VPC, preventing direct internet exposure.

### 4. Enable Cloud Audit Logs for Compliance

Track all access to secrets and services:

1. Go to left sidebar **≡ (Menu)** → **"Cloud Audit Logs"** or search for **"Audit Logs"**
2. Click **"LOGS"** tab
3. Filter by:
   - Service: **"Cloud Run"**
   - Action: **"google.cloud.run.v1.Services.CreateService"** (see all deployments)
4. Click any log entry to see detailed audit information

This is critical for compliance requirements (SOC 2, ISO 27001, etc.)

### 5. IAM Conditions (Advanced)

Restrict secret access by resource, time, or IP:

1. Go to Secret Manager → select a secret
2. Click **"PERMISSIONS"** tab
3. Click **"GRANT ACCESS"**
4. Add condition: **"Add IAM Condition"**
5. Example: **"Access only from europe-west1 region"**
6. This restricts the service account to only access secrets from that region

---

## Troubleshooting Guide

### Issue: Service Deployment Failed

**Problem**: Deployment process fails with an error

**Root Causes**:
- Service account missing required permissions
- Docker image not found in Container Registry
- Secrets don't exist or have wrong names
- Insufficient quota in the region

**Solutions**:

1. **Check Detailed Error Logs**:
   - Go to Cloud Run service details
   - Click **"LOGS"** tab
   - Read the error message carefully (scroll if needed)
   - Common patterns: "Permission denied", "Image not found", "Secret not found"

2. **Verify Service Account Permissions**:
   - Go to **IAM & Admin** → **"Service Accounts"**
   - Click your service account: `stock-alerter-sa`
   - Click **"GRANT ROLES"** button
   - Verify these roles are present:
     - ✅ Secret Manager Secret Accessor
     - ✅ Cloud Run Developer
   - If missing, click **"+ GRANT ROLES"** and add them

3. **Verify Image in Container Registry**:
   - Go to **Artifact Registry** or **Container Registry**
   - Search for: `gcr.io/PROJECT_ID/stock-alerter`
   - If not found, re-push image:
     ```bash
     docker push gcr.io/$PROJECT_ID/stock-alerter:latest
     ```

4. **Verify Secrets Exist**:
   - Go to **Secret Manager**
   - Check that all 5 secrets exist:
     - ✅ email-sender
     - ✅ email-app-password
     - ✅ email-sender-display-name
     - ✅ twilio-account-sid
     - ✅ twilio-auth-token

5. **Check Regional Quotas**:
   - Go to **IAM & Admin** → **"Quotas"**
   - Search for: **"Cloud Run"**
   - Verify quotas are not exceeded
   - If needed, request quota increase

### Issue: Container Failed to Start and Listen on PORT=8080

**Problem**: Service starts but can't bind to port 8080

**Root Causes**:
- Application crashes during startup (blocking operations)
- Module imports take too long
- Application doesn't properly bind to configured PORT

**Solutions**:

1. **Check Application Logs**:
   - Cloud Run service → **"LOGS"** tab
   - Look for Python errors or stack traces
   - Common: `ModuleNotFoundError`, `ImportError`, `TimeoutError`

2. **Increase Startup Timeout**:
   - Go to service details → **"EDIT & DEPLOY NEW REVISION"**
   - Find **"Timeout"** setting
   - Increase from 300 to **600 seconds** (10 minutes)
   - Click **"DEPLOY"**
   - If this fixes it, application has slow startup

3. **Increase Memory/CPU**:
   - Service details → **"EDIT & DEPLOY NEW REVISION"**
   - Increase **Memory** from 512MB to **2Gi** (2GB)
   - Increase **CPU** from 1 to **2**
   - Click **"DEPLOY"**
   - If this helps, application is resource-constrained during startup

4. **Check Environment Variables**:
   - Verify all required environment variables are set
   - Go to service details → **"EDIT & DEPLOY NEW REVISION"**
   - Scroll to **"Runtime settings"** or **"Environment variables"**
   - Ensure all these variables are present:
     - ✅ EMAIL_ENABLED=true
     - ✅ EMAIL_SMTP_SERVER=smtp.gmail.com
     - ✅ GOOGLE_CLOUD_PROJECT=your-project-id

5. **If problem persists**:
   - Try deploying a minimal test service first
   - Go back to Cloud Run → **"CREATE SERVICE"**
   - Select a different image (like `python:3.12` base)
   - Test if the issue is infrastructure or code
   - If minimal service works, the issue is in Stock Alerter code
   - If minimal service also fails, contact GCP support (possible account quota issue)

### Issue: Permission Denied - Secrets Not Accessible

**Problem**: Cloud Run shows "Permission denied" when accessing secrets

**Root Causes**:
- Service account not granted Secret Manager Accessor role
- Role not granted for specific secret
- Secret name case mismatch

**Solutions**:

1. **Grant Role at Project Level**:
   - Go to **IAM & Admin** → **"IAM"**
   - Find your service account: `stock-alerter-sa@...`
   - Click **"Edit"** (pencil icon)
   - Click **"+ ADD ROLE"**
   - Search for: **"Secret Manager Secret Accessor"**
   - Click **"SAVE"**

2. **Grant Role at Secret Level**:
   - Go to **Secret Manager**
   - Click each secret (email-sender, email-app-password, etc.)
   - Click **"PERMISSIONS"** tab
   - Click **"GRANT ACCESS"**
   - New principals: `stock-alerter-sa@PROJECT_ID.iam.gserviceaccount.com`
   - Role: **"Secret Manager Secret Accessor"**
   - Click **"SAVE"**
   - **Repeat for ALL 5 secrets**

3. **Verify Secret Names Match Exactly** (case-sensitive):
   - In Cloud Run deployment, you set:
     ```
     EMAIL_SENDER = email-sender:latest
     ```
   - In Secret Manager, secret must be named exactly: `email-sender` (lowercase)
   - Typos cause "Secret not found" errors

4. **Redeploy Service**:
   - After granting permissions, go to Cloud Run service
   - Click **"EDIT & DEPLOY NEW REVISION"**
   - Click **"DEPLOY"** (no changes needed)
   - This forces Cloud Run to re-authenticate and pick up new permissions

### Issue: Service Timeout on Requests

**Problem**: Requests to `/run-alerts` endpoint time out

**Root Causes**:
- Alert processing takes longer than timeout
- Background thread blocked by synchronous operation
- External API calls are slow (SMTP, Twilio, etc.)

**Solutions**:

1. **Increase Timeout**:
   - Service details → **"EDIT & DEPLOY NEW REVISION"**
   - Increase **"Timeout"** to 600 seconds (from 300)
   - Click **"DEPLOY"**

2. **Increase Memory/CPU for Performance**:
   - Service details → **"EDIT & DEPLOY NEW REVISION"**
   - Increase **Memory** to 2Gi or 4Gi
   - Increase **CPU** to 2 or 4
   - More resources = faster processing
   - Click **"DEPLOY"**

3. **Check External Integrations**:
   - If using email alerts, Gmail SMTP might be slow
   - If using SMS, Twilio API calls add latency
   - In logs, check for slow operations:
     - "email sending took X seconds"
     - "SMS delivery took X seconds"

4. **Verify Logs for Specific Delays**:
   - Cloud Run service → **"LOGS"** tab
   - Search for log entries related to alert processing
   - Timing information shows where delays occur

### Issue: Wrong Credentials Being Used

**Problem**: Logs show service is using old/wrong email or credentials

**Root Causes**:
- Secret was updated but old version cached
- Cloud Run still referencing old version
- Secret name typo or wrong version specified

**Solutions**:

1. **Verify Secret Current Version**:
   - Go to **Secret Manager**
   - Click the secret (e.g., `email-sender`)
   - Click **"VERSIONS"** tab
   - Check that **":latest"** points to the correct version
   - Latest version should show **"Current"** or **"Latest"** label

2. **Create New Secret Version** (proper way to update):
   - Go to Secret Manager
   - Click the secret to update
   - Click **"+ NEW VERSION"** button (NOT "EDIT")
   - Paste the new value (correct email, password, token, etc.)
   - Click **"ADD NEW VERSION"**
   - This version automatically becomes `:latest`

3. **Force Cloud Run to Pick Up New Secret**:
   - Go to Cloud Run service
   - Click **"EDIT & DEPLOY NEW REVISION"**
   - Don't change anything, just click **"DEPLOY"**
   - This re-deploys and forces re-reading of all `:latest` secrets

4. **Verify Email in Logs**:
   - Go to service **"LOGS"** tab
   - Look for log entries showing which email is being used
   - Should show the correct email from Secret Manager
   - If wrong email, repeat steps 1-3 above

### Issue: Secrets Show Correct but Still Get Access Error

**Problem**: Secret Manager shows permissions correct, but Cloud Run still can't access

**Root Causes**:
- Propagation delay (permission takes a minute to apply)
- Syntax error in secret reference
- Service account reference has typo

**Solutions**:

1. **Wait for Permission Propagation**:
   - After granting role, wait **1-2 minutes**
   - Go back and try again
   - GCP sometimes needs time to sync permissions across services

2. **Redeploy Service with Retry**:
   - Go to Cloud Run service → **"REVISIONS"** tab
   - Click the current revision
   - Click **"ROLLBACK"** if available, then re-deploy current
   - Or: **"EDIT & DEPLOY NEW REVISION"** → **"DEPLOY"** without changes

3. **Verify Exact Service Account Email**:
   - In Secret Manager permissions, copy the exact email:
     ```
     stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com
     ```
   - Paste it exactly in Secret permissions (no typos)

4. **Check Audit Logs for Details**:
   - Go to **Cloud Audit Logs**
   - Filter for "Secret Manager"
   - Find the failed access attempt
   - Click log entry to see detailed error message

### Issue: Need to Delete/Clean Up Service

**Problem**: Want to remove Cloud Run service to start fresh or save costs

**Via Google Cloud Console**:

1. Go to **Cloud Run**
2. Click your service: `stock-alerter`
3. Click **"DELETE"** button (top right)
4. Confirm by typing the service name: `stock-alerter`
5. Click **"DELETE"** button in confirmation dialog
6. Service is deleted, but secrets and service account remain (for reuse)

**If Also Deleting Everything** (complete cleanup):

1. Delete Cloud Run service (steps above)
2. Delete Cloud Scheduler job:
   - Go to **Cloud Scheduler**
   - Find job: `stock-alerter-scheduler`
   - Click **"⋮"** → **"DELETE"**
   - Confirm deletion
3. Delete secrets (optional, usually kept for reuse):
   - Go to **Secret Manager**
   - Click each secret
   - Click **"⋮"** → **"DELETE"**
4. Delete service account (optional):
   - Go to **IAM & Admin** → **"Service Accounts"**
   - Click service account: `stock-alerter-sa`
   - Click **"DELETE"**

---

## Deployment Checklist

Use this comprehensive checklist to ensure all steps are completed:

**Project Setup** ✓
- [ ] GCP Project created and active
- [ ] Project ID noted (format: `my-project-12345`)
- [ ] Region selected (recommended: `us-central1` or `europe-west1`)

**APIs Enabled** ✓
- [ ] Cloud Run API enabled
- [ ] Secret Manager API enabled
- [ ] Artifact Registry API enabled
- [ ] Compute Engine API enabled

**Secrets Created** ✓
- [ ] Secret: `email-sender` created with your Gmail
- [ ] Secret: `email-app-password` created with 16-char app password
- [ ] Secret: `email-sender-display-name` created
- [ ] Secret: `twilio-account-sid` created (if using SMS)
- [ ] Secret: `twilio-auth-token` created (if using SMS)

**Service Account Setup** ✓
- [ ] Service account `stock-alerter-sa` created
- [ ] Service account email noted and saved
- [ ] Role: Secret Manager Secret Accessor granted (project level)
- [ ] Role: Cloud Run Developer granted (project level)

**Secret Permissions** ✓
- [ ] `email-sender` - service account granted accessor role
- [ ] `email-app-password` - service account granted accessor role
- [ ] `email-sender-display-name` - service account granted accessor role
- [ ] `twilio-account-sid` - service account granted accessor role
- [ ] `twilio-auth-token` - service account granted accessor role

**Docker & Image** ✓
- [ ] Docker image built locally: `stock-alerter:latest`
- [ ] Docker authenticated with GCP: `gcloud auth configure-docker`
- [ ] Image tagged for GCP: `gcr.io/PROJECT_ID/stock-alerter:latest`
- [ ] Image pushed to Container Registry successfully

**Cloud Run Deployment** ✓
- [ ] Service created with correct container image
- [ ] Service name set to: `stock-alerter`
- [ ] Authentication set to: "Allow unauthenticated invocations"
- [ ] Service account set to: `stock-alerter-sa@...`
- [ ] **Environment Variables configured**:
  - [ ] GOOGLE_CLOUD_PROJECT
  - [ ] EMAIL_ENABLED=true
  - [ ] EMAIL_SMTP_SERVER
  - [ ] EMAIL_SMTP_PORT
  - [ ] EMAIL_RECEIVERS
  - [ ] EMAIL_BCC_RECEIVERS
  - [ ] EMAIL_SENDER_DISPLAY_NAME
  - [ ] NTFY_ENABLED
  - [ ] NTFY_TOPICS
  - [ ] TWILIO_ENABLED
  - [ ] TWILIO_PHONE_NUMBER
  - [ ] SMS_RECEIVER_PHONE_NUMBER
- [ ] **Secrets configured**:
  - [ ] EMAIL_SENDER secret mapped
  - [ ] EMAIL_APP_PASSWORD secret mapped
  - [ ] EMAIL_SENDER_DISPLAY_NAME secret mapped
  - [ ] TWILIO_ACCOUNT_SID secret mapped (if using)
  - [ ] TWILIO_AUTH_TOKEN secret mapped (if using)
- [ ] Memory: 512MB (or higher for production)
- [ ] CPU: 1 (or higher if needed)
- [ ] Timeout: 300 seconds (or 600 for slow processes)
- [ ] Max instances: 10 (or lower to limit costs)

**Service Verification** ✓
- [ ] Deployment completed successfully
- [ ] Service URL obtained (e.g., `https://stock-alerter-xxxxx.run.app`)
- [ ] Health endpoint tested: `/health` returns 200
- [ ] Logs reviewed for any errors
- [ ] Metrics showing request traffic (if applicable)

**Optional - Cloud Scheduler** ✓
- [ ] Cloud Scheduler API enabled
- [ ] Job created: `stock-alerter-scheduler`
- [ ] Schedule configured: `0 */4 * * *` (or your preferred frequency)
- [ ] Job URL points to correct service endpoint: `/run-alerts`
- [ ] Service account selected for job execution
- [ ] Job tested manually with "Force run"
- [ ] Logs show successful execution

**Security & Monitoring** ✓
- [ ] Service account has only necessary roles (principle of least privilege)
- [ ] All secrets properly restricted to service account
- [ ] Audit logging reviewed (optional but recommended)
- [ ] Cost budget set up in Billing console (recommended)
- [ ] Monitoring alerts configured (optional for production)

**Post-Deployment** ✓
- [ ] Documentation updated with service URL
- [ ] Team notified of deployment
- [ ] Runbook created for operations
- [ ] Disaster recovery plan in place

---

## Summary

You now have a fully functional Google Cloud Run deployment via the UI with:

✅ **Secure credential management** via Secret Manager  
✅ **No-downtime secret updates** - just create new secret versions  
✅ **Automatic scaling** based on traffic (0 to max instances)  
✅ **Scheduled execution** via Cloud Scheduler (optional)  
✅ **Comprehensive logging and monitoring** via Cloud Logging  
✅ **Service account authentication** for fine-grained access control  
✅ **Cost optimization** with free tier and instance limits  

Your Stock Alerter is now running in production on Google Cloud Run! 🚀

## References

For more information and advanced configurations:

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Secret Manager Best Practices](https://cloud.google.com/secret-manager/docs/best-practices)
- [Cloud Scheduler Cron Format](https://cloud.google.com/scheduler/docs/quickstart)
- [Cloud Run Pricing Calculator](https://cloud.google.com/run/pricing)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)
- [Securing Cloud Run Services](https://cloud.google.com/run/docs/securing/managing-access)

## Quick Reference - Common UI Operations

**View Service Details**:
1. Cloud Run → Click service name → See service URL, status, metrics, logs

**Update Environment Variable**:
1. Service → **"EDIT & DEPLOY NEW REVISION"** → Find variable → Change value → **"DEPLOY"**

**Update Secret**:
1. Secret Manager → Click secret → **"+ NEW VERSION"** → Paste new value → **"ADD NEW VERSION"**
2. Cloud Run automatically uses `:latest` version next time

**View Recent Logs**:
1. Cloud Run service → **"LOGS"** tab → See real-time logs with timestamps

**Test Service Manually**:
1. Copy service URL
2. Append endpoint: `https://your-service.run.app/health`
3. Open in browser or run: `curl https://your-service.run.app/health`

**Scale Resources**:
1. Service → **"EDIT & DEPLOY NEW REVISION"**
2. Adjust Memory, CPU, Timeout, Max instances
3. **"DEPLOY"** to apply changes

**Delete Everything**:
1. Cloud Run: Service → **"DELETE"**
2. Cloud Scheduler: Job → **"DELETE"**
3. Secret Manager: Each secret → **"DELETE"** (optional)
4. Service Account: **"DELETE"** (optional)


