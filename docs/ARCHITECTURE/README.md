# Architecture Documentation - Quick Start Map

Welcome! This directory contains comprehensive documentation for the stock trading alert system architecture. Use this page to navigate and choose your learning path.

---

## ⚡ 5-Minute Overview

The system detects real-time trading alerts by analyzing stock market candles using multiple strategies:

```
Market Data (OHLCV candles)
    ↓
[ ANALYZER ] - Analyzes patterns (static methods)
    ↓
[ VALIDATOR ] - Validates thresholds (static methods)
    ↓
[ EXECUTOR ] - Orchestrates & creates alerts (stateful)
    ↓
Trading Alerts (SELL/BUY signals)
```

**Key Design Patterns:**
- **Template Method**: Executor base defines algorithm structure
- **Strategy**: Each approach (STRONG_CANDLE, etc.) is a concrete strategy
- **Factory**: Creating executor/analyzer/validator instances

---

## 📚 Choose Your Learning Path

### Path 1: Complete Understanding (2.5-3 hours)
Perfect for: Developers who want comprehensive system knowledge
Files to read (in order):
1. ARCHITECTURE_OVERVIEW.md (20 min) - System purpose and components
2. ARCHITECTURE_VISUALIZATION.md (10 min) - Visual diagrams and flowcharts
3. DESIGN_PATTERNS_GUIDE.md (20 min) - Template Method, Strategy, Factory
4. ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md (10 min) - Quick class lookup
5. ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md (15 min) - Technical details
6. EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md (20 min) - Executor system deep dive
7. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (15 min) - Implementation decisions
8. CODE_QUALITY_STANDARDS.md (20 min) - Code expectations

### Path 2: Create New Approach (1.5 hours)
Perfect for: Developers who need to implement new trading strategies
Files to read (in order):
1. ARCHITECTURE_OVERVIEW.md (20 min) - Understand the system
2. DESIGN_PATTERNS_GUIDE.md (20 min) - Learn design patterns
3. ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md (10 min) - Class reference
4. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (10 min) - Decision guide
5. CODE_QUALITY_STANDARDS.md (20 min) - Code quality requirements
6. /docs/IMPLEMENTATION/CREATING_NEW_APPROACH.md (15 min) - Step-by-step guide

### Path 3: Quick Orientation (45 minutes)
Perfect for: Team members who need quick system understanding
Files to read (in order):
1. ARCHITECTURE_OVERVIEW.md (20 min) - System overview
2. ARCHITECTURE_VISUALIZATION.md (10 min) - Visual reference
3. DESIGN_PATTERNS_GUIDE.md (15 min) - Key patterns

### Path 4: Understand Existing Code (1 hour)
Perfect for: Developers who need to debug or modify code
Files to read (in order):
1. ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md (10 min) - Quick reference
2. EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md (10 min) - Decision guide
3. Look at src/stockreports/alert/approach/STRONG_CANDLE/ (20 min) - Real implementation
4. CODE_QUALITY_STANDARDS.md (20 min) - Understand standards

---

## 📖 File Descriptions

| File | Purpose | Best For | Read Time |
|------|---------|----------|-----------|
| **ARCHITECTURE_OVERVIEW.md** | System components, purpose, and data flow | Understanding the big picture | 20 min |
| **ARCHITECTURE_VISUALIZATION.md** | Diagrams, flowcharts, and visual explanations | Visual learners; keep open while reading | 10 min |
| **DESIGN_PATTERNS_GUIDE.md** | Template Method, Strategy, Factory patterns | Understanding why code is structured this way | 20 min |
| **ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md** | Quick lookup of base class methods | Reference while coding | 10 min |
| **ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md** | Deep technical details of base classes | Understanding implementation details | 15 min |
| **EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md** | Executor system and abstract method contracts | Before implementing executors | 20 min |
| **EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md** | Decision matrix for method implementation | Reference while coding | 15 min |
| **CODE_QUALITY_STANDARDS.md** | Type hints, naming, docstrings, formatting | **Read BEFORE writing code** | 20 min |

---

## 🏗️ System Architecture at a Glance

### Core Components

**Executor** (Orchestrator)
- Inherits from: `BaseExecutor`
- Responsibility: Orchestrates alert detection
- Method Pattern: Template Method base defines skeleton
- Key Methods: `execute()`, `_step_1_analyze()`, `_step_2_validate()`, etc.

**Analyzer** (Pattern Recognition)
- Inherits from: `BaseAnalyzer`
- Responsibility: Analyzes candle patterns
- Method Type: Static methods (pure analysis)
- No state: Same input → Same output always

**Validator** (Threshold Check)
- Inherits from: `BaseValidator`
- Responsibility: Validates against thresholds
- Method Type: Static methods (pure validation)
- No state: Same input → Same output always

