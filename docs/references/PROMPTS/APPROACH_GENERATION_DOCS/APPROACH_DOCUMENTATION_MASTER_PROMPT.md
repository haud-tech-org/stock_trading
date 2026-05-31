# Master Prompt for Approach Documentation

**Purpose**: Template for comprehensive, consistent, and accurate documentation of trading approaches  
**Template Version**: 1.0  
**Created**: March 30, 2026  
**Based on**: VRA approach complete documentation system

---

## 🎯 Master Prompt for Approach Documentation

Use this prompt to document any trading approach with the same level of completeness, accuracy, and consistency as VRA.

---

### **COMPREHENSIVE PROMPT TEMPLATE**

```
TASK: Complete Documentation Review and Alignment for [APPROACH_NAME] Approach

OBJECTIVE:
Review the [APPROACH_NAME] approach documentation and codebase to ensure 
perfect alignment, accuracy, and clarity. Create a clean, comprehensive 
documentation system that mirrors the actual implementation with:
- Main algorithm specification
- Visual architecture guide
- Detailed flow diagrams
- Navigation and index
All documents must be code-verified and mutually consistent.

SCOPE OF WORK:

1. CODEBASE REVIEW
   Location: src/stockreports/alert/approach/[APPROACH_NAME]/
   
   Files to analyze:
   - executor.py (main orchestration)
   - analyzer.py (calculation functions)
   - validator.py (validation functions)
   - settings.py (parameters and configuration)
   
   Review each file for:
   - Algorithm steps and sequence
   - Validation logic and order
   - Parameter usage and defaults
   - Data flow and transformations
   - Edge cases and error handling
   - Class variables and state management

2. DOCUMENTATION REVIEW
   Location: docs/APPROACHES/[APPROACH_NAME]/
   
   Files to review:
   - [APPROACH_NAME].md (main specification)
   - Any existing visual architecture docs
   - Any existing flow diagrams
   - Any related documentation
   
   Check for:
   - Accuracy against current code
   - Completeness of algorithm description
   - Clarity of parameter explanations
   - Alignment of diagrams with code
   - Missing or outdated information

3. VERIFICATION PROCESS
   
   For EACH algorithm step:
   ✓ Read documentation description
   ✓ Trace through actual code implementation
   ✓ Verify business logic matches
   ✓ Document exact line numbers
   ✓ Create/verify visual representation
   ✓ Provide concrete working examples
   
   For EACH parameter:
   ✓ Find in settings.py with default value
   ✓ Trace usage in code (which steps use it)
   ✓ Verify it's actually active (not dead code)
   ✓ Document impact and purpose
   ✓ Show in multiple documentation places
   ✓ Provide sensitivity/tuning guidance
   
   For EACH validation:
   ✓ Understand business purpose
   ✓ Locate exact code implementation
   ✓ Verify parameter usage
   ✓ Document in clear language
   ✓ Provide example scenarios
   ✓ Show what success/failure means
   
   For EACH diagram/visual:
   ✓ Trace through complete algorithm
   ✓ Verify data flow accuracy
   ✓ Check validation sequence
   ✓ Confirm all decision points
   ✓ Test with real examples
   ✓ Cross-reference with code

4. REQUIRED DOCUMENTS TO CREATE/UPDATE

   PRIMARY DOCUMENTS (Main focus):
   
   a) [APPROACH_NAME].md
      - Purpose: Complete algorithm specification
      - Contents:
        * Objective and approach overview
        * All parameters (name, default, description)
        * Step-by-step logic (all steps with all validations)
        * Flow diagram (Mermaid)
        * Key business logic explained
      - Verification: 100% code accuracy
      - Use: Main reference document
   
   b) [APPROACH_NAME]_VISUAL_ARCHITECTURE.md
      - Purpose: Implementation architecture and data flow
      - Contents:
        * Current architecture diagram
        * Detailed algorithm flows for each step
        * Complete data flow through execution
        * State transition diagrams
        * Signal/trend logic explained
        * Key concept clarifications
        * Prominence/strength calculations (if applicable)
        * Key characteristics table
      - Verification: Traced through code line-by-line
      - Use: Implementation details for developers
   
   c) [APPROACH_NAME]_VISUAL_FLOWS.md
      - Purpose: Step-by-step detailed walkthrough
      - Contents:
        * Each major concept explained with examples
        * Real validation scenarios
        * Actual data calculations
        * Step-by-step flows for each algorithm step
        * Timeline execution examples
        * Parameter sensitivity guide
        * Error handling and recovery paths
        * Complete examples with results
      - Verification: Every example traced through algorithm
      - Use: Step-by-step implementation guide
   
   d) INDEX.md
      - Purpose: Navigation guide and learning paths
      - Contents:
        * Overview of all documentation files
        * Use-case-based navigation (major user types)
        * Document relationships diagram
        * Quick reference tables (steps, parameters)
        * Code file locations mapped
        * Learning paths (4 different depths: 15min, 1hr, 2-3hrs, 4+hrs)
        * Document cross-references by topic
        * Maintenance schedule
      - Verification: All links accurate, all topics covered
      - Use: Help users find what they need

5. CONSISTENCY AND ACCURACY REQUIREMENTS

   CONSISTENCY MECHANISMS:
   ✓ Multiple document layers explaining same concepts
   ✓ Cross-references between all documents
   ✓ Code locations mapped in all documents
   ✓ Examples verified in multiple places
   ✓ Parameters referenced consistently
   
   ACCURACY VERIFICATION:
   ✓ Every step traced to exact code lines
   ✓ Every parameter verified active in settings
   ✓ Every validation documented with purpose
   ✓ Every example calculated/traced through algorithm
   ✓ Every diagram verified against code
   
   CLARITY STANDARDS:
   ✓ Jargon explained on first use
   ✓ Concepts explained at multiple levels
   ✓ Real examples provided for each major concept
   ✓ Visual diagrams support text explanations
   ✓ Code locations provided for deep dives

6. QUALITY ASSURANCE CHECKLIST

   Before finalizing, verify:
   
   [ ] All algorithm steps documented
   [ ] All parameters identified and documented
   [ ] All validations explained with purpose
   [ ] All code locations mapped
   [ ] All examples verified accurate
   [ ] All diagrams traced to code
   [ ] Cross-references all correct
   [ ] Navigation structure clear
   [ ] Learning paths defined
   [ ] Parameter sensitivity explained
   [ ] Error handling documented
   [ ] Consistency across all documents
   [ ] Clarity for different audiences
   [ ] Visual accuracy confirmed

7. DELIVERABLES

   FOCUS DOCUMENTS (Main):
   ✓ [APPROACH_NAME].md - Main specification (updated/verified)
   ✓ [APPROACH_NAME]_VISUAL_ARCHITECTURE.md - Architecture guide (new/updated)
   ✓ [APPROACH_NAME]_VISUAL_FLOWS.md - Detailed flows (new/updated)
   ✓ INDEX.md - Navigation guide (new)
   
   SUPPORTING DOCUMENTS (Optional, per project needs):
   - ALIGNMENT_REPORT.md - Code verification record
   - SUMMARY.md - Quick reference
   - README_FIRST.md - Quick start
   - COMPLETION_REPORT.md - Change history

8. OUTPUT FORMAT REQUIREMENTS

   For each document:
   - Use clear Markdown formatting
   - Include ASCII art diagrams where helpful
   - Use Mermaid diagrams for flow charts
   - Provide code references with line numbers
   - Include practical examples
   - Use tables for parameter/step summaries
   - Add cross-references to related sections
   - Provide quick-reference summaries

CRITICAL SUCCESS CRITERIA:

1. CODE ACCURACY
   - Every claim verifiable in code
   - No hypothetical or proposed features
   - All parameters actively used
   - All examples trace through actual algorithm
   - Line numbers accurate for current code

2. DOCUMENTATION CONSISTENCY
   - Same concepts explained same way across docs
   - No contradictions between documents
   - All cross-references work
   - Parameter names consistent
   - Step descriptions aligned

3. ACCESSIBILITY
   - Multiple entry points for different users
   - Navigation clear and organized
   - Concepts explained at multiple levels
   - Visual aids support text
   - Examples make concepts concrete

4. MAINTAINABILITY
   - Clear structure for future updates
   - Change tracking possible
   - Code-to-docs mapping preserved
   - Update process documented
   - Maintenance schedule defined

WHAT TO AVOID:

❌ Don't document proposed/theoretical changes
❌ Don't include outdated diagrams
❌ Don't make claims without code verification
❌ Don't use vague parameter descriptions
❌ Don't create examples without tracing algorithm
❌ Don't forget edge cases and error handling
❌ Don't ignore parameter sensitivity
❌ Don't create circular logic in validation sequence

APPROACH-SPECIFIC NOTES:

For [APPROACH_NAME] specifically:
- Identify main orchestration method: _find_alerts() or equivalent
- Map all major steps in sequence
- Understand data flow: inputs → processing → outputs
- Document all decision points
- Show parameter impact on each step
- Explain key concepts specific to approach
- Highlight any unique validation patterns

DELIVERABLE STRUCTURE:

Create in: docs/APPROACHES/[APPROACH_NAME]/

Final structure:
├── [APPROACH_NAME].md
│   └─ Main algorithm specification
├── [APPROACH_NAME]_VISUAL_ARCHITECTURE.md
│   └─ Implementation architecture
├── [APPROACH_NAME]_VISUAL_FLOWS.md
│   └─ Step-by-step detailed flows
├── INDEX.md
│   └─ Navigation and learning paths
└── [Supporting docs as needed]

SUCCESS METRICS:

✓ 100% code-to-documentation alignment
✓ All algorithm steps documented
✓ All parameters documented with examples
✓ All validations explained with purpose
✓ Multiple learning paths available
✓ Clear navigation structure
✓ Consistent format across documents
✓ Real examples verified through algorithm
✓ Code locations mapped
✓ Team can self-serve documentation needs

SUMMARY OF APPROACH:

You will create a documentation system that:
1. Reviews actual implementation code in detail
2. Traces every feature to source
3. Verifies all claims against code
4. Creates clear, multi-level documentation
5. Provides multiple entry points
6. Ensures perfect consistency
7. Maintains code-to-docs mapping
8. Enables future maintenance

This is NOT creating theoretical documentation.
This IS creating accurate, verified, practical guides
that serve actual developer and user needs.
```

