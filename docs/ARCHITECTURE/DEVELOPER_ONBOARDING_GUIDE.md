# Developer Onboarding Guide - Architecture Learning Path

**Welcome to the Stock Trading Alert System!** 🎯

This guide will help you understand the project architecture and codebase by reading the documentation in the optimal order. Follow this path to build a solid foundation.

---

## 📚 Reading Path Overview

### Phase 1: Understanding the Big Picture (30 minutes)
**Goal**: Get a high-level overview of the system

1. **START HERE** → [`ARCHITECTURE_OVERVIEW.md`](./ARCHITECTURE_OVERVIEW.md) (528 lines)
   - What the system does
   - Main components and their responsibilities
   - How data flows through the system
   - Key concepts you need to know

2. **THEN** → [`ARCHITECTURE_VISUALIZATION.md`](./ARCHITECTURE_VISUALIZATION.md) (743 lines)
   - Visual diagrams of the system
   - Component interaction flowcharts
   - Alert processing workflow
   - Reference these diagrams as you read other docs

### Phase 2: Core Architecture Patterns (45 minutes)
**Goal**: Understand the design patterns and abstract classes

3. **NEXT** → [`DESIGN_PATTERNS_GUIDE.md`](./DESIGN_PATTERNS_GUIDE.md) (629 lines)
   - Template Method pattern (the foundation of your approach system)
   - Strategy pattern (how different approaches work)
   - Factory pattern (how approaches are instantiated)
   - Why these patterns matter for this codebase

4. **THEN** → [`ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md`](./ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md) (234 lines)
   - Quick overview of base classes
   - Method signatures and purposes
   - What each class is responsible for
   - *This is a reference - use it while reading the deep dive*

5. **THEN** → [`ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md`](./ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md) (443 lines)
   - Deep technical dive into each base class
   - How abstract methods define contracts
   - How inheritance works in this system
   - Detailed method explanations

### Phase 3: Executor-Specific Knowledge (35 minutes)
**Goal**: Master the executor pattern and method implementation

6. **NEXT** → [`EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md`](./EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md) (488 lines)
   - Why abstract methods are essential
   - The executor architecture in detail
   - How to implement executors correctly
   - Common pitfalls and how to avoid them

7. **THEN** → [`EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md`](./EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md) (256 lines)
   - Quick reference for method implementation decisions
   - When to implement vs override
   - Decision matrix for each situation
   - *Quick reference - read when confused about which method to use*

### Phase 4: Code Quality and Standards (20 minutes)
**Goal**: Understand the code quality expectations

8. **FINALLY** → [`CODE_QUALITY_STANDARDS.md`](./CODE_QUALITY_STANDARDS.md) (697 lines)
   - Type hints requirements
   - Naming conventions
   - Docstring format and structure
   - Line length and formatting
   - Testing expectations
   - *This is your reference for writing code that fits the project*

---

## 🎯 Quick Navigation by Task

### If you want to...

**Understand the whole system quickly**
1. ARCHITECTURE_OVERVIEW.md (10 min)
2. ARCHITECTURE_VISUALIZATION.md (10 min)
3. DESIGN_PATTERNS_GUIDE.md (15 min)

**Create a new approach**
1. ARCHITECTURE_OVERVIEW.md (understand the system)
2. DESIGN_PATTERNS_GUIDE.md (understand patterns)
3. ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md (understand classes)
4. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (decide what to implement)
5. CODE_QUALITY_STANDARDS.md (write code correctly)
6. → Then read: `/docs/IMPLEMENTATION/CREATING_NEW_APPROACH.md`

**Understand the Executor system**
1. DESIGN_PATTERNS_GUIDE.md (understand Template Method)
2. EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md (executor details)
3. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (quick decisions)

**Learn code standards**
1. CODE_QUALITY_STANDARDS.md (read entire file)
2. ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md (see examples)
3. → Then read: `/docs/ARCHITECTURE/ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md` (reference)

**Debug or modify existing code**
1. ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md (understand the classes)
2. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (understand decisions)
3. The actual source code in `src/stockreports/alert/`

---

## 📖 Complete Reading Timeline

### For New Developers (Estimated 2.5-3 hours)

```
Phase 1: Big Picture (30 min)
├─ ARCHITECTURE_OVERVIEW.md ................... 20 min
└─ ARCHITECTURE_VISUALIZATION.md ............. 10 min

Phase 2: Architecture Patterns (45 min)
├─ DESIGN_PATTERNS_GUIDE.md .................. 20 min
├─ ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md . 10 min
└─ ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md .. 15 min

Phase 3: Executor Knowledge (35 min)
├─ EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md .... 20 min
└─ EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md 15 min

Phase 4: Quality Standards (20 min)
└─ CODE_QUALITY_STANDARDS.md ................. 20 min

TOTAL: ~2.5 hours for comprehensive understanding
```