**Settings** (Configuration)
- Inherits from: `BaseSettings`
- Responsibility: Stores configuration values
- Type: Pydantic models (validated configuration)
- Used by: Executor, Analyzer, Validator

### How They Work Together

```python
# The Executor orchestrates everything
executor = StrongCandleExecutor(settings)
alerts = executor.execute(candles)

# Under the hood:
# 1. Executor calls Analyzer.analyze() → gets patterns
# 2. Executor calls Validator.validate() → gets boolean
# 3. Executor reads from Settings → gets thresholds
# 4. Executor creates Alert if all validations pass
```

### Key Insight: Inheritance Contracts

Each class defines what subclasses MUST implement:
- If base class has `@abstractmethod` → subclass MUST implement
- If base class has concrete method → subclass can override or inherit
- Type hints are MANDATORY (100% coverage required)
- Docstrings are MANDATORY (for all public methods)

---

## 🔑 Key Concepts to Understand

### 1. Template Method Pattern
Base class (`BaseExecutor`) defines the algorithm skeleton:
```python
def execute(self):
    step_1_result = self._step_1_analyze()
    step_2_result = self._step_2_validate(step_1_result)
    step_3_result = self._step_3_create_alert(step_2_result)
    return step_3_result
```

Subclass (`StrongCandleExecutor`) implements the steps. This ensures consistent flow across all approaches.

### 2. Strategy Pattern
Each approach (STRONG_CANDLE, RSI_DIVERGENCE, etc.) is a strategy:
- Same interface (all inherit from BaseExecutor)
- Different implementation (each has unique logic)
- Swappable: Can use any approach in the same codebase
- Open/Closed: Add new approaches without modifying existing code

### 3. Factory Pattern
Create instances of Executor/Analyzer/Validator:
```python
executor = create_executor(approach="STRONG_CANDLE", settings=settings)
```

Hides complexity of construction. Future: Can change how instances are created without changing client code.

### 4. Abstract Methods vs Concrete Methods
- **Abstract method**: Subclass MUST implement (e.g., `_step_1_analyze()`)
- **Concrete method**: Subclass inherits as-is OR can override (e.g., `execute()`)
- **Interface contract**: When a method is abstract, subclass is bound to implement it

---

## 💡 Core Classes

### BaseExecutor
```python
class BaseExecutor(ABC):
    """Orchestrates alert detection using Template Method pattern"""
    
    @abstractmethod
    def _step_1_analyze(self) -> AnalysisResult:
        """Analyze candle patterns"""
    
    @abstractmethod
    def _step_2_validate(self, analysis: AnalysisResult) -> bool:
        """Validate against thresholds"""
    
    def execute(self) -> List[Alert]:
        """Template method - orchestrates all steps"""
```

### StrongCandleExecutor
```python
class StrongCandleExecutor(BaseExecutor):
    """Implements STRONG_CANDLE strategy"""
    
    def _step_1_analyze(self) -> AnalysisResult:
        """Implementation specific to STRONG_CANDLE"""
    
    def _step_2_validate(self, analysis: AnalysisResult) -> bool:
        """Validation specific to STRONG_CANDLE"""
```

### BaseAnalyzer
```python
class BaseAnalyzer(ABC):
    """Base for candle pattern analyzers"""
    
    @staticmethod
    @abstractmethod
    def analyze(candle: Candle) -> PatternResult:
        """Analyze a single candle"""
```

### BaseValidator
```python
class BaseValidator(ABC):
    """Base for threshold validators"""
    
    @staticmethod
    @abstractmethod
    def validate(pattern: PatternResult, settings: Settings) -> bool:
        """Validate pattern against thresholds"""
```

---

## 🔗 How They Connect

### Creating an Alert
```
1. Executor calls Analyzer.analyze(candle)
   ↓ (pure function - no side effects)
   → PatternResult { body_ratio: 2.5, color: BULLISH, ... }

2. Executor calls Validator.validate(pattern, settings)
   ↓ (pure function - no side effects)
   → True (pattern exceeds thresholds)

3. Executor reads Settings.body_ratio_threshold = 2.0
   ↓ (configuration loaded)
   → Passes validation

4. Executor creates Alert
   ↓ (stateful operation)
   → Alert { symbol: "AAPL", type: "BUY", ... }

5. Alert is returned to caller
```

---

## ✅ Readiness Checklist

Before you start coding, answer these questions:

