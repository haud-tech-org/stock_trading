# 📊 Cloud Operations & Reference Guide

**Purpose**: Post-deployment operations, monitoring, troubleshooting, and cost management  
**Audience**: Operations team and service maintainers  
**Time**: Reference guide (use as needed)  
**Status**: ✅ ACTIVE & DEPLOYED  
**Date**: March 24, 2026

---

## Overview

This guide covers all post-deployment operations:
- Daily service management
- Monitoring and alerting
- Troubleshooting and debugging
- Cost management and optimization
- Scheduler setup and management
- Emergency procedures

---

## 📋 Quick Reference

### Current Service Status

```
URL:              https://stock-alerter-717776322217.europe-west1.run.app
Image:            gcr.io/stock-trading-489001/stock-alerter:latest
Region:           europe-west1 (Belgium)
Billing:          Instance-Based (CPU throttling: DISABLED)
CPU:              8 cores (always available)
Memory:           16Gi
Min Instances:    1 (always warm)
Max Instances:    2
Monthly Cost:     ~$744-1,488 USD (depends on usage)
```

### Verify Service Status

```bash
gcloud run services describe stock-alerter --region=europe-west1
```

---

## 🚀 Deployment Architecture

### Instance-Based Billing (Current)

```
✅ Full 8 CPU cores always available
✅ No CPU throttling between requests
✅ 640 concurrent requests per instance
✅ 16Gi memory for data processing
✅ Optimal for real-time monitoring (24/7)
✅ Predictable fixed costs (~$744/month per instance)
```

### Why This Configuration?

- Stock alerts need continuous monitoring (not sporadic)
- High concurrency (640 requests/instance)
- Parallel data processing required
- Consistent low-latency performance needed
- Cost predictability important

---

## 🛠️ Common Operations

### View Service Status

```bash
# Get complete service details
gcloud run services describe stock-alerter --region=europe-west1

# JSON format for scripting
gcloud run services describe stock-alerter --region=europe-west1 --format=json
```

### View Logs

```bash
# Last 50 logs
gcloud run services logs read stock-alerter --region=europe-west1 --limit=50

# Stream live logs (real-time)
gcloud run services logs read stock-alerter --region=europe-west1 --stream

# Errors only
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" --limit=20
```

### Update Service Configuration

```bash
# Change memory/CPU (keeps instance-based billing)
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --memory 4Gi \
  --cpu 4 \
  --no-cpu-throttling

# Update environment variable
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --set-env-vars EMAIL_ENABLED=true

# Update secret
echo -n "new_password" | gcloud secrets versions add email-app-password --data-file=-

# Redeploy with new image
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --image gcr.io/stock-trading-489001/stock-alerter:latest
```

---

## 💰 Billing & Cost Management

### Current Costs

```
Per Instance/Month:     ~$744
For 2 Instances:        ~$1,488
Average (60% usage):    ~$890

Breakdown:
- CPU (8 cores):        $657
- Memory (16Gi):        $87
```

### Cost Optimization Options

#### Option 1: Switch to Request-Based Billing

**When**: If alerts only needed during market hours  
**Savings**: ~$400-500/month per instance  
**Tradeoff**: CPU throttled, higher latency

```bash
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --cpu 4 \
  --memory 4Gi \
  --cpu-throttling  # Enable request-based
```

#### Option 2: Reduce Max Instances

**When**: If alerts don't need high concurrency  
**Savings**: ~50% (from $1,488 to $744/month)  
**Tradeoff**: Lower availability

```bash
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --max-instances 1
```

#### Option 3: Schedule Execution (Market Hours Only)

**When**: If real-time 24/7 not needed  
**Savings**: ~70%  
**Tradeoff**: Alerts only on schedule

```bash
# Only run during market hours (9 AM - 4 PM, weekdays)
gcloud scheduler jobs update http stock-alerter-scheduler \
  --location=europe-west1 \
  --schedule="*/15 9-16 * * 1-5"
```

---

## 📊 Post-Deployment Monitoring & Alerts

### Cloud Logging Setup

