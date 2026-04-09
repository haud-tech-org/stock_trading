# Documentation Update Prompt for Feature Extensions

**Purpose:** Standardized procedure for updating documentation when adding/updating features  
**Created:** April 8, 2026  
**Status:** Ready to use  

---

## When to Use This Prompt

Use this prompt when:
- ✅ Adding new executor/approach
- ✅ Adding new data provider
- ✅ Adding new notification channel
- ✅ Extending performance metrics
- ✅ Any architectural change
- ✅ Modifying existing features

---

## DOCUMENTATION UPDATE TEMPLATE

### INSTRUCTION FOR COPILOT:
```
A new feature is being added to the stock trading system. 
Update all documentation according to this comprehensive procedure.
```

---

## FEATURE INFORMATION (Fill This Out)

```
- Feature Type: [EXECUTOR | DATA_PROVIDER | NOTIFICATION | METRICS | OTHER]
- Feature Name: [Exact name, e.g., "RSI_DIVERGENCE" executor]
- File Location(s): [Actual source file paths]
- Feature Purpose: [What does it do?]
- Integration Points: [What existing components does it interact with?]
- Configuration Required: [Any new settings needed?]
- Dependencies: [What must exist for this to work?]
```

---

## PHASE 1 DOCUMENTATION UPDATES

### 1. DEEP_DIVE_FINDINGS.md
- [ ] Add feature to appropriate section (1.1-1.14 for components)
- [ ] Include: Purpose, Location, Key Methods, Integration Points
- [ ] Update statistics (Total components count)
- [ ] Update cross-references
- [ ] Add to index/table of contents

### 2. VISUAL_GUIDE.md
- [ ] Add ASCII diagram in appropriate section
- [ ] Show: Data flow, Component interactions, Configuration points
- [ ] Add to relevant section (8-10 for providers, 11-13 for notifications, etc.)
- [ ] Update section count if adding new category
- [ ] Add to navigation table of contents

### 3. SUMMARY.md
- [ ] Update executive summary if significant change
- [ ] Add to "Key Findings" section if architectural impact
- [ ] Update statistics: "Components: 14 → 15"
- [ ] Verify correctness against new feature

### 4. INDEX.md
- [ ] Add new feature to quick lookup table
- [ ] Add to "Cross-references" section
- [ ] Update statistics
- [ ] Add to "By Component Type" section

### 5. CRITICAL_ARCHITECTURAL_DECISION.md
- [ ] Add note if feature affects DEVELOPMENT mode removal
- [ ] Add constraint if feature has LIVE/REPLAY implications
- [ ] Document any architectural decisions needed

### 6. AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md
- [ ] Add technical details about feature
- [ ] Include: Methods, parameters, return values
- [ ] Add code example (if applicable)
- [ ] Update "Extension Points" section
- [ ] Add to "All Components" table

---

## PHASE 2 DOCUMENTATION UPDATES

### Extension Guide (Choose Appropriate One)

#### IF Adding EXECUTOR:
File: `EXECUTOR_IMPLEMENTATION_GUIDE.md`
- [ ] Add as "Example 2" or "Example 3" (after STRONG_CANDLE)
- [ ] Include: Step-by-step implementation, Code snippets, Testing
- [ ] Update statistics: "Examples: 1 → 2"

#### IF Adding DATA_PROVIDER:
File: `DATA_PROVIDER_EXTENSION_GUIDE.md`
- [ ] Add as "Example 2" (after Vietstock)
- [ ] Include: Provider interface, Integration, Configuration
- [ ] Update statistics: "Examples: 1 → 2"

#### IF Adding NOTIFICATION:
File: `NOTIFICATION_CHANNEL_EXTENSION_GUIDE.md`
- [ ] Add as "Example 2" or "Example 3"
- [ ] Include: Channel interface, Configuration, Error handling
- [ ] Update statistics: "Examples: 2 → 3" or "Examples: 3 → 4"

#### IF Extending METRICS:
File: `PERFORMANCE_METRICS_EXTENSION_GUIDE.md`
- [ ] Add as new analysis type
- [ ] Include: Calculation method, ML integration, Configuration
- [ ] Update statistics: "Analysis Types: X → X+1"

