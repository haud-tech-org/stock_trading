# 🤖 AI Prompt: Generate AWS Deployment Guides

**Purpose**: Template for AI to generate AWS deployment guides (ECS/Lambda/Elastic Beanstalk)  
**Status**: Ready to use (not yet executed)  
**Date Created**: March 24, 2026  
**Execution**: Only when explicitly requested

---

## 📋 Prompt for AI Assistant

```
You are an expert cloud infrastructure documentation writer. Generate comprehensive 
deployment guides for deploying the Stock Alerter application to Amazon Web Services (AWS).

CONTEXT:
- Application: Stock Alerter (Python 3.12, Docker containerized)
- Current Reference: Google Cloud Run deployment guides (see Google Cloud guides structure)
- Target Platform: AWS (ECS on Fargate recommended, or Elastic Beanstalk)
- Region: eu-west-1 (Ireland, for GDPR compliance)
- Output Format: Markdown files matching Google Cloud structure

REQUIREMENTS:

1. STRUCTURE (Match Google Cloud Guides):
   - README.md (Navigation guide, 330 lines)
   - 01_DEPLOYMENT_SETUP.md (Prerequisites, 376 lines)
   - 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (Build & deploy, 431 lines)
   - 03_OPERATIONS_&_REFERENCE.md (Operations, 544 lines)

2. SETUP GUIDE (01_DEPLOYMENT_SETUP.md) - ~376 lines:
   
   Steps to include:
   - Step 1: Create AWS Account & Set Up IAM
     * Create IAM user for deployment
     * Attach necessary policies
     * Generate access keys
   
   - Step 2: Create VPC & Networking (if needed)
     * Security groups configuration
     * Network setup
     * Subnet configuration
   
   - Step 3: Create AWS Secrets Manager Secrets
     * Secrets needed:
       - email-sender
       - email-app-password
       - email-sender-display-name
       - twilio-account-sid
       - twilio-auth-token
     * IAM permissions for secret access
   
   - Step 4: Create ECR (Elastic Container Registry)
     * Create ECR repository
     * Configure access policies
   
   - Step 5: Create IAM Role for ECS Task Execution
     * Task execution role
     * Task role (with secret access)
     * CloudWatch logs permissions
   
   - Step 6: Grant Additional Permissions
     * CloudWatch permissions
     * CloudFormation (if using)
     * S3 access (if needed)
     * RDS access (if database)
   
   Include:
   - Detailed AWS CLI commands
   - AWS Management Console steps
   - Explanations for each command
   - Verification steps after each section
   - Checklist at end

3. EXECUTION GUIDE (02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md) - ~431 lines:
   
   Steps to include:
   - Step 7: Build Docker Image
     * docker buildx build --platform linux/amd64
     * Tag for ECR
   
   - Step 8: Push to ECR
     * aws ecr get-login-password
     * docker push {account}.dkr.ecr.eu-west-1.amazonaws.com/stock-alerter:latest
     * Verification steps
   
   - Step 9: Deploy to AWS (choose one):
     Option A: ECS on Fargate (Recommended)
     * Create ECS cluster
     * Create task definition
     * Create ECS service
     * Load balancer configuration
     * Environment variables from Secrets Manager
   
     Option B: Elastic Beanstalk
     * eb create command
     * Docker configuration
     * Environment variables
     * Scaling policy
   
     Option C: Lambda (if using scheduled execution)
     * Function creation
     * Docker image as Lambda
     * Environment configuration
     * Triggers
   
   - Step 10: Verify Deployment
     * Check service status
     * Test health endpoint
     * Review CloudWatch logs
   
   Include:
   - Actual deployment examples
   - Real output samples
   - Common errors and fixes
   - Verification checklist

4. OPERATIONS GUIDE (03_OPERATIONS_&_REFERENCE.md) - ~544 lines:
   
   Sections to include:
   - Quick Reference (service endpoint, configuration)
   - Common Operations
     * View logs (CloudWatch)
     * Update task definition
     * Scale tasks
     * Restart service
     * Update environment variables
   
   - CloudWatch Monitoring
     * Create log groups
     * Set up filters
     * Create dashboards
     * Configure alarms
   
   - Secrets Management
     * Rotate secrets
     * Update secret values
     * Audit secret access
   
   - Cost Management
     * Current costs
     * Optimization strategies (Fargate vs EC2, reserved capacity)
     * Cost monitoring
   
   - Troubleshooting
     * Service not starting
     * High CPU/memory
     * Secret access denied
     * Network connectivity
     * Task launch failures
   
   - Emergency Procedures
     * Rollback to previous task definition
     * Scale down service
     * Force task replacement
     * Database connection issues

5. NAVIGATION GUIDE (README.md) - ~330 lines:
   
   Include:
   - Quick navigation for different user types
   - Learning paths for new users
   - Decision matrix (ECS vs Elastic Beanstalk vs Lambda)
   - Key concepts explained
   - Folder structure overview
   - Troubleshooting quick links
   - Cost comparison notes

STYLE REQUIREMENTS:
- Match Google Cloud guides tone and structure
- Use same formatting (headers, code blocks, tables)
- Include actual AWS CLI command examples
- Add troubleshooting sections
- Use same emoji style (✅, ❌, 🚀, etc.)
- Include verification steps after each section
- Add checklists for completion
- Provide 3-5 line context before/after code blocks

KEY DIFFERENCES FROM GOOGLE CLOUD:
- Use AWS CLI instead of gcloud
- Use Secrets Manager instead of Secret Manager (similar concepts)
- Use ECR instead of Artifact Registry
- Use ECS/Elastic Beanstalk/Lambda instead of Cloud Run
- Use CloudWatch instead of Cloud Logging
- Use CloudWatch Alarms instead of Cloud Monitoring
- VPC and networking configuration (more complex)
- Different cost structure and optimization strategies

AWS SPECIFIC SECTIONS:
- Task definition creation and management
- Service vs Scheduled tasks
- Load balancer configuration
- Auto-scaling policies
- CloudWatch log groups and filters
- VPC and security group configuration
- IAM role and trust relationships

QUALITY REQUIREMENTS:
- 1,600-1,700 total lines across all 4 guides
- ~5% or less duplication between guides
- Clear single responsibility per guide
- Comprehensive troubleshooting
- Real examples where possible
- Security best practices included
- Cost optimization covered
- Multiple AWS service options documented

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
1. Team decides to deploy to AWS
2. Need documentation for new team members on AWS
3. Want to compare AWS vs Google Cloud deployment
4. Need multi-cloud strategy

### How to Use

1. Copy the prompt above
2. Paste into Claude/ChatGPT/your AI assistant
3. Specify which AWS service:
   - ECS on Fargate (recommended for simplicity)
   - Elastic Beanstalk (for managed platform)
   - Lambda (for serverless/scheduled tasks)
4. Add any specific requirements for your AWS setup
5. Save generated files to: `docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AWS/`
6. Review and adjust for your specific infrastructure

### Expected Output

4 markdown files (~1,680 lines total):
- README.md (~330 lines)
- 01_DEPLOYMENT_SETUP.md (~376 lines)
- 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (~431 lines)
- 03_OPERATIONS_&_REFERENCE.md (~544 lines)

### Quality Checklist

- [ ] All 4 files generated
- [ ] No duplicate content (< 5% overlap)
- [ ] All AWS CLI commands correct
- [ ] Step numbering correct (1-10)
- [ ] Troubleshooting comprehensive
- [ ] Security best practices included
- [ ] Cost management covered
- [ ] Formatting matches Google Cloud guides
- [ ] Checklists included in each guide
- [ ] Verification steps after each section
- [ ] Multiple AWS service options documented

---

## 📝 Customization Notes

Modify the prompt if you need:
- Different AWS region (change `eu-west-1`)
- Different AWS service (ECS vs Elastic Beanstalk vs Lambda vs EKS)
- Different secret names
- Different resource naming convention
- Different scaling requirements
- Different monitoring setup
- VPC/Network configuration details
- Database integration

---

## 🔗 AWS Service Comparison

| Service | Best For | Complexity | Cost |
|---------|----------|-----------|------|
| **ECS Fargate** | Containerized apps | Medium | Variable (pay per task) |
| **Elastic Beanstalk** | Managed deployment | Low | Variable |
| **Lambda** | Scheduled/Event-driven | Low | Low (pay per invocation) |
| **EKS** | Kubernetes orchestration | High | High (control plane fees) |

---

## 🔗 Related

- **Google Cloud Guides**: docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/
- **Azure Deployment Prompt**: AZURE_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md
- **Prompt Standards**: This file documents the template approach

