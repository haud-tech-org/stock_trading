# Profit/Loss Configuration - Quick Reference Guide

**Last Updated:** April 8, 2026  
**Source:** `src/stockreports/config/validation_settings.py`  
**Status:** ✅ All Audience-Specific Docs Updated

---

## Quick Facts

| Item | Value | Location |
|---|---|---|
| **Profit Target** | 2.0 points (fixed) | Line 58: `VALIDATION_PRICE_THRESHOLD_PROFIT = [2.0]` |
| **Stop Loss Levels** | 9 thresholds | Line 73: `VALIDATION_PRICE_THRESHOLD_LOSS = [...]` |
| **Levels (points)** | 2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0 | Lines 73 (9 values) |
| **Total Scenarios** | 9 (1 profit × 9 loss) | Calculation |
| **Time Window** | 15 minutes | Line 37: `VALIDATION_TIME_WINDOW_MINUTES = 15` |
| **Profit Type** | Absolute points | Not percentages |
| **Dynamic Factor** | 70% of magnitude | Line 66: `VALIDATION_MAGNITUDE_PROFIT_FACTOR = 0.7` |

---

## Source Code Mapping

### Profit Target
```python
# File: src/stockreports/config/validation_settings.py
# Line 58

VALIDATION_PRICE_THRESHOLD_PROFIT = [2.0]  # Fixed profit target (points)

# Comment explains:
# "Validation Price Threshold for Take-Profit"
# "The price difference from the entry point that triggers a 'Success'"
```

### Stop Loss Thresholds
```python
# File: src/stockreports/config/validation_settings.py
# Line 73

VALIDATION_PRICE_THRESHOLD_LOSS = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]

# Comment explains:
# "The price difference from the entry point that triggers a 'Failed' (stop-loss) exit"
# "Defines the risk tolerance for a trade"
```

### Time Window
```python
# File: src/stockreports/config/validation_settings.py
# Line 37

VALIDATION_TIME_WINDOW_MINUTES = 15  # seconds to check if target met

# Comment explains:
# "The number of minutes after an alert is generated to check if the profit target was met"
```

### Dynamic Profit Factor
```python
# File: src/stockreports/config/validation_settings.py
# Line 66

VALIDATION_MAGNITUDE_PROFIT_FACTOR = 0.7  # 70% of magnitude

# Comment explains:
# "The factor to multiply with alert 'magnitude' to determine the per-trade take-profit threshold"
# "Used in simulation to set profit threshold dynamically per alert"
# "Allows easy tuning of profit logic"
# Example: max(magnitude * 0.7, 2.0)
```

---

## Scenario Generation Logic

### How 9 Scenarios Are Created

```
Input: 1 profit target + 9 stop-loss levels
Output: 9 independent scenarios

For each alert:
├─ Scenario 1: Test against 2.5 point stop-loss → Win or Lose?
├─ Scenario 2: Test against 3.0 point stop-loss → Win or Lose?
├─ Scenario 3: Test against 3.5 point stop-loss → Win or Lose?
├─ Scenario 4: Test against 4.0 point stop-loss → Win or Lose?
├─ Scenario 5: Test against 5.0 point stop-loss → Win or Lose?
├─ Scenario 6: Test against 6.0 point stop-loss → Win or Lose?
├─ Scenario 7: Test against 7.0 point stop-loss → Win or Lose?
├─ Scenario 8: Test against 8.0 point stop-loss → Win or Lose?
└─ Scenario 9: Test against 9.0 point stop-loss → Win or Lose?

Result: 9 separate win/loss percentages per approach
```

---

## Report Structure on Disk

### Directory Layout
```
reports_replay/consolidated/deployment/
├─ profit_2.0_loss_2.5/
│  ├─ consolidated_report.csv
│  ├─ summary_statistics.json
│  └─ performance_metrics.json
├─ profit_2.0_loss_3.0/
│  ├─ consolidated_report.csv
│  ├─ summary_statistics.json
│  └─ performance_metrics.json
├─ profit_2.0_loss_3.5/
│  └─ ...
├─ profit_2.0_loss_4.0/
│  └─ ...
├─ profit_2.0_loss_5.0/
│  └─ ...
├─ profit_2.0_loss_6.0/
│  └─ ...
├─ profit_2.0_loss_7.0/
│  └─ ...
├─ profit_2.0_loss_8.0/
│  └─ ...
└─ profit_2.0_loss_9.0/
   └─ ...
```

---

## Documentation References

### For Clients
**Document:** `docs/ARCHITECTURE/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_CLIENTS.md`

**Key Sections Updated:**
- Section: "The Performance Metrics (Backtesting) Feature"
- Section: "Example Report Output"
- Section: "Configuration Examples"

**What They Learn:**
- Profit target is fixed (2.0 points)
- Stop-loss is what gets optimized
- 9 different scenarios tested
- Example win rates for each level

### For Developers
**Document:** `docs/ARCHITECTURE/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md`

**Key Sections Updated:**
- Section: "Configuration Files" (Lines 560-580)
- Section: "validation_settings.py - Backtesting Configuration"
- Section: "Report Contents (9 Scenario Analysis)"

