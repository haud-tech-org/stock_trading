# AI Approach Code Generation Prompt Template

**Purpose**: Comprehensive prompt for AI to automatically generate end-to-end production-ready trading approach code  
**Status**: ✅ AI Code Generation Ready  
**Last Updated**: March 12, 2026

---

## 🎯 Usage

Use this document to provide context and requirements to an AI system (like Claude/GPT) to generate complete, production-ready approach code automatically.

**Fill in the bracketed [PLACEHOLDERS] and provide the full document to AI with the request:**

```
Please generate the complete end-to-end implementation of the [APPROACH_NAME] approach following this specification document.

IMPORTANT: Follow the GENERATION PHASES below in order to ensure consistent, 
high-quality, production-ready code.
```

---

## 🔄 GENERATION PHASES (MANDATORY ORDER)

**CRITICAL**: Execute these phases in the exact order listed. Do NOT skip phases or rearrange steps. This ensures consistent, accurate code generation.

### Phase 1: ANALYZE Business Logic (5 minutes)

**Objective**: Deeply understand what the approach detects and why

**Required Output**: Write a summary addressing:
1. What market condition does this approach detect?
2. What are the 3-5 key trading rules?
3. What makes this approach different from others?
4. Which base class methods (Analyzer/Validator) will be needed?
5. What are the critical configuration parameters?

**Do NOT proceed to Phase 2 until you can answer all 5 questions clearly.**

---

### Phase 2: REVIEW Architecture & Patterns (5 minutes)

**Objective**: Understand how code should be structured

**Required Study**:
1. Read PART 2.1: "Executor → Analyzer → Validator Pattern"
2. Read PART 2.2: "Class Responsibilities"
3. Read PART 2.2.1: "Loop and Context Management Pattern"
4. Review PART 2.3: "Base Methods Available" (9 for Analyzer, 10 for Validator)
5. Read PART 2.5: "STRONG_CANDLE Reference Implementation"

**Required Output**: Document:
- Why Analyzer must be pure static functions
- Why Validator must have no calculations
- Why Executor uses _find_alerts() hook (not override run())
- Which loop pattern you'll use (forward vs backward)
- Which 3-5 base methods are most relevant

**Do NOT proceed to Phase 3 until you understand the architecture.**

---

### Phase 3: CONFIRM Quality Rules (3 minutes)

**Objective**: Verify you understand ALL code quality requirements before writing code

**Required Checklist** - Confirm you understand:
- [ ] Type Hints: ALL methods must have type hints (no missing types)
- [ ] Enums: ALL categorical values MUST use enums (not strings)
- [ ] Docstrings: Google-style with 7 sections (Summary, Args, Returns, Raises, Example, Note, Guidelines)
- [ ] Static Methods: ALL Analyzer/Validator methods are @staticmethod
- [ ] Line Length: Maximum 79 characters (PEP 8)
- [ ] Imports: Relative imports, organized (stdlib, third-party, local)
- [ ] Naming: PascalCase classes, snake_case methods, UPPER_SNAKE_CASE constants
- [ ] File Structure: 5 files (settings.py, analyzer.py, validator.py, executor.py, __init__.py)

**Do NOT proceed to Phase 4 until all items are checked.**

---

### Phase 4: REFERENCE STRONG_CANDLE (10 minutes)

**Objective**: Study actual working code to ensure your generated code matches patterns

**Required Study**: Open `src/stockreports/alert/approach/STRONG_CANDLE/`

For each of the 5 files, document:

1. **settings.py**
   - How does it inherit BaseSettings?
   - What's the pattern for default values?
   - How are enums defined and imported?

2. **analyzer.py**
   - How are methods decorated as @staticmethod?
   - How are calculations structured?
   - What type hints are used?

3. **validator.py**
   - How are validation methods structured?
   - What's the pattern for return values?
   - How do docstrings look?

4. **executor.py**
   - How is _find_alerts() implemented (NOT run())?
   - How is the backward loop structured?
   - How is logging integrated?

5. **__init__.py**
   - What imports are used (relative)?
   - What's the __all__ list contain?
   - How are classes exported?

**Required Output**: Create a mapping:
```
Business Logic Rule 1 → Use Analyzer method X + Validator method Y
Business Logic Rule 2 → Use Analyzer method Z + Validator method W
...
```

**Do NOT proceed to Phase 5 until you've documented similarities to STRONG_CANDLE.**

---

### Phase 5: PLAN Implementation (5 minutes)

**Objective**: Map business logic to code structure BEFORE writing

**Required Output**: Complete this implementation plan:

```
Settings Class:
  - Parameter 1: [name] → [enum type or built-in type]
  - Parameter 2: [name] → [type]
  ...

Analyzer Class (Pure Static Calculations):
  - Method 1: [calculate_something]
    * Input: [what data]
    * Output: [what result, with type]
    * Uses base methods: [which ones]
  - Method 2: ...

Validator Class (Pure Static Validation):
  - Method 1: [validate_something]
    * Input: [what data]
    * Output: [bool/validation result, with type]
    * Uses base methods: [which ones]
  - Method 2: ...

Executor Class (Orchestration & Alerts):
  - Implement _find_alerts():
    * Loop backwards through data
    * Call Analyzer methods
    * Call Validator methods
    * Create alerts
```

**Do NOT proceed to Phase 6 until this plan is complete and verified against STRONG_CANDLE.**

---

### Phase 6: GENERATE Code (20-30 minutes)

**Objective**: Write all 5 files with ALL rules from previous phases applied