---

## 📋 How to Use This Prompt

### For VRA (or any other approach):

**Step 1**: Copy the prompt above

**Step 2**: Replace placeholders:
- `[APPROACH_NAME]` → `RCM`, `MA_Crossover`, `MACD`, etc.
- `[APPROACH_NAME]` in file names

**Step 3**: Submit to AI assistant with query like:
```
Please review the [APPROACH_NAME] approach documentation and codebase.
Use the following master prompt to guide the work:

[paste the prompt above]

Follow all quality standards and verification requirements.
```

**Step 4**: Review deliverables against checklist

---

## 🔄 Customization Guide

### When approaching different approaches, customize:

**1. Algorithm Steps**
- Modify checklist items for approach-specific steps
- Add approach-specific parameters to verify

**2. Key Concepts**
- Add approach-specific concepts to explain
- Identify unique validation patterns

**3. Examples**
- Tailor examples to approach logic
- Use realistic data for calculations

**4. Parameters**
- List all parameters specific to approach
- Add sensitivity guidance for each

### Keep Consistent Across All Approaches:

✓ Structure (4 main documents)
✓ Verification process (trace to code)
✓ Documentation quality standards
✓ Navigation and learning paths
✓ Code mapping requirements
✓ Cross-reference methodology
✓ Quality assurance checklist