- [ ] Do you understand the difference between Executor, Analyzer, and Validator?
- [ ] Can you explain the Template Method pattern?
- [ ] Do you know what an abstract method is and why we use them?
- [ ] Do you understand that Analyzer and Validator are STATIC methods?
- [ ] Have you read at least the first 3 files for your chosen path?
- [ ] Do you know the naming conventions (PascalCase, snake_case, UPPER_SNAKE_CASE)?
- [ ] Do you understand that type hints are MANDATORY (100% coverage)?
- [ ] Have you seen the CODE_QUALITY_STANDARDS.md file?
- [ ] Do you know where to find STRONG_CANDLE implementation?
- [ ] Do you have a concrete next step (which file to read or code to write)?

---

## 🔗 Quick Links

### By Topic
- **System Overview**: Start with ARCHITECTURE_OVERVIEW.md
- **Design Patterns**: See DESIGN_PATTERNS_GUIDE.md
- **Base Classes**: See ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md
- **Code Quality**: See CODE_QUALITY_STANDARDS.md
- **Executor Decisions**: See EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md

### By Task
- **Create New Approach**: Follow Path 2 (1.5 hours)
- **Fix a Bug**: Follow Path 4 (1 hour)
- **Understand Everything**: Follow Path 1 (2.5-3 hours)
- **Quick Overview**: Follow Path 3 (45 minutes)

### Actual Code
- **Reference Implementation**: `src/stockreports/alert/approach/STRONG_CANDLE/`
- **Executor Code**: `src/stockreports/alert/approach/STRONG_CANDLE/executor.py`
- **Analyzer Code**: `src/stockreports/alert/approach/STRONG_CANDLE/analyzer.py`
- **Validator Code**: `src/stockreports/alert/approach/STRONG_CANDLE/validator.py`
- **Settings Code**: `src/stockreports/alert/approach/STRONG_CANDLE/settings.py`

---

## 💡 Pro Tips

1. **Keep ARCHITECTURE_VISUALIZATION.md open** while reading other files
   - Visual reference reinforces learning
   - Helps connect concepts across files

2. **Look at STRONG_CANDLE implementation** while reading architecture docs
   - Concrete examples clarify abstract concepts
   - See how patterns apply in real code

3. **Read CODE_QUALITY_STANDARDS.md BEFORE writing code**
   - Know expectations upfront
   - Makes code review faster
   - Saves revision cycles

4. **Use EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md as a checklist**
   - Reference it every time you implement a method
   - Ensures you make the right design decision

5. **Draw your own diagrams to reinforce learning**
   - Create mental models
   - Identify gaps in understanding
   - Useful reference for future work

---

## 🎓 Next Steps

### Immediate (Next 5 Minutes)
1. Choose your learning path based on your role/task
2. Note the files you need to read
3. Estimate time commitment
4. Schedule reading time

### During Reading (Follow Your Path)
1. Read files in recommended order
2. Keep visualizations visible
3. Reference quick cards while reading
4. Take notes on key concepts

### After Reading (Before Coding)
1. Review the Readiness Checklist above
2. Answer all 10 questions
3. Look at STRONG_CANDLE implementation
4. Read CODE_QUALITY_STANDARDS.md

### While Contributing Code
1. Keep CODE_QUALITY_STANDARDS.md open
2. Reference EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md for decisions
3. Use ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md for lookups
4. Check off readiness criteria as you code

---

## 📍 Directory Structure

```
docs/ARCHITECTURE/
├── README.md (you are here)
├── DEVELOPER_ONBOARDING_GUIDE.md (comprehensive guide)
├── ARCHITECTURE_OVERVIEW.md
├── ARCHITECTURE_VISUALIZATION.md
├── DESIGN_PATTERNS_GUIDE.md
├── ABSTRACT_BASE_CLASSES_QUICK_REFERENCE.md
├── ABSTRACT_BASE_CLASSES_IMPLEMENTATION.md
├── EXECUTOR_ABSTRACT_METHOD_PRINCIPLE.md
├── EXECUTOR_IMPLEMENT_VS_OVERRIDE_QUICK_CARD.md
└── CODE_QUALITY_STANDARDS.md
```

---

## 🚀 Ready to Begin?

1. **If you're new**: Start with Path 3 (Quick Orientation - 45 min)
2. **If you need to create something**: Follow Path 2 (Create New Approach - 1.5 hours)
3. **If you need deep understanding**: Follow Path 1 (Complete - 2.5-3 hours)
4. **If you're debugging code**: Follow Path 4 (Understand Code - 1 hour)

**Estimated total time**: 45 minutes to 3 hours (depending on your path)

**Success criteria**: You can answer the 10 questions in the Readiness Checklist

**Next action**: Read ARCHITECTURE_OVERVIEW.md (first file for all paths)

---

**Last Updated**: March 13, 2026  
**Status**: ✅ Complete and Ready to Use
