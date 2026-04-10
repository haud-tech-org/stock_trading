# Phase 1 Investigation - Documentation Index

**Date:** April 8, 2026  
**Status:** Complete  
**Three-Document Investigation Set**

---

## 📚 Quick Navigation

### Start Here: Executive Overview
👉 **[PHASE1_SUMMARY.md](./PHASE1_SUMMARY.md)** (5-10 min read)
- What was investigated
- Key findings (5 critical discoveries)
- Configuration examples
- How to use this information
- **Best for:** Quick understanding, decision-making

---

### Part A: Complete Architecture
👉 **[PHASE1_DEEP_DIVE_FINDINGS.md](./PHASE1_DEEP_DIVE_FINDINGS.md)** (20-30 min read)

**Sections:**
1. Executive Summary
2. Component Verification & Details (1.1-1.9)
   - SymbolAlertManager
   - SymbolAlerter (with multi-resolution support)
   - **ResolutionCoordinator** ⭐ NEW
   - DataServiceOrchestrator
   - PriceMovementAlerter
   - Executor Framework
   - Close Position Scheduler
   - NotificationManager
   - Supporting Components
3. Data Models
4. Critical Flow Details
5. Configuration Points
6. Clarifications & Corrections
7. Verified Data Flow
8. **Deployment Mode Architecture (with Time Sub-Modes)** ⭐ NEW
9. **Time Simulator Deep Dive** ⭐ NEW
10. Scope for Architecture Versions

**Best for:** Complete understanding, integration work, extension development

---

### Part B: Detailed Investigation
👉 **[DEBUG_REPLAY_START_TIME_INVESTIGATION.md](./DEBUG_REPLAY_START_TIME_INVESTIGATION.md)** (30-40 min read)

**Sections:**
1. Executive Summary
2. Configuration Hierarchy
3. Time Simulator Deep Dive
4. Main Monitoring Loop - Time-Dependent Behavior
5. Error Handling - Mode-Dependent Resilience
6. Report Storage - Mode-Driven Separation
7. System-Wide Impact Map
8. Complete Execution Flow (LIVE vs REPLAY)
9. Configuration Examples
10. Critical Insights
11. Code Paths Summary
12. Updated Phase 1 Understanding
13. Current Configuration Status

**Best for:** Deep understanding, troubleshooting, implementing features

---

## 🎯 Reading Recommendations by Role

### Product/Business (10-15 min)
1. PHASE1_SUMMARY.md - Key Findings section
2. PHASE1_DEEP_DIVE_FINDINGS.md - Scope Versions section
3. Executive Summary of each document

### QA/Testing (20-30 min)
1. PHASE1_SUMMARY.md - Complete
2. PHASE1_DEEP_DIVE_FINDINGS.md - Parts 8-9
3. DEBUG_REPLAY_START_TIME_INVESTIGATION.md - Parts 8-9

### Developers (45-60 min)
1. PHASE1_SUMMARY.md - Complete
2. PHASE1_DEEP_DIVE_FINDINGS.md - Complete
3. DEBUG_REPLAY_START_TIME_INVESTIGATION.md - Complete

### Architects/Tech Leads (60+ min)
1. All three documents in sequence
2. Study comparison tables and diagrams
3. Review all code locations and impacts

---

## 📋 Key Concepts Explained

### The Three Configuration Axes

```
┌──────────────────────────────┐
│ TIER 1: MODE                 │
│ - DEVELOPMENT (local files)  │
│ - DEPLOYMENT (API + time)    │
└──────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ TIER 2: DEBUG_REPLAY_START_TIME │  (DEPLOYMENT only)
│ - None (LIVE mode)           │
│ - Timestamp (REPLAY mode)    │
└──────────────────────────────┘
        ↓
┌──────────────────────────────┐
│ TIER 3: Approach Selection   │
│ - Symbol-specific config     │
│ - Default approaches         │
│ - Legacy ALERT_APPROACHES    │
└──────────────────────────────┘
```

### The Critical Discovery

❌ **Wrong:** DEBUG_REPLAY_START_TIME selects DEVELOPMENT/DEPLOYMENT mode