---

## 📊 Document Structure Template

### For Each Approach, Follow This Structure:

```
[APPROACH_NAME].md
├─ 1. Objective
├─ 2. Key Parameters (table)
├─ 3. Step-by-Step Logic (for each step)
└─ 4. Flow Diagram (Mermaid)

[APPROACH_NAME]_VISUAL_ARCHITECTURE.md
├─ Current Architecture (diagram)
├─ Algorithm Flows (for each step with details)
├─ Data Flow (full execution path)
├─ State Transitions (processing states)
├─ Key Concept (specific to approach)
└─ Characteristics Table

[APPROACH_NAME]_VISUAL_FLOWS.md
├─ Concept 1 (detailed walkthrough)
├─ Concept 2 (with examples)
├─ Step-by-Step Flows (for each step)
├─ Timeline Examples
├─ Parameter Sensitivity
├─ Error Handling
└─ Advanced Topics (if applicable)

INDEX.md
├─ Documentation Overview
├─ Use-Case Navigation
├─ Quick Reference Tables
├─ Code File Locations
├─ Learning Paths
├─ Cross-References
└─ Maintenance Guide
```

---

## ✅ Quality Verification Template

Use this checklist for each approach:

```
ALGORITHM COVERAGE:
[ ] All steps identified (count: ___)
[ ] Each step traced to code
[ ] All validations documented
[ ] All decision points explained
[ ] Data transformations shown
[ ] Edge cases identified
[ ] Error paths documented

PARAMETER COVERAGE:
[ ] All parameters identified (count: ___)
[ ] Each parameter in settings.py verified
[ ] Usage locations mapped
[ ] Defaults documented
[ ] Impact explained
[ ] Examples provided
[ ] Sensitivity guidance included

DOCUMENTATION QUALITY:
[ ] Main document complete
[ ] Architecture document complete
[ ] Flows document complete
[ ] Index document complete
[ ] All cross-references work
[ ] All code locations accurate
[ ] All examples verified
[ ] Visual diagrams accurate

CONSISTENCY:
[ ] Same concepts same way across docs
[ ] No contradictions found
[ ] Parameter names consistent
[ ] Step descriptions aligned
[ ] Examples trace through algorithm

ACCESSIBILITY:
[ ] Multiple entry points exist
[ ] Navigation clear
[ ] Different audience levels served
[ ] Visual aids support text
[ ] Examples make concepts concrete
```

