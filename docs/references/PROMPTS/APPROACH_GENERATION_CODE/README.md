# Documentation Index

## 🤖 AI CODE GENERATION

### **AI Approach Generation Prompt** ⭐ **CRITICAL**
- **`AI_APPROACH_GENERATION_PROMPT.md`** - Comprehensive prompt for AI to automatically generate end-to-end production-ready approach code
  - Part 1: Approach Specification Template (define your trading rules)
  - Part 2: Architecture Context (pattern requirements, base classes, folder structure)
  - **Part 2.5: Best Practices & Real-World Patterns** ← Links to case studies
  - Part 3: Implementation Details (code templates for all 4 files)
  - Part 4: Imports & Dependencies (all required imports and constants)
  - Part 5: Testing Requirements (unit test structure)
  - Execution Instructions for AI
  - Complete Validation Checklist
  - **USE THIS**: Fill in your approach spec and provide to AI for automatic code generation

---

## 🔗 Integration with Case Studies

The templates and code generation instructions in this folder are based on patterns documented in **`docs/REFERENCES/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md`**.

**Read the case studies to understand**:
- WHY patterns exist (not just what-to-do)
- Real-world issues that led to each pattern
- How patterns evolved through actual implementation
- Edge cases and gotchas to avoid

**Most relevant cases for code generation**:
- **Case Study 1**: Logging & context management (Executor implementation)
- **Case Study 3**: Shared utilities pattern (VRA refactoring example)
- **Case Study 7**: Type safety & enum handling (STRONG_CANDLE best practices)

See **`AI_APPROACH_GENERATION_PROMPT.md` PART 2.5** for detailed references to each case with code examples.

---

## 📁 Directory Structuredex

## 🤖 AI CODE GENERATION

### **AI Approach Generation Prompt** � **CRITICAL**
- **`AI_APPROACH_GENERATION_PROMPT.md`** - Comprehensive prompt for AI to automatically generate end-to-end production-ready approach code
  - Part 1: Approach Specification Template (define your trading rules)
  - Part 2: Architecture Context (pattern requirements, base classes, folder structure)
  - Part 3: Implementation Details (code templates for all 4 files)
  - Part 4: Imports & Dependencies (all required imports and constants)
  - Part 5: Testing Requirements (unit test structure)
  - Execution Instructions for AI
  - Complete Validation Checklist
  - **USE THIS**: Fill in your approach spec and provide to AI for automatic code generation

---

## �📁 Directory Structure

### `/ARCHITECTURE/`
System design and patterns (8 documents)
- ARCHITECTURE_OVERVIEW.md - System design
- ARCHITECTURE_VISUALIZATION.md - Visual diagrams
- DESIGN_PATTERNS_GUIDE.md - Pattern explanations
- EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md - Critical principle
- EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md - Quick reference
- ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md - Base methods
- ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md - Method lookup
- CODE_QUALITY_STANDARDS.md - Quality standards

### `/IMPLEMENTATION/`
Step-by-step implementation guides (2 documents)
- CREATING_NEW_APPROACH.md - 6-step guide with templates
- IMPLEMENTATION_BEST_PRACTICES.md - Tips and patterns

### `/development/`
Development process and technical documentation:
- `VERSION_HISTORY.md` - Complete project version history
- `CODEBASE_RESTRUCTURING.md` - Code reorganization process
- `DUPLICATE_DETECTION.md` - Enhanced duplicate detection implementation
- `LEGACY_CLEANUP.md` - Legacy code cleanup analysis
- `UTILS_MIGRATION.md` - Utils migration process
- `GITIGNORE_SETUP.md` - Git ignore configuration

### `/examples/`
Sample outputs and report examples:
- `sample_daily_analysis.md` - Example daily price analysis report
- `sample_symbol_summary.md` - Example symbol summary report  
- `sample_overview.md` - Example multi-symbol overview report

### `/archive/`
Historical documentation and completion markers:
- `RESTRUCTURING_COMPLETE.md` - Project restructuring completion record

## 🎯 Quick Access

### For AI Code Generation
1. Start: **`AI_APPROACH_GENERATION_PROMPT.md`**
2. Fill in: Part 1 (Approach Specification)
3. Provide to AI with request: "Generate the implementation"
4. AI generates: Complete 5-file approach implementation

### For Manual Implementation
1. Read: `/ARCHITECTURE/` documents
2. Reference: `/IMPLEMENTATION/CREATING_NEW_APPROACH.md`
3. Follow: 6-step guide with templates
4. Check: CODE_QUALITY_STANDARDS.md

### For Code Review
1. Check: `ARCHITECTURE/EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md`
2. Verify: `ARCHITECTURE/CODE_QUALITY_STANDARDS.md`
3. Review: Implementation against standards

### For Quick Principle Reminder
1. Read: `ARCHITECTURE/EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md` (2 min)

---

## 📊 Documentation Overview

- **Total Documents**: 12
- **Architecture Docs**: 8 (system design & patterns)
- **Implementation Docs**: 2 (step-by-step guides)
- **AI Generation Docs**: 1 (comprehensive prompt)
- **Total Lines**: ~6,000+

## 🎓 Use Cases

| Need | Use This |
|------|----------|
| Generate approach code automatically | `AI_APPROACH_GENERATION_PROMPT.md` |
| Understand system architecture | `/ARCHITECTURE/` documents |
| Implement approach manually | `/IMPLEMENTATION/CREATING_NEW_APPROACH.md` |
| Learn the critical principle | `ARCHITECTURE/EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md` |
| Check code quality | `ARCHITECTURE/CODE_QUALITY_STANDARDS.md` |
| Quick reference | `ARCHITECTURE/EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md` |

---

*Documentation Index Updated: March 12, 2026*