### Quick Reference Files

#### IF Adding EXECUTOR:
File: `EXECUTOR_QUICK_REFERENCE.md`
- [ ] Add code snippet for new executor
- [ ] Add checklist item
- [ ] Update "Common Patterns" if new pattern introduced

#### IF Adding DATA_PROVIDER:
File: `DATA_PROVIDER_QUICK_REFERENCE.md`
- [ ] Add provider instantiation code
- [ ] Add to integration checklist

#### IF Adding NOTIFICATION:
File: `NOTIFICATION_QUICK_REFERENCE.md`
- [ ] Add channel setup code
- [ ] Add configuration example

#### IF Extending METRICS:
File: `CONFIGURATION_QUICK_REFERENCE.md` (if config change)
- [ ] Add new configuration option
- [ ] Add to examples

### Other Phase 2 Documents

#### API_DOCUMENTATION.md
- [ ] Add new public APIs (if any)
- [ ] Document parameters and return types
- [ ] Add to relevant section (Executors, Providers, Channels, etc.)
- [ ] Include error codes if applicable
- [ ] Add example usage

#### TROUBLESHOOTING_GUIDE.md
- [ ] Add "Common Issues" for new feature
- [ ] Add debugging techniques
- [ ] Add mode-specific troubleshooting (if LIVE/REPLAY specific)
- [ ] Update statistics: "Issues: X → X+N"

#### OPERATIONS_DEPLOYMENT_GUIDE.md (if operational impact)
- [ ] Add configuration steps
- [ ] Add to "Pre-deployment Checklist"
- [ ] Add monitoring/health check (if needed)
- [ ] Add to "Scaling Considerations" (if applicable)

---

## COMPREHENSIVE UPDATES

### Architectural Refactoring Pattern (Consolidating Multiple Components)

When refactoring to consolidate multiple similar components into one:

1. **Code Changes:**
   - [ ] Create new unified component with dictionary/list-based state
   - [ ] Keep old files as deprecated wrappers (for backward compatibility)
   - [ ] Update all imports in dependent files
   - [ ] Update configuration (remove old, add new settings)

2. **Documentation Changes:**
   - [ ] DEEP_DIVE_FINDINGS.md: Update component section with new responsibilities
   - [ ] VISUAL_GUIDE.md: Update diagrams and ASCII art
   - [ ] PHASE1_PHASE2_ALIGNMENT.md: Update component tables
   - [ ] Extension guides: Add section explaining new pattern
   - [ ] Quick references: Show state structure and usage
   - [ ] Troubleshooting: Add known issues during/after consolidation

3. **Verification:**
   - [ ] All old imports migrated to new component
   - [ ] Configuration settings updated (old removed, new added)
   - [ ] Backward compatibility wrappers working (with deprecation warnings)
   - [ ] State structure documented (dict/list keys and usage)
   - [ ] Check order documented (if multiple checks involved)
   - [ ] Auto-reset/state cleanup behavior documented

### README.md Files

#### PHASE2/README.md:
- [ ] Add to "Quick Start" section (if major feature)
- [ ] Add to "What Each File Contains" table
- [ ] Update statistics: "Total files: 13 → X"
- [ ] Update "Finding What You Need" Q&A section
- [ ] Add to "Quick Help" table

#### PHASE1/README.md:
- [ ] Add to component list (if component-level)
- [ ] Update navigation if new section needed
- [ ] Update statistics

#### Root ARCHITECTURE/README.md (if significant):
- [ ] Add learning path if new skill needed
- [ ] Update prerequisites
- [ ] Add example reference

### Supporting Documents

- [ ] If new component type: Create type-specific document
- [ ] If architectural change: Update CRITICAL_ARCHITECTURAL_DECISION.md
- [ ] If configuration change: Create configuration guide
- [ ] If performance impact: Update PERFORMANCE_METRICS_EXTENSION_GUIDE.md

### Cross-References

- [ ] Search existing docs for similar features
- [ ] Add "See also: New Feature" sections
- [ ] Update "Related Documentation" sections
- [ ] Verify all links working and relative paths correct

### Documentation Consistency