---

## 🔍 Key Concepts by File

### ARCHITECTURE_OVERVIEW.md
- **System Purpose**: Real-time stock trading alert detection
- **Core Components**: Executor, Analyzer, Validator, Settings
- **Data Flow**: Market Data → Analyzer → Validator → Alert
- **Approach Pattern**: Multiple independent alert detection strategies
- **Key Learning**: How everything fits together

### ARCHITECTURE_VISUALIZATION.md
- **Alert Processing Flowchart**: Step-by-step execution sequence
- **Class Hierarchy Diagram**: Inheritance relationships
- **Component Interaction Diagram**: How modules talk to each other
- **Data Structure Diagram**: Alert object structure
- **Key Learning**: Visual understanding of the system

### DESIGN_PATTERNS_GUIDE.md
- **Template Method**: Base executor defines algorithm skeleton, subclasses implement steps
- **Strategy Pattern**: Each approach is a different strategy
- **Factory Pattern**: Creating executor/analyzer/validator instances
- **Inheritance**: How to use abstract classes effectively
- **Key Learning**: Why the code is structured this way

### ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md
- **Executor Base Class**: `execute()`, `_find_alerts()`, validation steps
- **Analyzer Base Class**: Static analysis methods for candle patterns
- **Validator Base Class**: Static validation methods for thresholds
- **Settings Base Class**: Configuration management
- **Key Learning**: What each class provides (quick lookup)

### ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md
- **Executor Details**: Full implementation logic and responsibilities
- **Analyzer Details**: All analysis methods with explanations
- **Validator Details**: All validation methods with parameters
- **Settings Details**: Configuration system explained
- **Key Learning**: Deep technical understanding of each class

### EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md
- **Why Abstract Methods Matter**: Enforcing contracts
- **Executor Hierarchy**: Base → Specific approach
- **Abstract vs Concrete**: When to use each
- **Implementation Rules**: How to implement correctly
- **Key Learning**: The philosophy behind the executor pattern

### EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md
- **Decision Matrix**: Which method to implement vs override
- **Quick Examples**: Common scenarios
- **Do's and Don'ts**: Best practices
- **Anti-patterns**: What NOT to do
- **Key Learning**: Practical guidance for implementation decisions

### CODE_QUALITY_STANDARDS.md
- **Type Hints**: 100% coverage requirements
- **Naming Conventions**: PascalCase, snake_case, UPPER_SNAKE_CASE
- **Docstrings**: Google-style format with sections
- **Line Length**: 79 characters maximum (PEP 8)
- **Enums**: Mandatory for categorical values
- **Key Learning**: How to write code that fits the project

---

## 💡 Learning Tips

### 1. **Use the Visualizations**
   - Keep ARCHITECTURE_VISUALIZATION.md open while reading other files
   - Reference the diagrams when you get lost
   - Draw your own diagrams to reinforce understanding

### 2. **Understand the Design Patterns First**
   - Patterns are the "why" behind the code structure
   - Understanding patterns makes everything else make sense
   - Don't skip DESIGN_PATTERNS_GUIDE.md

### 3. **See the Code**
   After reading each section, look at the actual code:
   - ARCHITECTURE → `src/stockreports/alert/executor.py`
   - DESIGN_PATTERNS → `src/stockreports/alert/approach/STRONG_CANDLE/`
   - QUALITY_STANDARDS → Any file in `src/stockreports/alert/`

### 4. **Read with Purpose**
   - Don't read everything at once
   - Read based on your immediate task
   - Use the "Quick Navigation by Task" section above

### 5. **Keep a Reference**
   - ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md is your cheat sheet
   - EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md is your decision guide
   - CODE_QUALITY_STANDARDS.md is your style guide
   - Keep these open while coding

---

## 🎓 Learning Outcomes

After completing this reading path, you will understand:

✅ **The Big Picture**
- What the system does
- How components interact
- Data flow through the system

✅ **Design Patterns**
- Why Template Method is used
- How Strategy pattern enables multiple approaches
- How Factory pattern creates instances
- How inheritance enforces contracts

✅ **Code Architecture**
- Executor base class and responsibilities
- Analyzer base class and methods
- Validator base class and methods
- Settings base class and configuration