**Critical Reminders**:
- Follow the plan from Phase 5 EXACTLY
- Every method must have complete type hints (no missing types)
- Every categorical value MUST be an enum (check STRONG_CANDLE for examples)
- Every class/function must have Google-style docstring
- Every line must be ≤79 characters
- Relative imports only
- Study STRONG_CANDLE structure for file organization

**Generate**: All 5 files in correct order:
1. `settings.py` - Settings class inheriting BaseSettings
2. `analyzer.py` - YourApproachAnalyzer class
3. `validator.py` - YourApproachValidator class
4. `executor.py` - YourApproachExecutor with _find_alerts()
5. `__init__.py` - Exports with relative imports

---

### Phase 7: VERIFY Against Checklist (5 minutes)

**Objective**: Confirm all code meets quality standards BEFORE output

**Run Through Validation Checklist** (in PART 4):
- [ ] All 20 items from validation checklist pass
- [ ] All 8 items from STRONG_CANDLE comparison pass
- [ ] Code ready for production

**Only output code if ALL items checked. If any unchecked, regenerate Phase 6.**

---

## 📋 PART 1: APPROACH SPECIFICATION

### 1.1 Basic Information

**Approach Name**: [YOUR_APPROACH_NAME]  
**Short Code**: [APPROACH_CODE, e.g., SC for STRONG_CANDLE, VRA for Volume Reversal Analysis]  
**Category**: [BUY_SIGNAL / SELL_SIGNAL / BIDIRECTIONAL]  
**Description**: [2-3 sentence description of what the approach detects]

**Example**:
- Approach Name: Strong Candle
- Short Code: SC
- Category: BIDIRECTIONAL
- Description: Detects strong candles with significant body size, volume confirmation, and color consistency with lookback window trend. Used to identify breakout and reversal opportunities.

---

### 1.2 Trading Rules & Logic

**Rule Set**: Define your trading rules clearly

```
RULE 1: [Description]
- Input: [what you measure]
- Condition: [when is it true]
- Result: [BUY/SELL/NEUTRAL]

RULE 2: [Description]
...
```

**Example**:
```
RULE 1: Strong Candle Body
- Input: Current candle body ratio and size
- Condition: body_ratio >= 0.7 AND body_size >= 50 pips
- Result: PASSES (go to next rule)

RULE 2: Volume Confirmation
- Input: Current candle volume vs historical max
- Condition: volume <= max_historical_volume * 1.5
- Result: PASSES (go to next rule)

RULE 3: Trend Consistency
- Input: Current candle color vs lookback window colors
- Condition: Majority of lookback window has same color
- Result: Signal = Current_Candle_Color
```

---

### 1.3 Configuration Thresholds

**List all configurable parameters**:

| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| [PARAM_NAME] | [default] | [min] | [max] | [description] |
| [PARAM_NAME] | [default] | [min] | [max] | [description] |

**Example**:
| Parameter | Default | Min | Max | Description |
|-----------|---------|-----|-----|-------------|
| LOOKBACK_WINDOW | 50 | 10 | 200 | Number of candles to analyze |
| MIN_BODY_RATIO | 0.7 | 0.5 | 1.0 | Minimum body ratio (0-1) |
| MIN_BODY_SIZE | 50 | 10 | 500 | Minimum body size in pips |
| MAX_VOLUME_MULTIPLIER | 1.5 | 1.0 | 3.0 | Volume multiplier threshold |
| COOLDOWN_WINDOW | 5 | 1 | 20 | Minimum candles between alerts |
| MAGNITUDE_THRESHOLD | 0.025 | 0.01 | 0.1 | Alert magnitude threshold |

---

### 1.4 Required Data

**Data Input**:
- Format: pandas DataFrame with OHLCV columns
- Columns Required: `open`, `high`, `low`, `close`, `volume`
- Index: datetime index with timestamps
- Frequency: [Specify, e.g., 1H, 4H, 1D]
- Minimum History: [number of candles needed]

**Example**:
```
Input: OHLCV DataFrame
Columns: ['open', 'high', 'low', 'close', 'volume']
Index: datetime
Frequency: 1 Hour
Minimum History: 60 candles (to calculate 50-candle lookback + buffer)
```

---

## 📋 PART 2: ARCHITECTURE CONTEXT

### 2.1 Pattern Requirements

**MANDATORY: Follow the Executor → Analyzer → Validator Pattern**

The approach must be implemented as 4 classes:

1. **Settings Class** (Configuration)
   - Inherits from: `BaseSettings`
   - Responsibility: Load and store configuration thresholds
   - Method: `__init__(self, symbol: str)` - loads from centralized config

2. **Analyzer Class** (Pure Calculations)
   - Inherits from: `Analyzer` (base class)
   - Responsibility: Pure mathematical calculations, NO business logic
   - Methods: Static methods only, no instance state
   - Pattern: Call base methods + add custom methods if needed

3. **Validator Class** (Pure Validation)
   - Inherits from: `Validator` (base class)
   - Responsibility: Pure boolean validation checks, NO calculations
   - Methods: Static methods only, no instance state
   - Pattern: Call base methods + add custom methods if needed

