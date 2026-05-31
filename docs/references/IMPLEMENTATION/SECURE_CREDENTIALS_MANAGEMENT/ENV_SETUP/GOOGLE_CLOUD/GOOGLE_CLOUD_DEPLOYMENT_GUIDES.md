# 🚀 Google Cloud Deployment Guides

**Status**: ✅ **OPTIMIZED STRUCTURE**  
**Last Updated**: March 24, 2026  
**Total Size**: ~1,500 lines (reduced from 3,562)  
**Reduction**: -58% documentation volume

---

## � Table of Contents

1. [Quick Navigation](#-quick-navigation) - Find your path
2. [File Overview](#-file-overview) - What's in each guide
3. [Decision Matrix](#-decision-matrix) - Choose your guide
4. [Learning Path](#-learning-path) - New member onboarding
5. [Key Improvements](#-key-improvements-from-optimization) - What changed
6. [File Organization](#-file-organization) - Directory structure
7. [Content Distribution](#-content-distribution) - What's covered
8. [Quick Start](#-quick-start) - Deploy in 5 minutes
9. [Key Concepts](#-key-concepts) - Important terms
10. [Additional Resources](#-additional-resources) - External links
11. [Need Help?](#-need-help) - Support guide
12. [Guide Features](#-guide-features) - What you get
13. [AI-Assisted Deployment Prompts](#-ai-assisted-deployment-prompts) - Using AI for deployment
14. [Quick Decision Guide](#-quick-decision-guide) - Choose deployment option (A/B/C/D/E)
15. [Usage Example](#-usage-example) - Real scenario
16. [Benefits](#-benefits-of-using-these-prompts) - Why use prompts
17. [Template Format](#-template-format) - Prompt structure

---

## �📋 Quick Navigation

### I'm deploying for the **first time**

Follow this sequence:

1. **`01_DEPLOYMENT_SETUP.md`** (20 minutes)
   - Set up project variables
   - Enable APIs
   - Create secrets
   - Create service account
   - Configure IAM permissions
   - ✅ **Do this first**

2. **`02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md`** (15 minutes)
   - Build Docker image
   - Push to Container Registry
   - Deploy to Cloud Run
   - Verify deployment success
   - ✅ **Do this second**

3. **`DEPLOYMENT_EXECUTION_LOG_20260320.md`** (Reference)
   - See actual execution results from March 20, 2026
   - Use for comparison and troubleshooting
   - ✅ **Reference as needed**

---

### I'm already operating the service

Use these guides:

1. **`03_OPERATIONS_&_REFERENCE.md`** (Use daily)
   - Daily service management
   - Monitoring and alerting
   - Troubleshooting guide
   - Cost management
   - Scheduler setup
   - Emergency procedures
   - ✅ **Your daily operations guide**

2. **`DEPLOYMENT_EXECUTION_LOG_20260320.md`** (Reference)
   - Real execution results
   - Actual output examples
   - Real error cases
   - ✅ **Reference for troubleshooting**

---

## 📄 File Overview

### 1. **01_DEPLOYMENT_SETUP.md** (400 lines)
**When**: First-time setup only  
**What**: Pre-deployment prerequisites  
**Steps**:
- ✅ Project variables
- ✅ API enablement
- ✅ Secret Manager setup
- ✅ Service account creation
- ✅ IAM permission configuration

**Key Info**:
- Time: ~20 minutes
- One-time setup
- Must complete before deployment

---

### 2. **02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md** (300 lines)
**When**: Ready to build and deploy  
**What**: Build, push, and deploy workflow  
**Steps**:
- ✅ Build Docker image (8.1 seconds on recent hardware)
- ✅ Tag and push to Container Registry
- ✅ Deploy to Cloud Run
- ✅ Verify deployment success

**Key Info**:
- Time: ~15 minutes
- Uses credentials from Setup guide
- Includes actual March 20, 2026 execution results
- Quick troubleshooting section

---

### 3. **03_OPERATIONS_&_REFERENCE.md** (400 lines)
**When**: After deployment, ongoing operations  
**What**: Post-deployment operations and reference  
**Sections**:
- ✅ Daily service management
- ✅ Monitoring and alerting setup
- ✅ Cloud Scheduler configuration
- ✅ Cost management and optimization
- ✅ Troubleshooting workflows
- ✅ Emergency procedures
- ✅ Security and audit

**Key Info**:
- Time: Reference guide (use as needed)
- Ongoing operations
- Comprehensive troubleshooting
- Cost optimization strategies

---

### 4. **DEPLOYMENT_EXECUTION_LOG_20260320.md** (400 lines)
**When**: Need real execution examples or troubleshooting  
**What**: Actual deployment results from March 20, 2026  
**Content**:
- ✅ Real deployment configuration
- ✅ Actual build output (8.1 seconds)
- ✅ Real image digest
- ✅ Real service URL
- ✅ Actual revision ID
- ✅ Real execution log entries

**Key Info**:
- Reference/proof document
- Use to verify your steps match
- See real error messages and resolutions

---

## 🎯 Decision Matrix

| Situation | Guide | Action |
|-----------|-------|--------|
| **First time deploying** | `01_DEPLOYMENT_SETUP.md` | Start here |
| **Have setup, ready to deploy** | `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md` | Deploy here |
| **Service is running, need daily ops** | `03_OPERATIONS_&_REFERENCE.md` | Refer here |
| **Need troubleshooting help** | `03_OPERATIONS_&_REFERENCE.md` + `LOG_20260320.md` | Reference both |
| **Want to verify against real example** | `DEPLOYMENT_EXECUTION_LOG_20260320.md` | Compare here |
| **Need cost management advice** | `03_OPERATIONS_&_REFERENCE.md` | Optimize here |
| **Setting up scheduled execution** | `03_OPERATIONS_&_REFERENCE.md` | Configure here |

---

## ✅ Learning Path

### For New Team Members (First Time)

**Time**: ~1 hour total

1. Read Overview (this file) - 5 minutes
2. Follow `01_DEPLOYMENT_SETUP.md` - 20 minutes
3. Follow `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md` - 15 minutes
4. Review `03_OPERATIONS_&_REFERENCE.md` summary - 10 minutes
5. Keep `03_OPERATIONS_&_REFERENCE.md` bookmarked for reference

### For Operations Team (Ongoing)

**Time**: ~30 minutes to get familiar

1. Skim `03_OPERATIONS_&_REFERENCE.md` - 15 minutes
2. Run troubleshooting exercises from `DEPLOYMENT_EXECUTION_LOG_20260320.md` - 10 minutes
3. Set up monitoring from `03_OPERATIONS_&_REFERENCE.md` - 5 minutes
4. Keep all guides bookmarked

---

## 🔑 Key Improvements (from Optimization)

### Before (5 files, 3,562 lines):
- ❌ 40-50% content duplication
- ❌ Mixed responsibilities (setup + deployment + operations in one file)
- ❌ Unclear user journey
- ❌ Average file size: 712 lines
- ❌ Total: 119KB

### After (4 files, ~1,500 lines):
- ✅ ~5% duplication (down from 40-50%)
- ✅ Single responsibility per guide
- ✅ Clear user journey (Setup → Deploy → Operate)
- ✅ Average file size: 375 lines
- ✅ Total: ~50KB
- ✅ **58% reduction in documentation volume**

---

## 📝 File Organization

```
GOOGLE_CLOUD/ (Deployment Guides Directory)
├── README.md (this file - navigation guide)
├── 01_DEPLOYMENT_SETUP.md (pre-deployment)
├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (build & deploy)
├── 03_OPERATIONS_&_REFERENCE.md (post-deployment)
├── DEPLOYMENT_EXECUTION_LOG_20260320.md (reference/proof)
├── GOOGLE_CLOUD_DEPLOYMENT_OPTIMIZATION_ANALYSIS.md (analysis)
│
├── cloud-run-service-config.json (service config snapshot)
│
└── [ARCHIVED - See optimization analysis]
    ├── GOOGLE_CLOUD_DEPLOYMENT.md (consolidated into new files)
    ├── GOOGLE_CLOUD_DEPLOYMENT_EXECUTION_GUIDE.md (replaced by #2)
    ├── GOOGLE_CLOUD_RUN_DEPLOYMENT_GUIDE.md (replaced by #3)
    └── GOOGLE_CLOUD_DEPLOYMENT_GUIDES_INDEX.md (meta-doc, no longer needed)
```

---

## 🔍 Content Distribution

### Setup Guide (01)
```
Step 1: Project Variables       ← Environment setup
Step 2: Enable APIs             ← Service activation
Step 3: Create Secrets          ← Credential storage
Step 4: Create Service Account  ← Identity
Step 5: Grant Secret Access     ← Permissions (secrets)
Step 6: Grant Additional Roles  ← Permissions (compute/storage/logs)
```

### Execution Guide (02)
```
Step 7:  Build Docker Image      ← Container creation
Step 8:  Tag & Push              ← Registry upload
Step 9:  Deploy to Cloud Run     ← Service deployment
Step 10: Verify                  ← Success confirmation
Teardown: Full Cleanup           ← Resource deletion (reverse order)
```

### Operations Guide (03)
```
- Quick Reference               ← Service status
- Common Operations             ← Daily management
- Monitoring & Alerts           ← Observability
- Cloud Scheduler               ← Automation
- Cost Management               ← Optimization
- Troubleshooting               ← Problem solving
- Emergency Procedures          ← Disaster recovery
- Security & Audit              ← Compliance
```

---

## 🚀 Quick Start

### Deploy in 5 Minutes

```bash
# 1. Setup (one-time, ~20 min)
# Follow 01_DEPLOYMENT_SETUP.md

# 2. Deploy (when ready, ~15 min)
docker buildx build --platform linux/amd64 -t stock-alerter:latest .
docker tag stock-alerter:latest gcr.io/stock-trading-489001/stock-alerter:latest
gcloud auth configure-docker
docker push gcr.io/stock-trading-489001/stock-alerter:latest
gcloud run deploy stock-alerter --image gcr.io/stock-trading-489001/stock-alerter:latest --region europe-west1

# 3. Verify (instantly)
curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
  https://stock-alerter-717776322217.europe-west1.run.app/health
```

---

## 💡 Key Concepts

### Instance-Based Billing (Current)
- Full 8 CPU cores always available
- Charged for instance lifetime, not just requests
- Best for continuous, always-on services
- Cost: ~$744/month per active instance

### Service Account
- Dedicated identity for Cloud Run service
- Limited IAM permissions (least privilege)
- Used for secret access and Cloud Storage
- Audit trail of all actions

### Secrets Management
- Encrypted storage in Google Secret Manager
- Fine-grained IAM access control
- Automatic versioning
- Never visible in logs

### Cloud Scheduler
- Automated job execution on schedule
- Cron expression format
- Integrates with Cloud Run
- Useful for time-based alerts

---

## 🔗 Additional Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)
- [IAM Best Practices](https://cloud.google.com/iam/docs/best-practices)

---

## 📞 Need Help?

1. **Deployment Issues**: Check `02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md` troubleshooting
2. **Operations Questions**: Check `03_OPERATIONS_&_REFERENCE.md` comprehensive guide
3. **Setup Problems**: Check `01_DEPLOYMENT_SETUP.md` verification sections
4. **Real Examples**: Check `DEPLOYMENT_EXECUTION_LOG_20260320.md` actual output

---

## ✨ Guide Features

✅ **Clear Purpose**: Each guide has single responsibility  
✅ **Concise Content**: Average 375 lines per guide  
✅ **Actual Results**: Real execution examples included  
✅ **Quick Navigation**: README helps you find right guide  
✅ **Complete Troubleshooting**: Comprehensive error solutions  
✅ **Cost Optimization**: Multiple cost-saving strategies  
✅ **Security Focused**: IAM permissions explained  
✅ **Easy Maintenance**: Changes in one place, not five  

---

## 🤖 AI-Assisted Deployment Prompts

Use these reusable prompts to request AI assistance for deployments. Choose the option that matches your situation.

### 📋 Option A: FULL REBUILD, PUSH & DEPLOY
**Use when**: Code changes require complete rebuild

**Prompt to use**:
```
Execute full Google Cloud deployment following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option A: FULL REBUILD, PUSH & DEPLOY (Steps 7-10)
- Step 7: Build Docker Image
- Step 8: Tag and Push to Container Registry
- Step 9: Deploy to Cloud Run
- Step 10: Verify Deployment

Static IP / VPC Connector: [YES — include --vpc-connector=my-connector --vpc-egress=all-traffic | NO — omit VPC connector flags]

Follow the guidance document exactly, step-by-step from top to bottom.
Include actual execution results and outputs for each step.
```

> 💡 **Replace the bracket** with your choice before sending:
> - `YES` → Binance **live/production** API (IP whitelisting required)
> - `NO` → Binance **demo/testnet** API (no IP whitelisting needed)

**When to use**:
- Code changes in alert service
- Configuration file updates
- Dependencies changed
- Want fresh build from source

**Expected time**: ~15-20 minutes

---

### 📦 Option B: PUSH & DEPLOY (Skip Build)
**Use when**: Only minor code changes, recent Docker image exists

**Prompt to use**:
```
Execute Google Cloud push and deploy following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option B: PUSH & DEPLOY (Steps 8-10)
- Step 8: Tag and Push to Container Registry
- Step 9: Deploy to Cloud Run
- Step 10: Verify Deployment

Static IP / VPC Connector: [YES — include --vpc-connector=my-connector --vpc-egress=all-traffic | NO — omit VPC connector flags]

Docker image already built. Only push updated code and redeploy.
Follow the guidance document exactly, step-by-step from top to bottom.
Include actual execution results and outputs for each step.
```

> 💡 **Replace the bracket** with your choice before sending:
> - `YES` → Binance **live/production** API (IP whitelisting required)
> - `NO` → Binance **demo/testnet** API (no IP whitelisting needed)

**When to use**:
- Minor code changes only
- Docker image built within last few hours
- Avoid rebuilding when not necessary

**Expected time**: ~10-15 minutes

---

### 🚀 Option C: DEPLOY ONLY (Skip Build & Push)
**Use when**: Only configuration/secrets changed, image already current

**Prompt to use**:
```
Execute Google Cloud deployment only following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option C: DEPLOY ONLY (Steps 9-10)
- Step 9: Deploy to Cloud Run
- Step 10: Verify Deployment

Static IP / VPC Connector: [YES — include --vpc-connector=my-connector --vpc-egress=all-traffic | NO — omit VPC connector flags]

Docker image in Container Registry is current. Only redeploy with configuration updates.
Follow the guidance document exactly, step-by-step from top to bottom.
Include actual execution results and outputs for each step.
```

> 💡 **Replace the bracket** with your choice before sending:
> - `YES` → Binance **live/production** API (IP whitelisting required)
> - `NO` → Binance **demo/testnet** API (no IP whitelisting needed)

**When to use**:
- Configuration/secrets changes only
- No code changes
- Docker image is current (built today or recently)
- Fast redeployment needed

**Expected time**: ~5-10 minutes

---

### 🗑️ Option D: FULL CLEANUP & TEARDOWN
**Use when**: Permanently decommissioning the service and all its GCP infrastructure

**Prompt to use**:
```
Execute full Google Cloud teardown following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option D: FULL CLEANUP & TEARDOWN
Delete all resources in the correct reverse dependency order:
1. Delete Cloud Run service (stock-alerter)
2. Delete VPC Connector (my-connector)
3. Delete NAT Gateway (my-nat)
4. Delete Cloud Router (my-router)
5. Release Static IP (my-static-ip → 34.156.14.253)

Follow the Teardown section of the guidance document exactly, step-by-step.
Verify each resource is deleted before proceeding to the next.
Include actual execution results and outputs for each step.
Remind me to remove 34.156.14.253 from the Binance API whitelist at the end.
```

**When to use**:
- Permanently shutting down the service
- Migrating to a different region or project
- Cleaning up after testing/staging environment
- Reducing GCP costs by removing all resources

**⚠️ Warning**: This is **irreversible**. The static IP `34.156.14.253` will be released and may not be recoverable. You will need to update Binance API whitelist with a new IP on next deployment.

**Expected time**: ~5-10 minutes

---

### 🔧 Option E: CLEANUP STATIC IP INFRASTRUCTURE ONLY (Keep Service Running)
**Use when**: Switching to Binance Demo/Testnet which does NOT require IP whitelisting, but keeping the Cloud Run service active

**Prompt to use**:
```
Execute Google Cloud static IP infrastructure cleanup following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option E: CLEANUP STATIC IP INFRASTRUCTURE ONLY
The Cloud Run service (stock-alerter) must remain running.
Only delete the static outbound IP infrastructure in the correct reverse dependency order:
1. Delete VPC Connector (my-connector)  ← detach from Cloud Run service first
2. Delete NAT Gateway (my-nat)
3. Delete Cloud Router (my-router)
4. Release Static IP (my-static-ip → 34.156.14.253)

Before deleting the VPC connector, update the Cloud Run service to remove the VPC binding:
gcloud run services update stock-alerter --region=europe-west1 --clear-vpc-connector

Verify the service is still healthy after VPC connector removal.
Verify each infrastructure resource is deleted before proceeding to the next.
Include actual execution results and outputs for each step.
Remind me to remove 34.156.14.253 from the Binance live API whitelist at the end.
```

**When to use**:
- Switching from Binance **live/production** API → Binance **demo/testnet** API
- Binance demo does not require IP whitelisting — static IP infrastructure is unnecessary
- Want to reduce GCP costs by removing idle NAT/router/connector resources
- Service itself continues running normally

**⚠️ Warning**:
- The static IP `34.156.14.253` will be **permanently released** — not recoverable
- After this cleanup, Cloud Run will use **dynamic outbound IPs** again
- If you ever switch back to Binance **live** API, you must redo **Step 6.5** in `01_DEPLOYMENT_SETUP.md` to get a new static IP and re-whitelist it on Binance

**Expected time**: ~5-10 minutes

---

## 📊 Quick Decision Guide

| Situation | Use Option | Time |
|-----------|-----------|------|
| Code changes in service | **A** (Full) | 15-20 min |
| Dependencies updated | **A** (Full) | 15-20 min |
| Minor code changes | **B** (Push & Deploy) | 10-15 min |
| Config/secrets only | **C** (Deploy) | 5-10 min |
| Image built today | **B** or **C** | 5-15 min |
| Major refactoring | **A** (Full) | 15-20 min |
| Decommission service entirely | **D** (Teardown) | 5-10 min |
| Switch to Binance demo (keep service) | **E** (Static IP cleanup only) | 5-10 min |

---

## 🎯 Usage Example

**Scenario**: You've updated the alert notification logic and want to deploy

**Your request to AI**:
```
Execute full Google Cloud deployment following:
docs/REFERENCES/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md

Option A: FULL REBUILD, PUSH & DEPLOY (Steps 7-10)
- Step 7: Build Docker Image
- Step 8: Tag and Push to Container Registry
- Step 9: Deploy to Cloud Run
- Step 10: Verify Deployment

Follow the guidance document exactly, step-by-step from top to bottom.
Include actual execution results and outputs for each step.
```

**AI will**:
1. ✅ Follow the deployment guide step-by-step
2. ✅ Build Docker image with your latest code
3. ✅ Tag and push to Container Registry
4. ✅ Deploy to Cloud Run
5. ✅ Verify deployment success
6. ✅ Show all actual outputs and results

---

## ✨ Benefits of Using These Prompts

✅ **Consistent execution** - Same steps every time  
✅ **Clear intent** - AI knows exactly what to do  
✅ **Complete documentation** - Actual results captured  
✅ **Reproducible** - Can run again with same prompt  
✅ **Traceable** - Clear audit trail of deployments  
✅ **Flexible** - Choose option based on your changes  
✅ **Time-saving** - Only do necessary steps  

---

## 📝 Template Format

All prompts follow this structure:
1. **Document reference** - Which guide to follow
2. **Option choice** - Which steps to execute
3. **Step list** - Exactly which steps (7, 8, 9, or 10)
4. **Static IP flag** - `YES` or `NO` — controls whether `--vpc-connector` and `--vpc-egress` are included in the Step 9 deploy command
5. **Context** - Why skipping certain steps
6. **Execution mode** - "Follow exactly, step-by-step from top to bottom"
7. **Output requirement** - "Include actual execution results"

### Static IP Flag Reference

| Flag Value | Binance Mode | VPC Connector in Deploy Command |
|---|---|---|
| `YES` | Live / Production | ✅ Include `--vpc-connector=my-connector --vpc-egress=all-traffic` |
| `NO` | Demo / Testnet | ❌ Omit VPC connector flags entirely |

This ensures consistent, reliable deployments every time.

---

**Last Updated**: March 24, 2026  
**Status**: ✅ Ready for Team Use  
**Questions?**: Refer to appropriate guide or check troubleshooting sections

