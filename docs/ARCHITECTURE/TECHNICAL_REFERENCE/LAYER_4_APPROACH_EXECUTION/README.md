# Layer 4: Approach Execution - Tier 2 Reference

**Layer Number**: 4  
**Layer Name**: Approach Execution (18+ Trading Strategies)  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding executor patterns and trading strategy architecture  

---

## 🎯 Layer Responsibility

Layer 4 contains the **trading strategy executors** - 18+ configurable approaches for analyzing price action and detecting trading opportunities. All follow the Executor → Analyzer → Validator pattern.

**Key Concept**: Unified executor framework enabling diverse trading strategies through consistent Template Method pattern and abstract base classes.

---

## 📖 Contents at This Layer

| File | Purpose | Read Time | Audience |
|------|---------|-----------|----------|
| **EXECUTOR_PATTERN_OVERVIEW.md** | Complete Executor→Analyzer→Validator pattern | 20 min | Developers, architects |
| **EXECUTOR_PATTERN_DIAGRAMS.md** | Visual representation of pattern and flows | 10 min | Visual learners, architects |
| **EXECUTOR_ANALYZER_VALIDATOR_PATTERN.md** | Deep technical dive into EAV pattern ✅ NEW | 30 min | Developers learning patterns |
| **ABSTRACT_BASE_CLASSES_ARCHITECTURE.md** | Base class design and inheritance hierarchy | 15 min | Developers extending system |
| **DEEP_DIVE_FINDINGS.md** | Pattern discoveries and design decisions | 15 min | Architects, senior developers |

---

## 🏗️ How This Layer Works

### Executor Pattern Overview

```
EXECUTOR (Strategy Container)
  ↓
  Loads configuration for the approach via ExecutorConfigurationOrchestrator
  (from executor_approach_configuration.json)
  ↓
ANALYZER (Analyze Candle Data)
  ├─ Study price action
  ├─ Calculate indicators
  └─ Generate analysis
  ↓
VALIDATOR (Validate Signal)
  ├─ Check thresholds
  ├─ Apply rules
  └─ Confirm trading opportunity
  ↓
DECISION (Buy/Sell/Hold signal)
```

### 18+ Trading Approaches

**Categories**:
1. **Trend-Following**: Identify and follow price trends
2. **Mean Reversion**: Trade reversals to average prices
3. **Momentum**: Trade strong directional moves
4. **Pattern Recognition**: Identify chart patterns
5. **Indicator-Based**: RSI, MACD, Bollinger Bands, etc.
6. **Hybrid**: Combine multiple signals

### Template Method Pattern

All executors inherit from abstract base:
- `analyze()` - Each strategy implements unique analysis
- `validate()` - Each strategy applies unique validation rules
- Common interface enables uniform orchestration

### Abstract Base Classes

**Hierarchy**:
```
BaseExecutor (Abstract)
  ├─ MovingAverageCrossover
  ├─ RSIStrategy
  ├─ MACDStrategy
  ├─ BollingerBands
  ├─ TrendFollower
  └─ ... (12+ more)
```

---

## 🔗 Layer Connections

| Direction | Connected Layer | Purpose |
|-----------|-----------------|---------|
| **← Prev** | Layer 3: Resolution Coordination | Called for each approach in mapping |
| **→ Next** | Layer 5: Data Services | Fetches indicators and candle data |
| **→ Next** | Layer 6: Alert Aggregation | Sends signals for storage |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Create new trading executors or modify existing ones
- **Key Learning**: Executor pattern and base class design
- **Must Read**: EXECUTOR_PATTERN_OVERVIEW.md first
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_4 for how-to

### 🏗️ Architects
- **Use Case**: Understand strategy architecture and extensibility
- **Key Learning**: Template Method pattern applied to trading strategies
- **Must Read**: All files in this layer
- **Next Step**: Study abstract base classes and pattern diagrams

### 📊 Quantitative Analysts
- **Use Case**: Develop new trading algorithms
- **Key Learning**: How to integrate analysis into executor framework
- **Must Read**: EXECUTOR_PATTERN_OVERVIEW.md + DEEP_DIVE_FINDINGS.md
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_4

---

## 🚀 Quick Navigation by Use Case

### **"How do I create a new trading strategy?"**
1. Read: EXECUTOR_PATTERN_OVERVIEW.md
2. Study: ABSTRACT_BASE_CLASSES_ARCHITECTURE.md
3. Follow: IMPLEMENTATION_GUIDES/LAYER_4/EXECUTOR_IMPLEMENTATION_GUIDE.md

### **"Why is this strategy framework designed this way?"**
→ Read DEEP_DIVE_FINDINGS.md for design decisions and rationale

### **"What's the difference between Executor, Analyzer, and Validator?"**
→ See EXECUTOR_PATTERN_DIAGRAMS.md for visual explanation

### **"How do I modify an existing approach?"**
→ Find it in src/stockreports/approaches/, study base class, modify analyze() or validate()

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **Previous Layer**: [Layer 3 README](../LAYER_3_RESOLUTION_COORDINATION/README.md) - Resolution mapping
- **Next Layer**: [Layer 5 README](../LAYER_5_DATA_SERVICES/README.md) - Data services
- **Next Layer**: [Layer 6 README](../LAYER_6_ALERT_AGGREGATION/README.md) - Alert storage
- **Implementation Guide**: [IMPLEMENTATION_GUIDES Layer 4](../../../IMPLEMENTATION_GUIDES/LAYER_4_APPROACH_EXECUTION/README.md)

---

## 🔍 Key Concepts

**Executor Pattern**: Strategy container coordinating analysis and validation  
**Template Method**: Base class defines structure; subclasses implement specifics  
**Abstract Base Classes**: Enforce consistent interface across all strategies  
**18+ Approaches**: Diverse trading strategies sharing unified architecture  
**Analyzer**: Processes market data and generates analysis  
**Validator**: Applies rules and confirms trading signals  

---

## 📖 Deep Dive Files

### EXECUTOR_PATTERN_OVERVIEW.md
Comprehensive guide to the pattern:
- Pattern structure and components
- Why this pattern was chosen
- How to extend with new strategies
- Real-world examples

### EXECUTOR_PATTERN_DIAGRAMS.md
Visual representations:
- Component relationships
- Data flow through executor
- Inheritance hierarchy
- Pattern sequence diagrams

### ABSTRACT_BASE_CLASSES_ARCHITECTURE.md
Technical design:
- Base class definitions
- Required methods
- Override patterns
- Integration points

### DEEP_DIVE_FINDINGS.md
Design rationale:
- Why Template Method
- Evolution of pattern
- Lessons learned
- Future considerations

---

## 📞 Need More Information?

- **How to implement a strategy**: See IMPLEMENTATION_GUIDES/LAYER_4
- **Data services for indicators**: See LAYER_5
- **Storing and using signals**: See LAYER_6
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 10, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