- [ ] Check naming consistency (CamelCase for executors, etc.)
- [ ] Verify code examples compile/follow patterns
- [ ] Ensure audience-specific versions all updated
- [ ] Confirm statistics accurate

---

## VERIFICATION CHECKLIST

Before finalizing, verify:

- [ ] Source code location documented (exact file path)
- [ ] Feature purpose clearly explained
- [ ] How it integrates with existing system documented
- [ ] Configuration parameters documented (with defaults)
- [ ] Code examples provided (copy-paste ready)
- [ ] All cross-references added and verified
- [ ] Statistics updated throughout
- [ ] No broken links in any document
- [ ] PHASE1 docs updated (DEEP_DIVE_FINDINGS, VISUAL_GUIDE, etc.)
- [ ] PHASE2 docs updated (Extension guide + quick reference)
- [ ] README files updated with statistics
- [ ] Audience-specific versions all consistent
- [ ] Real examples used (not hypothetical)
- [ ] LIVE/REPLAY implications documented
- [ ] Testing procedures documented
- [ ] Error cases documented
- [ ] All audience versions reviewed for accuracy

---

## ORGANIZATION STRUCTURE TO MAINTAIN

When adding features, maintain this directory organization:

```
docs/ARCHITECTURE/
├── PHASE1/
│   ├── README.md (✅ update statistics)
│   ├── DEEP_DIVE_FINDINGS.md (✅ add feature)
│   ├── VISUAL_GUIDE.md (✅ add diagram)
│   ├── SUMMARY.md (✅ update if significant)
│   ├── INDEX.md (✅ add to lookup)
│   ├── CRITICAL_ARCHITECTURAL_DECISION.md (✅ add constraints if needed)
│   ├── AUDIENCE_SPECIFIC_ARCHITECTURE/
│   │   ├── ARCHITECTURE_FOR_CLIENTS.md (✅ add if user-facing)
│   │   ├── ARCHITECTURE_FOR_OPERATIONS.md (✅ add if operational)
│   │   └── ARCHITECTURE_FOR_DEVELOPERS.md (✅ add technical details)
│   └── [Other supporting docs...]
│
├── PHASE2/
│   ├── README.md (✅ update statistics + navigation)
│   ├── [EXTENSION_GUIDE.md] (✅ add if new feature type)
│   ├── [QUICK_REFERENCE.md] (✅ add snippets)
│   ├── CONFIGURATION_QUICK_REFERENCE.md (✅ add config options)
│   ├── API_DOCUMENTATION.md (✅ add API endpoints)
│   ├── TROUBLESHOOTING_GUIDE.md (✅ add known issues)
│   ├── OPERATIONS_DEPLOYMENT_GUIDE.md (✅ add deployment steps)
│   ├── METRIC_TRADE_CALCULATION_REPORTS/
│   │   └── [Real-world examples with new feature] (✅ add if relevant)
│   └── [Other guides...]
│
├── AUDIENCE_SPECIFIC_ARCHITECTURE/
│   ├── ARCHITECTURE_FOR_CLIENTS.md (✅ update)
│   ├── ARCHITECTURE_FOR_OPERATIONS.md (✅ update)
│   └── ARCHITECTURE_FOR_DEVELOPERS.md (✅ update)
│
└── README.md (✅ update if needed)
```

---

## SPECIFIC EXAMPLES

### Example 1: Adding New Executor (e.g., "RSI_DIVERGENCE")

**Files to update: 10**

1. `PHASE1/DEEP_DIVE_FINDINGS.md` - Add as component 1.7 (after VOLUME_SPIKE)
2. `PHASE1/VISUAL_GUIDE.md` - Add diagram in section 2-7 executors
3. `PHASE1/SUMMARY.md` - Update: "14 components → 14 components" (or add to list)
4. `PHASE1/INDEX.md` - Add to executors table
5. `PHASE1/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md`
   - Add code example (3-5 lines showing class structure)
   - Add to "Extension Points" section
   - Add to "All Executors" comparison table