```bash
# Set up Cloud Run logs filter in Cloud Logging
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=stock-alerter" \
  --limit=50 \
  --format=json

# Or use Cloud Logging in Google Cloud Console
# Navigation: Cloud Logging > Logs Explorer
# Filter: resource.type="cloud_run_revision" AND resource.labels.service_name="stock-alerter"
# Add field extraction:
#   - Extract severity level
#   - Extract error messages
#   - Extract response times
```

### Cloud Monitoring Alerts

```bash
# Set up Cloud Monitoring for service availability
# Navigate to Cloud Console > Monitoring > Alerting Policies
# Create alerts for:

# Alert 1: High Error Rate
#   - Metric: cloud.run/request_count
#   - Filter: response_code >= 500
#   - Threshold: error rate > 1%
#   - Duration: 5 minutes

# Alert 2: High Latency
#   - Metric: cloud.run/request_latencies
#   - Threshold: p95 latency > 1000ms
#   - Duration: 5 minutes

# Alert 3: Service Unavailable
#   - Metric: cloud.run/request_count
#   - Threshold: 0 requests for 10 minutes
#   - Duration: 5 minutes

# Alert 4: High Memory Usage
#   - Metric: cloud.run/container_memory_allocations
#   - Threshold: > 14Gi
#   - Duration: 5 minutes
```

---

## 🔄 Cloud Scheduler Setup

Configure Cloud Scheduler to trigger the alert generation automatically.

```bash
# Create a Cloud Scheduler job to trigger alerts periodically
gcloud scheduler jobs create http stock-alerter-scheduler \
  --location=europe-west1 \
  --schedule="*/60 * * * *" \
  --uri="https://stock-alerter-717776322217.europe-west1.run.app/run-alerts" \
  --http-method=POST \
  --oidc-service-account-email=stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --oidc-token-audience=https://stock-alerter-717776322217.europe-west1.run.app
```

### Manage Scheduler Jobs

```bash
# Modify the schedule
gcloud scheduler jobs update http stock-alerter-scheduler \
  --location=europe-west1 \
  --schedule="0 */4 * * *"  # Change to every 4 hours

# View job details
gcloud scheduler jobs describe stock-alerter-scheduler --location=europe-west1

# Trigger job manually (for testing)
gcloud scheduler jobs run stock-alerter-scheduler --location=europe-west1

# View job execution history
gcloud logging read "resource.type=cloud_scheduler_job AND resource.labels.job_id=stock-alerter-scheduler" \
  --limit=10 \
  --format=json
```

### Cron Expression Reference

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

---

## 🔧 Troubleshooting

### Service Not Responding

**Symptoms**: Health endpoint returns errors or times out

**Steps**:
```bash
# 1. Check if service is running
gcloud run services describe stock-alerter --region=europe-west1

# 2. Check recent errors
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" --limit=20

# 3. Check container startup logs
gcloud logging read "resource.type=cloud_run_revision" --order=desc --limit=50

# 4. Manually trigger via Cloud Run
gcloud run services call stock-alerter --region=europe-west1
```

**Solutions**:
- Check container logs for startup errors
- Verify environment variables are set correctly
- Check Secret Manager access permissions
- Increase timeout if service takes long to start

---

### High Error Rate

**Symptoms**: Many 5xx errors in logs

**Steps**:
```bash
# 1. Check error rate
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --limit=50 \
  --format=json | jq '.[] | .textPayload'

# 2. Check specific error messages
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --stream

# 3. Check service configuration
gcloud run services describe stock-alerter --region=europe-west1 --format=json
```

**Common Causes**:
- Secret access denied (permissions issue)
- Database connection error
- Memory exhausted (too many concurrent requests)
- Timeout exceeded

**Solutions**:
```bash
# Verify secret access
gcloud secrets get-iam-policy email-sender

# Re-grant if needed
gcloud secrets add-iam-policy-binding email-sender \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Increase timeout if alerts take longer
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --timeout=600  # 10 minutes
```

---

### High Memory Usage

**Symptoms**: Memory usage approaching 16Gi limit

