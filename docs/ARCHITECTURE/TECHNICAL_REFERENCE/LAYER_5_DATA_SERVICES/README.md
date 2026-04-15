# Layer 5: Data Services - Tier 2 Reference

**Layer Number**: 5  
**Layer Name**: Data Services  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding market data, indicators, and data architecture  

---

## 🎯 Layer Responsibility

Layer 5 provides **market data infrastructure** - OHLCV candles, technical indicators, and data services. It enables trading strategies to access consistent, multi-resolution price and indicator data.

**Key Concept**: Unified data service layer providing diverse data sources (Vietstock, Binance, etc.) through consistent interfaces while managing caching and performance.

---

## 📖 Contents at This Layer

| File | Purpose | Read Time | Audience |
|------|---------|-----------|----------|
| **DATA_LAYER_ARCHITECTURE.md** | Complete data services design and architecture | 25 min | Developers, architects |
| **DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md** | ⭐ Technical reference for timezone handling | 15 min | Provider developers |
| **PROVIDER_RESOURCE_LIFECYCLE.md** | Comprehensive guide on context managers and resource management | 20 min | Provider developers, operators |
| **CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md** | Step-by-step implementation guide for adding context managers | 15 min | Developer extending providers |

---

## 🏗️ How This Layer Works

### Data Services Architecture

```
Trading Strategy (Layer 4)
  ↓
Data Service Interface
  ├─ Get OHLCV(symbol, resolution)
  ├─ Calculate Indicator(symbol, indicator_name, params)
  └─ Get Historical Data(symbol, start_date, end_date)
  ↓
Data Providers
  ├─ Vietstock Provider
  ├─ Binance Provider
  └─ Custom Providers
  ↓
Market Data (Cached/Fresh)
```

### Multi-Resolution Support

Strategies access data at any resolution:
- **1-minute candles**: Intraday details
- **5-minute candles**: Short-term trends
- **15-minute candles**: Medium-term analysis
- **1-hour candles**: Long-term trends
- **Daily candles**: Extended history

### Technical Indicators

Supported indicators:
- **Trend**: SMA, EMA, Moving Average Crossovers
- **Momentum**: RSI, Stochastic, MACD
- **Volatility**: Bollinger Bands, ATR
- **Volume-Based**: OBV, VWAP
- **Custom**: User-defined indicators

### Caching Strategy

Performance optimization:
- Recent candles cached in memory
- Historical data cached per resolution
- Indicator calculations cached
- Cache invalidation on new data

### Multi-Provider Support

Abstracts away exchange differences:
- Vietstock API wrapper
- Binance API wrapper
- Custom provider interface
- Unified error handling

### Context Manager Support (Resource Management)

All data providers implement Python's context manager pattern for guaranteed resource cleanup:

```python
# Usage pattern - guarantees cleanup
with provider:
    data = provider.fetch_ohlcv(symbol, resolution)
# On exit: __exit__() automatically calls close() → connections cleaned up ✅

# Inside coordinator's 57-second monitoring loop
with provider:
    ohlcv = provider.fetch_ohlcv(symbol, resolution)
    # Process data...
# Fresh connection every 57 seconds → no timeouts ✅
```

**All 3 Providers Support Context Managers:**
- **VietstockProvider**: Default behavior (no special cleanup)
- **BinanceAPIProvider**: Overrides to cleanup HTTP session
- **BinanceCCXTProvider**: Overrides to cleanup exchange connection

**Benefits:**
- Automatic resource cleanup (no memory leaks)
- Fresh connections every cycle (prevents timeouts)
- Exception-safe (cleanup happens even if error occurs)
- Consistent interface across all providers

**Monitoring Loop Integration:**
The 57-second monitoring cycle uses context managers to ensure fresh connections, solving the 1-2 hour timeout problem that occurred when connections were reused indefinitely.

---

## 🔗 Layer Connections

| Direction | Connected Layer | Purpose |
|-----------|-----------------|---------|
| **← Prev** | Layer 4: Approach Execution | Strategies request data/indicators |
| **→ Next** | Layer 1-4: All trading layers | Provides data foundation |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Add new indicators or data providers
- **Key Learning**: Data layer design and service interfaces
- **Must Read**: DATA_LAYER_ARCHITECTURE.md
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_5 for how-to