4. **Executor Class** (Orchestration)
   - Inherits from: `Executor` (base class)
   - Responsibility: Orchestrate the analysis workflow
   
   **Key Responsibilities**:
   - Load market data (OHLCV candles)
   - Apply settings and configuration thresholds
   - Call Analyzer for calculations
   - Call Validator for verification checks
   - Combine results into final trading signal
   - Manage error handling and edge cases
   - Track execution state and context variables
   
   **CRITICAL PRINCIPLE**: 
   - ✅ DO IMPLEMENT: `_find_alerts()` (abstract method)
   - ❌ DO NOT override: `run()` (concrete method in base)
   
   **Why NOT override run()?**
   The base class `run()` method provides:
   - Standardized error handling and logging
   - Consistent garbage collection
   - Uniform AlertResult formatting
   - Template Method pattern enforcement
   Overriding breaks these guarantees (except RCM, documented exception).
   
   - Base class utilities available:
     - `get_loop_setup()` - setup loop boundaries
     - `set_window_context()` - extract lookback window
     - `next_step()` / `next_validation()` - increment step counters
     - `_create_alert_with_details()` - create alert objects
     - `_add_details_for_alert()` - build details dict

### 2.2 Base Class Methods Available

**Analyzer Base Methods** (9 available, all static):
1. `calculate_body_ratio(candle)` → float
2. `calculate_body_size(candle)` → float
3. `get_candle_color(candle)` → CandleColor
4. `get_window_size_and_trend(df)` → (size, trend)
5. `calculate_window_price_range(df)` → dict(low, high)
6. `calculate_conditional_window_price_range(df)` → dict(low, high)
7. `get_max_volume_in_window(df)` → float
8. `get_max_volume_in_conditional_window(df)` → float
9. `get_opposite_color_candles(df, color)` → DataFrame

**Validator Base Methods** (10 available, all static):
1. `validate_candle_color_consistency(df, target_color)` → bool
2. `validate_opposite_color_exists(df, color)` → bool
3. `validate_price_threshold(price, threshold)` → bool
4. `validate_ratio_threshold(ratio, threshold)` → bool
5. `validate_volume_threshold(volume, threshold)` → bool
6. `validate_volume_multiplier(current_vol, max_vol, multiplier)` → bool
7. `validate_dataframe_not_empty(df)` → bool
8. `validate_required_columns(df)` → bool
9. `validate_window_size(window, min_size, max_size)` → bool
10. `validate_data_quality(df)` → bool

### 2.2.1 Loop and Context Management Pattern

**Backward Loop Pattern**:
```python
loop_setup = self.get_loop_setup(df, new_candle_count)
for i in range(loop_setup.start_index, loop_setup.end_index - 1, -1):
    # Process candles from latest (highest index) to oldest
```

**Why Backward Iteration?**
- Market analysis examines recent candles first
- Allows breaking early when pattern found
- Matches trader's mental model (recent → old)

**What get_loop_setup() Returns**:
- `start_index`: Starting position for loop
- `end_index`: Ending position for loop
- Handles: Data validation, minimum size checks, boundary safety

**Window Context Extraction**:
```python
self.set_window_context(df, i, lookback_period=your_period)
# Sets: self.current_window_start_time, self.current_window_end_time
# Extracts: DataFrame slice for historical lookback
```

**What set_window_context() Does**:
- Extracts lookback period from dataframe
- Sets time context variables (start_time, end_time)
- Prepares data for current analysis window
- Handles edge cases (insufficient data)

### 2.3 Folder Structure

```
src/stockreports/alert/approach/[YOUR_APPROACH_NAME]/
├── __init__.py                 # Exports all 4 classes
├── settings.py                 # YourApproachSettings class
├── analyzer.py                 # YourApproachAnalyzer class
├── validator.py                # YourApproachValidator class
└── executor.py                 # YourApproachExecutor class
```

### 2.4 Code Quality Standards

**MANDATORY REQUIREMENTS**:

1. **Type Hints**
   - All function parameters must have type hints
   - All return values must have type hints
   - Use correct types for complex data structures
   
   **Basic Type Hints**:
   ```python
   def calculate_value(candle: pd.Series, threshold: float) -> float:
       """Calculate a value from candle and threshold."""
       pass
   ```
   
   **Complex Type Examples**:
   ```python
   from typing import Dict, List, Optional, Tuple
   import pandas as pd
   
   # Optional value (can be None)
   def get_max_price(df: pd.DataFrame) -> Optional[float]:
       pass
   
   # List of objects
   def get_alerts(df: pd.DataFrame) -> list[AlertData]:
       pass
   
   # Dictionary with string keys and float values
   def calculate_metrics(candle: pd.Series) -> Dict[str, float]:
       return {"body_ratio": 0.8, "body_size": 50.0}
   
   # Tuple of multiple values
   def get_window_info(df: pd.DataFrame) -> Tuple[float, Trend]:
       return (window_size, trend)
   ```
   
   **Key Patterns**:
   - `pd.DataFrame`: Complete market data
   - `pd.Series`: Single candle or row
   - `Optional[T]`: Value that might be None
   - `List[T]` or `list[T]`: Array of items
   - `Dict[K, V]`: Key-value mapping
   - Custom classes: `AlertData`, `Trend`, `CandleColor`

2. **Type Safety - Enum Usage (MANDATORY)**
   
   All categorical values must use enums, NEVER magic strings.
   
   **Why Enums Instead of Strings?**
   - ✅ IDE autocomplete support
   - ✅ Type checking catches errors at development time
   - ✅ No silent failures from typos
   - ✅ Self-documenting code
   
   **Examples of Required Enum Usage**:
   
   Colors → Use `CandleColor` enum:
   ```python
   # ❌ WRONG - Magic string
   if candle_color == "GREEN":
       pass
   
   # ✅ CORRECT - Enum
   from src.stockreports.alert.common.constants import CandleColor
   if candle_color == CandleColor.GREEN:
       pass
   ```
   
   Comparisons → Use `Comparison` enum:
   ```python
   # ❌ WRONG
   def validate_threshold(price, threshold, comparison="greater"):
       pass
   
   # ✅ CORRECT
   from src.stockreports.alert.common.constants import Comparison
   def validate_threshold(price: float, threshold: float, comparison: Comparison) -> bool:
       if comparison == Comparison.GREATER:
           return price > threshold
   ```
   
   Columns → Use `CandleColumn` enum:
   ```python
   # ❌ WRONG - Magic string
   price = candle['close']
   
   # ✅ CORRECT - Enum
   from src.stockreports.alert.common.constants import CandleColumn
   price = candle[CandleColumn.CLOSE]
   ```
   
   **When to Create New Enums**:
   - Multiple hardcoded values of same category
   - Same values used in multiple places
   - Likely to evolve in the future
   - Improves code readability

