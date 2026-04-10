# Layer 3: Resolution Coordination - Tier 2 Reference

**Layer Number**: 3  
**Layer Name**: Resolution Coordination  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding multi-resolution approach mapping  

---

## 🎯 Layer Responsibility

Layer 3 handles **mapping trading approaches to specific candle resolutions**. It coordinates which approaches run at which time resolutions (1m, 5m, 15m, 1h) for each symbol.

**Key Concept**: Configuration-driven approach-to-resolution mapping that allows flexible strategy deployment across multiple timeframes without code changes.

---

## 📖 Contents at This Layer

Currently, this layer has **no reference documentation files**. Resolution coordination theory can be found in the parent Tier 2 directory.

| File | Purpose | Status |
|------|---------|--------|
| (No files) | Resolution mapping theory | Ready for documentation |

---

## 🏗️ How This Layer Works

### Multi-Resolution Approach Mapping

The `ResolutionCoordinator` handles mapping:

```
Input: Symbol + Current Candle
  ↓
For each RESOLUTION (1m, 5m, 15m, 1h):
  ├─ Fetch candle data at that resolution
  ├─ Load configured approaches for this resolution
  ├─ Yield (resolution, approaches) tuple
  └─ Pass to Layer 4 for execution
  ↓
Output: Aggregated results from all resolutions
```

### Configuration-Driven Design

**APPROACH_RESOLUTION_MAPPING**:
- Defines which approaches run at which resolutions
- Enables flexible strategy deployment
- No code changes needed for new resolution combinations
- Example:
  ```
  {
    "1m": ["MovingAverageCrossover", "RSIStrategy"],
    "5m": ["MACDStrategy", "BollingerBands"],
    "15m": ["TrendFollower"],
    "1h": ["LongTermTrend"]
  }
  ```

### Multi-Resolution Conflicts

When multiple resolutions generate conflicting signals:
- All signals are recorded
- Caller determines precedence
- Majority voting or layered analysis possible
- Flexible aggregation strategy

---

## 🔗 Layer Connections

| Direction | Connected Layer | Purpose |
|-----------|-----------------|---------|
| **← Prev** | Layer 2: Symbol-Level Coordination | Called each monitoring cycle |
| **→ Next** | Layer 4: Approach Execution | Executes approaches returned by coordinator |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Add new approaches or change resolution mapping
- **Key Learning**: Configuration-driven approach deployment
- **Next Step**: Layer 4 for approach execution details

### 🏗️ Architects
- **Use Case**: Design multi-resolution trading strategies
- **Key Learning**: Flexible approach-to-resolution mapping pattern
- **Next Step**: Layer 4 for executor pattern

### 🚀 Operations/DevOps
- **Use Case**: Modify which strategies run at which resolutions
- **Key Learning**: Configuration management for strategy deployment
- **Next Step**: Layer 9 for configuration management details

---

## 🚀 Quick Navigation by Use Case

### **"How do I run a strategy only on 5-minute candles?"**
→ Update APPROACH_RESOLUTION_MAPPING configuration: "5m": ["MyStrategy"]

### **"What if different resolutions conflict?"**
→ All signals recorded; application logic determines handling

### **"How do I add a new resolution (e.g., 30m)?"**
→ Add to configuration and data provider; coordinator handles automatically

### **"Can approaches run at multiple resolutions?"**
→ Yes - configure same approach in multiple resolution lists

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **Previous Layer**: [Layer 2 README](../LAYER_2_SYMBOL_COORDINATION/README.md) - Symbol coordination
- **Next Layer**: [Layer 4 README](../LAYER_4_APPROACH_EXECUTION/README.md) - Approach execution
- **Implementation Guide**: [IMPLEMENTATION_GUIDES Layer 3](../../../IMPLEMENTATION_GUIDES/LAYER_3_RESOLUTION_COORDINATION/README.md)

---

## 🔍 Key Concepts

**Resolution Coordinator**: Maps approaches to timeframe resolutions  
**APPROACH_RESOLUTION_MAPPING**: Configuration driving strategy deployment  
**Multi-Resolution Analysis**: Running strategies across 1m, 5m, 15m, 1h timeframes  
**Conflict Aggregation**: Handling signals from multiple resolutions  

---

## 📞 Need More Information?

- **Approach execution**: See LAYER_4 for trading strategy implementation
- **Data retrieval**: See LAYER_5 for multi-resolution data services
- **Configuration**: See LAYER_9 for settings management
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 10, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