6. `PHASE2/EXECUTOR_IMPLEMENTATION_GUIDE.md` - Add as "Example 2: RSI_DIVERGENCE"
7. `PHASE2/EXECUTOR_QUICK_REFERENCE.md` - Add code snippet
8. `PHASE2/API_DOCUMENTATION.md` - Add to Executors section
9. `PHASE2/README.md` - Update example count in statistics
10. `PHASE2/TROUBLESHOOTING_GUIDE.md` - Add "RSI_DIVERGENCE not triggering" issue

**Time Estimate:** 2-2.5 hours

---

### Example 2: Unified Scheduler Refactoring (Consolidating Multiple Schedulers)

**Real-World Example:** Unifying separate `close_position_scheduler.py` and potential `order_reminder_scheduler.py` into single `unified_scheduler.py`

**Scenario:** Multiple notification schedulers have similar logic (state tracking, time-based checks, auto-reset). Rather than maintain separate files, consolidate into ONE scheduler with dictionary-based state.

**Files to update: 12**

1. `src/stockreports/notification/unified_scheduler.py` - Create new unified file (260+ lines)
   - Dictionary-based state: `{'alert': AlertNotification, 'sent': {'order_reminder': bool, 'close_position': bool}}`
   - Function: `update_latest_signal(notification)` - called when new BUY/SELL generated
   - Function: `check_and_notify(current_time)` - returns list of notifications to send
   - Checks in order: 1) Order Reminder (5 min), 2) Close Position (10 min)
   - Auto-resets state when both sent

2. `src/stockreports/config/signal_settings.py` - Update configuration
   - Remove: `CLOSE_POSITION_DELAY_MINUTES = 10` (old, unused)
   - Add: `SCHEDULED_REMINDER_ORDER_DELAY_MINUTES = 5` (new)
   - Add: `SCHEDULED_REMINDER_CLOSE_DELAY_MINUTES = 10` (new)

3. `src/stockreports/notification/close_position_scheduler.py` - Deprecate old file
   - Keep wrapper functions for backward compatibility (deprecation warnings)
   - Document migration path to unified_scheduler

4. `src/stockreports/alert/symbol_alerter.py` - Update imports
   - Change: `from src.stockreports.notification.close_position_scheduler import check_and_notify`
   - To: `from src.stockreports.notification.unified_scheduler import check_and_notify`

5. `src/stockreports/notification/notification_manager.py` - Update imports
   - Change: `from src.stockreports.notification.close_position_scheduler import update_latest_signal`
   - To: `from src.stockreports.notification.unified_scheduler import update_latest_signal`

6. `PHASE1/DEEP_DIVE_FINDINGS.md` - Update component documentation
   - Update section 1.6 from "Close Position Scheduler" to "Unified Scheduler"
   - Add: New responsibilities (handles both order reminder + close position)
   - Add: State structure with dictionary showing 'sent' keys
   - Add: Both public functions with updated signatures
   - Add: Sequence diagram showing check order (reminder first, close position second)

7. `PHASE1/VISUAL_GUIDE.md` - Update diagram
   - Update section 9 (Component Responsibility Map)
   - Replace: `ClosePositionScheduler` with `UnifiedScheduler`
   - Add ASCII showing dictionary state: `{'alert': ..., 'sent': {'order_reminder': bool, 'close_position': bool}}`

8. `PHASE1/PHASE1_PHASE2_ALIGNMENT.md` - Update component reference
   - Update table: Replace `ClosePositionScheduler` → `UnifiedScheduler`
   - Note: Now handles 2 notification types (order reminder + close position)

9. `PHASE2/NOTIFICATION_CHANNEL_EXTENSION_GUIDE.md` - Add new section
   - Add section: "Understanding the Unified Scheduler Pattern"
   - Show dictionary-based state management approach
   - Show how to extend for new notification types (add new key to 'sent')
   - Include complete code example of dictionary state

10. `PHASE2/NOTIFICATION_QUICK_REFERENCE.md` - Add scheduler code
    - Add code snippet showing how scheduler is called
    - Show state structure and how to interpret it
    - Add example of extending for new notification type

11. `PHASE2/TROUBLESHOOTING_GUIDE.md` - Add known issues
    - "Order Reminder and Close Position both sending at same time"
    - "Scheduler state not resetting when new signal arrives"
    - "Notification delays not working as expected"