3. **Docstrings (Google Style Format)**
   
   All classes and public methods must have docstrings.
   
   **Minimum Required Sections**:
   - One-line summary
   - Args (parameter descriptions)
   - Returns (return value description)
   
   **Recommended Additional Sections**:
   - Raises (exceptions that can be raised)
   - Example (usage example)
   - Note (important caveats or considerations)
   
   **Template - Minimum Required**:
   ```python
   def validate_price_threshold(
       price: float,
       threshold: float
   ) -> bool:
       """
       Validate if price exceeds threshold.
       
       Args:
           price: The price value to validate (float).
           threshold: The threshold to compare against (float).
       
       Returns:
           bool: True if price > threshold, False otherwise.
       """
       return price > threshold
   ```
   
   **Template - Full Format (Recommended)**:
   ```python
   def validate_price_threshold(
       price: float,
       threshold: float,
       comparison: Comparison
   ) -> bool:
       """
       Validate if price meets threshold using comparison operator.
       
       Pure function - no side effects. Returns True if condition 
       is met, False otherwise. Accepts Comparison enum for type safety.
       
       Args:
           price: Current price to validate (float).
           threshold: Price threshold to compare against (float).
           comparison: Comparison type (Comparison enum).
               Must be explicitly specified (no defaults).
       
       Returns:
           bool: True if condition met (e.g., price > threshold
                 when comparison=Comparison.GREATER), False otherwise.
       
       Raises:
           ValueError: If comparison not in Comparison enum.
       
       Example:
           >>> from src.stockreports.alert.common.constants import Comparison
           >>> validate_price_threshold(100.5, 100.0, Comparison.GREATER)
           True
           >>> validate_price_threshold(99.5, 100.0, Comparison.GREATER)
           False
       
       Note:
           - Pure function (deterministic, no side effects)
           - Works with any float values (positive, negative, zero)
           - Comparison must be explicit (no default "greater")
       """
       if comparison == Comparison.GREATER:
           return price > threshold
       # ... handle other comparisons
   ```
   
   **Key Guidelines**:
   1. **One-line summary**: Use verb-noun format ("Calculate...", "Validate...")
   2. **Detailed description**: Explain WHY method exists, key assumptions
   3. **Args**: Each parameter with type and description
   4. **Returns**: What value is returned and what it means
   5. **Raises**: What exceptions can occur and when
   6. **Example**: Real usage examples
   7. **Note**: Important caveats or edge cases

4. **Static Methods**
   - All Analyzer methods must be `@staticmethod`
   - All Validator methods must be `@staticmethod`
   - No instance state in these classes

5. **Naming Conventions**
   - Classes: `PascalCase` (e.g., `YourApproachExecutor`)
   - Functions/Methods: `snake_case` (e.g., `validate_condition`)
   - Constants: `UPPER_SNAKE_CASE`
   - Private methods: Start with `_` (e.g., `_step_validate_something`)

6. **Code Style: Line Length (PEP 8)**
   
   **Rule**: Maximum line length of 79 characters
   
   ```python
   # ❌ WRONG - 92 characters (too long)
   result = validator.validate_candle_color_consistency(dataframe, CandleColor.GREEN)
   
   # ✅ CORRECT - Break into multiple lines
   result = validator.validate_candle_color_consistency(
       dataframe,
       CandleColor.GREEN
   )
   ```
   
   **When Line Too Long**:
   - Break function calls across multiple lines
   - Align parameters for readability
   - Use parentheses for implicit line continuation
   
   **Example - Long Parameter List**:
   ```python
   # ❌ Too long
   validator.validate_window(df, MIN_SIZE, MAX_SIZE, trend, volume, magnitude)
   
   # ✅ Correct - Broken into lines
   validator.validate_window(
       df,
       MIN_SIZE,
       MAX_SIZE,
       trend,
       volume,
       magnitude
   )
   ```

7. **Imports**
   - Use relative imports in `__init__.py`: `from .executor import ...`
   - Group imports: stdlib, third-party, local
   - Example:
     ```python
     import pandas as pd
     import logging
     from typing import Optional
     
     from src.stockreports.alert.executor import Executor
     from src.stockreports.alert.common.constants import Approach, Signal
     ```

---

### 2.5 Best Practices & Real-World Patterns

The patterns and requirements documented in PART 2-4 are derived from real-world implementation experience. For deeper understanding of WHY these patterns exist and how they evolved, see `docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md`.

#### 🔗 Reference Implementation: STRONG_CANDLE Approach

**Working Example Location**: `src/stockreports/alert/approach/STRONG_CANDLE/`

**What to Study**:
- `settings.py` - Configuration pattern with Pydantic BaseSettings
- `analyzer.py` - Pure static methods for calculations and data extraction
- `validator.py` - Pure static validation logic with no side effects
- `executor.py` - Template Method pattern implementation with _find_alerts() hook
- `__init__.py` - Proper module exports with relative imports

