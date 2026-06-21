# DOJI_ANCHOR_SIGNAL_CANDLE Documentation Index & Navigation Guide

**Document Type**: Navigation & Quick Reference  
**Purpose**: Help users find what they need and choose the right learning path  
**Last Updated**: June 21, 2026

---

## 🎯 Quick Start: Choose Your Path

### ⚡ **I have 15 minutes** → Quick Overview

**Goal**: Understand what DOJI_ANCHOR_SIGNAL_CANDLE does

**Read**:
1. **This document** (5 min): Read "What is DOJI_ANCHOR_SIGNAL_CANDLE?" section below
2. **DOJI_ANCHOR_SIGNAL_CANDLE.md** (10 min): 
   - Executive Summary section
   - Algorithm Overview diagram
   - Algorithm Parameters table

**Time**: ~15 minutes  
**Outcome**: Basic understanding of approach purpose and parameters

---

### 📖 **I have 1 hour** → Comprehensive Understanding

**Goal**: Understand how the approach works and when it generates alerts

**Read** (in order):
1. **This document** (5 min): What is it? Why use it?
2. **DOJI_ANCHOR_SIGNAL_CANDLE.md** (25 min):
   - Executive Summary
   - Algorithm Overview
   - Detailed Step-by-Step Logic (all 5 steps)
   - Key Concepts Explained
3. **DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md** (25 min):
   - Read Sections 1-4:
     - Current Architecture Diagram
     - Data Flow Through Execution
     - Decision Points & Control Flow
     - Signal & Trend Logic

**Time**: ~1 hour  
**Outcome**: Complete understanding of algorithm execution and decision logic

---

### 💻 **I have 2-3 hours** → Implementation Ready

**Goal**: Understand enough to implement, test, or modify the approach

**Read** (in order):
1. **DOJI_ANCHOR_SIGNAL_CANDLE.md** (45 min):
   - Everything (read sections in sequence)
2. **DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md** (50 min):
   - All sections including:
     - Validation Logic Detailed (all 4 validations)
     - Class Structure & Relationships
     - State Management
     - Performance Characteristics
3. **DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md** (25 min):
   - Read Sections:
     - Complete Execution Walkthrough
     - One Scenario Example (Scenario 4)

**Time**: ~2-3 hours  
**Outcome**: Can understand, debug, and modify implementation

---

### 🔬 **I have 4+ hours** → Expert Knowledge

**Goal**: Deep mastery of all aspects (implementation, performance, edge cases)

**Read** (in order):
1. **All main documents** (2-3 hours):
   - DOJI_ANCHOR_SIGNAL_CANDLE.md
   - DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md
   - DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md
   
2. **Review source code** (1-2 hours):
   - executor.py: Follow _find_alerts() method line by line
   - analyzer.py: Understand find_most_recent_doji() and discover_anchor_with_trend()
   - validator.py: Study validation logic for each step
   - settings.py: Understand parameter loading
   
3. **Study examples** (30-60 min):
   - Walk through Scenarios 1-4 in VISUAL_FLOWS.md
   - Trace each step with real numbers
   - Understand parameter sensitivity

4. **Performance analysis** (optional):
   - Read "Performance Characteristics" section in ARCHITECTURE
   - Benchmark execution on your data

**Time**: 4+ hours  
**Outcome**: Expert-level understanding, can optimize or extend

---

## 📚 Document Map

### Documents Included

