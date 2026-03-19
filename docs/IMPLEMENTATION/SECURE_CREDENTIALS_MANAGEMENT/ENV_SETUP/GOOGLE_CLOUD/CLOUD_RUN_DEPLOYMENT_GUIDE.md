# Stock Alerter - Cloud Run Deployment & Operations Guide

**Last Updated**: March 19, 2026  
**Service**: stock-alerter  
**Region**: europe-west1 (Belgium)  
**Status**: ✅ ACTIVE & DEPLOYED

---

## 📋 Quick Reference

### Current Service Status
```
URL:              https://stock-alerter-717776322217.europe-west1.run.app
Image:            gcr.io/stock-trading-489001/stock-alerter:latest
Billing:          Instance-Based (CPU throttling: DISABLED)
CPU:              8 cores (always available)
Memory:           8Gi
Max Instances:    2
Monthly Cost:     ~$744-1,488 USD
```

### Verify Service
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
✅ 8Gi memory for data processing
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
- Memory (8Gi):         $87
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
# Run only weekdays 9 AM - 4 PM
gcloud scheduler jobs update http stock-alerter-scheduler \
  --location=europe-west1 \
  --schedule="*/15 9-16 * * 1-5"
```

---

## 🔍 Troubleshooting Guide

### Issue: Service Not Starting
**Symptoms**: Container failed to start
**Solution**:
```bash
# Check logs for errors
gcloud run services logs read stock-alerter --region=europe-west1 --stream

# Increase timeout if startup takes long
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --timeout 600  # 10 minutes

# Test container locally
docker run -e PORT=8080 gcr.io/stock-trading-489001/stock-alerter:latest
```

### Issue: Permission Denied Accessing Secrets
**Symptoms**: "Permission denied" errors in logs
**Solution**:
```bash
# Re-grant secret access to service account
gcloud secrets add-iam-policy-binding email-app-password \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor

# Verify permission
gcloud secrets get-iam-policy email-app-password
```

### Issue: High Memory Usage
**Symptoms**: OOM (Out of Memory) errors
**Solution**:
```bash
# Increase memory allocation
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --memory 16Gi

# Or reduce concurrency
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --concurrency 320  # Lower than 640
```

### Issue: Slow Response Times
**Symptoms**: Requests timing out (300s limit)
**Solution**:
```bash
# Check CPU throttling status
gcloud run services describe stock-alerter --region=europe-west1 --format=json | grep cpu-throttling

# If request-based (cpu-throttling: true), switch to instance-based
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --no-cpu-throttling

# Or increase CPU cores
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --cpu 8  # Maximum
```

### Issue: Service Account Permissions
**Symptoms**: "Service account does not have permission"
**Solution**:
```bash
# Grant required roles
gcloud projects add-iam-policy-binding stock-trading-489001 \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/run.invoker

gcloud projects add-iam-policy-binding stock-trading-489001 \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

### Issue: Docker Image Not Found
**Symptoms**: "Could not pull image" error
**Solution**:
```bash
# Verify image exists
gcloud container images list --repository=gcr.io/stock-trading-489001

# Check image details
gcloud container images describe gcr.io/stock-trading-489001/stock-alerter:latest

# Re-push image if needed
docker tag stock-alerter:latest gcr.io/stock-trading-489001/stock-alerter:latest
docker push gcr.io/stock-trading-489001/stock-alerter:latest
```

---

## 📚 Configuration Details

### Environment Variables (10 total)
```
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_RECEIVERS=haud.fin@gmail.com
EMAIL_BCC_RECEIVERS=haud.fin@gmail.com
NTFY_ENABLED=false
NTFY_TOPICS=vn30_alerts_f8a9b2c1
TWILIO_ENABLED=false
TWILIO_PHONE_NUMBER=""
SMS_RECEIVER_PHONE_NUMBER=""
```

### Secrets (5 total - Encrypted in Secret Manager)
```
email-sender                    → Gmail address
email-app-password              → Gmail App Password
email-sender-display-name       → Email display name
twilio-account-sid              → SMS service (unused)
twilio-auth-token               → SMS service (unused)
```

### Storage Configuration
```
Cloud Storage Bucket:   gs://stock-trading-2
Mount Path:             /mnt
Driver:                 gcsfuse.run.googleapis.com
Access:                 Read/Write
```

### Health Check
```
Type:               TCP
Port:               8080
Interval:           240 seconds (4 minutes)
Timeout:            240 seconds (4 minutes)
Failure Threshold:  1 (single failure triggers restart)
```

---

## 🔐 Security Configuration

### Authentication
```
Authentication:     ✅ Required (IAM permissions)
Service Account:    stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com
Secrets:            ✅ Encrypted in Secret Manager
Logging:            ✅ All requests logged in Cloud Logging
Audit Trail:        ✅ Available in Cloud Audit Logs
```