**Why Reference This**:
- ✅ Implements ALL patterns documented in this prompt
- ✅ Uses enums for all categorical values (CandleColor, Comparison, CandleColumn)
- ✅ Has complete type hints including complex types (Optional, List, Dict)
- ✅ Contains comprehensive Google-style docstrings with all 7 sections
- ✅ Demonstrates proper Executor and base class usage
- ✅ Shows correct import structure and __init__.py template
- ✅ Exemplifies logging, context management, and error handling
- ✅ Production-tested and currently active in trading system

**When Generating New Approaches**:
1. Review STRONG_CANDLE structure first (5 minutes)
2. Use it as reference while AI generates code (side-by-side comparison)
3. Verify generated code matches STRONG_CANDLE patterns
4. Copy import structure and __init__.py from STRONG_CANDLE exactly
5. Cross-check type hints and docstrings against STRONG_CANDLE examples

---

**Key case studies most relevant to approach generation**:

#### Case Study 1: Standardized Logging & Context Management
**Location**: `docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md` → Case Study 1

**Why it matters for your code**:
- Documents the `log_factory` pattern (referenced in PART 3: Executor template)
- Explains class-level context variables: `self.current_step`, `self.current_window_start_time`, `self.current_window_end_time`
- Shows step/validation tracking implementation
- Provides real examples from VRA, STRONG CANDLE executors

**Reference this when**:
- Implementing logging in your Executor class
- Setting up context variable management
- Understanding step and validation tracking

**Key pattern from Case Study 1**:
```python
# How logging should work in your executor
log(
    logger=self.logger,
    status=ValidationStatus.FAILED,
    name=self.__class__.__name__,
    alert_time=self.current_window_end_time,
    step=self.current_step,
    message="Validation failed.",
    log_level=LogLevel.DEBUG,
    execution_symbol=self.symbol
)
```

#### Case Study 3: VRA Executor Refactoring & Shared Utilities
**Location**: `docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md` → Case Study 3

**Why it matters for your code**:
- Shows how to use base Analyzer and Validator methods effectively
- Documents shared utility pattern (`window_utils`, `candle_utils`)
- Demonstrates step consolidation and code simplification
- Real example of how to structure a clean executor

**Reference this when**:
- Using base Analyzer methods (`calculate_body_ratio`, `get_candle_color`, etc.)
- Understanding how to leverage shared utilities
- Organizing your validation steps efficiently

**Key pattern from Case Study 3**:
```python
# Structure your executor steps logically:
# Step 1: Trend & magnitude validation
# Step 2: Volume validation
# Step 3: Reversal confirmation
# This prevents code duplication and improves readability
```

#### Case Study 7: STRONG_CANDLE Refactoring & Type Safety
**Location**: `docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md` → Case Study 7

**Why it matters for your code**:
- Documents Enum handling best practices (Case 7a: Enum vs String)
- Shows parameter naming for clarity (Case 7b: STRONG_CANDLE renaming)
- Explains step consolidation (Case 7c)
- Prevents common type-related bugs

**Reference this when**:
- Working with Enum types (`Approach`, `Signal`, `Trend`, `CandleColor`, etc.)
- Naming configuration parameters
- Ensuring type safety in your code

**Critical pattern from Case Study 7a (Enum handling)**:
```python
# WRONG: Calling .value on potentially mixed types
window_trend = Trend.UPTREND  # This is an Enum
f"{window_trend.value}"  # ✅ Returns "UPTREND" but prone to errors

# RIGHT: Let Python handle type conversion
f"{window_trend}"  # ✅ Works for both Enum and string automatically

# CORRECT USE of .value: Only for JSON serialization or external APIs
alert_dict = {
    "trend": window_trend.value  # ✅ Use .value only when needed
}
```

**Pattern from Case Study 7b (Parameter naming)**:
```python
# UNCLEAR: What does this parameter do?
self.threshold_1 = self.get("THRESHOLD_1")

# CLEAR: Parameter name documents its purpose
self.max_opposite_color_candle_body_size = self.get("MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE")
# Now readers immediately understand: maximum size of opposite color candles
```

---

## 📋 PART 2.5: ADDITIONAL RESOURCES & REFERENCES

### Testing, Troubleshooting & Best Practices

After generating the code with this prompt, use these resources for implementation:

1. **Implementation Best Practices Guide**
   - Location: `/docs/IMPLEMENTATION/IMPLEMENTATION_BEST_PRACTICES.md`
   - Covers: Testing strategies (4 levels: unit → E2E), code review checklist, troubleshooting
   - Useful for: Post-generation refinement, validation testing, quality assurance
   - Key Sections:
     - Quick checklist for new approach (10-step process)
     - Adding new validation steps (with RSI example)
     - Testing strategy (unit → integration → E2E)
     - Code review checklist (12-point quality review)
     - Troubleshooting common issues (5 real problems)
     - Performance optimization patterns
     - Logging & debugging standard pattern

2. **Technical Case Studies**
   - Location: `/docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md`
   - Covers: Real implementation examples, context management, import patterns
   - Useful for: Understanding complex patterns, reference implementations, best practices
   - Case Studies Include:
     - Case Study 1: Logging and context management (STRONG_CANDLE)
     - Case Study 3: Shared utilities pattern (VRA)
     - Case Study 7: Type safety and Enum handling (All approaches)

3. **Architecture Documentation**
   - Location: `/docs/ARCHITECTURE/`
   - Covers: System design, base classes, inheritance patterns
   - Useful for: Understanding the framework, debugging inheritance issues