**Steps**:
```bash
# Check memory metrics
gcloud monitoring dashboards list

# View memory usage logs
gcloud logging read "resource.type=cloud_run_revision AND metric.type=cloud.run/container_memory_allocations" \
  --limit=20
```

**Solutions**:
```bash
# Option 1: Increase max instances (distribute load)
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --max-instances=3

# Option 2: Reduce memory if possible (profile application)
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --memory=8Gi  # Reduce from 16Gi

# Option 3: Optimize code (database queries, caching, etc.)
```

---

### Permission Denied Errors

**Symptoms**: "Permission denied" errors in logs

**Steps**:
```bash
# 1. Verify service account has required roles
gcloud projects get-iam-policy stock-trading-489001 --format=json | \
  jq ".bindings[] | select(.members[] | contains(\"stock-alerter-sa\"))"

# 2. Verify secret access
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token; do
  gcloud secrets get-iam-policy $secret
done

# 3. Check Cloud Storage access
gcloud gs-cp --list-buckets
```

**Solutions**:
```bash
# Grant missing role
gcloud projects add-iam-policy-binding stock-trading-489001 \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin

# Grant secret access
gcloud secrets add-iam-policy-binding email-sender \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

---

## 🚨 Emergency Procedures

### Rollback to Previous Revision

```bash
# List recent revisions
gcloud run services describe stock-alerter --region=europe-west1 --format=json | \
  jq '.status.traffic'

# If current revision is broken, route traffic to previous
gcloud run services update-traffic stock-alerter \
  --region=europe-west1 \
  --to-revisions=stock-alerter-00001-abc=100  # Previous revision ID
```

### Disable Service (Emergency Shutdown)

```bash
# Allow unauthenticated access (make service internal only)
gcloud run services update stock-alerter \
  --region=europe-west1 \
  --no-allow-unauthenticated

# Scale down to zero instances
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --min-instances=0 \
  --max-instances=1
```

### Force Restart Service

```bash
# Update timestamp to force redeployment
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --image=gcr.io/stock-trading-489001/stock-alerter:latest \
  --revision-suffix=$(date +%s)
```

---

## 📈 Performance Monitoring

### Monitor CPU & Memory

```bash
# View current metrics
gcloud run services describe stock-alerter \
  --region=europe-west1 \
  --format='value(status.conditions[].message)'

# Create custom dashboard (optional)
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

### Check Scaling Activity

```bash
# View instance count over time
gcloud logging read "resource.type=cloud_run_revision" \
  --limit=50 \
  --format=json | jq '.[] | {timestamp:.timestamp, instances:.labels.instance_id}'

# View concurrency metrics
gcloud run services describe stock-alerter \
  --region=europe-west1 \
  --format=json | grep -i "concurrency\|request"
```

---

## 🔐 Security & Audit

### View Audit Logs

```bash
# Check Cloud Audit Logs
gcloud logging read "protoPayload.serviceName=run.googleapis.com" \
  --limit=20 \
  --format=json

# Filter by operation
gcloud logging read "protoPayload.methodName=google.cloud.run.v1.Services.CreateService" \
  --limit=10
```

### Verify IAM Permissions

```bash
# Check all permissions assigned to service account
gcloud projects get-iam-policy stock-trading-489001 --format=json | \
  jq ".bindings[] | select(.members[] | contains(\"stock-alerter-sa\"))"

# Check secret access
for secret in email-sender email-app-password email-sender-display-name \
              twilio-account-sid twilio-auth-token; do
  echo "=== $secret ==="
  gcloud secrets get-iam-policy $secret --format=json | \
    jq ".bindings[] | select(.members[] | contains(\"stock-alerter-sa\"))"
done
```

---

## 🔗 Related Guides

- **Setup Guide**: `01_DEPLOYMENT_SETUP.md`
- **Execution Guide**: `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md`
- **Execution Log (Reference)**: `DEPLOYMENT_EXECUTION_LOG_20260320.md`
- **Full Original Guide**: `GOOGLE_CLOUD_DEPLOYMENT.md`

---

## 📚 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Cloud Logging Documentation](https://cloud.google.com/logging/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)