```
Index (this document)
├─ Choose your learning path based on available time
└─ Maps to all other documents
    │
    ├─ DOJI_ANCHOR_SIGNAL_CANDLE.md
    │  ├─ Executive Summary
    │  ├─ Algorithm Overview (with flow diagram)
    │  ├─ Parameters Table
    │  ├─ Detailed Step-by-Step Logic (Pre + 5 steps)
    │  ├─ Key Concepts Explained
    │  ├─ Trading Logic Summary
    │  └─ Code References
    │
    ├─ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md
    │  ├─ Architecture Diagram (visual)
    │  ├─ Data Flow Diagram (visual)
    │  ├─ Decision Points & Control Flow
    │  ├─ Signal & Trend Logic
    │  ├─ Validation Logic Detailed (4 sections)
    │  ├─ Key Concept: Why This Order?
    │  ├─ Class Structure & Relationships
    │  ├─ State Management
    │  └─ Performance Characteristics
    │
    ├─ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md
    │  ├─ Complete Execution Walkthrough
    │  ├─ 4 Real Data Scenarios (with full analysis)
    │  ├─ Parameter Sensitivity Guide
    │  ├─ Error Handling & Edge Cases
    │  ├─ Debugging Strategies
    │  └─ Code References
    │
    └─ INDEX.md (this document)
       ├─ Learning paths (15 min - 4+ hours)
       ├─ Document map
       ├─ Topic-based navigation
       ├─ Quick reference tables
       ├─ Maintenance schedule
       └─ FAQ
```

---

## 🗂️ Topic-Based Navigation

### Topic: Understanding Doji

**What is a doji candle?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Key Concepts Explained" → "Doji Candle" section

**How is doji detected?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Step-by-Step Logic" → "Pre-Step: Prepare Candles"

**What parameters control doji detection?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Algorithm Parameters" table → MAX_DOJI_BODY_RATIO, MIN_DOJI_RANGE

**How to adjust doji sensitivity?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Parameter Sensitivity Guide" → MAX_DOJI_BODY_RATIO

---

### Topic: Understanding Anchor

**What is an anchor candle?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Key Concepts Explained" → "Anchor Candle" section

**How is anchor found?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Step-by-Step Logic" → "Pre-Step: Prepare Candles"

**What makes a valid anchor?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Step-by-Step Logic" → "Step 4: Trend Candle Validation"

**How far back to search for anchor?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Algorithm Parameters" → ANCHOR_SEARCH_LIMIT

---

### Topic: Understanding Validations

**What are the 4 validation steps?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Validation Sequence (Optimized Order)" table

**Why is this validation order used?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md → "Key Concept: Why This Order?"

**How does cooldown work?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md → "Validation 1: Cooldown Check Logic"

**How does momentum validation work?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md → "Validation 3: Momentum Logic"

**What does alert candle validation check?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Step 2: Alert Candle Validation"

---

### Topic: Working with Parameters

**What are all the parameters?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Algorithm Parameters" table

**How do I tune parameters?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Parameter Sensitivity Guide" section

**What's the impact of each parameter?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Parameter Sensitivity Guide" (each parameter detailed)

**Where are parameters stored?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Code References" → settings.py

---

### Topic: Debugging

**Where are logs?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Debugging Strategies" → "Strategy 1: Enable Detailed Logging"

**How to debug a specific window?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Debugging Strategies" → "Strategy 2: Trace Through Single Window"

**Why isn't my approach generating alerts?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Debugging Strategies" → "Strategy 3: Parameter Tuning Experiment"

**Where do windows fail most often?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Debugging Strategies" → "Strategy 4: Analyze Failure Distribution"

**What are common edge cases?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Error Handling & Edge Cases" (5 detailed cases)

---

### Topic: Implementation & Code

**Where is the implementation?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Code References" section

**What does executor.py do?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md → "Class Structure & Relationships"

**What does analyzer.py do?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Key Concepts Explained" (mentions analyzer usage)

**What does validator.py do?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Detailed Step-by-Step Logic" (each step references validator)

**How fast is the execution?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_ARCHITECTURE.md → "Performance Characteristics"

---

### Topic: Trading Logic

**When does the approach generate a BUY signal?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Trading Logic Summary" → "When DOJI_ANCHOR_SIGNAL_CANDLE Generates BUY Signal"

**When does the approach generate a SELL signal?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Trading Logic Summary" → "When DOJI_ANCHOR_SIGNAL_CANDLE Generates SELL Signal"

**What does the signal pattern look like?**
→ DOJI_ANCHOR_SIGNAL_CANDLE_VISUAL_FLOWS.md → "Real Data Scenario Examples" → Scenario 4

