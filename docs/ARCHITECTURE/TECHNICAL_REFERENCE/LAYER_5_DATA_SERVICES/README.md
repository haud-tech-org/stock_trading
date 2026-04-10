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
→ Follow IMPLEMENTATION_GUIDES/LAYER_5/DATA_PROVIDER_EXTENSION_GUIDE.md

### **"What's the performance impact of each resolution?"**
→ Check caching strategy in DATA_LAYER_ARCHITECTURE.md

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

---

## 📞 Need More Information?

- **How to add new indicator**: See IMPLEMENTATION_GUIDES/LAYER_5
- **How to add new data provider**: See IMPLEMENTATION_GUIDES/LAYER_5
- **Using data in strategies**: See LAYER_4
- **Monitoring data services**: See LAYER_9
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: April 10, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
