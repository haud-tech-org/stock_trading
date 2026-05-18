# IMPLEMENTATION_GUIDES - Practical How-To Documentation

**Purpose**: Tier 3 practical implementation documentation  
**Audience**: Developers building features, extending systems, solving problems  
**Scope**: How-to guides, practical examples, implementation patterns  
**Last Updated**: May 18, 2026

---

## 🎯 What is IMPLEMENTATION_GUIDES?

This directory contains **practical, hands-on documentation** - the "how to do it" guides. It focuses on implementation details, step-by-step instructions, and working examples without theoretical deep-dives.

**Use this when**: You need to implement features, debug issues, or extend the system.

---

## 🏗️ Layer-Based Organization (10 Layers)

Each layer contains practical implementation guides:

| Layer | Name | Purpose | Navigation |
|-------|------|---------|------------|
| **1** | Entry Point | Starting the system | [→ Layer 1](./LAYER_1_ENTRY_POINT/README.md) |
| **2** | Symbol-Level Coordination | Per-symbol setup | [→ Layer 2](./LAYER_2_SYMBOL_COORDINATION/README.md) |
| **3** | Resolution Coordination | Multi-resolution config | [→ Layer 3](./LAYER_3_RESOLUTION_COORDINATION/README.md) |
| **4** | Approach Execution | Creating strategies | [→ Layer 4](./LAYER_4_APPROACH_EXECUTION/README.md) ⭐ |
| **5** | Data Services | Adding data providers | [→ Layer 5](./LAYER_5_DATA_SERVICES/README.md) |
| **6** | Alert Aggregation | Alert storage config | [→ Layer 6](./LAYER_6_ALERT_AGGREGATION/README.md) |
| **7** | Notification Delivery | Notification setup | [→ Layer 7](./LAYER_7_NOTIFICATION_DELIVERY/README.md) |
| **8** | Performance Analysis | Metrics & analysis | [→ Layer 8](./LAYER_8_PERFORMANCE_ANALYSIS/README.md) |
| **9** | Operational Support | Deployment & ops | [→ Layer 9](./LAYER_9_OPERATIONAL_SUPPORT/README.md) |
| **10** | Trade Execution Service | Live DCA bracket trading | [→ Layer 10](./LAYER_10_TRADE_EXECUTION/README.md) ⚡ NEW |

---

## 🎯 Quick Navigation by Use Case

### 👨‍💻 **Creating a New Trading Strategy**
1. **Read**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Understand system (20 min)
2. **Learn Pattern**: [TECHNICAL_REFERENCE/Layer 4](../TECHNICAL_REFERENCE/LAYER_4_APPROACH_EXECUTION/README.md) - Theory
3. **Follow Guide**: [LAYER_4: EXECUTOR_IMPLEMENTATION_GUIDE.md](./LAYER_4_APPROACH_EXECUTION/EXECUTOR_IMPLEMENTATION_GUIDE.md)
4. **Quick Ref**: [LAYER_4: ANALYZER_VALIDATOR_QUICK_REFERENCE.md](./LAYER_4_APPROACH_EXECUTION/ANALYZER_VALIDATOR_QUICK_REFERENCE.md)

### 🔌 **Adding a New Data Provider**
1. **Understand Data Layer**: [TECHNICAL_REFERENCE/Layer 5](../TECHNICAL_REFERENCE/LAYER_5_DATA_SERVICES/README.md)
2. **Follow Guide**: [LAYER_5: DATA_PROVIDER_EXTENSION_GUIDE.md](./LAYER_5_DATA_SERVICES/DATA_PROVIDER_EXTENSION_GUIDE.md)
3. **Quick Ref**: [LAYER_5: DATA_SERVICES_QUICK_REFERENCE.md](./LAYER_5_DATA_SERVICES/DATA_SERVICES_QUICK_REFERENCE.md)