**Why use doji-anchor pattern?**
→ DOJI_ANCHOR_SIGNAL_CANDLE.md → "Executive Summary" → "Core Pattern"

---

## 🎯 Quick Reference Tables

### Algorithm Steps Summary

| # | Name | Complexity | Fail Rate | Purpose |
|---|------|-----------|-----------|---------|
| Pre | Prepare Candles | O(n) | 60% | Find doji and anchor |
| — | Signal Determination | O(1) | ~5% | Calculate reversal signal |
| 1 | Cooldown Check | O(1) | ~75% | Prevent alert spam |
| 2 | Alert Candle Validation | O(1) | ~55% | Confirm reversal |
| 3 | Momentum Validation | O(m) | ~45% | Validate volatility |
| 4 | Trend Candle Validation | O(s) | ~30% | Validate anchor strength |
| 5 | Alert Creation | O(1) | ~0% | Create alert |

**Usage**: Quick lookup for step details

---

### Parameters Quick Reference

| Parameter | Type | Typical Range | Impact |
|-----------|------|---------------|--------|
| LOOKBACK_WINDOW | int | 4-10 | Larger = more history = more patterns |
| COOLDOWN_WINDOW | int | 2-10 min | Larger = fewer alerts (less spam) |
| MAX_DOJI_BODY_RATIO | float | 0.1-0.4 | Smaller = stricter doji detection |
| MIN_DOJI_RANGE | float | 0.0-0.5 | Larger = stricter doji detection |
| ANCHOR_SEARCH_LIMIT | int | 3-7 | Larger = search deeper for anchor |
| TREND_WINDOW | int | 3-6 | Larger = longer trend calculation |
| MOMENTUM_MIN_PRICE_MOVE | float | 1.0-3.0 | Larger = require more volatility |
| TREND_CANDLE_RANGE_MULTIPLIER | float | 1.2-2.0 | Larger = require stronger anchor |
| TREND_CANDLE_MIN_BODY | float | 0.5-2.0 | Larger = require bigger anchor body |
| ALERT_CANDLE_CLOSE_TO_EXTREME | float | 0.3-1.0 | Controls reversal confirmation distance |
| ALERT_CANDLE_MAX_VOLUME_RATIO | float | 1.0-1.5 | Larger = accept higher alert volume |
| MIN_ALERT_BODY_SIZE | float | 0.5-2.0 | Larger = require bigger alert body |

**Usage**: Quick lookup for parameter effects

---

### Validation Decision Matrix

| Step | Fails When | Impact | Adjustment |
|------|-----------|--------|------------|
| Cooldown | Less time than COOLDOWN_WINDOW | Prevents spam | Increase/decrease COOLDOWN_WINDOW |
| Alert | Close not in reversal direction | Wrong signal | Adjust ALERT_CANDLE_CLOSE_TO_EXTREME |
| Alert | Volume too high | Spike rejection | Adjust ALERT_CANDLE_MAX_VOLUME_RATIO |
| Alert | Body too small | No direction | Adjust MIN_ALERT_BODY_SIZE |
| Momentum | Price range too low | Weak setup | Decrease MOMENTUM_MIN_PRICE_MOVE |
| Trend | Anchor not strong enough | Weak trend | Decrease TREND_CANDLE_RANGE_MULTIPLIER |
| Trend | Anchor body too small | Weak direction | Decrease TREND_CANDLE_MIN_BODY |

**Usage**: When alerts aren't being generated, check which step is failing most

---

## 📅 Maintenance Schedule

### Regular Reviews

**Weekly**:
- Monitor alert quality (false signals)
- Check for exceptions in logs
- Verify parameter appropriateness for market conditions

**Monthly**:
- Review algorithm performance metrics
- Compare with other approaches
- Adjust parameters if needed based on results

**Quarterly**:
- Full code review for any issues
- Update documentation if changes made
- Verify implementation still matches documentation

**Annually**:
- Complete retest against historical data
- Consider improvements or optimizations
- Update documentation with lessons learned

---

### Documentation Updates

When approach is modified:

1. Update relevant code sections in source files
2. Update affected documentation sections
3. Add version note with date
4. Re-verify all examples and cross-references
5. Test all scenarios in VISUAL_FLOWS.md

---

## ❓ Frequently Asked Questions

### Q: When would I use DOJI_ANCHOR_SIGNAL_CANDLE vs. other approaches?

**A**: Use DOJI_ANCHOR_SIGNAL_CANDLE when:
- You want to identify reversals after consolidation
- You have clear anchor candles establishing trends
- You want momentum validation in your setup
- You want doji-based patterns

Comparison:
- **STRONG_CANDLE**: Direct strong candle detection (no doji/anchor)
- **REVERSAL_ANCHOR**: Reversal without doji requirement
- **DOJI_ANCHOR_SIGNAL_CANDLE**: Doji + Anchor + Reversal (most specific)

---

### Q: How many alerts should I expect per day?

**A**: Depends heavily on parameters and market conditions.

Expected range:
- Very strict settings: 2-5 alerts/day
- Moderate settings: 5-15 alerts/day
- Loose settings: 15-30+ alerts/day

Use COOLDOWN_WINDOW to control frequency:
- 2 minutes: Up to 30 alerts/hour
- 5 minutes: Up to 12 alerts/hour
- 10 minutes: Up to 6 alerts/hour

---

### Q: Why does the approach skip so many windows?

**A**: By design - 99%+ of windows don't generate alerts.

Failure breakdown:
- 60% fail pre-step (no doji found)
- 75% of remainder fail cooldown
- 55% of remainder fail alert validation
- 45% of remainder fail momentum
- 30% of remainder fail trend strength

Only ~0.5% of windows generate alerts. This is expected and healthy.

---

### Q: Which parameter is most important?

**A**: Depends on your goal:

For **quality** (fewer false signals):
→ TREND_CANDLE_RANGE_MULTIPLIER (anchor strength)

For **frequency** (more alerts):
→ MOMENTUM_MIN_PRICE_MOVE (volatility requirement)

For **spam prevention**:
→ COOLDOWN_WINDOW (time between alerts)

For **pattern detection**:
→ MAX_DOJI_BODY_RATIO (doji definition)

---

### Q: Can I modify the approach?

**A**: Yes, follow these steps:

1. Study the current implementation thoroughly (all 4 documents)
2. Identify what you want to change
3. Understand dependencies and side effects
4. Update code in `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/`
5. Update affected documentation sections
6. Test thoroughly with historical data
7. Add version note to documentation

---

### Q: How do I report an issue or suggest improvement?

**A**: Document the issue:

1. Include current approach configuration
2. Provide example data/candles that trigger the issue
3. Show logs from the execution
4. Describe expected vs. actual behavior
5. Suggest potential fixes if known

Submit to development team with this information.

---

## 🔗 External References

### Related Documents (in repo)

- **General Architecture**: `/docs/ARCHITECTURE/LAYER_4_APPROACH_EXECUTION/`
- **Design Patterns**: `/docs/ARCHITECTURE/DESIGN_PATTERNS_GUIDE.md`
- **Code Quality**: `/docs/ARCHITECTURE/CODE_QUALITY_STANDARDS.md`

### Implementation Files

- **Executor**: `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/executor.py`
- **Analyzer**: `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/analyzer.py`
- **Validator**: `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/validator.py`
- **Settings**: `src/stockreports/alert/approach/DOJI_ANCHOR_SIGNAL_CANDLE/settings.py`

---

## 📊 Document Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | June 21, 2026 | Initial complete documentation suite |

---

## 👥 Document Support

**Questions about documentation?**
→ Refer to main approach document (DOJI_ANCHOR_SIGNAL_CANDLE.md) first

**Questions about implementation?**
→ Check source code and VISUAL_ARCHITECTURE.md

**Questions about parameters?**
→ See VISUAL_FLOWS.md "Parameter Sensitivity Guide"

**Questions about debugging?**
→ See VISUAL_FLOWS.md "Debugging Strategies"

---

**Status**: ✅ Complete and navigable  
**Last Updated**: June 21, 2026  
**Verification**: All cross-references verified
