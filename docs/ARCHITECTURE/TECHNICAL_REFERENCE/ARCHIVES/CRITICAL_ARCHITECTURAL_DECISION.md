# ⚠️ CRITICAL ARCHITECTURAL DECISION

**Date:** April 8, 2026  
**Status:** Active & Binding  
**Scope:** All Development Phases & All Code Changes

---

## Decision

### DEVELOPMENT MODE IS REMOVED

**Final Configuration:**
- ❌ DEVELOPMENT mode → **WILL BE REMOVED FROM CODEBASE**
- ✅ LIVE mode → Production-ready behavior
- ✅ REPLAY mode → Testing/debugging behavior

### Two-Mode System (Going Forward)

```
DEPLOYMENT MODE
├─ LIVE (production)
│  ├─ Time: Real system time
│  ├─ Data: Live API feeds
│  ├─ Report: reports/ directory
│  └─ Loop: Indefinite (until stopped)
│
└─ REPLAY (testing)
   ├─ Time: Simulated from DEBUG_REPLAY_START_TIME
   ├─ Data: Historical API data
   ├─ Report: reports_replay/ directory
   └─ Loop: Bounded to replay period
```

---

## Why This Matters

1. **Simplified Architecture**: Only one mode to maintain vs two
2. **Clearer Intent**: Code doesn't have legacy DEVELOPMENT paths
3. **Consistent Behavior**: All production code uses TimeSimulator
4. **Easier Testing**: All test scenarios use REPLAY mode
5. **Reduced Configuration**: Fewer settings to manage

---

## Implementation Checklist

**Technical Reference (Current):**
- ✅ Update all documentation to reflect LIVE/REPLAY only
- ✅ Remove any references to DEVELOPMENT mode
- ✅ Clarify that LIVE/REPLAY are determined by `DEBUG_REPLAY_START_TIME`

**Implementation Guides:**
- [ ] Review all code for DEVELOPMENT mode references
- [ ] Remove MODE setting if no longer needed
- [ ] Remove all development-specific code paths
- [ ] Update configuration system
- [ ] Test all LIVE/REPLAY scenarios

**Phase 3+:**
- [ ] Verify codebase cleanup
- [ ] Update deployment procedures
- [ ] Update all operational documentation

---

## Key Points to Remember

### ✅ What We Keep

- **LIVE Mode**: Production monitoring with real data, real time, indefinite operation
- **REPLAY Mode**: Testing with simulated time, bounded operation, replay directory storage
- **TimeSimulator**: Central control point for time behavior
- **DEBUG_REPLAY_START_TIME**: Configuration that determines LIVE vs REPLAY

### ❌ What We Remove

- **DEVELOPMENT Mode**: All development-specific code paths
- **MODE Setting**: If only used to switch DEVELOPMENT/DEPLOYMENT
- **Dual Code Paths**: Any conditional logic for DEVELOPMENT vs DEPLOYMENT
- **Legacy Development Logic**: File-based data loading for testing

---

## Critical Enforcement Points

These points MUST be checked in every phase:

1. **Documentation**: No references to DEVELOPMENT mode
2. **Code Review**: No MODE-based conditionals for DEVELOPMENT
3. **Configuration**: Only LIVE/REPLAY distinction via DEBUG_REPLAY_START_TIME
4. **Testing**: All tests use REPLAY mode with TimeSimulator
5. **Deployment**: Only LIVE or REPLAY configurations allowed

---

## Related Documentation

- Technical Reference: `/docs/ARCHITECTURE/TECHNICAL_REFERENCE/DEEP_DIVE_FINDINGS.md`
- Technical Reference: `/docs/ARCHITECTURE/TECHNICAL_REFERENCE/DEBUG_REPLAY_TIME_INVESTIGATION.md`
- Technical Reference: `/docs/ARCHITECTURE/TECHNICAL_REFERENCE/VISUAL_GUIDE.md`

---

**Status: BINDING DECISION - ENFORCE THROUGHOUT ALL PHASES**

