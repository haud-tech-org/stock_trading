# Layer 4: Approach Execution - Tier 3 Implementation Guide

**Layer Number**: 4  
**Layer Name**: Approach Execution (18+ Trading Strategies)  
**Tier**: 3 (Implementation & How-To)  
**Purpose**: Practical guides for creating and modifying trading executors  

---

## 🎯 Layer Responsibility

Layer 4 implementation focuses on **creating new trading strategies** and modifying existing executors.

---

## 📖 Contents at This Layer

| File | Purpose | Read Time | Level |
|------|---------|-----------|-------|
| **EAV_PATTERN_STEP_BY_STEP.md** | Step-by-step implementation walkthrough ✅ NEW | 2-3 hours | Intermediate |
| **EXECUTOR_IMPLEMENTATION_GUIDE.md** | Complete guide to creating new executors | 30 min | Intermediate |
| **ANALYZER_VALIDATOR_QUICK_REFERENCE.md** | Quick reference for analyzer and validator methods | 10 min | Beginner |

---

## 🚀 Quick Navigation by Use Case

### **"How do I create a new trading strategy?"**
1. Read: EXECUTOR_IMPLEMENTATION_GUIDE.md (30 min)
2. Study: ANALYZER_VALIDATOR_QUICK_REFERENCE.md (10 min)
3. Create: New executor class inheriting from BaseExecutor
4. Test: Add to APPROACH_RESOLUTION_MAPPING and run in test mode
5. Deploy: Enable in configuration for production use

### **"How do I modify an existing strategy?"**
1. Locate executor in `src/stockreports/approaches/`
2. Review: ANALYZER_VALIDATOR_QUICK_REFERENCE.md
3. Modify: `analyze()` or `validate()` methods
4. Test: Run in REPLAY mode with historical data
5. Verify: Check performance metrics

### **"What's the easiest strategy to start with?"**
→ Moving Average Crossover - simple logic, good for learning the pattern

### **"How do I test my new strategy?"**
→ Add to mapping → Use `--mode REPLAY` → Check performance metrics in Layer 8

---

## 📚 Reference Files

### EXECUTOR_IMPLEMENTATION_GUIDE.md
Step-by-step guide to creating new trading executors:
- Executor anatomy and components
- Analyzer implementation
- Validator implementation
- Testing and validation
- Integration with system
- Example: Creating a custom strategy

### ANALYZER_VALIDATOR_QUICK_REFERENCE.md
Quick lookup for common patterns:
- Available indicators and utilities
- Common validation checks
- Error handling patterns
- Best practices

---

## 🔗 Related Documentation

- **Theory**: [Layer 4 Reference](../../TECHNICAL_REFERENCE/LAYER_4_APPROACH_EXECUTION/README.md) - MUST READ first
- **Pattern Details**: TECHNICAL_REFERENCE/LAYER_4/EXECUTOR_PATTERN_OVERVIEW.md
- **Pattern Diagrams**: TECHNICAL_REFERENCE/LAYER_4/EXECUTOR_PATTERN_DIAGRAMS.md
- **Base Classes**: TECHNICAL_REFERENCE/LAYER_4/ABSTRACT_BASE_CLASSES_ARCHITECTURE.md
- **Previous Layer**: [Layer 3 Implementation](../LAYER_3_RESOLUTION_COORDINATION/README.md)
- **Next Layer**: [Layer 5 Implementation](../LAYER_5_DATA_SERVICES/README.md)

---

## 💡 Common Patterns

### Basic Executor Template
```python
class MyStrategy(BaseExecutor):
    def analyze(self, candles, indicators):
        # Your analysis logic here
        return analysis_result
    
    def validate(self, analysis, thresholds):
        # Your validation logic here
        return signal (BUY/SELL/HOLD)
```

### Accessing Data
- `candles.high`, `candles.low`, `candles.close`, `candles.volume`
- Use data services for indicators
- Apply your analysis logic

### Generating Signals
- Return BUY (1), SELL (-1), or HOLD (0)
- Include confidence if applicable
- Log analysis details for debugging

---

## 🚀 Step-by-Step: Creating Your First Executor

1. **Study** the pattern (20 min)
   - Read EXECUTOR_IMPLEMENTATION_GUIDE.md
   - Review ANALYZER_VALIDATOR_QUICK_REFERENCE.md

2. **Choose** a strategy type (5 min)
   - Simple momentum, trend-following, mean reversion?
   - Start with something analyzable

3. **Implement** analyze() method (30 min)
   - Calculate indicators
   - Generate analysis

4. **Implement** validate() method (15 min)
   - Apply rules
   - Return signal

5. **Test** your executor (30 min)
   - Add to configuration
   - Run in REPLAY mode
   - Check performance

6. **Deploy** to production (5 min)
   - Update production configuration
   - Monitor performance in Layer 8

---

## 📞 Need Help?

- **Theory**: See TECHNICAL_REFERENCE/LAYER_4
- **How to extend**: See EXECUTOR_IMPLEMENTATION_GUIDE.md
- **Quick lookup**: See ANALYZER_VALIDATOR_QUICK_REFERENCE.md
- **Debugging**: See LAYER_9 TROUBLESHOOTING_GUIDE.md

---

*Last Updated: April 10, 2026*  
*Part of Tier 3 Documentation - Implementation & How-To*
