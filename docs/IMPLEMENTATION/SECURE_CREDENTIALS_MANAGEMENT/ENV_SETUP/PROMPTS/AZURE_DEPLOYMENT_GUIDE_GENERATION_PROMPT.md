# 🤖 AI Prompt: Generate Azure Deployment Guides

**Purpose**: Template for AI to generate Azure Container Instances/App Service deployment guides  
**Status**: Ready to use (not yet executed)  
**Date Created**: March 24, 2026  
**Execution**: Only when explicitly requested

---

## 📋 Prompt for AI Assistant

```
You are an expert cloud infrastructure documentation writer. Generate comprehensive 
deployment guides for deploying the Stock Alerter application to Microsoft Azure.

CONTEXT:
- Application: Stock Alerter (Python 3.12, Docker containerized)
- Current Reference: Google Cloud Run deployment guides (see Google Cloud guides structure)
- Target Platform: Azure (Container Instances OR App Service)
- Region: westeurope (Belgium/Ireland, for GDPR compliance)
- Output Format: Markdown files matching Google Cloud structure

REQUIREMENTS:

1. STRUCTURE (Match Google Cloud Guides):
   - README.md (Navigation guide, 330 lines)
   - 01_DEPLOYMENT_SETUP.md (Prerequisites, 376 lines)
   - 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (Build & deploy, 431 lines)
   - 03_OPERATIONS_&_REFERENCE.md (Operations, 544 lines)

2. SETUP GUIDE (01_DEPLOYMENT_SETUP.md) - ~376 lines:
   
   Steps to include:
   - Step 1: Create Azure Resource Group
     * Region: westeurope
     * Naming convention: stock-trading-rg
   
   - Step 2: Create Azure Container Registry
     * SKU: Standard or Premium
     * Authentication: admin user for CI/CD
   
   - Step 3: Create Secrets in Azure Key Vault
     * Secrets needed:
       - email-sender
       - email-app-password
       - email-sender-display-name
       - twilio-account-sid
       - twilio-auth-token
     * Access policies for service principal
   
   - Step 4: Create Service Principal (or Managed Identity)
     * For container authentication
     * IAM roles assignment
   
   - Step 5: Grant Key Vault Access
     * Service principal permissions
     * Secret retrieval access
   
   - Step 6: Grant Additional Permissions
     * Container Registry pull
     * Storage account access
     * Monitoring permissions
   
   Include:
   - Detailed CLI commands (az cli)
   - Explanations for each command
   - Verification steps after each section
   - Checklist at end

3. EXECUTION GUIDE (02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md) - ~431 lines:
   
   Steps to include:
   - Step 7: Build Docker Image
     * docker buildx build --platform linux/amd64
     * Tag for Azure Container Registry
   
   - Step 8: Push to Azure Container Registry
     * docker push {registry}.azurecr.io/stock-alerter:latest
     * Verification steps
   
   - Step 9: Deploy to Azure (choose one):
     Option A: Container Instances
     * az container create command
     * Environment variables setup
     * Secrets from Key Vault integration
     * Resource sizing
   
     Option B: App Service
     * az appservice plan create
     * az webapp create
     * Docker configuration
     * Environment variables
   
   - Step 10: Verify Deployment
     * Check service status
     * Test health endpoint
     * Review logs
   
   Include:
   - Actual deployment examples
   - Real output samples
   - Common errors and fixes
   - Verification checklist

4. OPERATIONS GUIDE (03_OPERATIONS_&_REFERENCE.md) - ~544 lines:
   
   Sections to include:
   - Quick Reference (service URL, configuration)
   - Common Operations
     * View logs
     * Update configuration
     * Scale resources
     * Restart service
   
   - Monitoring & Alerts
     * Azure Monitor setup
     * Application Insights integration
     * Alert policies
   
   - Key Vault Management
     * Rotate secrets
     * Access policies
   
   - Cost Management
     * Current costs
     * Optimization strategies
   
   - Troubleshooting
     * Service not starting
     * High memory/CPU
     * Authentication failures
     * Container registry issues
   
   - Emergency Procedures
     * Rollback to previous version
     * Disable service
     * Force restart

5. NAVIGATION GUIDE (README.md) - ~330 lines:
   
   Include:
   - Quick navigation for different user types
   - Learning paths for new users
   - Decision matrix (when to use which guide)
   - Key concepts explained
   - Folder structure overview
   - Troubleshooting quick links

STYLE REQUIREMENTS:
- Match Google Cloud guides tone and structure
- Use same formatting (headers, code blocks, tables)
- Include actual CLI command examples
- Add troubleshooting sections
- Use same emoji style (✅, ❌, 🚀, etc.)
- Include verification steps after each section
- Add checklists for completion
- Provide 3-5 line context before/after code blocks

KEY DIFFERENCES FROM GOOGLE CLOUD:
- Use Azure CLI (az) instead of gcloud
- Use Key Vault instead of Secret Manager
- Use Container Registry instead of Artifact Registry
- Use either Container Instances OR App Service (document both)
- Use Azure Monitor instead of Cloud Monitoring
- Use Application Insights for observability
- Different cost structure and optimization strategies

QUALITY REQUIREMENTS:
- 1,600-1,700 total lines across all 4 guides
- ~5% or less duplication between guides
- Clear single responsibility per guide
- Comprehensive troubleshooting
- Real examples where possible
- Security best practices included
- Cost optimization covered

OUTPUT FORMAT:
Return 4 separate markdown files:
1. README.md (navigation)
2. 01_DEPLOYMENT_SETUP.md (setup)
3. 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (deployment)
4. 03_OPERATIONS_&_REFERENCE.md (operations)

Each file should be production-ready and usable immediately by team.
```

---

## 🎯 Execution Instructions

### When to Run This Prompt

Run this prompt when:
1. Team decides to deploy to Azure
2. Need documentation for new team members on Azure
3. Want to compare Azure vs Google Cloud deployment

### How to Use

1. Copy the prompt above
2. Paste into Claude/ChatGPT/your AI assistant
3. Add any specific requirements for your Azure setup
4. Save generated files to: `docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AZURE/`
5. Review and adjust for your specific infrastructure

### Expected Output

4 markdown files (~1,680 lines total):
- README.md (~330 lines)
- 01_DEPLOYMENT_SETUP.md (~376 lines)
- 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (~431 lines)
- 03_OPERATIONS_&_REFERENCE.md (~544 lines)

### Quality Checklist

- [ ] All 4 files generated
- [ ] No duplicate content (< 5% overlap)
- [ ] All Azure CLI commands correct
- [ ] Step numbering correct (1-10)
- [ ] Troubleshooting comprehensive
- [ ] Security best practices included
- [ ] Cost management covered
- [ ] Formatting matches Google Cloud guides
- [ ] Checklists included in each guide
- [ ] Verification steps after each section

---

## 📝 Customization Notes

Modify the prompt if you need:
- Different Azure region (change `westeurope`)
- Different Azure service (App Service vs Container Instances vs AKS)
- Different secret names
- Different resource naming convention
- Different scaling requirements
- Different monitoring setup

---

## 🔗 Related

- **Google Cloud Guides**: docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/
- **AWS Deployment Prompt**: AWS_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md
- **Prompt Standards**: This file documents the template approach