### Permissions (Service Account Roles)
```
roles/run.admin                         → Manage Cloud Run
roles/iam.serviceAccountUser            → Use service account
roles/storage.objectAdmin               → Access Cloud Storage
roles/run.invoker                       → Invoke service
roles/artifactregistry.reader           → Pull Docker images
roles/compute.admin                     → Manage compute resources
roles/logging.logWriter                 → Write logs
roles/monitoring.metricWriter           → Write metrics
roles/secretmanager.secretAccessor      → Access secrets
```

---

## 📊 Performance Monitoring

### Monitor Billing
```bash
# Check current costs
gcloud billing budgets list

# View project info
gcloud compute project-info describe --project=stock-trading-489001
```

### Monitor Resource Usage
```bash
# CPU and Memory usage
gcloud monitoring dashboards list

# Cloud Run metrics
gcloud run services describe stock-alerter --region=europe-west1 --format=json | grep -E "cpu|memory|concurrency"
```

### Check Scaling Activity
```bash
# View recent deployments
gcloud run services describe stock-alerter --region=europe-west1 --format=json | grep -E "instance|scale"

# Monitor instance count over time (Cloud Console → Monitoring)
```

---

## 🚀 Redeployment Checklist

When redeploying after code changes:

- [ ] Build Docker image: `docker buildx build --platform linux/amd64 -t stock-alerter:latest .`
- [ ] Tag for registry: `docker tag stock-alerter:latest gcr.io/stock-trading-489001/stock-alerter:latest`
- [ ] Authenticate Docker: `gcloud auth configure-docker`
- [ ] Push image: `docker push gcr.io/stock-trading-489001/stock-alerter:latest`
- [ ] Deploy to Cloud Run: `gcloud run deploy stock-alerter --region=europe-west1 --image gcr.io/stock-trading-489001/stock-alerter:latest`
- [ ] Verify deployment: `gcloud run services describe stock-alerter --region=europe-west1`
- [ ] Check logs: `gcloud run services logs read stock-alerter --region=europe-west1 --limit=50`

---

## 🆘 Emergency Troubleshooting

### Service Not Responding
```bash
# 1. Check if service is running
gcloud run services describe stock-alerter --region=europe-west1

# 2. View error logs
gcloud run services logs read stock-alerter --region=europe-west1 --stream

# 3. Restart service (redeploy)
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --image gcr.io/stock-trading-489001/stock-alerter:latest

# 4. If still broken, check secrets
gcloud secrets list
```

### Cannot Access Cloud Storage
```bash
# Verify storage bucket exists
gsutil ls gs://stock-trading-2

# Check service account has access
gcloud projects get-iam-policy stock-trading-489001 | grep storage

# Grant storage access if missing
gcloud projects add-iam-policy-binding stock-trading-489001 \
  --member=serviceAccount:stock-alerter-sa@stock-trading-489001.iam.gserviceaccount.com \
  --role=roles/storage.objectAdmin
```

### Secrets Not Found
```bash
# List all secrets
gcloud secrets list

# Verify service account can access
gcloud secrets get-iam-policy email-app-password

# Recreate if missing
echo -n "your_email@gmail.com" | gcloud secrets create email-sender --data-file=-
```

---

## 📞 Key Commands Summary

```bash
# View service
gcloud run services describe stock-alerter --region=europe-west1

# View logs (live)
gcloud run services logs read stock-alerter --region=europe-west1 --stream

# Deploy
gcloud run deploy stock-alerter \
  --image gcr.io/stock-trading-489001/stock-alerter:latest \
  --region=europe-west1

# Update config
gcloud run deploy stock-alerter \
  --region=europe-west1 \
  --memory 8Gi \
  --cpu 8 \
  --no-cpu-throttling

# Delete service (if needed)
gcloud run services delete stock-alerter --region=europe-west1 --quiet

# List all services
gcloud run services list --region=europe-west1
```

---

## 📁 Configuration Files

- **cloud-run-service-config.json** - Complete service configuration (JSON export)
- **docs/.../GOOGLE_CLOUD_DEPLOYMENT.md** - Full step-by-step deployment guide

---

## ✅ Current Status Checklist

- [x] Service deployed and running
- [x] Billing model: Instance-Based (CPU throttling: disabled)
- [x] CPU cores: 8 (always available)
- [x] Memory: 8Gi
- [x] Max instances: 2
- [x] Startup CPU boost: Enabled
- [x] Health checks: Active (TCP:8080)
- [x] Secrets: 5 secrets accessible
- [x] Storage: Cloud Storage mounted
- [x] Authentication: IAM required
- [x] Logging: Enabled
- [x] Monitoring: Enabled

---

**Version**: production-v1  
**Last Verified**: March 19, 2026  
**Next Review**: After 30 days of operation