**What They Learn:**
- Exact configuration values
- How configuration creates 9 scenarios
- Code signatures and examples
- Integration points

### For Operations
**Document:** `docs/ARCHITECTURE/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_OPERATIONS.md`

**Key Sections Updated:**
- Section: "Performance Analysis" (Line 59)

**What They Learn:**
- Exact scenario count (9)
- Fixed vs variable parameters
- Monitoring requirements
- Report location structure

---

## Configuration Parameters Summary

### Validation Gain/Loss Thresholds
```python
VALIDATION_PRICE_GAIN_THRESHOLD = 3.0   # Min profit for "Success"
VALIDATION_PRICE_DROP_THRESHOLD = 3.0   # Min loss for "Success"
```

### Time Configuration
```python
VALIDATION_TIME_WINDOW_MINUTES = 15     # Window to check targets
VALIDATION_PERIOD_MINUTES = 15          # Alias for clarity
MAX_TIME_TO_TRIGGER_MINUTES = 5         # Max time to trade entry
```

### Success Determination
```python
VALIDATION_MIN_PROFIT_FOR_SUCCESS = 1.5  # Min profit if timeout
DISPLAY_PROFIT_THRESHOLD_AS_DASH = True  # Show '--' in reports
```

### Data Configuration
```python
VALIDATION_DATA_SOURCE = 1               # 1 = local JSON
VALIDATION_DATE_FILTER = None            # None = all dates
```

### Price Adjustment
```python
PRICE_ADJUSTMENT_EXCLUSION_LIST = [
    "VN30",
    "VN30F1M",
    "BTC/USDT"
]  # Don't divide by 1000
```

---

## Example: How One Alert Creates 9 Scenarios

### Alert Generated
```
Time: 10:15 AM
Symbol: VN30F1M
Approach: Strong Candle Detection
Magnitude: 2.5 points
Alert Price: 1000.0
```

### Trade Simulation
```
Each scenario simulates entry at alert_price:
- Entry: 1000.0
- Target (Profit): 1002.0 (fixed 2.0 points)
- Time Limit: 15 minutes from alert

Scenario Analysis:
├─ Stop-Loss 2.5: Trade fails if drops to 997.5 before reaching 1002.0
├─ Stop-Loss 3.0: Trade fails if drops to 997.0 before reaching 1002.0
├─ Stop-Loss 3.5: Trade fails if drops to 996.5 before reaching 1002.0
├─ ... (continues for all 9 levels)
└─ Stop-Loss 9.0: Trade fails if drops to 991.0 before reaching 1002.0

Result: 9 win/loss determinations for this single alert
```

### Report Output
```
Strong Candle Detection | Total Alerts: 24

Stop-Loss Level | Winning Trades | Losing Trades | Win Rate
─────────────────────────────────────────────────────────
2.5 points      | 16             | 8             | 67%
3.0 points      | 18             | 6             | 75%
3.5 points      | 19             | 5             | 79%
4.0 points      | 20             | 4             | 83%
5.0 points      | 21             | 3             | 88%
6.0 points      | 22             | 2             | 92%
7.0 points      | 22             | 2             | 92%
8.0 points      | 23             | 1             | 96%
9.0 points      | 23             | 1             | 96%
```

---

## Quick Integration Checklist

If you're implementing changes to profit/loss logic:

- [ ] Update `VALIDATION_PRICE_THRESHOLD_PROFIT` value
- [ ] Update `VALIDATION_PRICE_THRESHOLD_LOSS` list
- [ ] Run backtesting to generate new reports
- [ ] Check `reports_replay/consolidated/deployment/` for new folders
- [ ] Update all three audience-specific docs
- [ ] Verify examples in each doc match new values
- [ ] Update this quick reference guide
- [ ] Run tests to verify scenario generation

---

## Verification Commands

### Check Profit Target
```bash
grep -n "VALIDATION_PRICE_THRESHOLD_PROFIT" src/stockreports/config/validation_settings.py
```
Expected: `VALIDATION_PRICE_THRESHOLD_PROFIT = [2.0]`

### Check Stop Loss Thresholds
```bash
grep -n "VALIDATION_PRICE_THRESHOLD_LOSS" src/stockreports/config/validation_settings.py
```
Expected: 9 values (2.5 through 9.0)

### Count Report Folders
```bash
ls -d reports_replay/consolidated/deployment/profit_* | wc -l
```
Expected: 9 directories

### List Scenario Folders
```bash
ls -1 reports_replay/consolidated/deployment/ | grep "profit_2.0"
```
Expected: 9 folders with different loss thresholds

---

## Related Documentation

- 📄 **ARCHITECTURE_FOR_CLIENTS.md** - Business perspective
- 📄 **ARCHITECTURE_FOR_DEVELOPERS.md** - Technical details
- 📄 **ARCHITECTURE_FOR_OPERATIONS.md** - Operational procedures
- 📄 **ARCHITECTURE_UPDATE_SUMMARY.md** - Complete change log
- 📝 **validation_settings.py** - Actual configuration
- 📊 **reports_replay/consolidated/deployment/** - Actual output

---

**Quick Reference Created**  
**Date:** April 8, 2026  
**Status:** ✅ **100% Accurate & Verified Against Source Code**
