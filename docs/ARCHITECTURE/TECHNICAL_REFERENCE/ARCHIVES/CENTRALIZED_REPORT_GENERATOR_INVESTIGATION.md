# Centralized Report Generator: Deep Investigation

**Date:** April 8, 2026  
**Component:** Performance Metrics & Reporting Service  
**Status:** Critical Service - Needs Architecture Documentation

---

## Executive Summary

The **Centralized Report Generator** is a critical service for **performance metrics analysis and backtesting orchestration**. It's an extensible tool that analyzes trading performance, generates profitability reports, and provides performance analytics to clients and internal teams.

### What It Does:
Generates comprehensive performance reports by simulating trading scenarios across multiple profit/loss thresholds and time periods, providing insights into strategy effectiveness.

### Why It's Important:
- **Client Value**: Provides end clients with detailed performance metrics
- **Strategy Validation**: Validates trading approaches across multiple scenarios
- **Decision Support**: Enables data-driven strategy refinement
- **Compliance**: Generates audit trails of trading performance

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│         Centralized Report Generator                            │
│         (Performance Metrics & Backtesting Orchestrator)        │
└─────────────────────────────────────────────────────────────────┘
          │
          ├─→ [1] Individual Trade Simulator
          │        ├─ Simulates each alert as independent trade
          │        ├─ Evaluates within validation window
          │        ├─ Calculates profit/loss outcomes
          │        └─ Groups by entry approach
          │
          ├─→ [2] Consolidation Engine
          │        ├─ Aggregates daily reports
          │        ├─ Calculates performance metrics
          │        ├─ Updates alert settings
          │        └─ Generates scenario summaries
          │
          ├─→ [3] Performance Analysis
          │        ├─ Analyzes overall performance
          │        ├─ Calculates win rates
          │        ├─ Generates client-facing reports
          │        └─ Provides actionable insights
          │
          ├─→ [4] Support/Resistance Detector
          │        ├─ Analyzes historical price data
          │        ├─ Identifies key price levels
          │        ├─ Updates trading parameters
          │        └─ Optimizes entry/exit points
          │
          └─→ [5] Suggested Price Backfiller
                   ├─ Updates alert files with prices
                   ├─ Performance-based pricing
                   ├─ Structural-based pricing
                   └─ All types combined
