# Performance Metrics Extension Guide - CORRECTED

**Date:** April 8, 2026  
**Status:** Based on Actual Codebase Analysis  
**Target Audience:** Developers extending performance analytics  
**Prerequisites:** Understanding Technical Reference architecture  

---

## Overview

### What is the Report Generator?

The centralized report generator is:
- **Primary Purpose:** Simulate trades and generate performance reports
- **Mode:** Backtesting tool (not real-time)
- **Output:** Performance metrics, profitability analysis, S/R levels
- **Base Process:** 2 always-done steps + 3 optional steps

### CRITICAL: Not a Fixed 5-Step Process

The documentation previously claimed 5 fixed steps. **This is WRONG.** The actual system has:

**2 Base Steps (ALWAYS done):**
1. Trade simulation for each day
2. Report consolidation per scenario

**3 Optional Steps (CONDITIONAL on flags):**
3. Support/Resistance detection (optional)
4. Suggested price updates (optional)
5. Performance analysis (optional)

---

## Actual Architecture

### Entry Point

**File:** `/src/tools/centralized_report_generator/centralized_report_generator.py` (330 lines)

**Main Function:**
```python
def generate_reports_for_period(
    execution_symbol: str,
    alert_sources: list,
    from_date_str: str,
    to_date_str: str,
    mode: str,
    run_sr: bool,                  # Optional: run S/R detection
    sr_start_time: str,            # Optional: S/R start
    sr_end_time: str,              # Optional: S/R end
    sr_resolution: int,            # Optional: S/R resolution
    sr_min_touches: int,           # Optional: S/R min touches
    suggestion_type: Optional[str], # Optional: suggestion type
    update_price_alert_settings: bool,  # Optional: update prices
    run_analysis_flag: bool         # Optional: run analysis
):
    """
    Orchestrates report generation with optional features.
    
    Base workflow:
    - For each profit/loss threshold scenario:
        1. Run daily trade simulations (individual_trade_simulator.py)
        2. Consolidate daily reports (consolidate_reports.py)
    
    Then conditionally:
    - If run_sr: Run S/R detection
    - If suggestion_type: Update suggested prices
    - If run_analysis: Run performance analysis
    """
```

### Scenario Iteration

```python
# From centralized_report_generator.py
from src.stockreports.config.validation_settings import (
    VALIDATION_PRICE_THRESHOLD_PROFIT,
    VALIDATION_PRICE_THRESHOLD_LOSS
)

# Each combination of profit/loss threshold is a "scenario"
for profit_threshold in VALIDATION_PRICE_THRESHOLD_PROFIT:
    for loss_threshold in VALIDATION_PRICE_THRESHOLD_LOSS:
        # Scenario: (profit_threshold, loss_threshold)
        
        # Step 1: Simulate for all days
        for day in date_range:
            run_individual_trade_simulation(
                execution_symbol=execution_symbol,
                alert_sources=alert_sources,
                day=day,
                profit_threshold=profit_threshold,
                loss_threshold=loss_threshold,
                mode=mode
            )
        
        # Step 2: Consolidate this scenario
        consolidate_reports(
            execution_symbol=execution_symbol,
            profit_threshold=profit_threshold,
            loss_threshold=loss_threshold,
            mode=mode
        )
```

---

## Base Workflow: 2 Steps

### Step 1: Individual Trade Simulation

**File:** `/src/tools/centralized_report_generator/individual_trade_simulator.py`

```python
def run_individual_trade_simulation(
    execution_symbol: str,
    alert_sources: list,
    day: datetime,
    profit_threshold: float,
    loss_threshold: float,
    mode: str
) -> None:
    """
    Simulate trades for ONE day with ONE profit/loss threshold pair.
    
    What it does:
    - Loads alerts for the day
    - Simulates entry/exit for each alert
    - Applies profit/loss thresholds
    - Records outcomes: profitable, loss, breakeven
    - Writes report to disk
    
    Output:
    - Report file for this day + scenario
    - Metrics: win rate, avg profit/loss, max drawdown, etc.
    """
```

**Key Points:**
- Runs PER DAY (for each day in date range)
- Runs PER SCENARIO (for each profit/loss combo)
- Uses REPLAY mode with TimeSimulator
- Generates individual daily report

### Step 2: Consolidate Reports

**File:** `/src/tools/centralized_report_generator/consolidate_reports.py`

```python
def consolidate_reports(
    execution_symbol: str,
    profit_threshold: float,
    loss_threshold: float,
    mode: str
) -> None:
    """
    Aggregate all daily reports for ONE scenario into summary.
    
    What it does:
    - Reads all daily reports for this scenario
    - Aggregates metrics:
        - Total trades
        - Win/loss counts
        - Overall profitability
        - Performance statistics
    - Writes consolidated report
    
    Output:
    - Summary report for this scenario
    - Metrics: total return, Sharpe ratio, etc.
    """
```