### ⚡ **Working on Live Trade Execution** (NEW)
1. **Architecture theory**: [TECHNICAL_REFERENCE/Layer 10](../TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/README.md)
2. **Deep reference**: [BINANCE_PERPETUAL_TRADING_REFERENCE.md](../TECHNICAL_REFERENCE/LAYER_10_TRADE_EXECUTION/BINANCE_PERPETUAL_TRADING_REFERENCE.md)
3. **Follow Guide**: [LAYER_10: Trade Execution Implementation Guide](./LAYER_10_TRADE_EXECUTION/README.md)

### 🚀 **Deploying to Production**
1. **Deployment Guide**: [LAYER_9: OPERATIONS_DEPLOYMENT_GUIDE.md](./LAYER_9_OPERATIONAL_SUPPORT/OPERATIONS_DEPLOYMENT_GUIDE.md)
2. **Troubleshooting**: [LAYER_9: TROUBLESHOOTING_GUIDE.md](./LAYER_9_OPERATIONAL_SUPPORT/TROUBLESHOOTING_GUIDE.md)

### 📊 **Adding Performance Metrics**
1. **Metrics Guide**: [LAYER_8: PERFORMANCE_METRICS_EXTENSION_GUIDE.md](./LAYER_8_PERFORMANCE_ANALYSIS/PERFORMANCE_METRICS_EXTENSION_GUIDE.md)
2. **Reports System**: [LAYER_8: METRIC_TRADE_CALCULATION_REPORTS/](./LAYER_8_PERFORMANCE_ANALYSIS/METRIC_TRADE_CALCULATION_REPORTS/)

---

## 📖 Quick Reference Guides

### ⭐ Most Important (Layer 4: Approach Execution)
- **[EXECUTOR_IMPLEMENTATION_GUIDE.md](./LAYER_4_APPROACH_EXECUTION/EXECUTOR_IMPLEMENTATION_GUIDE.md)** - How to create new executor
- **[ANALYZER_VALIDATOR_QUICK_REFERENCE.md](./LAYER_4_APPROACH_EXECUTION/ANALYZER_VALIDATOR_QUICK_REFERENCE.md)** - Quick reference for components

### Data Services (Layer 5)
- **[DATA_SERVICES_QUICK_REFERENCE.md](./LAYER_5_DATA_SERVICES/DATA_SERVICES_QUICK_REFERENCE.md)** - Quick reference for data APIs
- **[DATA_PROVIDER_EXTENSION_GUIDE.md](./LAYER_5_DATA_SERVICES/DATA_PROVIDER_EXTENSION_GUIDE.md)** - How to add new providers
- **[API_DOCUMENTATION.md](./LAYER_5_DATA_SERVICES/API_DOCUMENTATION.md)** - Data API reference

### Operational (Layer 9)
- **[OPERATIONS_DEPLOYMENT_GUIDE.md](./LAYER_9_OPERATIONAL_SUPPORT/OPERATIONS_DEPLOYMENT_GUIDE.md)** - How to deploy
- **[TROUBLESHOOTING_GUIDE.md](./LAYER_9_OPERATIONAL_SUPPORT/TROUBLESHOOTING_GUIDE.md)** - How to fix issues

### Analysis (Layer 8)
- **[PERFORMANCE_METRICS_EXTENSION_GUIDE.md](./LAYER_8_PERFORMANCE_ANALYSIS/PERFORMANCE_METRICS_EXTENSION_GUIDE.md)** - Add custom metrics
- **[METRIC_TRADE_CALCULATION_REPORTS/](./LAYER_8_PERFORMANCE_ANALYSIS/METRIC_TRADE_CALCULATION_REPORTS/)** - Reports system

---

## 🚀 Common Use Cases

