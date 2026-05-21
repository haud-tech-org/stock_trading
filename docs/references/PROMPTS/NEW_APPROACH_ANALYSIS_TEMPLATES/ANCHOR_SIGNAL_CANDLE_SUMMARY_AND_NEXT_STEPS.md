# Anchor-Signal-Candle (ASC) Approach - Summary & Next Steps

**Date**: April 10, 2026  
**Status**: ✅ READY FOR CODE GENERATION

---

## 📋 What We've Completed

### 1. **Analysis Document** ✅
📄 File: `ANCHOR_SIGNAL_CANDLE_APPROACH_ANALYSIS.md`

**Includes**:
- Executive summary of ASC approach
- 4 detailed validations with pseudocode
- 9 configuration parameters
- 5 clarification questions (ALL ANSWERED)
- Implementation readiness checklist

**Key Decisions Made**:
1. ✅ Anchor body = HIGH - LOW (full candle range)
2. ✅ Signal search = entire window with verification
3. ✅ Doji candles = FAIL validation
4. ✅ Trend = first close vs. last close
5. ✅ **REVERSAL APPROACH**: Original trend → opposite reversal signal

---

### 2. **Visual Reference Guide** ✅
📄 File: `ANCHOR_SIGNAL_CANDLE_VISUAL_REFERENCE.md`

**Includes**:
- Uptrend vs. Downtrend examples
- Anchor candle visualization
- Signal candle identification diagrams
- Alert candle extremes & wick validation visuals
- Complete validation sequence flowchart
- Configuration example values

---

### 3. **Implementation Plan** ✅
📄 File: `ANCHOR_SIGNAL_CANDLE_IMPLEMENTATION_PLAN.md`

**Includes**:
- 6 implementation phases (Settings, Analyzer, Validator, Executor, Init, Constants)
- 8 Analyzer methods (with signatures & pseudocode)
- 10 Validator methods (with signatures & pseudocode)
- 8 Executor methods (with detailed implementation flows)
- Complete code quality requirements
- Full checklist for code generation

---

## 🎯 ASC Approach Overview

### What It Detects
**Reversal signals** following high-volume price expansion events within a lookback window.

### The 3 Candle Roles
```
ANCHOR CANDLE     → SIGNAL CANDLE     → ALERT CANDLE
High volatility    High volume          Price extremes
(largest body)     (after anchor)       (wick validation)
         ↓                ↓                      ↓
     Size check    Volume check          Extreme check
     Min/multiplier  Min/multiplier      + Wick % check
```

### Validation Sequence
```
1. Window Size & Trend     → Validates window has sufficient range
2. Anchor Identification   → Finds abnormally large candle
3. Signal Identification   → Finds highest volume after anchor
4. Alert Confirmation      → Validates final candle & wick
5. Cooldown Check          → Prevents alert spam
6. Alert Creation          → Generate REVERSAL alert
```

### Signal Generation (REVERSAL)
```
If Original Trend = UPTREND
  └─ Then Reversal Trend = DOWNTREND
      └─ And Reversal Signal = SELL

If Original Trend = DOWNTREND
  └─ Then Reversal Trend = UPTREND
      └─ And Reversal Signal = BUY
```

---

## 📊 Configuration Parameters (9 Total)

| Parameter | Type | Purpose | Example |
|---|---|---|---|
| `lookback_window` | int | Window size for analysis | 50 candles |
| `min_size_price_window` | float | Minimum window price range | 0.5 |
| `min_size_candle` | float | Minimum anchor body size | 0.01 |
| `multiplier_size` | float | Anchor size vs. average multiplier | 1.5x |
| `min_volume` | float | Minimum signal volume | 100,000 |
| `multiplier_volume` | float | Signal volume vs. average multiplier | 1.2x |
| `min_percentage` | float | Minimum wick as % of body | 20% |
| `max_percentage` | float | Maximum wick as % of body | 60% |
| `cooldown_window` | int | Minutes between alerts | 60 |

---

## 📁 File Structure (5 Files to Generate)

```
src/stockreports/alert/approach/ANCHOR_SIGNAL_CANDLE/
├── __init__.py                          (5 lines)
├── settings.py                          (30 lines)
├── analyzer.py                          (~300 lines, 8 methods)
├── validator.py                         (~350 lines, 10 methods)
└── executor.py                          (~600 lines, 8 methods)

Total: ~1,285 lines of production-ready code
```

---

## 🔑 Key Architectural Patterns

### 1. Settings (Configuration)
- Inherits from `BaseSettings`
- All params loaded via `self.get(PARAM_NAME)`
- One instance per symbol

### 2. Analyzer (Pure Calculations)
- All `@staticmethod` methods
- No instance state
- Can reuse base `Analyzer` methods
- Pure functions (no side effects)

### 3. Validator (Pure Validations)
- All `@staticmethod` methods
- Returns boolean results
- Can reuse base `Validator` methods
- Pure functions (no side effects)

### 4. Executor (Orchestration)
- Implements `_find_alerts()` abstract method
- Uses `get_loop_setup()` and `set_window_context()` from base
- Tracks steps with `next_step()` and `next_validation()`
- Leverages Analyzer and Validator
- Logs all operations
- Creates `AlertData` objects

