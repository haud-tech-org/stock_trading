# Layer 5: Data Services - Tier 3 Implementation Guide

**Layer Number**: 5  
**Layer Name**: Data Services  
**Tier**: 3 (Implementation & How-To)  
**Purpose**: Practical guides for extending data services and indicators  

---

## 🎯 Layer Responsibility

Layer 5 implementation focuses on **adding data providers, indicators, and extending data services**.

---

## 📖 Contents at This Layer

| File | Purpose | Read Time | Level |
|------|---------|-----------|-------|
| **DATA_SERVICES_QUICK_REFERENCE.md** | Quick reference for available data services and indicators | 10 min | Beginner |
| **DATA_PROVIDER_EXTENSION_GUIDE.md** | Complete guide to adding new data providers | 25 min | Intermediate |
| **TIMEZONE_CONSISTENCY_GUIDE.md** | ⭐ CRITICAL: Timezone handling for data providers | 20 min | Intermediate |
| **API_DOCUMENTATION.md** | Data service API documentation | 15 min | Reference |

---

## 🚀 Quick Navigation by Use Case

### **"How do I add a new technical indicator?"**
1. Read: DATA_SERVICES_QUICK_REFERENCE.md (understand available services)
2. Implement: New indicator calculation method
3. Test: Verify calculation accuracy
4. Integrate: Add to executor usage
5. Deploy: Enable for strategies

### **"How do I support a new data provider (exchange)?"**
1. ⭐ **First:** Read TIMEZONE_CONSISTENCY_GUIDE.md (critical requirement)
2. Study: DATA_PROVIDER_EXTENSION_GUIDE.md
3. Implement: New provider class
4. Test: Fetch data and verify accuracy
5. Configure: Add to provider configuration
6. Validate: Multi-symbol support

### **"What indicators are already available?"**
→ See DATA_SERVICES_QUICK_REFERENCE.md for complete list

### **"What's the API for getting candle data?"**
→ See API_DOCUMENTATION.md for method signatures and examples

### **"How do I handle timezones in a data provider?"**
→ ⭐ **See TIMEZONE_CONSISTENCY_GUIDE.md** - This is critical and must be done correctly

---

## 📚 Reference Files

### DATA_SERVICES_QUICK_REFERENCE.md
Quick reference guide:
- Available indicators and their parameters
- Data service methods and signatures
- Common usage patterns
- Performance considerations

### DATA_PROVIDER_EXTENSION_GUIDE.md
Step-by-step guide to extending data providers:
- Provider interface requirements
- Implementing multi-exchange support
- Error handling and retries
- Testing new providers
- Performance optimization

### TIMEZONE_CONSISTENCY_GUIDE.md
⭐ **CRITICAL GUIDE** for timezone handling in data providers:
- Why timezone consistency is critical
- Standard pattern for all providers
- Common mistakes and how to avoid them
- Real-world Binance bug example (before/after)
- Implementation verification steps
- Unit test template
- Troubleshooting guide for timezone issues

**⚠️ Important:** All data providers MUST use market timezone (Asia/Ho_Chi_Minh), NOT UTC. Missing this causes cascading TypeErrors downstream. See this guide before implementing any provider.

### API_DOCUMENTATION.md
Complete API reference:
- Data service methods
- Parameter specifications
- Return value formats
- Error handling
- Examples and use cases

---

## 🔗 Related Documentation

- **Theory**: [Layer 5 Reference](../../TECHNICAL_REFERENCE/LAYER_5_DATA_SERVICES/README.md) - MUST READ first
- **Data Architecture**: TECHNICAL_REFERENCE/LAYER_5/DATA_LAYER_ARCHITECTURE.md
- **Previous Layer**: [Layer 4 Implementation](../LAYER_4_APPROACH_EXECUTION/README.md)
- **Next Layer**: [Layer 6 Implementation](../LAYER_6_ALERT_AGGREGATION/README.md)

---

## 💡 Common Patterns

### Adding a New Indicator
```python
def calculate_my_indicator(candles, period=14):
    # Your calculation logic
    return indicator_values

# Use in executor
analysis['my_indicator'] = calculate_my_indicator(candles)
```

### Adding a New Provider
```python
class MyExchangeProvider(BaseDataProvider):
    def get_ohlcv(self, symbol, resolution):
        # Fetch from your API
        return candles
    
    def get_indicator(self, symbol, indicator, params):
        # Calculate or fetch indicator
        return values
```

---

## 🚀 Step-by-Step: Adding Your First Indicator

1. **Understand** available services (10 min)
   - Read DATA_SERVICES_QUICK_REFERENCE.md
   - Review existing indicators

2. **Implement** calculation logic (20 min)
   - Create indicator function
   - Handle edge cases

3. **Test** accuracy (20 min)
   - Compare with known values
   - Test edge cases

4. **Integrate** into executor (10 min)
   - Use in analyze() method
   - Document in validator

5. **Validate** performance (10 min)
   - Check calculation speed
   - Monitor memory usage

---

## 📞 Need Help?

- **Theory**: See TECHNICAL_REFERENCE/LAYER_5
- **How to add indicator**: See this guide + DATA_SERVICES_QUICK_REFERENCE.md
- **How to add provider**: See DATA_PROVIDER_EXTENSION_GUIDE.md (start with TIMEZONE_CONSISTENCY_GUIDE.md!)
- **Timezone handling**: ⭐ See TIMEZONE_CONSISTENCY_GUIDE.md (critical for providers)
- **API details**: See API_DOCUMENTATION.md
- **Debugging**: See LAYER_9 TROUBLESHOOTING_GUIDE.md

---

*Last Updated: April 11, 2026*  
*Part of Tier 3 Documentation - Implementation & How-To*
*Note: TIMEZONE_CONSISTENCY_GUIDE.md added to address critical timezone requirement in data providers*