---

## 📋 PART 3: IMPLEMENTATION DETAILS

### 3.1 Settings Class Template

**File**: `settings.py`

**Requirements**:
- Inherit from `BaseSettings`
- Constructor: `__init__(self, symbol: str)`
- Load all thresholds via `self.get("CONFIG_KEY")`
- No validation logic (just configuration storage)

**Structure**:
```python
class YourApproachSettings(BaseSettings):
    """Settings for the [YOUR_APPROACH_NAME] approach."""
    
    def __init__(self, symbol: str):
        super().__init__(symbol, Approach.YOUR_APPROACH_NAME)
        
        # Load all settings from centralized configuration
        self.[param_name] = self.get("[CONFIG_KEY_NAME]")
        ...
```

---

### 3.2 Analyzer Class Template

**File**: `analyzer.py`

**Requirements**:
- Inherit from `Analyzer`
- NO custom methods needed if using only base methods
- Custom methods if base methods insufficient
- All methods must be `@staticmethod`
- Pure calculations only, NO business logic

**Structure for approach using only base methods**:
```python
class YourApproachAnalyzer(Analyzer):
    """Analyzer for [YOUR_APPROACH_NAME] approach.
    
    Inherits all calculation methods from base Analyzer class.
    """
    pass
```

**Structure for approach with custom methods**:
```python
class YourApproachAnalyzer(Analyzer):
    """Analyzer for [YOUR_APPROACH_NAME] approach."""
    
    @staticmethod
    def your_custom_calculation(data: pd.Series) -> float:
        """
        [One-line description].
        
        Args:
            data: [description]
        
        Returns:
            float: [description]
        """
        # Pure calculation logic
        return result
```

---

### 3.3 Validator Class Template

**File**: `validator.py`

**Requirements**:
- Inherit from `Validator`
- NO custom methods needed if using only base methods
- Custom methods if base methods insufficient
- All methods must be `@staticmethod`
- Only business logic validation, NO calculations

**Structure for approach using only base methods**:
```python
class YourApproachValidator(Validator):
    """Validator for [YOUR_APPROACH_NAME] approach.
    
    Inherits all validation methods from base Validator class.
    """
    pass
```

**Structure for approach with custom methods**:
```python
class YourApproachValidator(Validator):
    """Validator for [YOUR_APPROACH_NAME] approach."""
    
    @staticmethod
    def validate_custom_condition(value: float, threshold: float) -> bool:
        """
        [One-line description].
        
        Args:
            value: [description]
            threshold: [description]
        
        Returns:
            bool: [description]
        """
        # Pure validation logic - only returns boolean
        return condition_met
```

---

### 3.4 Executor Class Template

**File**: `executor.py`

**CRITICAL REQUIREMENTS**:

1. **Inheritance**: 
   - `class YourApproachExecutor(Executor):`

2. **Constructor**:
   - Must call `super().__init__(symbol, approach_name, settings)`
   - Initialize Analyzer and Validator
   - Must NOT accept or override `run()` parameter

3. **Main Method**:
   - **IMPLEMENT** `_find_alerts(df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]`
   - **DO NOT** override `run()` method

4. **Loop Pattern**:
   - Use `get_loop_setup()` to get loop boundaries
   - Use `set_window_context()` to extract window for each candle
   - Loop backward: `for i in range(loop_end, loop_start - 1, -1)`

5. **Step Pattern** (See Case Study 1 for detailed explanation):
   - Initialize context variables at start of each window iteration
   - Call `self.next_step()` before each major validation step
   - Call `self.next_validation()` for validation tracking
   - Use `log()` function with proper context (see Case Study 1 pattern)

6. **Alert Creation**:
   - Use `_create_alert_with_details()` base class method
   - Use `_add_details_for_alert()` to build details dict
   - Append to `self.alerts` list

7. **Return**:
   - Return `self.alerts` list (list of AlertData objects)
   - Base class `run()` will handle formatting to AlertResult

**⭐ CASE STUDY REFERENCES** (See PART 2.5 for details):
- **Case Study 1**: Logging and context management - how to properly log during execution
- **Case Study 3**: Shared utilities pattern - how to structure validation steps efficiently
- **Case Study 7**: Type safety - ensure Enum handling is correct

