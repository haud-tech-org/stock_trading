# Architecture Documentation - Top-Level Navigation

Welcome! This directory contains comprehensive documentation for the stock trading alert system architecture.

---

## 🏗️ Directory Structure

Choose your starting point based on your needs:

### 📋 **SYSTEM_ARCHITECTURE_OVERVIEW.md** ⭐ START HERE
**Purpose:** Complete end-to-end system architecture from entry point to delivery
- **Audience:** Everyone - start here first
- **Read Time:** 20 minutes
- **What You'll Learn:** All 10 system layers, data flows, operational support, capabilities
- **Next Steps:** Choose a path below based on your role

---

### 📚 **TECHNICAL_REFERENCE/** 
**Purpose:** Architecture theory, patterns, and design decisions
- **Tier 2 Documentation:** Reference and theoretical knowledge
- **Contains:**
  - Executor → Analyzer → Validator pattern (overview + diagrams)
  - Abstract Base Classes architecture
  - Deep dive findings and investigations
  - Data layer architecture
  - Trade Execution Service** — DCA ladder + dynamic bracket theory
  
👉 [View TECHNICAL_REFERENCE/README.md](./TECHNICAL_REFERENCE/README.md) for detailed navigation

---

### 🛠️ **IMPLEMENTATION_GUIDES/**
**Purpose:** Practical how-to guides for developers
- **Tier 3 Documentation:** Implementation and practical knowledge
- **Contains:**
  - How to create new trading executors
  - Analyzer/Validator quick reference
  - Operations and deployment guide
  - Troubleshooting guide
  - Data provider extension guide
  - Trade Execution Service** — How to add new trading platforms
  
👉 [View IMPLEMENTATION_GUIDES/README.md](./IMPLEMENTATION_GUIDES/README.md) for detailed navigation

---

### 👥 **AUDIENCE_SPECIFIC_ARCHITECTURE/**
**Purpose:** Architecture documentation tailored for specific roles
- **Contains:**
  - Architecture for Developers
  - Architecture for Operations
  - Architecture for Business/Clients
  
👉 [View AUDIENCE_SPECIFIC_ARCHITECTURE/README.md](./AUDIENCE_SPECIFIC_ARCHITECTURE/README.md) for role-specific guides

---

## 🎯 Quick Navigation by Role

### 👨‍💻 **I'm a Developer**
1. Start with: **SYSTEM_ARCHITECTURE_OVERVIEW.md** (20 min) - Understand full system
2. Then choose:
   - **Creating new approach?** → IMPLEMENTATION_GUIDES/README.md
   - **Debugging existing code?** → TECHNICAL_REFERENCE/README.md
   - **Working on trade execution?** → TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md
   - **Want complete knowledge?** → Both guides

### 🏗️ **I'm an Architect**
1. Start with: **SYSTEM_ARCHITECTURE_OVERVIEW.md** (20 min)
2. Deep dive: **TECHNICAL_REFERENCE/README.md** (60+ min)
3. Reference: Individual files as needed

### 🚀 **I'm in Operations/DevOps**
1. Start with: **SYSTEM_ARCHITECTURE_OVERVIEW.md** (15 min) - Focus on Layer 9 & 10
2. Then: **IMPLEMENTATION_GUIDES/README.md** → OPERATIONS_DEPLOYMENT_GUIDE.md
3. Reference: TROUBLESHOOTING_GUIDE.md as needed

### 📊 **I'm a Product/Business Person**
1. Start with: **SYSTEM_ARCHITECTURE_OVERVIEW.md** (15 min)
2. Then: **AUDIENCE_SPECIFIC_ARCHITECTURE/README.md** → Business guide
3. Reference: System capabilities matrix in overview

---

## 📖 Root-Level Files at This Level

| File | Purpose | Who Should Read |
|------|---------|-----------------|
| **SYSTEM_ARCHITECTURE_OVERVIEW.md** | Complete 10-layer system architecture | Everyone - start here |
| **DESIGN_PATTERNS_GUIDE.md** | Template Method, Strategy, Factory patterns | Developers, architects |
| **CODE_QUALITY_STANDARDS.md** | Type hints, naming, docstring standards | **Read BEFORE coding** |

---

## 🔗 Quick Links

- 📊 **System Overview** → [SYSTEM_ARCHITECTURE_OVERVIEW.md](./SYSTEM_ARCHITECTURE_OVERVIEW.md)
- 📚 **Reference Docs** → [TECHNICAL_REFERENCE/](./TECHNICAL_REFERENCE/)
- 🛠️ **How-To Guides** → [IMPLEMENTATION_GUIDES/](./IMPLEMENTATION_GUIDES/)
- 👥 **Role-Based Views** → [AUDIENCE_SPECIFIC_ARCHITECTURE/](./AUDIENCE_SPECIFIC_ARCHITECTURE/)
- 🔐 **Credentials & Security** → [SECURE_CREDENTIALS_MANAGEMENT/](./SECURE_CREDENTIALS_MANAGEMENT/)
- ⚡ **Trade Service Deep Dive** → [TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md](./TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md)

---

## 📞 Additional Support

- **Contributing to Architecture Docs?** See individual directory README files
- **Need help?** Check IMPLEMENTATION_GUIDES/TROUBLESHOOTING_GUIDE.md
- **Security questions?** See SECURE_CREDENTIALS_MANAGEMENT/README.md

---

*Last Updated: May 18, 2026*  
*For detailed navigation within each directory, see the individual README.md files*
