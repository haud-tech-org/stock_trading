# 🔧 Cloud Deployment Setup Guide

**Purpose**: Pre-deployment prerequisite configuration (Steps 1-6)  
**Audience**: First-time deployers preparing for deployment  
**Time**: ~15-20 minutes  
**Status**: ✅ Ready to Begin Deployment  
**Date**: March 24, 2026

---

## Overview

This guide covers all prerequisite setup required **before** building and deploying to Cloud Run:
1. Project variables configuration
2. API enablement
3. Secret Manager setup
4. Service account creation
5. IAM permission configuration

**After completing this guide**, proceed to `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md` to build and deploy.

---

## Step 1: Set Up Project Variables

Initialize deployment by setting up project-level variables used throughout all steps.

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

---

## Step 2: Enable Required APIs

Enable the Google Cloud APIs needed for running the Stock Alerter service.

```bash
# Enable necessary APIs for Cloud Run and related services
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  artifactregistry.googleapis.com \
  compute.googleapis.com \
  vpcaccess.googleapis.com
```

**Argument Explanations**:
- `run.googleapis.com`: Cloud Run API - enables serverless container deployment
- `secretmanager.googleapis.com`: Secret Manager API - enables secure credential storage
- `artifactregistry.googleapis.com`: Artifact Registry API - enables container image storage
- `compute.googleapis.com`: Compute Engine API - enables VM and networking resources
- `vpcaccess.googleapis.com`: Serverless VPC Access API - enables VPC connector for static outbound IP

**Verification**:
```bash
# Check that all APIs are enabled
gcloud services list --enabled | grep -E "run|secretmanager|artifactregistry|compute|vpcaccess"
```

---

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

# Store Binance live production API credentials
echo -n "your_live_api_key_here" | gcloud secrets create binance-api-key \
  --data-file=-

echo -n "your_live_api_secret_here" | gcloud secrets create binance-api-secret \
  --data-file=-

# Store Binance demo/paper-trading API credentials
echo -n "your_demo_api_key_here" | gcloud secrets create binance-demo-api-key \
  --data-file=-

echo -n "your_demo_api_secret_here" | gcloud secrets create binance-demo-api-secret \
  --data-file=-

# Store Slack Incoming Webhook URL(s)
# Treat the webhook URL as a secret — anyone with it can post to your Slack channel
# Comma-separate multiple URLs if posting to more than one channel
echo -n "https://your-org.webhook.office.com/webhookb2/xxx/IncomingWebhook/yyy/zzz" | \
  gcloud secrets create slack-webhook-urls \
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

**Verification**:
```bash
# List all created secrets
gcloud secrets list

# Verify each secret was created
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token \
              binance-api-key binance-api-secret \
              binance-demo-api-key binance-demo-api-secret \
              slack-webhook-urls; do
  echo "Checking $secret..."
  gcloud secrets describe $secret
done
```

---

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

# Save to environment for use in Step 5 and 6
export SERVICE_ACCOUNT_EMAIL
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

**Verification**:
```bash
# Verify service account was created
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL

# List all service accounts
gcloud iam service-accounts list
```

---

## Step 5: Grant Secret Access Permissions

Grant the service account permission to access the secrets created in Step 3.

```bash
# For each secret, grant the service account read-only access
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token \
              binance-api-key binance-api-secret \
              binance-demo-api-key binance-demo-api-secret \
              slack-webhook-urls; do
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

**Verification**:
```bash
# Verify service account has access to each secret
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token \
              binance-api-key binance-api-secret \
              binance-demo-api-key binance-demo-api-secret \
              slack-webhook-urls; do
  echo "Permissions for $secret:"
  gcloud secrets get-iam-policy $secret
done
```

---

## Step 6: Grant Additional Permissions

Grant the service account all necessary roles for deployment, execution, and Cloud Run management.

```bash
# Set variables for clarity
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

---

## Step 6.5: Set Up Static Outbound IP for Binance API Whitelisting

**⚠️ MANDATORY** — Binance requires a whitelisted IP for API key security. Cloud Run uses **dynamic outbound IPs** by default, which change unpredictably. This step creates a **fixed static IP** that your service will always use when calling Binance (or any external API).

### Why This Is Required

| Without Static IP | With Static IP |
|---|---|
| Cloud Run uses random Google IPs | All outbound traffic exits via one fixed IP |
| Binance API calls fail (IP not whitelisted) | Binance accepts requests from `34.156.14.253` |
| IP changes on every new revision | IP never changes unless manually deleted |

### Architecture

```
Cloud Run → VPC Connector (my-connector)
          → Cloud Router  (my-router)
          → Cloud NAT     (my-nat)
          → Static IP     34.156.14.253
          → Binance API / External Services
```

### Step 6.5.1: Create VPC Connector

The VPC Connector is the "bridge" that connects Cloud Run (serverless) to your VPC network.

```bash
# Create a VPC Access Connector in the same region as Cloud Run
gcloud compute networks vpc-access connectors create my-connector \
  --region=europe-west1 \
  --range=10.8.0.0/28 \
  --network=default
```

**Argument Explanations**:
- `my-connector`: Name of the connector (referenced in Cloud Run deployment)
- `--region=europe-west1`: Must match the Cloud Run service region
- `--range=10.8.0.0/28`: Internal IP range for the connector VMs (must not overlap existing subnets)
- `--network=default`: VPC network to attach to (use `default` unless you have a custom VPC)

**Verify**:
```bash
gcloud compute networks vpc-access connectors describe my-connector --region=europe-west1
# STATUS should be: READY
```