---

## 🎯 Success Indicators

When documentation is ready for production:

✅ **Code Accuracy**: Every claim traced to source code  
✅ **Completeness**: All steps, parameters, validations documented  
✅ **Consistency**: All documents agree with each other  
✅ **Clarity**: Different audience levels served  
✅ **Navigation**: Users can find what they need  
✅ **Maintainability**: Structure supports future updates  
✅ **Examples**: All traced through actual algorithm  
✅ **Visual Accuracy**: All diagrams match code  

---

## 📞 Common Approach Categories

Use this prompt for approaches like:

- **RCM** (Reversal Confirmation Model)
- **MACD_Crossover**
- **MA_Crossover** (Moving Average)
- **RSI_Divergence**
- **Bollinger_Bands**
- **Stochastic_Signals**
- **Volume_Profile**
- Any other signal/alert approach

Each follows same documentation pattern, adapted for approach-specific logic.

---

## 🚀 Getting Started

To document a new approach:

1. **Copy this prompt**
2. **Replace `[APPROACH_NAME]` placeholder**
3. **Submit to AI assistant**
4. **Verify against quality checklist**
5. **Adjust if needed for approach specifics**
6. **Deploy final documentation**

---

**This prompt ensures consistent, accurate, comprehensive documentation across all trading approaches.**