✅ **Implementation Details**
- How to implement abstract methods
- When to override methods
- How to extend the system
- What makes code "good" in this project

✅ **Code Quality**
- Proper type hints
- Correct naming conventions
- Complete docstring format
- Formatting standards

---

## 🚀 After Reading: Next Steps

### 1. **Review the Reference Implementation**
Read: `/docs/PROMPTS/APPROACH_GENERATION_CODE/EXAMPLE_AI_GENERATION.md`
- See a working implementation
- Understand the pattern in practice
- Compare against standards

### 2. **Read Implementation Guides**
Read: `/docs/IMPLEMENTATION/CREATING_NEW_APPROACH.md`
- Step-by-step guide for creating new approaches
- Common tasks and how to accomplish them
- Testing and validation procedures

### 3. **Review Real Code**
Look at: `src/stockreports/alert/approach/STRONG_CANDLE/`
- See how all the concepts apply
- Study the actual implementation
- Reference when writing your own code

### 4. **Start Contributing**
- Pick a small task
- Reference CODE_QUALITY_STANDARDS.md while coding
- Use EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md for decisions
- Ask questions!

---

## ❓ FAQ

**Q: Do I need to read all 8 files?**
A: For a comprehensive understanding, yes. But if you're short on time, start with Phase 1 and Phase 2, then read based on your specific task.

**Q: What if I'm already familiar with design patterns?**
A: You can skim DESIGN_PATTERNS_GUIDE.md and focus on the executor and base class files.

**Q: Where can I find the actual code?**
A: Start in `src/stockreports/alert/` directory. The file structure mirrors the documentation.

**Q: What if something in the docs is unclear?**
A: Check ARCHITECTURE_VISUALIZATION.md for diagrams, then read the implementation details. If still unclear, look at the actual code in `src/stockreports/alert/`.

**Q: Can I skip the quality standards?**
A: No. Your code will be reviewed against CODE_QUALITY_STANDARDS.md. Read it before writing code.

**Q: How long does this take?**
A: 2.5-3 hours for complete understanding. 30-45 minutes for a quick overview. It depends on your background.

---

## 📋 Checklist for New Developers

Use this checklist to track your progress:

### Phase 1: Big Picture
- [ ] Read ARCHITECTURE_OVERVIEW.md
- [ ] Read ARCHITECTURE_VISUALIZATION.md
- [ ] Understand: System purpose, components, data flow

### Phase 2: Architecture Patterns
- [ ] Read DESIGN_PATTERNS_GUIDE.md
- [ ] Read ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md
- [ ] Read ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md
- [ ] Understand: Template Method, Strategy, Factory patterns

### Phase 3: Executor Knowledge
- [ ] Read EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md
- [ ] Read EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md
- [ ] Understand: How to implement executors correctly

### Phase 4: Quality Standards
- [ ] Read CODE_QUALITY_STANDARDS.md
- [ ] Understand: Type hints, naming, docstrings, formatting

### Phase 5: Apply Knowledge
- [ ] Look at actual code in src/stockreports/alert/
- [ ] Read EXAMPLE_AI_GENERATION.md
- [ ] Read CREATING_NEW_APPROACH.md
- [ ] Ready to contribute!

---

## 🎯 Success Criteria

You're ready to work on the codebase when you can answer:

1. **What is the system's purpose?**
   - Real-time stock trading alert detection using multiple strategies

2. **What are the main components?**
   - Executor (orchestrates execution), Analyzer (analyzes patterns), Validator (validates thresholds), Settings (configuration)

3. **How does data flow?**
   - Market data → Analyzer analyzes → Validator validates → Executor creates alerts

4. **What design patterns are used?**
   - Template Method (executor structure), Strategy (multiple approaches), Factory (instance creation)

5. **How do I add a new approach?**
   - Inherit from base classes, implement required methods, follow code quality standards

6. **What are the code quality expectations?**
   - Type hints required, proper naming, complete docstrings, 79 char line limit

---

## 📞 Getting Help

If you're stuck:

1. **Check ARCHITECTURE_VISUALIZATION.md** for diagrams
2. **Check ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md** for class details
3. **Check EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md** for decisions
4. **Look at STRONG_CANDLE implementation** for working examples
5. **Ask a team member** - they'll appreciate your preparation!

---

**Ready to get started?** Begin with [`ARCHITECTURE_OVERVIEW.md`](./ARCHITECTURE_OVERVIEW.md) and follow the path above. Good luck! 🚀
