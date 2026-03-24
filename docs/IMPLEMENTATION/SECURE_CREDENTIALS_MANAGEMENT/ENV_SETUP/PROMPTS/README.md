# 🤖 AI Generation Prompts for Deployment Guides

**Purpose**: Templates for generating deployment guides for multiple cloud platforms  
**Status**: Ready to use (not yet executed)  
**Date Created**: March 24, 2026  
**Update Strategy**: Execute prompts only when explicitly requested

---

## 📋 Available Prompts

### 1. **AZURE_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md**

Generate deployment guides for Microsoft Azure (Container Instances or App Service)

**Output**: 4 focused guides (~1,680 lines total)
- README.md (Navigation)
- 01_DEPLOYMENT_SETUP.md (Prerequisites)
- 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (Build & Deploy)
- 03_OPERATIONS_&_REFERENCE.md (Operations)

**Services Covered**:
- Azure Container Registry
- Azure Key Vault
- Azure Container Instances OR App Service
- Azure Monitor
- Application Insights

**When to Use**: Team wants to deploy to Azure

---

### 2. **AWS_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md**

Generate deployment guides for Amazon Web Services (ECS, Elastic Beanstalk, or Lambda)

**Output**: 4 focused guides (~1,680 lines total)
- README.md (Navigation)
- 01_DEPLOYMENT_SETUP.md (Prerequisites)
- 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md (Build & Deploy)
- 03_OPERATIONS_&_REFERENCE.md (Operations)

**Services Covered**:
- ECR (Elastic Container Registry)
- ECS (Elastic Container Service) on Fargate
- Elastic Beanstalk (alternative)
- Lambda (serverless option)
- Secrets Manager
- CloudWatch

**When to Use**: Team wants to deploy to AWS

---

## 🎯 How to Use These Prompts

### Step 1: Choose Your Cloud Platform

- Azure? Use `AZURE_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md`
- AWS? Use `AWS_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md`
- Google Cloud? Already done - see docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/GOOGLE_CLOUD/

### Step 2: Copy the Prompt

Copy the entire prompt from the chosen file (between the triple backticks).

### Step 3: Run with AI Assistant

Paste into:
- Claude (claude.ai)
- ChatGPT (openai.com)
- Copilot (github.com/copilot)
- Your preferred AI assistant

### Step 4: Add Customizations

Before running, add any specific requirements:

```
[Paste prompt here]

ADDITIONAL REQUIREMENTS:
- Use region: [your-region]
- Service name: [your-service-name]
- Database: [yes/no, type if yes]
- Load balancer: [yes/no, type if yes]
- Auto-scaling: [policy details if needed]
- Budget limit: [$amount/month]
```

### Step 5: Save Generated Files

Create directory structure:
```
docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AZURE/
  ├── README.md
  ├── 01_DEPLOYMENT_SETUP.md
  ├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md
  └── 03_OPERATIONS_&_REFERENCE.md
```

Or for AWS:
```
docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AWS/
  ├── README.md
  ├── 01_DEPLOYMENT_SETUP.md
  ├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md
  └── 03_OPERATIONS_&_REFERENCE.md
```

### Step 6: Review & Adjust

- [ ] Check all command syntax
- [ ] Verify region names
- [ ] Adjust secret names if different
- [ ] Update service names
- [ ] Add company-specific details
- [ ] Verify troubleshooting sections
- [ ] Test commands if possible

---

## 📊 Prompt Comparison

| Aspect | Azure | AWS |
|--------|-------|-----|
| **Total Lines** | ~1,680 | ~1,680 |
| **Services** | 4-5 | 4-6 |
| **Setup Complexity** | Medium | Medium-High |
| **Deployment Options** | 2 | 3 |
| **Cost Optimization** | Moderate | High |
| **Learning Curve** | Moderate | Steep |

---

## 🔧 Prompt Structure

Each prompt follows this consistent structure:

1. **Context Section**
   - Application details
   - Target platform
   - Reference architecture

2. **Requirements Section**
   - Output format (4 focused guides)
   - Detailed content for each guide
   - Setup steps with explanations
   - Execution steps with options
   - Operations sections

3. **Style Requirements**
   - Formatting consistency
   - Code block patterns
   - Emoji usage
   - Verification steps

4. **Quality Requirements**
   - Line count targets
   - Duplication limits
   - Coverage requirements

---

## 🎓 Learning Path

### For New Cloud Platform

1. Read the relevant prompt file (5 minutes)
2. Review the Google Cloud guides for style reference (10 minutes)
3. Run the prompt with your AI assistant (10-15 minutes)
4. Review generated files (10 minutes)
5. Test the deployment process (30+ minutes depending on complexity)

### For Team Adoption