✅ **Right:** DEBUG_REPLAY_START_TIME controls LIVE vs REPLAY time behavior within DEPLOYMENT mode

**Impact:** Different error handling, different time progression, different report storage

---

## 🔍 Finding What You Need

### "How does the system start monitoring?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.1-1.2 (SymbolAlertManager, SymbolAlerter)

### "How does multi-resolution support work?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.2 (SymbolAlerter with multi-resolution) and Part 1.3 (ResolutionCoordinator)

### "How are approaches mapped to resolutions?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.3 (ResolutionCoordinator)
→ Configuration: `APPROACH_RESOLUTION_MAPPING` in signal_settings.py
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 9
→ DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Parts 2-3

### "How does LIVE mode differ from REPLAY mode?"
→ DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 8 (Complete Execution Flow)
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 8 (Sub-Mode Comparison Table)

### "Where are reports stored and why?"
→ DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 5 (Report Storage)
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 9 (Report Storage section)

### "How do executors work?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.5 (Executor Framework)

### "What happens when an error occurs?"
→ DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 4 (Error Handling)
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 9 (Error Recovery)

### "How is data fetched and cached?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.3 (DataServiceOrchestrator)

### "What are all the configuration options?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 4 (Configuration Points)
→ DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 9 (Configuration Examples)

### "How do notifications work?"
→ PHASE1_DEEP_DIVE_FINDINGS.md → Part 1.7 (NotificationManager)

---

## 📊 Quick Reference Tables

### Location of All Major Components

| Component | File | Lines |
|-----------|------|-------|
| SymbolAlertManager | `alert/symbol_alert_manager.py` | 312 |
| SymbolAlerter | `alert/symbol_alerter.py` | 491 |
| **ResolutionCoordinator** | **`coordination/resolution_coordinator.py`** | **180** |
| **TimeSimulator** | `utils/time_utils.py` | 35-80 |
| DataServiceOrchestrator | `data_services/orchestrator.py` | ~100 |
| PriceMovementAlerter | `alert/price_movement_alerter.py` | 252 |
| Executor (Base) | `alert/executor.py` | 345 |
| NotificationManager | `notification/notification_manager.py` | 113 |

See PHASE1_DEEP_DIVE_FINDINGS.md → Quick Reference for complete list

### Time Sub-Mode Comparison

| Aspect | LIVE | REPLAY |
|--------|------|--------|
| Config | `DEBUG_REPLAY_START_TIME = None` | `= "2026-04-08 09:05:00"` |
| Time | System time | Simulated |
| Loop | Indefinite | Until end_of_day |
| Non-hours | Sleep 900s | Advance simulator |
| Errors | Auto-restart | Exit |
| Reports | `reports/` | `reports_replay/` |

See PHASE1_DEEP_DIVE_FINDINGS.md → Part 8 for detailed table

### Configuration Decision Points

| Check Location | File | Line | Decides |
|---|---|---|---|
| TimeSimulator init | time_utils.py | 44 | LIVE vs REPLAY |
| is_running() | time_utils.py | 78 | Loop exit |
| Trading hours | symbol_alerter.py | 273 | Sleep vs advance |
| Error handling | symbol_alerter.py | 234 | Restart vs exit |
| Report path | report_utils.py | 54 | Directory selection |

See DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 10 for complete map

---

## ✨ Key Insights Highlighted

### Insight 1: Same Code, Different Behavior
All monitoring loop code is identical. TimeSimulator determines behavior.

### Insight 2: Resilience Pattern (LIVE)
```
Crash → Supervisor catches → Sleep → Restart
```

### Insight 3: Trading Hours (Mode-Aware)
```
LIVE:   time.sleep(900)          [Wait 15 min]
REPLAY: time_simulator.advance()  [Jump forward]
```

### Insight 4: Report Isolation
```
reports/        ← Production alerts
reports_replay/ ← Test simulations
```

See PHASE1_SUMMARY.md → Critical Insights for all 4

---

## 🔧 Implementation Guidance

### When Adding Time-Sensitive Features
1. Check TimeSimulator.is_replay_mode()
2. Test both LIVE and REPLAY paths
3. Update error handling if mode-dependent
4. Verify report directory usage

