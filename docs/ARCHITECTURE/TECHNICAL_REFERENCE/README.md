# TECHNICAL_REFERENCE - Architecture Theory & Patterns

**Purpose**: Tier 2 reference documentation  
**Audience**: Architects, senior developers, anyone needing deep architectural knowledge  
**Scope**: Architecture patterns, design decisions, theoretical knowledge  
**Last Updated**: April 10, 2026

---

## 🎯 What is TECHNICAL_REFERENCE?

This directory contains **reference-level architecture documentation** - the "why and how" behind design decisions. It explains patterns, theoretical concepts, and architectural principles without implementation details.

**Use this when**: You need to understand architecture deeply, learn patterns, or make architectural decisions.

---

## 🏗️ Layer-Based Organization (9 Layers)

Each layer contains theory and reference materials:

| Layer | Name | Purpose | Navigation |
|-------|------|---------|------------|
| **1** | Entry Point | Multi-symbol orchestration | [→ Layer 1](./LAYER_1_ENTRY_POINT/README.md) |
| **2** | Symbol-Level Coordination | Per-symbol monitoring loops | [→ Layer 2](./LAYER_2_SYMBOL_COORDINATION/README.md) |
| **3** | Resolution Coordination | Multi-resolution mapping | [→ Layer 3](./LAYER_3_RESOLUTION_COORDINATION/README.md) |
| **4** | Approach Execution | 18+ trading strategies | [→ Layer 4](./LAYER_4_APPROACH_EXECUTION/README.md) ⭐ |
| **5** | Data Services | Market data & indicators | [→ Layer 5](./LAYER_5_DATA_SERVICES/README.md) |
| **6** | Alert Aggregation | Alert storage & persistence | [→ Layer 6](./LAYER_6_ALERT_AGGREGATION/README.md) |
| **7** | Notification Delivery | User notifications | [→ Layer 7](./LAYER_7_NOTIFICATION_DELIVERY/README.md) |
| **8** | Performance Analysis | Metrics & backtesting | [→ Layer 8](./LAYER_8_PERFORMANCE_ANALYSIS/README.md) |
| **9** | Operational Support | Logging, config, deployment | [→ Layer 9](./LAYER_9_OPERATIONAL_SUPPORT/README.md) |

---

## 🎯 Quick Navigation by Role

### 👨‍💻 **I'm a Developer**
1. **Start**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md) (20 min)
2. **Choose Layer**: Based on what you're working on
3. **Example**: New strategy? → [Layer 4](./LAYER_4_APPROACH_EXECUTION/README.md) → [EXECUTOR_PATTERN_OVERVIEW.md](./LAYER_4_APPROACH_EXECUTION/EXECUTOR_PATTERN_OVERVIEW.md)
4. **Example**: Data provider? → [Layer 5](./LAYER_5_DATA_SERVICES/README.md) → [DATA_LAYER_ARCHITECTURE.md](./LAYER_5_DATA_SERVICES/DATA_LAYER_ARCHITECTURE.md)

### 🏗️ **I'm an Architect**
1. **Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md)
2. **Deep Dive**: Read all layer READMEs for complete view
3. **Key Files**: 
   - [Layer 4: Executor Pattern](./LAYER_4_APPROACH_EXECUTION/README.md)
   - [Layer 5: Data Architecture](./LAYER_5_DATA_SERVICES/README.md)
   - [Layer 9: Operational Support](./LAYER_9_OPERATIONAL_SUPPORT/README.md)

### 🚀 **I'm in Operations/DevOps**
1. **Focus**: [Layer 9: Operational Support](./LAYER_9_OPERATIONAL_SUPPORT/README.md)
2. **Key Topics**: Deployment, monitoring, error recovery
3. **Reference**: Health checks, configuration, logging patterns

---

## 📖 Key Reference Files

### ⭐ Most Important (Layer 4: Approach Execution)
- **[EXECUTOR_PATTERN_OVERVIEW.md](./LAYER_4_APPROACH_EXECUTION/EXECUTOR_PATTERN_OVERVIEW.md)** - Complete executor pattern documentation
- **[EXECUTOR_PATTERN_DIAGRAMS.md](./LAYER_4_APPROACH_EXECUTION/EXECUTOR_PATTERN_DIAGRAMS.md)** - Visual diagrams and relationships
- **[ABSTRACT_BASE_CLASSES_ARCHITECTURE.md](./LAYER_4_APPROACH_EXECUTION/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md)** - Class hierarchy design
- **[DEEP_DIVE_FINDINGS.md](./LAYER_4_APPROACH_EXECUTION/DEEP_DIVE_FINDINGS.md)** - Design decisions and rationale