### 5. Initialization
- Exports all classes
- Simple `__all__` list

---

## ✅ Quality Standards Compliance

### Code Quality
- ✅ **Type Hints**: 100% (all parameters and returns)
- ✅ **Docstrings**: Google style with 7 sections
- ✅ **PEP 8**: All standards followed
- ✅ **Line Length**: Max 79 characters
- ✅ **Imports**: Organized (stdlib, third-party, local)
- ✅ **Enums**: All categorical values use enums (no magic strings)
- ✅ **Error Handling**: Graceful failures with logging
- ✅ **Static Methods**: All Analyzer/Validator methods are static
- ✅ **No Overrides**: Never overrides `run()` method

### Architecture Compliance
- ✅ Implements `_find_alerts()` hook (not `run()`)
- ✅ Uses base class utilities (get_loop_setup, set_window_context)
- ✅ Follows EAV (Executor-Analyzer-Validator) pattern
- ✅ Proper Layer 4 integration
- ✅ Matches existing approach patterns
- ✅ Consistent with VRA, STRONG_CANDLE, etc.

---

## 📚 Reference Materials Reviewed

### Existing Implementations
- ✅ VRA Executor (most similar - volume + trend analysis)
- ✅ STRONG_CANDLE (simpler validation flow reference)
- ✅ Base Executor class (abstract methods & utilities)
- ✅ Base Analyzer class (common calculations)
- ✅ Base Validator class (common validations)

### Architecture Documentation
- ✅ DESIGN_PATTERNS_GUIDE.md
- ✅ CODE_QUALITY_STANDARDS.md
- ✅ LAYER_4_APPROACH_EXECUTION architecture
- ✅ EAV_PATTERN_STEP_BY_STEP.md

---

## 🚀 Next Steps

### Step 1: Review & Approve
- [ ] Review all 3 analysis documents
- [ ] Confirm all validations are clear
- [ ] Verify configuration parameters
- [ ] Approve implementation plan

### Step 2: Code Generation
Once approved, generate:
1. **settings.py** - Configuration file
2. **analyzer.py** - Calculation functions
3. **validator.py** - Validation functions
4. **executor.py** - Orchestration logic
5. **__init__.py** - Module initialization

### Step 3: Integration
- Add `Approach.ANCHOR_SIGNAL_CANDLE` to constants
- Add ASC config to `signal_settings.py`
- Register ASC in approach factory/coordinator

### Step 4: Testing
- Unit tests for all methods
- Integration tests for complete flow
- Validation with sample data
- Code quality verification

### Step 5: Documentation
- API documentation
- Configuration guide
- Usage examples
- Case studies

---

## 📖 Documents Generated

### Document 1: Analysis & Design
**File**: `ANCHOR_SIGNAL_CANDLE_APPROACH_ANALYSIS.md`
- Detailed validation logic
- Configuration parameters
- Clarification questions (ALL ANSWERED)
- ~400 lines

### Document 2: Visual Reference
**File**: `ANCHOR_SIGNAL_CANDLE_VISUAL_REFERENCE.md`
- ASCII diagrams for each validation
- Flowchart of execution sequence
- Configuration examples
- ~250 lines

### Document 3: Implementation Plan (THIS FILE)
**File**: `ANCHOR_SIGNAL_CANDLE_IMPLEMENTATION_PLAN.md`
- Phase-by-phase code structure
- Method signatures with pseudocode
- Quality standards checklist
- ~700 lines

**Total Documentation**: ~1,350 lines of specification

---

## ⚡ Quick Reference

### The 4 Core Validations

**1️⃣ Window Analysis**
- Check: window_size >= min_size_price_window
- Return: (window_size, trend)

**2️⃣ Anchor Candle**
- Check: anchor_body >= min_size_candle AND anchor_body >= multiplier_size × average_body
- Return: anchor_candle

**3️⃣ Signal Candle**
- Check: signal_volume >= min_volume AND signal_volume >= multiplier_volume × average_volume
- Check: signal_index >= anchor_index
- Return: signal_candle

**4️⃣ Alert Candle**
- Check: alert_index >= signal_index
- Check: body_size > 0 (no doji)
- Check: alert has extremes (HIGH/CLOSE for uptrend, LOW/CLOSE for downtrend)
- Check: wick_percentage in [min_percentage, max_percentage]
- Return: True or None

---

## 🎯 Success Criteria

Code generation is successful when:

- ✅ All 5 files created with proper structure
- ✅ All methods implemented following pseudocode
- ✅ All type hints present (100%)
- ✅ All docstrings complete (Google style)
- ✅ All validations follow analysis document logic
- ✅ All code passes style checks (PEP 8)
- ✅ All integration tests pass
- ✅ Approach works with coordinator pipeline
- ✅ Alerts generated correctly (REVERSAL signals)
- ✅ Configuration loads from signal_settings.py

---

## 📞 Questions or Clarifications?

If anything is unclear:
1. Review the visual reference guide
2. Check the analysis document
3. Refer to similar implementations (VRA)
4. Ask for specific clarification

**Current Status**: ✅ READY TO GENERATE CODE

---

**Generated**: April 10, 2026  
**Approach Name**: ANCHOR_SIGNAL_CANDLE (ASC)  
**Status**: Production-Ready Specification Complete