| Task | Guide |
|------|-------|
| **Create new strategy** | [Layer 4 Guides](./LAYER_4_APPROACH_EXECUTION/) |
| **Add data provider** | [Layer 5 Guides](./LAYER_5_DATA_SERVICES/) |
| **Deploy to production** | [Layer 9: Deployment](./LAYER_9_OPERATIONAL_SUPPORT/OPERATIONS_DEPLOYMENT_GUIDE.md) |
| **Fix problem** | [Layer 9: Troubleshooting](./LAYER_9_OPERATIONAL_SUPPORT/TROUBLESHOOTING_GUIDE.md) |
| **Add performance metrics** | [Layer 8 Guides](./LAYER_8_PERFORMANCE_ANALYSIS/) |
| **Replay historical data** | [Layer 3: Replay Guide](./LAYER_3_RESOLUTION_COORDINATION/REPLAY_MODE_ARCHITECTURE.md) |
| **Extend live trade execution** | [Layer 10 Guides](./LAYER_10_TRADE_EXECUTION/) ⚡ NEW |

---

## 📚 Directory Structure

```
IMPLEMENTATION_GUIDES/
├── LAYER_1_ENTRY_POINT/
│   └── README.md (Entry point how-to guides)
├── LAYER_2_SYMBOL_COORDINATION/
│   └── README.md (Symbol coordination guides)
├── LAYER_3_RESOLUTION_COORDINATION/
│   ├── README.md
│   └── REPLAY_MODE_ARCHITECTURE.md (How replay mode works)
├── LAYER_4_APPROACH_EXECUTION/
│   ├── README.md
│   ├── EXECUTOR_IMPLEMENTATION_GUIDE.md ⭐ (How to create executor)
│   └── ANALYZER_VALIDATOR_QUICK_REFERENCE.md (Quick ref)
├── LAYER_5_DATA_SERVICES/
│   ├── README.md
│   ├── DATA_SERVICES_QUICK_REFERENCE.md (Quick ref)
│   ├── DATA_PROVIDER_EXTENSION_GUIDE.md (How to add provider)
│   └── API_DOCUMENTATION.md (API reference)
├── LAYER_6_ALERT_AGGREGATION/
│   └── README.md (Alert storage guides)
├── LAYER_7_NOTIFICATION_DELIVERY/
│   └── README.md (Notification guides)
├── LAYER_8_PERFORMANCE_ANALYSIS/
│   ├── README.md
│   ├── PERFORMANCE_METRICS_EXTENSION_GUIDE.md (How to add metrics)
│   └── METRIC_TRADE_CALCULATION_REPORTS/ (Reports system)
├── LAYER_9_OPERATIONAL_SUPPORT/
│   ├── README.md
│   ├── OPERATIONS_DEPLOYMENT_GUIDE.md ⭐ (How to deploy)
│   └── TROUBLESHOOTING_GUIDE.md (How to troubleshoot)
├── LAYER_10_TRADE_EXECUTION/          ⚡ NEW
│   └── README.md (How to extend trading platforms and add new symbols)
├── README.md (this file)
└── INDEX.md
```

---

## 💡 How to Use This Directory

1. **Identify Your Task**: What do you need to do?
2. **Find Relevant Layer**: Based on task, choose layer
3. **Read Layer README**: Get overview of available guides
4. **Follow Specific Guide**: Step-by-step instructions
5. **Reference**: Use quick reference guides as needed

**Key Principle**: Each layer contains guides relevant to that layer only. Start with layer README, then read specific guides.

---

## 🔗 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md) - START HERE
- **Reference Docs**: [TECHNICAL_REFERENCE/](../TECHNICAL_REFERENCE/) - Theory and patterns
- **Root Navigation**: [Root README](../README.md) - Top-level directory guide
- **Role-Based Guides**: [AUDIENCE_SPECIFIC_ARCHITECTURE/](../AUDIENCE_SPECIFIC_ARCHITECTURE/) - By role

---

## 📞 Need Help?

- **"How do I...?"** → Find relevant layer guide
- **"Why is it designed...?"** → See TECHNICAL_REFERENCE/ for theory
- **"System overview"** → [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md)
- **"I have an error"** → [Troubleshooting Guide](./LAYER_9_OPERATIONAL_SUPPORT/TROUBLESHOOTING_GUIDE.md)

---

*Tier 3 Documentation - Practical Implementation*  
*Each layer maintains its own README for self-contained how-to guides*  
*For theory and patterns, see TECHNICAL_REFERENCE/ directory*