**Key Points:**
- Runs ONCE PER SCENARIO (after all days simulated)
- Aggregates daily results
- Creates summary performance metrics
- Writes to scenario-specific directory

---

## Optional Features: 3 Steps

### Optional Step 3: Support/Resistance Detection

**File:** `/src/tools/centralized_report_generator/support_resistance_detector.py`

**Flag:** `run_sr` (boolean)

```python
def run_sr_detection_for_symbols(
    symbols: list,
    start_time: str,
    end_time: str,
    resolution: int,
    min_touches: int
) -> None:
    """
    Detect S/R levels from historical data.
    
    What it does:
    - Loads historical data
    - Identifies price levels with multiple touches
    - Classifies as support or resistance
    - Updates S/R level database
    
    Parameters:
    - start_time: S/R analysis start (e.g., "2026-01-01")
    - end_time: S/R analysis end (e.g., "2026-04-08")
    - resolution: Candle resolution in minutes
    - min_touches: Minimum touches to qualify as S/R
    
    Output:
    - S/R level database updates
    - Used by subsequent trade simulations
    """
```

**Only runs if:**
```python
if run_sr:  # CLI flag --run-sr-detector
    run_sr_detection_for_symbols(...)
```

### Optional Step 4: Suggested Price Updates

**File:** `/src/tools/centralized_report_generator/update_alert_files_with_suggestion.py`

**Flag:** `suggestion_type` (string)

```python
def update_alerts_with_suggested_prices(
    symbols: list,
    suggestion_type: str
) -> None:
    """
    Update suggested entry/exit prices in alerts.
    
    What it does:
    - Loads existing alerts
    - Recalculates suggested prices based on:
        - Support/resistance levels
        - Performance history
        - Market conditions
    - Updates alert files with new suggestions
    
    Suggestion Types:
    - "structural": Based on S/R levels
    - "performance": Based on historical profitability
    - "all": Both types
    
    Output:
    - Updated alert files
    - New suggested_price fields
    """
```

**Only runs if:**
```python
if suggestion_type:  # CLI flag --suggestion-type [structural|performance|all]
    update_alerts_with_suggested_prices(
        symbols=alert_sources,
        suggestion_type=suggestion_type
    )
```

### Optional Step 5: Performance Analysis

**File:** `/src/tools/analysis/analyze_overall_performance.py`

**Flag:** `run_analysis_flag` (boolean)

```python
def run_analysis(
    mode: str,
    execution_symbol: str,
    profit_threshold: Optional[float] = None,
    loss_threshold: Optional[float] = None
) -> None:
    """
    Analyze overall system performance.
    
    What it does:
    - Loads all consolidated reports
    - Compares across scenarios
    - Identifies best/worst configurations
    - Generates performance graphs
    - Creates analysis summary
    
    Output:
    - Analysis report
    - Performance comparisons
    - Optimization recommendations
    """
```

**Only runs if:**
```python
if run_analysis_flag:  # CLI flag --run-analysis
    run_analysis(...)
```

---

## Validation Settings

### Threshold Configuration

**File:** `/src/stockreports/config/validation_settings.py`

```python
# Example configuration
VALIDATION_PRICE_THRESHOLD_PROFIT = [
    1.0,   # 1% profit
    1.5,   # 1.5% profit
    2.0,   # 2% profit
    2.5,   # 2.5% profit
    3.0    # 3% profit
]

VALIDATION_PRICE_THRESHOLD_LOSS = [
    -0.5,  # 0.5% loss
    -1.0,  # 1% loss
    -1.5,  # 1.5% loss
    -2.0   # 2% loss
]
```

**Scenario Generation:**
- Each combination of PROFIT × LOSS is a scenario
- Example: 5 profit × 4 loss = 20 scenarios
- Each scenario runs ALL days

### Usage in Simulation

```python
# In individual_trade_simulator.py
for alert in alerts:
    # Simulate entry
    entry_price = alert.alert_price
    
    # Calculate exit based on thresholds
    profit_target = entry_price * (1 + profit_threshold/100)
    loss_limit = entry_price * (1 + loss_threshold/100)
    
    # Simulate until hit
    # Record: profitable, loss, breakeven
```

---

## Creating a Custom Metric

### Pattern for New Metrics

**Location:** Create a new module in `/src/tools/centralized_report_generator/` or `/src/tools/analysis/`

**Example: Custom Volatility Analyzer**

