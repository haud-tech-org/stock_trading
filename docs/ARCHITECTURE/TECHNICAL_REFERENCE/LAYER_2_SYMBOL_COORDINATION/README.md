# Layer 2: Symbol-Level Coordination - Tier 2 Reference

**Layer Number**: 2  
**Layer Name**: Symbol-Level Coordination  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding per-symbol orchestration and monitoring loops  

---

## 🎯 Layer Responsibility

Layer 2 handles **per-symbol monitoring orchestration**. Each symbol gets its own `SymbolAlerter` instance running in a dedicated thread, maintaining an independent monitoring loop.

**Key Concept**: Single symbol monitoring loop that coordinates with Resolution Coordinator to manage multi-resolution analysis while respecting LIVE vs REPLAY mode differences.

---


---

## � Layer 2 Documentation Map

This README provides a high-level summary and navigation for Layer 2 (Symbol Coordination). For all technical and implementation details, see:

- **Architecture Transformation & Model**
  - `ARCHITECTURE_TRANSFORMATION.md` — Symbol-centric, DRY configuration and orchestration
- **TimeSimulator & Session Model**
  - `TIME_SIMULATOR_AND_SESSIONS.md` — Session model integration, type safety, and usage
- **Session Structure Optimization**
  - `LIST_SESSIONS_OPTIMIZATION.md` — Why and how List[Session] replaced dict, performance and clarity
- **Executor Pattern (Technical Reference)**
  - `EXECUTOR_PATTERN_REFERENCE.md`
- **Executor Implementation Guide**
  - `../../IMPLEMENTATION_GUIDES/LAYER_2_SYMBOL_COORDINATION/EXECUTOR_IMPLEMENTATION_GUIDE.md`
- **Configuration & Multi-Approach Execution**
  - `../../CONFIGURATION_SERVICE/TRADING_HOURS_AND_MULTI_APPROACH_EXECUTION.md`
- **System Overview**
  - `../../SYSTEM_ARCHITECTURE_OVERVIEW.md`

All deep-dive and implementation details are in the above docs. This README is for orientation and quick navigation only.

---

---

## 🏗️ How This Layer Works


---

### Per-Symbol Isolation
- **Independent Thread**: Each symbol runs in separate ThreadPoolExecutor thread
- **Isolated State**: Symbol's alerts and metrics don't affect others
- **Error Containment**: Symbol's crash doesn't impact other symbols
- **Resource Management**: Each symbol has own connection pool, caches

### Mode-Specific Behavior

**LIVE Mode**:
- Indefinite monitoring loop
- Auto-restart on error
- Continuous market monitoring

**REPLAY Mode**:
- Loop until end-of-day
- Exit on error (deterministic)
- Bounded execution for backtesting

---

## 🔗 Layer Connections

| Direction | Connected Layer | Purpose |
|-----------|-----------------|---------|
| **← Prev** | Layer 1: Entry Point | Launched by main orchestrator |
| **→ Next** | Layer 3: Resolution Coordination | Maps approaches to resolutions each cycle |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Debug symbol-specific monitoring issues
- **Key Learning**: Monitoring loop structure and error handling
- **Next Step**: Layer 3 for resolution coordination details

### 🏗️ Architects
- **Use Case**: Understand symbol isolation and threading model
- **Key Learning**: Per-symbol state management and lifecycle
- **Next Step**: Layer 3 for coordination patterns

### 🚀 Operations/DevOps
- **Use Case**: Monitor individual symbol health
- **Key Learning**: Symbol-level error recovery and isolation
- **Next Step**: Layer 9 for operational monitoring

---

## 🚀 Quick Navigation by Use Case

### **"Why is symbol X stuck?"**
→ Check symbol's dedicated thread state and error logs

### **"How does monitoring work for each symbol?"**
→ Continuous cycles of: fetch data → analyze → store alerts → sleep → repeat

### **"What happens if symbol Y crashes?"**
→ Other symbols continue; Y restarts in LIVE mode, exits in REPLAY mode

### **"How often does each symbol get analyzed?"**
→ Configurable interval; each cycle fetches latest candle and runs approaches

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **Previous Layer**: [Layer 1 README](../LAYER_1_ENTRY_POINT/README.md) - Entry point orchestration
- **Next Layer**: [Layer 3 README](../LAYER_3_RESOLUTION_COORDINATION/README.md) - Resolution mapping
- **Operational Support**: [Layer 9 README](../LAYER_9_OPERATIONAL_SUPPORT/README.md) - Monitoring and alerts

---

## 🔍 Key Concepts

**SymbolAlerter**: Per-symbol orchestrator maintaining independent monitoring loop  
**Monitoring Cycle**: Fetch → Analyze → Store → Sleep → Repeat  
**Per-Symbol Isolation**: Independent threads with separate state management  
**Threading Model**: ThreadPoolExecutor ensures concurrent yet isolated symbol monitoring  

---

## 📞 Need More Information?

- **Resolution coordination**: See LAYER_3 for approach mapping
- **Approach execution**: See LAYER_4 for trading strategy details
- **Error handling**: See LAYER_9 for operational support
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 10, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