### Step 6.5.2: Reserve a Static IP Address

Reserve a fixed external IP in the same region — this will be the permanent outbound IP.

```bash
# Reserve a static external IP address
gcloud compute addresses create my-static-ip --region=europe-west1

# Get and record the reserved IP address
gcloud compute addresses describe my-static-ip \
  --region=europe-west1 \
  --format='value(address)'
```

**📌 Record this IP — you will whitelist it on Binance.**

**Actual Execution Result (May 21, 2026)**:
```
34.156.14.253
```

**Status**: ✅ Static IP reserved: **`34.156.14.253`**

### Step 6.5.3: Create a Cloud Router

The Cloud Router manages the routing rules for traffic leaving your VPC.

```bash
# Create a Cloud Router in the same region and VPC network
gcloud compute routers create my-router \
  --network=default \
  --region=europe-west1
```

**Argument Explanations**:
- `my-router`: Name of the router (referenced by the NAT gateway)
- `--network=default`: Must match the VPC network used by the VPC Connector
- `--region=europe-west1`: Must match the Cloud Run service region

### Step 6.5.4: Create the NAT Gateway

The NAT Gateway is the "exit door" — it routes all outbound VPC traffic through your static IP.

```bash
# Create a Cloud NAT gateway using the static IP and router
gcloud compute routers nats create my-nat \
  --router=my-router \
  --region=europe-west1 \
  --nat-all-subnet-ip-ranges \
  --nat-external-ip-pool=my-static-ip
```

**Argument Explanations**:
- `my-nat`: Name of the NAT gateway
- `--router=my-router`: The router created in Step 6.5.3
- `--nat-all-subnet-ip-ranges`: Apply NAT to all subnets in the VPC
- `--nat-external-ip-pool=my-static-ip`: Use the reserved static IP as the exit IP

**Verify**:
```bash
gcloud compute routers nats describe my-nat \
  --router=my-router \
  --region=europe-west1
# natIpAllocateOption should be: MANUAL_ONLY
# natIps should contain: my-static-ip
```

### Binance Whitelisting

After completing the above steps, add the static IP to your Binance API key whitelist:

1. Log in to **Binance** → **Account** → **API Management**
2. Select your API key → **Edit restrictions**
3. Enable **"Restrict access to trusted IPs only"**
4. Add IP: **`34.156.14.253`**
5. Save changes

> ℹ️ The VPC connector is wired into the Cloud Run deployment command in **Step 9 of `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md`** via `--vpc-connector=my-connector --vpc-egress=all-traffic`.

### Actual Execution Results (May 21, 2026)

| Resource | Name | Status |
|---|---|---|
| VPC Connector | `my-connector` | ✅ READY |
| Static IP | `my-static-ip` → `34.156.14.253` | ✅ Reserved |
| Cloud Router | `my-router` | ✅ Created |
| NAT Gateway | `my-nat` | ✅ Created |

---

## ✅ Setup Checklist

- [ ] Project variables set (`PROJECT_ID`, `REGION`, `SERVICE_NAME`)
- [ ] APIs enabled (Cloud Run, Secret Manager, Artifact Registry, Compute, VPC Access)
- [ ] All 10 secrets created in Secret Manager
  - [ ] email-sender
  - [ ] email-app-password
  - [ ] email-sender-display-name
  - [ ] twilio-account-sid
  - [ ] twilio-auth-token
  - [ ] binance-api-key
  - [ ] binance-api-secret
  - [ ] binance-demo-api-key
  - [ ] binance-demo-api-secret
  - [ ] slack-webhook-urls
- [ ] Service account created (stock-alerter-sa)
- [ ] Service account email captured and exported
- [ ] Service account has `secretmanager.secretAccessor` role for all 10 secrets
- [ ] Service account has 8 additional roles assigned
- [ ] All roles verified with `gcloud projects get-iam-policy`
- [ ] VPC Connector created (`my-connector`, status: READY)
- [ ] Static IP reserved (`my-static-ip` → `34.156.14.253`)
- [ ] Cloud Router created (`my-router`)
- [ ] NAT Gateway created (`my-nat` using `my-static-ip`)
- [ ] Static IP `34.156.14.253` whitelisted on Binance API key

---

## 🚀 Next Steps

After completing all setup steps above:

1. **Build & Deploy**: Proceed to `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md`
2. **After Deployment**: Proceed to `03_OPERATIONS_&_REFERENCE.md`

---

## 🔗 Related Guides

- **Deployment Execution**: `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md`
- **Operations & Reference**: `03_OPERATIONS_&_REFERENCE.md`
- **Execution Log (Reference)**: `DEPLOYMENT_EXECUTION_LOG_20260320.md`
- **Optimization Analysis**: `GOOGLE_CLOUD_DEPLOYMENT_OPTIMIZATION_ANALYSIS.md`

---

## ⚠️ Troubleshooting

### Error: "API not enabled"
```bash
# Re-enable APIs
gcloud services enable run.googleapis.com secretmanager.googleapis.com \
  artifactregistry.googleapis.com compute.googleapis.com
```

### Error: "Service account creation failed"
```bash
# Verify you have iam.serviceAccountAdmin role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/iam.serviceAccountAdmin"
```

### Error: "Cannot add IAM binding"
```bash
# Verify service account exists
gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL

# Verify you have roles.resourcemanager.organizationAdmin or roles/owner
gcloud projects get-iam-policy $PROJECT_ID
```