### 🏗️ Architects
- **Use Case**: Design data infrastructure and caching strategy
- **Key Learning**: Abstraction layer for multiple data sources
- **Must Read**: DATA_LAYER_ARCHITECTURE.md
- **Next Step**: Consider performance and scalability implications

### 🚀 Operations/DevOps
- **Use Case**: Monitor data service health and performance
- **Key Learning**: Data cache configuration and data providers
- **Must Read**: Data architecture overview
- **Next Step**: LAYER_9 for operational monitoring

---

## 🚀 Quick Navigation by Use Case

### **"How do I add a new technical indicator?"**
1. Read: DATA_LAYER_ARCHITECTURE.md
2. Follow: IMPLEMENTATION_GUIDES/LAYER_5/DATA_PROVIDER_EXTENSION_GUIDE.md
3. Implement: New indicator in data service

### **"What data sources are supported?"**
→ See DATA_LAYER_ARCHITECTURE.md for provider list

### **"How do I handle data from a new exchange?"**
→ ⭐ **Start with:** DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md (critical timezone requirement)
→ **Then follow:** IMPLEMENTATION_GUIDES/LAYER_5/DATA_PROVIDER_EXTENSION_GUIDE.md

### **"What's the performance impact of each resolution?"**
→ Check caching strategy in DATA_LAYER_ARCHITECTURE.md

### **"How do I handle timezones in a data provider?"**
→ ⭐ **See:** DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md (technical reference)

### **"How do I implement resource cleanup for a new provider?"**
→ **See:** CONTEXT_MANAGER_IMPLEMENTATION_GUIDE.md (step-by-step)
→ **Reference:** PROVIDER_RESOURCE_LIFECYCLE.md (comprehensive guide)

### **"Why do providers use context managers?"**
→ **Read:** PROVIDER_RESOURCE_LIFECYCLE.md (resource management benefits)
→ **Problem Solved:** Fresh connections in 57-second cycles prevent 1-2 hour timeouts

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **Previous Layer**: [Layer 4 README](../LAYER_4_APPROACH_EXECUTION/README.md) - Approach execution
- **Implementation Guide**: [IMPLEMENTATION_GUIDES Layer 5](../../../IMPLEMENTATION_GUIDES/LAYER_5_DATA_SERVICES/README.md)
- **Operational Support**: [Layer 9 README](../LAYER_9_OPERATIONAL_SUPPORT/README.md) - Monitoring data services

---

## 🔍 Key Concepts

**Data Services**: Unified interface for market data and indicators  
**Multi-Resolution**: Support 1m, 5m, 15m, 1h, daily candles  
**Technical Indicators**: RSI, MACD, Bollinger Bands, Moving Averages, etc.  
**Caching**: Performance optimization for repeated data access  
**Multi-Provider**: Vietstock, Binance, custom data sources  
**Provider Abstraction**: Unified interface hiding exchange differences  

---

## 📖 Reference Files

### DATA_LAYER_ARCHITECTURE.md
Complete data services documentation:
- Architecture overview and design
- Supported data providers
- Indicator calculations
- Caching strategy
- Performance characteristics
- Integration points with strategies

### DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md
⭐ **Technical reference for timezone handling in data providers:**
- Standard pattern for timezone conversion
- Live implementation examples (Vietstock, Binance)
- Common mistakes with solutions
- Verification steps and checklist
- Why timezone consistency is critical
- Troubleshooting guide

**Critical Requirement:** All data providers MUST return market-timezone-indexed DataFrames (Asia/Ho_Chi_Minh), NOT UTC.

---

## 📞 Need More Information?

- **How to add new indicator**: See IMPLEMENTATION_GUIDES/LAYER_5
- **How to add new data provider**: See IMPLEMENTATION_GUIDES/LAYER_5
- **Timezone requirement**: ⭐ See DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md (critical!)
- **Using data in strategies**: See LAYER_4
- **Monitoring data services**: See LAYER_9
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 11, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
*Note: Added DATA_PROVIDER_TIMEZONE_CONSISTENCY_REFERENCE.md for critical timezone requirements*