```

---

## Five Core Steps (In-Depth Analysis)

### Step 1: Individual Trade Simulator

**Location:** `src/tools/centralized_report_generator/individual_trade_simulator.py`

**Purpose:** Simulate each trading alert as an independent trade within a validation window

**Process:**

1. **Input Collection**
   - Load alert files for specified symbols and date
   - Extract alert data (entry price, time, approach, signal)
   - Load OHLCV price data for the trading day

2. **Trade Simulation**
   ```
   For each alert:
     ├─ Establish entry point (alert trigger price)
     ├─ Set validation window (fixed minutes after alert)
     ├─ Track price movement within window
     ├─ Calculate profit/loss at exit
     ├─ Determine worst loss during holding
     └─ Record trade outcome
   ```

3. **Profit/Loss Calculation**
   - Compares entry price vs exit price (end of window)
   - Applies profit threshold (take profit level)
   - Applies loss threshold (stop loss level)
   - Calculates actual profit/loss in points

4. **Performance Grouping**
   - Groups trades by `entry_approach` (which executor generated the alert)
   - Calculates per-approach metrics:
     - Min/max/average profit/loss
     - Win rates per approach
     - Worst loss during holding

5. **Output Generation**
   - Generates `ProfitabilityReport` with all trade details
   - Saves report to `reports_replay/` or `reports/` directory
   - Stores metrics for consolidation step

**Key Parameters:**
- `profit_threshold`: Take-profit level (points)
- `loss_threshold`: Stop-loss level (points)
- `validation_period_minutes`: How long to hold each trade
- `execution_symbol`: Primary trading symbol
- `alert_sources`: Symbols providing alert signals

**Output:**
```json
{
  "date": "2026-04-02",
  "symbol": "VN30F1M",
  "total_trades": 45,
  "profitable_trades": 28,
  "losing_trades": 17,
  "total_profit_loss": 150.50,
  "by_approach": {
    "STRONG_CANDLE": {
      "total_trades": 15,
      "avg_profit_loss": 8.5,
      "win_rate": 0.73
    }
  }
}
```

---

### Step 2: Consolidation Engine

**Location:** `src/tools/centralized_report_generator/consolidate_reports.py`

**Purpose:** Aggregate daily reports and generate scenario-level performance summary

**Process:**

1. **Report Collection**
   - Gathers all daily reports for date range
   - Filters by profit/loss threshold scenario
   - Validates report integrity

2. **Metrics Aggregation**
   ```
   Aggregates across multiple days:
     ├─ Total trades across period
     ├─ Total profit/loss cumulative
     ├─ Win rate (profitable / total)
     ├─ Average trade profit/loss
     ├─ Best performing approach
     └─ Risk metrics (drawdown, worst trade)
   ```

3. **Performance Analysis**
   - Calculates Sharpe ratio analogs
   - Identifies consistent performers
   - Detects problematic approaches
   - Compares scenarios

4. **Settings Update (Optional)**
   - Updates `price_alert_settings.py` with new performance data
   - Adjusts thresholds based on results
   - Enables dynamic strategy refinement

5. **Output Generation**
   - Creates consolidated scenario report
   - Formats for client consumption
   - Stores in scenario-specific directory

**Key Parameters:**
- `profit_threshold`: Profit level for scenario
- `loss_threshold`: Loss level for scenario
- `update_price_alert_settings`: Whether to update config

**Output:**
```json
{
  "period": "2026-04-02 to 2026-04-07",
  "scenario": "Profit: 10, Loss: -5",
  "total_trades": 270,
  "cumulative_profit": 850.00,
  "win_rate": 0.68,
  "trades_by_approach": {
    "STRONG_CANDLE": {
      "trades": 90,
      "profit": 320.00,
      "win_rate": 0.71
    }
  }
}
```

---

### Step 3: Performance Analysis Service

**Location:** `src/tools/analysis/analyze_overall_performance.py`

**Purpose:** Analyze overall performance and generate actionable insights

**Process:**

1. **Report Discovery**
   - Locates all consolidated reports
   - Identifies best/worst scenarios
   - Traces performance trends

2. **Comprehensive Analysis**
   ```
   Analyzes:
     ├─ Overall win rate
     ├─ Consistency metrics
     ├─ Approach effectiveness ranking
     ├─ Time-of-day performance
     ├─ Risk-adjusted returns
     └─ Client-facing insights
   ```

3. **Insight Generation**
   - Identifies winning approaches
   - Detects problematic signals
   - Recommends configuration changes
   - Suggests optimization opportunities

4. **Report Formatting**
   - Generates client-friendly summaries
   - Creates executive dashboard data
   - Produces detailed analysis documents

**Output:**
- Client-facing performance summary
- Executive dashboard data
- Detailed analytics report

---

### Step 4: Support/Resistance Detector

**Location:** `src/tools/centralized_report_generator/support_resistance_detector.py`

**Purpose:** Identify key price levels to optimize trading parameters

**Process:**

1. **Historical Data Analysis**
   - Loads historical OHLCV data for specified period
   - Analyzes price action patterns
   - Identifies significant price levels

2. **Level Detection**
   ```
   For each potential level:
     ├─ Count touches (bounces or rejections)
     ├─ Measure strength (price range impact)
     ├─ Verify consistency (repeated tests)
     ├─ Validate significance (min-touches threshold)
     └─ Calculate confidence level
   ```

3. **Validation**
   - Ensures minimum number of touches
   - Checks for consecutive tests
   - Measures level persistence

4. **Settings Update**
   - Updates support/resistance levels in config
   - Adjusts alert parameters based on levels
   - Optimizes entry/exit points

**Key Parameters:**
- `sr_start_time`: Analysis period start
- `sr_end_time`: Analysis period end
- `sr_resolution`: Candle timeframe (minutes)
- `sr_min_touches`: Minimum touches to qualify

**Output:**
- Updated support/resistance levels
- Confidence scores for each level
- Recommended parameter adjustments

---

### Step 5: Suggested Price Backfiller

**Location:** `src/tools/centralized_report_generator/update_alert_files_with_suggestion.py`

**Purpose:** Update alert files with optimal entry/exit prices based on performance

**Process:**

1. **Performance Data Collection**
   - Reviews consolidated reports for period
   - Identifies best-performing price levels
   - Calculates optimal entry/exit prices

2. **Price Calculation**
   ```
   For each approach:
     ├─ Performance-Based: 
     │    └─ Uses historical P&L to suggest prices
     ├─ Structural-Based:
     │    └─ Uses support/resistance levels
     └─ Combined (All):
          └─ Merges both approaches
   ```

3. **Alert File Updates**
   - Locates existing alert files
   - Adds suggested prices to alert records
   - Maintains historical data

4. **Validation**
   - Ensures prices are within reasonable bounds
   - Checks for outliers
   - Validates against current market prices

**Suggestion Types:**
- **Performance**: Based on historical profitability
- **Structural**: Based on support/resistance levels
- **All**: Combined approach using both methods

**Output:**
- Updated alert files with suggested prices
- Audit trail of all price updates
- Performance metadata

---

## Command Breakdown

```bash
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \          # Symbol to execute trades on
    --alert-sources VN30 VN30F1M \        # Symbols providing alert signals
    --from-date 2026-04-02 \              # Start of analysis period
    --to-date 2026-04-07 \                # End of analysis period
    --mode deployment                      # Use LIVE/REPLAY configured data