12. `PHASE2/README.md` - Update statistics
    - Note new unified scheduler pattern
    - Update: "Notification Scheduling: Previously 1 scheduler → Now 1 unified scheduler (2 notification types)"

**Code Pattern to Document (Unified Scheduler):**
```python
# Module-level dictionary state
_scheduled_state = {
    'alert': None,
    'sent': {
        'order_reminder': False,
        'close_position': False
    }
}

# Called when new BUY/SELL signal generated
def update_latest_signal(notification: AlertNotification) -> None:
    global _scheduled_state
    _scheduled_state = {
        'alert': notification,
        'sent': {'order_reminder': False, 'close_position': False}
    }

# Called in main loop to check what to send
def check_and_notify(current_time: datetime) -> List[AlertNotification]:
    # Check 1: Order Reminder (5 min delay)
    # Check 2: Close Position (10 min delay)
    # Auto-reset when both sent
    return notifications_to_send

# Manual reset if needed
def reset_state() -> None:
    global _scheduled_state
    _scheduled_state = {'alert': None, 'sent': {...}}
```

**Time Estimate:** 2-3 hours (includes refactoring code + documenting pattern)

**Key Documentation Points:**
- ✅ Dictionary-based state advantages (extensible for new notification types)
- ✅ Sequential checking order (reminder before close position)
- ✅ Auto-reset behavior (when both notifications sent)
- ✅ Configuration-driven delays (easy to adjust without code changes)
- ✅ Backward compatibility (old imports still work with deprecation warnings)

---

### Example 3: Adding New Data Provider (e.g., "CoinGecko")

**Files to update: 10**

1. `PHASE1/DEEP_DIVE_FINDINGS.md` - Add as component 1.11 (after BinanceCCXT)
2. `PHASE1/VISUAL_GUIDE.md` - Add diagram in section 8-10 data providers
3. `PHASE1/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md`
   - Add provider class structure
   - Add to "Data Providers" table
4. `PHASE2/DATA_PROVIDER_EXTENSION_GUIDE.md` - Add as "Example 2: CoinGecko"
5. `PHASE2/DATA_PROVIDER_QUICK_REFERENCE.md` - Add instantiation code
6. `PHASE2/API_DOCUMENTATION.md` - Add CoinGeckoProvider to Providers section
7. `PHASE2/CONFIGURATION_QUICK_REFERENCE.md` - Add CoinGecko configuration
8. `PHASE2/OPERATIONS_DEPLOYMENT_GUIDE.md` - Add CoinGecko setup steps
9. `PHASE2/README.md` - Update statistics
10. `PHASE2/TROUBLESHOOTING_GUIDE.md` - Add CoinGecko connection issues

**Time Estimate:** 2-2.5 hours

---

### Example 3: Adding New Notification Channel (e.g., "Discord")

**Files to update: 10**

1. `PHASE1/DEEP_DIVE_FINDINGS.md` - Add as component 1.13 (after Ntfy)
2. `PHASE1/VISUAL_GUIDE.md` - Add diagram in section 11-13 notifications
3. `PHASE1/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_CLIENTS.md`
   - Add Discord to notification options
4. `PHASE1/AUDIENCE_SPECIFIC_ARCHITECTURE/ARCHITECTURE_FOR_DEVELOPERS.md`
   - Add Discord channel implementation
5. `PHASE2/NOTIFICATION_CHANNEL_EXTENSION_GUIDE.md` - Add as "Example 3: Discord"
6. `PHASE2/NOTIFICATION_QUICK_REFERENCE.md` - Add Discord setup code
7. `PHASE2/CONFIGURATION_QUICK_REFERENCE.md` - Add Discord token configuration
8. `PHASE2/API_DOCUMENTATION.md` - Add Discord channel to Notifications
9. `PHASE2/OPERATIONS_DEPLOYMENT_GUIDE.md` - Add Discord webhook setup
10. `PHASE2/README.md` - Update notification channel count

**Time Estimate:** 2-2.5 hours

---

## EXECUTION STEPS (6 Steps, 2-3 Hours Total)