**Structure**:
```python
class YourApproachExecutor(Executor):
    """Executor for [YOUR_APPROACH_NAME] approach.
    
    See Case Study 1 for logging and context management patterns.
    See Case Study 3 for how to structure validation steps.
    """
    
    def __init__(self, symbol: str):
        self.settings = YourApproachSettings(symbol)
        self.analyzer = YourApproachAnalyzer()
        self.validator = YourApproachValidator()
        super().__init__(symbol, Approach.YOUR_APPROACH_NAME, self.settings)
        self.logger = logging.getLogger(__name__)
    
    def _find_alerts(self, df: pd.DataFrame, new_candle_count: int = 0) -> list[AlertData]:
        """
        Find alerts in the dataframe.
        
        For logging and context management patterns, see Case Study 1.
        For shared utility usage examples, see Case Study 3 (VRA).
        
        Args:
            df: OHLCV data
            new_candle_count: Number of new candles to process
        
        Returns:
            list[AlertData]: Found alerts
        """
        # Validate input
        if len(df) < self.settings.lookback_window:
            return self.alerts
        
        # Setup loop
        df_indexed, loop_start, loop_end = self.get_loop_setup(
            df, new_candle_count, self.settings.lookback_window
        )
        
        # Main loop
        for i in range(loop_end, loop_start - 1, -1):
            # Extract window context
            self.set_window_context(i, df_indexed, self.settings.lookback_window)
            
            if self.lookback_window_df is None or self.last_candle is None:
                continue
            
            # --- Reset context for new window ---
            # See Case Study 1 for detailed context management pattern
            self.current_window_end_time = self.lookback_window_df.iloc[-1]['time']
            self.current_window_start_time = self.lookback_window_df.iloc[0]['time']
            self.current_step = 1
            
            # Step 1: Validation check
            self.next_step()
            if not self.validator.validate_condition(...):
                # See Case Study 1 for logging pattern (how to use log_factory)
                log(
                    logger=self.logger,
                    status=ValidationStatus.FAILED,
                    name=self.__class__.__name__,
                    alert_time=self.current_window_end_time,
                    step=self.current_step,
                    message="Validation failed.",
                    log_level=LogLevel.DEBUG,
                    execution_symbol=self.symbol
                )
                continue
            
            # Step 2: More validations...
            self.next_step()
            # ...
            
            # Create alert if all pass
            self.next_step()
            alert = self._create_alert_with_details(
                final_signal=Signal.BUY,
                final_trend=Trend.UPTREND,
                final_alert_candle=self.last_candle,
                final_magnitude=self.settings.magnitude_threshold,
                details=self._add_details_for_alert(...)
            )
            
            if alert is not None:
                self.alerts.append(alert)
                if not self.is_development_mode:
                    return self.alerts
        
        return self.alerts
```

### 3.5 __init__.py Module Exports

**File**: `__init__.py`

**Purpose**: Export all approach classes for easy importing from outside the module

**Requirements**:
- Use relative imports (from .filename import ClassName)
- Export all 4 classes
- Maintain alphabetical order in __all__
- Include docstring at module top

**Structure**:
```python
"""
[YOUR_APPROACH_NAME] trading approach implementation.

Exports all classes needed for [YOUR_APPROACH_NAME] approach:
- Analyzer: Pure calculations
- Executor: Main orchestration and alert finding
- Settings: Configuration loading
- Validator: Business logic validation
"""

# Relative imports from module files
from .analyzer import YourApproachAnalyzer
from .executor import YourApproachExecutor
from .settings import YourApproachSettings
from .validator import YourApproachValidator

# Export for external use (allows: from approach import YourApproachExecutor)
__all__ = [
    "YourApproachAnalyzer",
    "YourApproachExecutor",
    "YourApproachSettings",
    "YourApproachValidator",
]
```

**Key Points**:
- Always use relative imports (from .filename)
- Always list all 4 classes in __all__
- Keep imports in alphabetical order
- Include docstring at module top

---

## 📋 PART 4: IMPORTS & DEPENDENCIESfrom .executor import YourApproachExecutor
from .analyzer import YourApproachAnalyzer
from .validator import YourApproachValidator
from .settings import YourApproachSettings

__all__ = [
    'YourApproachExecutor',
    'YourApproachAnalyzer',
    'YourApproachValidator',
    'YourApproachSettings',
]
```

---

## 📋 PART 4: IMPORTS & DEPENDENCIES

### 4.1 Standard Imports

**Always use these imports**:

```python
# settings.py
from src.stockreports.alert.common.constants import Approach
from src.stockreports.alert.common.base_settings import BaseSettings

# analyzer.py
from src.stockreports.alert.analyzer import Analyzer

# validator.py
from src.stockreports.alert.validator import Validator

# executor.py
import pandas as pd
import logging
from typing import Optional

from src.stockreports.alert.executor import Executor
from src.stockreports.alert.common.constants import Approach, Signal, Trend, ValidationStatus, LogLevel
from src.stockreports.alert.model.models import AlertData, Validation
from varname import nameof
from src.stockreports.utils.log_factory import log
from .settings import YourApproachSettings
from .analyzer import YourApproachAnalyzer
from .validator import YourApproachValidator
```

### 4.2 Constants Usage

**Use these enums (NOT strings)**:

- `Approach.[APPROACH_NAME]` - e.g., `Approach.STRONG_CANDLE`
- `Signal.BUY`, `Signal.SELL`, `Signal.NEUTRAL`
- `Trend.UPTREND`, `Trend.DOWNTREND`, `Trend.NEUTRAL`
- `ValidationStatus.PASSED`, `ValidationStatus.FAILED`
- `LogLevel.DEBUG`, `LogLevel.INFO`, `LogLevel.WARNING`, `LogLevel.ERROR`
- `CandleColor.GREEN`, `CandleColor.RED`, `CandleColor.NEUTRAL`

---

## 📋 PART 5: TESTING REQUIREMENTS

### 5.1 Unit Tests

**Analyzer Tests**:
- Test each custom method with valid input
- Test edge cases (zero division, empty data, etc.)
- Verify return types

**Validator Tests**:
- Test each custom method with True/False scenarios
- Test boundary conditions (at threshold, below, above)
- Verify boolean return type

**Executor Tests**:
- Test with sample OHLCV data
- Verify returns `list[AlertData]`
- Test with insufficient data (should return empty list)
- Test development vs deployment mode

### 5.2 Test Structure

```python
import pytest
from src.stockreports.alert.approach.YOUR_APPROACH_NAME.executor import YourApproachExecutor
from src.stockreports.alert.approach.YOUR_APPROACH_NAME.analyzer import YourApproachAnalyzer
from src.stockreports.alert.approach.YOUR_APPROACH_NAME.validator import YourApproachValidator

class TestYourApproachAnalyzer:
    def test_custom_method_valid(self):
        # Test code
        pass