### When Implementing New Executors
1. Follow Executor abstract base class pattern
2. Implement _find_alerts(df, new_candle_count)
3. Add to SYMBOL_ALERT_APPROACHES config
4. Test in both modes

### When Troubleshooting
1. Check DEBUG_REPLAY_START_TIME value
2. Verify report directory matches
3. Check error logs in supervisor loop
4. Review TimeSimulator initialization

---

## 📖 Reading Order (Recommended)

**First Time (30 minutes):**
1. PHASE1_SUMMARY.md (10 min)
2. PHASE1_DEEP_DIVE_FINDINGS.md → Executive Summary + Parts 1-3 (15 min)
3. PHASE1_DEEP_DIVE_FINDINGS.md → Part 8 (5 min)

**Deep Dive (60+ minutes):**
1. All of PHASE1_SUMMARY.md
2. All of PHASE1_DEEP_DIVE_FINDINGS.md
3. All of DEBUG_REPLAY_START_TIME_INVESTIGATION.md

**Reference Use:**
- Use index to jump to specific sections
- Use comparison tables for quick lookups
- Use code location tables for implementation

---

## 📌 Current System State (April 8, 2026)

```python
MODE = "DEPLOYMENT"
DEBUG_REPLAY_START_TIME = "2026-04-08 09:05:00"
SYMBOLS = ["VN30F1M", "VN30"]
MONITORING_INTERVAL_SECONDS = 57
```

**Current Execution Mode:** REPLAY DEPLOYMENT
- Simulating April 8 trading day
- Starting at 09:05 local time
- Will process until 14:27 (end of last session)
- 57-second intervals between checks
- Alerts saved to `reports_replay/`

See DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 12 for details

---

## 🎓 Learning Path

### Beginner (Architecture Overview)
1. PHASE1_SUMMARY.md
2. PHASE1_DEEP_DIVE_FINDINGS.md - Executive Summary & Parts 1-3
3. Quick Reference tables in this index

### Intermediate (System Understanding)
1. All sections of PHASE1_DEEP_DIVE_FINDINGS.md
2. Parts 8-9 focus (Deployment & Time Simulator)
3. DEBUG_REPLAY_START_TIME_INVESTIGATION.md - Parts 1-5

### Advanced (Complete Mastery)
1. All three documents in full
2. Review all code locations
3. Study execution flow diagrams
4. Understand all decision points

---

## ❓ Frequently Asked Questions

**Q: Is DEBUG_REPLAY_START_TIME the same as MODE setting?**
A: No. MODE is DEVELOPMENT/DEPLOYMENT. DEBUG_REPLAY_START_TIME controls LIVE/REPLAY within DEPLOYMENT.
→ See PHASE1_SUMMARY.md → Finding 2

**Q: Why are there two report directories?**
A: To prevent production alerts from being polluted with test simulations.
→ See DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 5

**Q: How does the system know when to stop monitoring?**
A: TimeSimulator.is_running() checks if we've passed end_of_day (REPLAY) or returns True (LIVE).
→ See PHASE1_DEEP_DIVE_FINDINGS.md → Part 9 → TimeSimulator init

**Q: What happens if an error occurs in REPLAY mode?**
A: System exits immediately to maintain deterministic testing.
→ See DEBUG_REPLAY_START_TIME_INVESTIGATION.md → Part 4

**Q: How can I test new features without waiting real time?**
A: Use REPLAY mode with a timestamp. System processes instantly.
→ See PHASE1_SUMMARY.md → For Testing section

---

## 📞 Quick Help

**Lost?** → Start with PHASE1_SUMMARY.md

**Need architecture overview?** → PHASE1_DEEP_DIVE_FINDINGS.md

**Need detailed mechanism?** → DEBUG_REPLAY_START_TIME_INVESTIGATION.md

**Need specific answer?** → Use "Finding What You Need" section above

---

**Last Updated:** April 8, 2026  
**Status:** Phase 1 Complete - Ready for Phase 2  
**Next:** Architecture Documentation Generation Phase