```

### What Happens Step-by-Step:

1. **Day-by-Day Simulation**
   - For each day in 2026-04-02 to 2026-04-07:
     - Run individual trade simulator
     - Generate daily report with trade outcomes
   - Total: 6 daily reports

2. **Multi-Scenario Processing**
   - For each profit/loss threshold combination:
     - Run all days through Step 1
     - Run consolidation (Step 2)
   - Multiple scenario reports generated

3. **Default Behavior**
   - Performance analysis runs (if enabled)
   - Report files stored in `reports_replay/` (REPLAY mode) or `reports/` (LIVE mode)
   - Summary logged to console

---

## Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│  Input: Command Parameters + Configuration                       │
├──────────────────────────────────────────────────────────────────┤
│  ├─ Execution Symbol (VN30F1M)                                   │
│  ├─ Alert Sources (VN30, VN30F1M)                                │
│  ├─ Date Range (2026-04-02 to 2026-04-07)                        │
│  ├─ Profit/Loss Thresholds (multiple scenarios)                  │
│  └─ Mode (DEPLOYMENT - uses LIVE/REPLAY based on config)         │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 1: Individual Trade Simulator (for each day)                │
├──────────────────────────────────────────────────────────────────┤
│  Input: Alert files + Price data                                  │
│  Process: Simulate trades, calculate P&L                          │
│  Output: Daily profitability reports                              │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 2: Consolidation Engine                                     │
├──────────────────────────────────────────────────────────────────┤
│  Input: Daily reports for date range                              │
│  Process: Aggregate metrics, analyze performance                  │
│  Output: Scenario-level consolidated report                       │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 3: Performance Analysis (Optional)                          │
├──────────────────────────────────────────────────────────────────┤
│  Input: All consolidated reports                                  │
│  Process: Generate insights, identify patterns                    │
│  Output: Client-facing analytics                                  │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 4: S/R Detection (Optional, if --run-sr-detector)           │
├──────────────────────────────────────────────────────────────────┤
│  Input: Historical price data                                     │
│  Process: Identify key price levels                               │
│  Output: Updated support/resistance settings                      │
└──────────────────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────────────────┐
│  Step 5: Suggested Prices (Optional, if --suggestion-type)        │
├──────────────────────────────────────────────────────────────────┤
│  Input: Performance data + Price levels                           │
│  Process: Calculate optimal entry/exit prices                     │
│  Output: Updated alert files with suggestions                     │
└──────────────────────────────────────────────────────────────────┘
```

---

## Key Insights

### 1. Multi-Scenario Analysis
- Runs simulations across **multiple profit/loss threshold combinations**
- Enables strategy optimization for different risk appetites
- Identifies robust vs fragile approaches

### 2. Performance Metrics
- **Granular**: Tracks performance by approach (executor)
- **Comprehensive**: Includes win rates, P&L, risk metrics
- **Actionable**: Enables data-driven configuration refinement

### 3. Extensibility
- **Modular design**: Each step can run independently
- **Optional steps**: S/R detection and price updates are optional
- **Flexible parameters**: Easily adjustable thresholds and timeframes

### 4. Client Value
- Provides transparent performance data
- Validates strategy effectiveness
- Enables performance-based optimization
- Supports continuous improvement

### 5. Integration Points**
- **Input**: Alert files from SymbolAlerter
- **Output**: Performance reports for clients
- **Feedback**: Updates settings for next trading cycle
- **Analysis**: Drives strategy refinement

---

## Critical Metrics Generated

### Per-Trade Metrics:
- Entry price & time
- Exit price & time
- Profit/loss amount
- Entry approach (which executor)
- Holding duration
- Worst loss during holding

### Per-Approach Metrics:
- Total trades
- Win rate (winning / total)
- Average profit/loss
- Min/max profit/loss
- Consistency measures

### Per-Period Metrics:
- Cumulative profit/loss
- Total trades
- Overall win rate
- Best/worst performing approach
- Risk-adjusted returns

---

## Configuration Impact

### Profit/Loss Thresholds:
- **Aggressive scenario**: High profit target, tight stop-loss
- **Conservative scenario**: Low profit target, wide stop-loss
- **Balanced scenario**: Medium targets for both

### Entry Approaches:
- Each executor contributes trades
- Performance compared across approaches
- Underperforming approaches identified

### Time Periods:
- Different market conditions may favor different approaches
- Seasonal analysis possible
- Trend identification enabled

---

## Deliverables for Clients

1. **Daily Profitability Reports**
   - What alerts were triggered
   - Which alerts were profitable
   - Overall day performance

2. **Scenario Performance Analysis**
   - Best profit/loss threshold combination
   - Approach effectiveness ranking
   - Risk-return profile

3. **Performance Metrics Dashboard**
   - Win rates by approach
   - Cumulative P&L trends
   - Risk metrics

4. **Actionable Insights**
   - Which approaches perform best
   - Optimal parameter settings
   - Recommended configuration changes

---

## Summary

The **Centralized Report Generator** is a sophisticated performance analytics service that:

✅ **Validates trading strategies** through comprehensive simulation  
✅ **Quantifies approach effectiveness** with detailed metrics  
✅ **Enables optimization** through multi-scenario analysis  
✅ **Provides transparency** to clients with detailed reports  
✅ **Supports continuous improvement** through performance feedback  

It's a **critical client-facing component** that justifies the trading system's value through documented, data-driven performance evidence.