### Step 1: Identify Feature Type & Affected Files (5 min)
- [ ] Determine: Executor, Provider, Notification, Metrics, or Other
- [ ] List all files to update
- [ ] Check current documentation structure

### Step 2: Update PHASE 1 Documents (30-45 min)
- [ ] DEEP_DIVE_FINDINGS.md: Add component details
- [ ] VISUAL_GUIDE.md: Add diagram and flow
- [ ] INDEX.md: Add to lookup
- [ ] Audience-specific docs: Add technical/business details

### Step 3: Update PHASE 2 Documents (45-60 min)
- [ ] Extension guide: Add step-by-step example
- [ ] Quick reference: Add code snippet
- [ ] API documentation: Add endpoints/methods
- [ ] Configuration reference: Add new parameters
- [ ] Troubleshooting: Add known issues

### Step 4: Update Navigation & Statistics (15-20 min)
- [ ] Update all README.md files
- [ ] Update statistics: file counts, component counts, lines
- [ ] Add to "Quick Help" sections
- [ ] Add to "Finding What You Need" sections

### Step 5: Verification & Cross-References (15-20 min)
- [ ] Run search to verify all references updated
- [ ] Check all links working
- [ ] Verify statistics accurate
- [ ] Ensure no contradictory information

### Step 6: Quality Assurance (10-15 min)
- [ ] Read through audience-specific versions
- [ ] Verify consistency across all documents
- [ ] Check code examples for correctness
- [ ] Ensure organization/structure maintained

---

## QUALITY CRITERIA

✅ Feature documented in all relevant places  
✅ All statistics updated accurately  
✅ All cross-references working and current  
✅ Code examples accurate and testable  
✅ PHASE 1 & PHASE 2 both updated  
✅ All 3 audience versions consistent  
✅ Real examples used (not hypothetical)  
✅ No broken links  
✅ Professional formatting maintained  
✅ Clear and accessible to target audience  

---

## FINAL CHECKLIST BEFORE COMMITTING

- [ ] DEEP_DIVE_FINDINGS.md updated with new component
- [ ] VISUAL_GUIDE.md diagram added and ASCII correct
- [ ] All audience-specific docs reviewed for consistency
- [ ] All README.md statistics updated
- [ ] All extension guides have concrete example
- [ ] All quick references have code snippet
- [ ] Troubleshooting guide has known issues
- [ ] No broken links (verified with grep search)
- [ ] Line counts updated in statistics
- [ ] File organization maintained
- [ ] Professional tone throughout
- [ ] Ready for production documentation

---

## DOCUMENTATION UPDATE COMPLEXITY MATRIX

| Feature Type | Phase 1 Files | Phase 2 Files | Time Est. | Complexity |
|---|---|---|---|---|
| New Executor | 3 files | 3 files | 2-2.5h | Medium |
| New Data Provider | 3 files | 3 files | 2-2.5h | Medium |
| New Notification | 3 files | 3 files | 2-2.5h | Medium |
| Unify Schedulers | 5 files | 2 files | 2-3h | Medium |
| Extend Metrics | 2 files | 3 files | 1.5-2h | Low-Medium |
| Architectural Change | 5+ files | 4+ files | 3-4h | High |

---

## USAGE INSTRUCTIONS

### When to Use This Prompt:
1. ✅ Before implementing any new feature
2. ✅ After implementing feature (to document)
3. ✅ Before merging code to main branch
4. ✅ When architecture changes
5. ✅ When user requirements change

### How to Use:
1. Copy the relevant sections for your feature type
2. Fill in FEATURE INFORMATION
3. Follow DOCUMENTATION UPDATE CHECKLIST
4. Run through VERIFICATION CHECKLIST
5. Complete FINAL CHECKLIST

### Success Metrics:
- ✅ All documentation updated
- ✅ Statistics accurate
- ✅ Cross-references verified
- ✅ Code examples working
- ✅ No broken links
- ✅ Professional formatting
- ✅ Ready for production

---

**Created:** April 8, 2026  
**Purpose:** Standardized documentation update procedure  
**Status:** ✅ Ready to use  

See **DOCUMENTATION_WORK_ANALYSIS.md** for complete context and background.