### Data Architecture (Layer 5)
- **[DATA_LAYER_ARCHITECTURE.md](./LAYER_5_DATA_SERVICES/DATA_LAYER_ARCHITECTURE.md)** - Complete data design and services
- **[PROVIDER_RESOURCE_LIFECYCLE.md](./LAYER_5_DATA_SERVICES/PROVIDER_RESOURCE_LIFECYCLE.md)** - Resource management, context managers, connection lifecycle
- **[CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md](./LAYER_5_DATA_SERVICES/CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md)** - Implementation guide for context managers

---

## 🚀 Common Use Cases

| Question | Answer |
|----------|--------|
| **"How is the system structured?"** | [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md) |
| **"Why the executor pattern?"** | [Layer 4: Deep Dive](./LAYER_4_APPROACH_EXECUTION/DEEP_DIVE_FINDINGS.md) |
| **"What's the data architecture?"** | [Layer 5: Data Layer](./LAYER_5_DATA_SERVICES/DATA_LAYER_ARCHITECTURE.md) |
| **"How do 9 layers connect?"** | Each layer README shows connections |
| **"Operational patterns?"** | [Layer 9 README](./LAYER_9_OPERATIONAL_SUPPORT/README.md) |

---

## 📚 Directory Structure

```
TECHNICAL_REFERENCE/
├── LAYER_1_ENTRY_POINT/
│   └── README.md (Layer theory, purpose, connections)
├── LAYER_2_SYMBOL_COORDINATION/
│   └── README.md
├── LAYER_3_RESOLUTION_COORDINATION/
│   └── README.md
├── LAYER_4_APPROACH_EXECUTION/
│   ├── README.md
│   ├── EXECUTOR_PATTERN_OVERVIEW.md ⭐
│   ├── EXECUTOR_PATTERN_DIAGRAMS.md
│   ├── ABSTRACT_BASE_CLASSES_ARCHITECTURE.md
│   └── DEEP_DIVE_FINDINGS.md
├── LAYER_5_DATA_SERVICES/
│   ├── README.md
│   └── DATA_LAYER_ARCHITECTURE.md
├── LAYER_6_ALERT_AGGREGATION/
│   └── README.md
├── LAYER_7_NOTIFICATION_DELIVERY/
│   └── README.md
├── LAYER_8_PERFORMANCE_ANALYSIS/
│   └── README.md
├── LAYER_9_OPERATIONAL_SUPPORT/
│   └── README.md
├── ARCHIVES/
│   └── (Historical docs, investigations, reviews)
├── README.md (this file)
└── INDEX.md
```

---

## 💡 How to Use This Directory

1. **Start Here**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md)
2. **Pick Your Layer**: Based on your focus area
3. **Read Layer README**: Understand purpose and connections
4. **Dive Deeper**: Read specific documentation files as needed
5. **Reference**: Return here to navigate to other layers

**Key Principle**: Each layer is self-contained with links to related documentation. Follow links based on your needs.

---

## 🔗 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md) - START HERE
- **Implementation Guides**: [IMPLEMENTATION_GUIDES/](../IMPLEMENTATION_GUIDES/) - How-to and practical guides
- **Root Navigation**: [Root README](../README.md) - Top-level directory guide
- **Archives**: [ARCHIVES/](./ARCHIVES/) - Historical documents and decisions

---

## 📞 Navigation Help

- **Looking for how-to guides?** → Go to [IMPLEMENTATION_GUIDES/](../IMPLEMENTATION_GUIDES/)
- **Looking for system overview?** → [SYSTEM_ARCHITECTURE_OVERVIEW.md](../SYSTEM_ARCHITECTURE_OVERVIEW.md)
- **Looking for role-based architecture?** → [AUDIENCE_SPECIFIC_ARCHITECTURE/](../AUDIENCE_SPECIFIC_ARCHITECTURE/)
- **Looking for security info?** → [SECURE_CREDENTIALS_MANAGEMENT/](../SECURE_CREDENTIALS_MANAGEMENT/)

---

*Tier 2 Documentation - Reference & Theory*  
*Each layer maintains its own README for self-contained navigation*  
*For implementation guides, see IMPLEMENTATION_GUIDES/ directory*