1. Save generated files to appropriate directory
2. Create ARCHIVING folder for old versions
3. Update main documentation index
4. Share with team for feedback
5. Refine based on team experience

---

## ✅ Quality Checklist Template

Use this checklist after generating files:

### Structure
- [ ] README.md created and formatted correctly
- [ ] 01_DEPLOYMENT_SETUP.md created (~376 lines)
- [ ] 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md created (~431 lines)
- [ ] 03_OPERATIONS_&_REFERENCE.md created (~544 lines)

### Content Quality
- [ ] No duplication between guides (< 5%)
- [ ] Each guide has single responsibility
- [ ] All commands are correct for the platform
- [ ] Step numbering is sequential (1-10)
- [ ] Verification steps included after each section

### Style Consistency
- [ ] Matches Google Cloud guides formatting
- [ ] Emoji usage consistent
- [ ] Code blocks properly formatted
- [ ] Tables formatted correctly
- [ ] Headers consistent

### Completeness
- [ ] Setup guide covers all prerequisites
- [ ] Deployment guide covers build, push, deploy, verify
- [ ] Operations guide covers monitoring, troubleshooting, costs
- [ ] README provides clear navigation
- [ ] Checklists included in each guide

### Practicality
- [ ] Commands tested or verified
- [ ] Real output examples where possible
- [ ] Troubleshooting covers common issues
- [ ] Security best practices included
- [ ] Cost optimization strategies explained

---

## 🔗 Directory Structure

```
docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/
├── GOOGLE_CLOUD/ (✅ Complete)
│   ├── README.md
│   ├── 01_DEPLOYMENT_SETUP.md
│   ├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md
│   ├── 03_OPERATIONS_&_REFERENCE.md
│   ├── DEPLOYMENT_EXECUTION_LOG_20260320.md
│   └── ARCHIVING/
│
├── PROMPTS/ (This directory)
│   ├── README.md (This file)
│   ├── AZURE_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md
│   └── AWS_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md
│
├── AZURE/ (To be created when needed)
│   ├── README.md
│   ├── 01_DEPLOYMENT_SETUP.md
│   ├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md
│   ├── 03_OPERATIONS_&_REFERENCE.md
│   └── ARCHIVING/
│
└── AWS/ (To be created when needed)
    ├── README.md
    ├── 01_DEPLOYMENT_SETUP.md
    ├── 02_DEPLOYMENT_EXECUTION_&_VERIFICATION.md
    ├── 03_OPERATIONS_&_REFERENCE.md
    └── ARCHIVING/
```

---

## 💡 Tips for Best Results

### 1. **Be Specific in Customizations**
Instead of generic "database access", specify:
- Database type (PostgreSQL, MySQL, DynamoDB)
- Access pattern (read-only, read-write)
- Network location (same VPC, separate account)

### 2. **Include Real Constraints**
- Budget limits
- Compliance requirements (GDPR, HIPAA)
- Performance requirements
- Scaling expectations

### 3. **Reference Your Setup**
If you have existing infrastructure, mention it:
- "We already have a PostgreSQL database at..."
- "We need to integrate with existing VPC..."
- "Use existing service accounts..."

### 4. **Request Specific Details**
- "Include CI/CD pipeline integration"
- "Add disaster recovery procedures"
- "Include multi-region deployment"
- "Add cost breakdown by service"

### 5. **Test Generated Files**
- Try running the commands in a test environment
- Verify service-specific syntax (CLI versions change)
- Check for any missing prerequisites
- Test the health endpoint after deployment

---

## 🚀 Next Steps

### When Ready to Deploy to Azure:
1. Open `AZURE_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md`
2. Copy the prompt
3. Run with AI assistant
4. Save to `docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AZURE/`
5. Test and adjust

### When Ready to Deploy to AWS:
1. Open `AWS_DEPLOYMENT_GUIDE_GENERATION_PROMPT.md`
2. Copy the prompt
3. Run with AI assistant
4. Save to `docs/IMPLEMENTATION/SECURE_CREDENTIALS_MANAGEMENT/ENV_SETUP/AWS/`
5. Test and adjust

### For Other Platforms:
Follow the same pattern and create new prompts for:
- Digital Ocean
- Heroku
- Linode
- OracleCloud
- Alibaba Cloud
- etc.

---

## 📝 Prompt Maintenance

### When to Update Prompts

- Cloud platform API changes
- New services become available
- Team discovers better practices
- Security requirements change
- Pricing models change

### How to Update

1. Update the relevant prompt file
2. Document what changed
3. Mark version/date updated
4. Test generation with updated prompt
5. Archive old prompt version

---

**Status**: ✅ **Ready for Use**  
**Last Updated**: March 24, 2026  
**Execution**: Only when explicitly requested by user