```python
# src/tools/analysis/custom_volatility_analyzer.py

class CustomVolatilityAnalyzer:
    """Analyze volatility impact on alert profitability."""
    
    def __init__(self, reports_dir: str):
        self.reports_dir = reports_dir
        self.logger = logging.getLogger(__name__)
    
    def analyze(self) -> dict:
        """
        Analyze volatility correlation.
        
        Returns:
            dict: Analysis results with metrics
        """
        # Load reports
        # Calculate volatility
        # Correlate with profitability
        # Return metrics
        return {
            "avg_volatility": 1.2,
            "volatility_impact": 0.45,
            "recommendation": "High volatility reduces profitability"
        }
    
    def generate_report(self, output_path: str) -> None:
        """Generate analysis report."""
        results = self.analyze()
        # Write to file
```

**Integration with Main Generator:**

```python
# In generate_reports_for_period
if run_volatility_analysis:
    analyzer = CustomVolatilityAnalyzer(reports_dir)
    analysis = analyzer.analyze()
    logging.info(f"Volatility analysis: {analysis}")
```

---

## Workflow Example

### Command-Line Usage

```bash
# Base workflow only (2 steps)
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-04-01 \
    --to-date 2026-04-08 \
    --mode deployment

# Add S/R detection
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-04-01 \
    --to-date 2026-04-08 \
    --mode deployment \
    --run-sr-detector \
    --sr-start-time "2026-01-01 09:00:00" \
    --sr-min-touches 3

# Add suggestion updates
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-04-01 \
    --to-date 2026-04-08 \
    --mode deployment \
    --suggestion-type all

# Complete with analysis
python3 -m src.tools.centralized_report_generator.centralized_report_generator \
    --execution-symbol VN30F1M \
    --alert-sources VN30 VN30F1M \
    --from-date 2026-04-01 \
    --to-date 2026-04-08 \
    --mode deployment \
    --run-sr-detector \
    --suggestion-type all \
    --run-analysis
```

---

## Output Structure

### Directory Organization

```
reports/
├── deployment/
│   ├── profit_1.0_loss_-0.5/
│   │   ├── daily/
│   │   │   ├── 2026-04-01.json
│   │   │   ├── 2026-04-02.json
│   │   │   └── ...
│   │   └── consolidated.json
│   ├── profit_1.0_loss_-1.0/
│   │   ├── daily/
│   │   └── consolidated.json
│   └── ...
├── analysis/
│   └── overall_performance.json
└── sr_levels/
    └── 2026-01-01_to_2026-04-08.json
```

### Consolidated Report Format

```json
{
    "scenario": {
        "profit_threshold": 1.0,
        "loss_threshold": -1.0
    },
    "metrics": {
        "total_alerts": 150,
        "profitable_alerts": 85,
        "loss_alerts": 45,
        "breakeven_alerts": 20,
        "win_rate": 0.567,
        "avg_profit": 0.85,
        "avg_loss": -0.95,
        "total_pnl": 42.5,
        "sharpe_ratio": 1.23
    },
    "period": {
        "start_date": "2026-04-01",
        "end_date": "2026-04-08",
        "days": 8
    }
}
```

---

## Testing

### Unit Tests

```python
# tests/test_centralized_report_generator.py
import pytest
from src.tools.centralized_report_generator.individual_trade_simulator import (
    run_individual_trade_simulation
)
from datetime import datetime

def test_trade_simulation():
    """Test trade simulation for one day."""
    run_individual_trade_simulation(
        execution_symbol="VN30F1M",
        alert_sources=["VN30"],
        day=datetime(2026, 4, 8),
        profit_threshold=1.0,
        loss_threshold=-1.0,
        mode="deployment"
    )
    
    # Verify output report was created
    # Verify metrics are reasonable
```

---

## Important Notes

### The 2 Always-Done Steps

These ALWAYS happen regardless of flags:

1. **Trade Simulation** - Simulates trades for each day/scenario
2. **Report Consolidation** - Aggregates daily results

### The 3 Optional Steps

These are ONLY done if flags are provided:

3. **S/R Detection** - Requires `--run-sr-detector`
4. **Suggestion Updates** - Requires `--suggestion-type`
5. **Performance Analysis** - Requires `--run-analysis`

### Scenario System

- **NOT** a fixed "5-step process"
- **IS** a flexible scenario-based approach
- Each scenario = one (profit_threshold, loss_threshold) pair
- All days tested against each scenario

---

**Status:** Corrected based on actual codebase  
**Date:** April 8, 2026  
**Base Steps:** 2 (always)  
**Optional Steps:** 3 (conditional)  
**Ready to Use:** Yes