class TestYourApproachValidator:
    def test_validation_true(self):
        # Test code
        pass

class TestYourApproachExecutor:
    def test_executor_with_valid_data(self):
        # Test code
        pass
```

---

## 🎯 EXECUTION INSTRUCTIONS FOR AI

### When generating code, FOLLOW THESE STEPS:

1. **Parse** the approach specification (Part 1)
2. **Validate** rules fit the Executor → Analyzer → Validator pattern
3. **Generate 4 files**:
   - `settings.py` - Configuration loading
   - `analyzer.py` - Calculations (pure functions)
   - `validator.py` - Validations (pure functions)
   - `executor.py` - Orchestration (main logic)
   - `__init__.py` - Module exports

4. **Ensure**:
   - All code has type hints
   - All methods have docstrings
   - All imports are correct
   - Executor implements `_find_alerts()` (NOT override `run()`)
   - All Analyzer/Validator methods are `@staticmethod`
   - Uses base class utilities correctly
   - Follows code quality standards

5. **Include**:
   - Proper error handling
   - Logging at appropriate steps
   - Comments explaining complex logic
   - Support for both development and deployment modes

6. **Generate**:
   - Complete, working code
   - Ready to copy into repository
   - No placeholders or TODOs
   - Production quality

---

## ✅ VALIDATION CHECKLIST (AI Must Verify)

- [ ] Settings class inherits from `BaseSettings`
- [ ] Analyzer class inherits from `Analyzer`
- [ ] Validator class inherits from `Validator`
- [ ] Executor class inherits from `Executor`
- [ ] Executor implements `_find_alerts()` (not override `run()`)
- [ ] All type hints present
- [ ] All docstrings complete
- [ ] All Analyzer methods are `@staticmethod`
- [ ] All Validator methods are `@staticmethod`
- [ ] Uses base class utilities correctly
- [ ] Proper logging statements
- [ ] Development/deployment mode handling
- [ ] Alert creation with details
- [ ] Backward loop implementation
- [ ] Step and validation tracking
- [ ] Proper imports and constants
- [ ] All 4 files created
- [ ] `__init__.py` exports all classes
- [ ] Code meets quality standards
- [ ] Ready for testing

---

## 🔍 COMPARE GENERATED CODE WITH STRONG_CANDLE

**Before Moving Forward**: Compare your generated code with the working STRONG_CANDLE reference

**Location**: `src/stockreports/alert/approach/STRONG_CANDLE/`

**Quick Comparison Points** (5 minutes):
1. **File Structure**: Do you have the same 5 files? (settings.py, analyzer.py, validator.py, executor.py, __init__.py)
2. **Imports**: Are imports identical to STRONG_CANDLE in all files?
3. **Class Definitions**: Do class names and inheritance match the pattern?
4. **Type Hints**: Are complex types used the same way? (Optional, List, Dict, etc.)
5. **Docstrings**: Do docstrings follow the same 7-section format?
6. **Enums**: Are enums used the same way? (CandleColor, Comparison, CandleColumn)
7. **Static Methods**: Do Analyzer/Validator methods have @staticmethod decorator?
8. **Executor Hook**: Does Executor implement _find_alerts() like STRONG_CANDLE?

**If discrepancies found**:
- STRONG_CANDLE is the source of truth
- Regenerate code with more specific guidance
- Or manually align the generated code to match STRONG_CANDLE structure

---

## 🎯 NEXT STEPS AFTER CODE GENERATION

**After this prompt generates code:**

1. **Verify Generated Code** (5 min)
   - Check all checklist items pass
   - Review type hints and docstrings
   - Verify enum usage is correct

2. **Implement & Test** (1-2 weeks)
   - Follow testing strategy: Unit → Integration → E2E
   - Use code review checklist from `/docs/IMPLEMENTATION/IMPLEMENTATION_BEST_PRACTICES.md`
   - Reference troubleshooting guide for common issues

3. **Quality Assurance**
   - Quick checklist: See Section 1 of `IMPLEMENTATION_BEST_PRACTICES.md`
   - Code review: Use 12-point checklist in Section 12
   - Testing levels: See Section 7 (4-level testing strategy)

4. **Helpful References**
   - **Implementation Guide**: `/docs/IMPLEMENTATION/IMPLEMENTATION_BEST_PRACTICES.md`
     - Quick checklist for new approaches (10 steps)
     - Anti-patterns to avoid
     - Testing strategies and templates
     - Code review checklist
     - Troubleshooting common issues
   
   - **Case Studies**: `/docs/CASE_STUDIES/TECHNICAL_CASE_STUDIES.md`
     - Real implementation examples
     - Context management patterns
     - Type safety examples
     - Performance optimization

---

## 📝 EXAMPLE USAGE

**User Request to AI**:
```
Please generate the complete implementation of the [APPROACH_NAME] approach.

Here is the specification:

[Fill in PART 1: APPROACH SPECIFICATION]

Rules:
[Your trading rules]

Configuration:
[Your thresholds table]

Required Data:
[Your data specifications]

Generate all 4 files (settings.py, analyzer.py, validator.py, executor.py, __init__.py)
following the architecture context (PART 2) and implementation details (PART 3).
Ensure all code quality standards (PART 4) are met and validation checklist passes.
```

**AI Output**:
Complete, production-ready code for all files ready to be placed in the repository.

---

**Last Updated**: March 12, 2026  
**Status**: ✅ Ready for AI Code Generation  
**Version**: 1.0

Use this comprehensive prompt to generate end-to-end approach implementations automatically!
