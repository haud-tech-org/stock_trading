# Executor-Analyzer-Validator (EAV) Pattern - Technical Deep Dive

**Status**: ✅ Complete Technical Reference  
**Purpose**: Understand the technical design and implementation of the EAV pattern  
**Audience**: Developers implementing new executors, architects  
**Layer**: Layer 4 - Approach Execution  
**Last Updated**: April 10, 2026

---

## 📚 Pattern Overview

### What is the EAV Pattern?

The **Executor-Analyzer-Validator (EAV) Pattern** is a three-layer architectural pattern that separates concerns in trading approach implementation:

```
User Input
    ↓
┌─────────────────────────────────┐
│ Executor (Orchestration Layer)  │
│ • Coordinates flow              │
│ • Manages state                 │
│ • Returns final result          │
└─────────────────────────────────┘
    ↓              ↓
 Analyzer    Validator
  (Pure      (Pure Logic
 Calcs)     Verification)
    ↓              ↓
  Output ← Combined Result
```

### Core Philosophy

- **Single Responsibility**: Each class has ONE job
- **Separation of Concerns**: Orchestration ≠ Calculation ≠ Verification
- **Pure Functions**: Analyzers and Validators have no side effects
- **Inheritance-Based Reuse**: 19 common methods in base classes
- **Type Safety**: Enums instead of magic strings
- **Modularity**: Each class 20-100 lines (never monolithic)

---

## 🏗️ Layer 1: Executor (Orchestration)

### Responsibility

**Orchestrate, don't implement**. The Executor's job is to coordinate flow, not do calculations or validation.

### Typical Size

30-50 lines of code

### Characteristics

- ✅ Has dependencies on Analyzer and Validator
- ✅ Holds configuration/settings
- ✅ Manages execution flow
- ✅ Returns final trading signal
- ✅ Handles errors and edge cases
- ❌ Does NOT contain calculations
- ❌ Does NOT contain validation logic
- ❌ Does NOT contain data access logic

### Structure

```python
class ExecutorClass:
    def __init__(self, settings):
        """Initialize with settings and create analyzer/validator instances."""
        self.settings = settings
        self.analyzer = AnalyzerClass()
        self.validator = ValidatorClass()
    
    def run(self, dataframe):
        """
        Main execution method.
        1. Extract data
        2. Call analyzer for calculations
        3. Call validator for checks
        4. Combine results
        5. Return signal
        """
        # Your orchestration logic here
        pass
```

### Real Example: StrongCandleExecutor

```python
class StrongCandleExecutor:
    """
    Executor for STRONG_CANDLE approach.
    Coordinates analysis and validation to determine trading signal.
    """
    
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = StrongCandleAnalyzer()
        self.validator = StrongCandleValidator()
    
    def run(self, dataframe):
        """
        Execute STRONG_CANDLE strategy.
        
        Args:
            dataframe: OHLCV data with multiple candles
            
        Returns:
            Signal: SELL, BUY, or NEUTRAL
        """
        # Step 1: Get latest candle
        latest = dataframe.iloc[-1]
        
        # Step 2: Call analyzer to calculate metrics
        body_ratio = self.analyzer.calculate_body_ratio(latest)
        candle_color = self.analyzer.get_candle_color(latest)
        
        # Step 3: Call validator to check conditions
        checks = [
            self.validator.validate_candle_color_consistency(
                dataframe, candle_color),
            self.validator.validate_ratio_threshold(
                body_ratio, self.settings.min_body_ratio)
        ]
        
        # Step 4: Combine results and return signal
        if all(checks):
            return Signal.SELL
        return Signal.NEUTRAL
```

### Common Executor Patterns

**Pattern 1: Simple Sequence**
```python
def run(self, dataframe):
    latest = dataframe.iloc[-1]
    calc1 = self.analyzer.method1(latest)
    calc2 = self.analyzer.method2(dataframe)
    check1 = self.validator.check1(calc1, threshold1)
    check2 = self.validator.check2(calc2, threshold2)
    return Signal.SELL if (check1 and check2) else Signal.NEUTRAL
```

**Pattern 2: With Conditional Logic**
```python
def run(self, dataframe):
    latest = dataframe.iloc[-1]
    
    # First check - quick exit if fails
    if not self.validator.validate_basic(latest):
        return Signal.NEUTRAL
    
    # Second level checks
    calc1 = self.analyzer.complex_calc(dataframe)
    if self.validator.validate_threshold(calc1, self.settings.threshold):
        return Signal.SELL
    return Signal.NEUTRAL
```

**Pattern 3: Multiple Signal Types**
```python
def run(self, dataframe):
    latest = dataframe.iloc[-1]
    
    buy_checks = [
        self.validator.validate_buy_condition1(latest),
        self.validator.validate_buy_condition2(dataframe)
    ]
    
    sell_checks = [
        self.validator.validate_sell_condition1(latest),
        self.validator.validate_sell_condition2(dataframe)
    ]
    
    if all(buy_checks):
        return Signal.BUY
    elif all(sell_checks):
        return Signal.SELL
    return Signal.NEUTRAL
```

### Anti-Patterns (What NOT to do)

❌ **Anti-Pattern 1: Calculations in Executor**
```python
# WRONG!
def run(self, dataframe):
    latest = dataframe.iloc[-1]
    # Putting calculation here defeats the pattern
    body_ratio = abs(latest['close'] - latest['open']) / \
                 (latest['high'] - latest['low'])
    return check_signal(body_ratio)
```

❌ **Anti-Pattern 2: Validation Logic in Executor**
```python
# WRONG!
def run(self, dataframe):
    latest = dataframe.iloc[-1]
    color = get_color(latest)
    # Putting validation here defeats the pattern
    if color == CandleColor.GREEN and latest['volume'] > 1000000:
        return Signal.SELL
    return Signal.NEUTRAL
```

❌ **Anti-Pattern 3: Too Many Concerns**
```python
# WRONG!
def run(self, dataframe):
    # Loading data
    df_filtered = filter_data(dataframe)
    # Transforming
    df_normalized = normalize(df_filtered)
    # Calculating
    values = calculate_all(df_normalized)
    # Validating
    checks = validate_all(values)
    # Error handling
    try:
        result = combine(checks)
    except:
        return Signal.NEUTRAL
    # Way too much!
```

---

## 🧮 Layer 2: Analyzer (Pure Calculation)

### Responsibility

**Calculate values with no business logic**. The Analyzer performs numerical calculations and transformations.

### Typical Size

20-80 lines of code (many inherit 9 base methods as-is)

### Characteristics

- ✅ All methods are `@staticmethod` (no instance state)
- ✅ No conditional logic based on thresholds
- ✅ Returns calculated values (numbers, colors, DataFrames)
- ✅ Pure functions (same input → same output always)
- ✅ Input: candle dict/row or DataFrame
- ✅ Output: float, int, CandleColor, or DataFrame
- ❌ No business logic (no if/else based on thresholds)
- ❌ No validation (just calculations)
- ❌ No instance state

### Base Analyzer Class (9 Methods)

```python
class Analyzer:
    """Base class for all analyzers - 220 lines, 9 methods."""
    
    @staticmethod
    def calculate_body_ratio(candle: dict) -> float:
        """
        Calculate body ratio: body_size / hl_range
        
        Args:
            candle: {"open": 100, "close": 105, "high": 108, "low": 98}
        
        Returns:
            0.667 (body 5 / hl_range 10)
        """
        body = abs(candle[CandleColumn.CLOSE] - candle[CandleColumn.OPEN])
        hl_range = candle[CandleColumn.HIGH] - candle[CandleColumn.LOW]
        return body / hl_range if hl_range > 0 else 0.0
    
    @staticmethod
    def calculate_body_size(candle: dict) -> float:
        """Calculate body size: |close - open|"""
        return abs(candle[CandleColumn.CLOSE] - candle[CandleColumn.OPEN])
    
    @staticmethod
    def get_candle_color(candle: dict) -> CandleColor:
        """Determine candle color: GREEN if close > open, RED otherwise"""
        if candle[CandleColumn.CLOSE] > candle[CandleColumn.OPEN]:
            return CandleColor.GREEN
        return CandleColor.RED
    
    @staticmethod
    def calculate_window_price_range(dataframe: pd.DataFrame) -> float:
        """Calculate price range across entire window"""
        return dataframe[CandleColumn.HIGH].max() - \
               dataframe[CandleColumn.LOW].min()
    
    @staticmethod
    def get_max_volume_in_window(dataframe: pd.DataFrame) -> float:
        """Find maximum volume in window"""
        return dataframe[CandleColumn.VOLUME].max()
    
    @staticmethod
    def get_trend_direction(dataframe: pd.DataFrame) -> str:
        """Determine trend: UP, DOWN, or SIDEWAYS"""
        first_close = dataframe.iloc[0][CandleColumn.CLOSE]
        last_close = dataframe.iloc[-1][CandleColumn.CLOSE]
        
        if abs(last_close - first_close) / first_close < 0.01:
            return "SIDEWAYS"
        return "UP" if last_close > first_close else "DOWN"
    
    @staticmethod
    def get_opposite_color_candles(
        dataframe: pd.DataFrame,
        filter_color: CandleColor
    ) -> pd.DataFrame:
        """Return candles of opposite color"""
        opposite = CandleColor.RED if filter_color == CandleColor.GREEN \
                   else CandleColor.GREEN
        
        mask = dataframe.apply(
            lambda row: Analyzer.get_candle_color(row) == opposite,
            axis=1
        )
        return dataframe[mask]
    
    @staticmethod
    def calculate_average_volume_in_window(dataframe: pd.DataFrame) -> float:
        """Calculate average volume across window"""
        return dataframe[CandleColumn.VOLUME].mean()
    
    @staticmethod
    def get_price_at_position(
        dataframe: pd.DataFrame,
        position: int,
        price_type: str = CandleColumn.CLOSE
    ) -> float:
        """Get specific price at position (0-indexed from start)"""
        return dataframe.iloc[position][price_type]
```

### Derived Analyzer: StrongCandleAnalyzer

```python
class StrongCandleAnalyzer(Analyzer):
    """
    Analyzer for STRONG_CANDLE approach.
    Inherits all 9 base methods.
    """
    
    # This approach reuses all 9 base methods - no custom methods needed!
    # Inherits: calculate_body_ratio, calculate_body_size, get_candle_color,
    #           calculate_window_price_range, get_max_volume_in_window,
    #           get_trend_direction, get_opposite_color_candles,
    #           calculate_average_volume_in_window, get_price_at_position
    pass
```

### Extended Analyzer: ICHIMOKU Example

```python
class IchimokuAnalyzer(Analyzer):
    """
    Analyzer for ICHIMOKU approach.
    Inherits 9 base methods + adds 5 custom methods.
    """
    
    # Inherits all 9 base methods automatically
    
    @staticmethod
    def calculate_tenkan_sen(dataframe: pd.DataFrame, period: int = 9) -> float:
        """Tenkan-sen: (9-period high + 9-period low) / 2"""
        high9 = dataframe[CandleColumn.HIGH].tail(period).max()
        low9 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high9 + low9) / 2
    
    @staticmethod
    def calculate_kijun_sen(dataframe: pd.DataFrame, period: int = 26) -> float:
        """Kijun-sen: (26-period high + 26-period low) / 2"""
        high26 = dataframe[CandleColumn.HIGH].tail(period).max()
        low26 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high26 + low26) / 2
    
    @staticmethod
    def calculate_senkou_span_a(
        dataframe: pd.DataFrame
    ) -> float:
        """Senkou Span A: (Tenkan-sen + Kijun-sen) / 2"""
        tenkan = IchimokuAnalyzer.calculate_tenkan_sen(dataframe)
        kijun = IchimokuAnalyzer.calculate_kijun_sen(dataframe)
        return (tenkan + kijun) / 2
    
    @staticmethod
    def calculate_senkou_span_b(
        dataframe: pd.DataFrame,
        period: int = 52
    ) -> float:
        """Senkou Span B: (52-period high + 52-period low) / 2"""
        high52 = dataframe[CandleColumn.HIGH].tail(period).max()
        low52 = dataframe[CandleColumn.LOW].tail(period).min()
        return (high52 + low52) / 2
    
    @staticmethod
    def calculate_chikou_span(dataframe: pd.DataFrame) -> float:
        """Chikou Span: Close plotted 26 periods back"""
        if len(dataframe) >= 26:
            return dataframe.iloc[-26][CandleColumn.CLOSE]
        return dataframe.iloc[0][CandleColumn.CLOSE]
```

### Pure Function Guarantees

- ✅ **Deterministic**: Same input always produces same output
- ✅ **No Side Effects**: Doesn't modify external state
- ✅ **Reproducible**: Can run offline or in tests
- ✅ **Trivial to Test**: Just test input/output pairs
- ✅ **Parallelizable**: Can run multiple analyzers simultaneously

### Usage in Executor

```python
# In StrongCandleExecutor.run():
body_ratio = self.analyzer.calculate_body_ratio(latest)
color = self.analyzer.get_candle_color(latest)
max_volume = self.analyzer.get_max_volume_in_window(dataframe)
avg_volume = self.analyzer.calculate_average_volume_in_window(dataframe)
```

---

## ✓ Layer 3: Validator (Pure Verification)

### Responsibility

**Verify business logic conditions with no calculations**. The Validator checks if conditions are met.

### Typical Size

25-100 lines of code (many inherit 10 base methods as-is)

### Characteristics

- ✅ All methods are `@staticmethod` (no instance state)
- ✅ No calculations, only comparisons
- ✅ Returns boolean only (True/False)
- ✅ Takes enums instead of strings (type-safe)
- ✅ Pure functions (no side effects)
- ✅ Input: values and thresholds
- ✅ Output: boolean (condition met or not)
- ❌ No calculations
- ❌ No instance state
- ❌ No default values on required parameters

### Base Validator Class (10 Methods)

```python
class Validator:
    """Base class for all validators - 240 lines, 10 methods."""
    
    @staticmethod
    def validate_candle_color_consistency(
        dataframe: pd.DataFrame,
        target_color: CandleColor
    ) -> bool:
        """
        Check if most candles in window are target_color.
        
        Args:
            dataframe: OHLCV data
            target_color: Expected color (GREEN or RED)
        
        Returns:
            True if >= 50% candles are target_color
        """
        analyzer = Analyzer()
        target_candles = 0
        
        for _, row in dataframe.iterrows():
            if analyzer.get_candle_color(row) == target_color:
                target_candles += 1
        
        return target_candles >= len(dataframe) / 2
    
    @staticmethod
    def validate_price_threshold(
        price: float,
        threshold: float,
        comparison: Comparison
    ) -> bool:
        """
        Compare price against threshold using comparison.
        
        Args:
            price: Actual price value
            threshold: Threshold to compare against
            comparison: Comparison.GREATER, LESS, EQUAL, etc.
        
        Returns:
            True if condition is met
        """
        if comparison == Comparison.GREATER:
            return price > threshold
        elif comparison == Comparison.LESS:
            return price < threshold
        elif comparison == Comparison.EQUAL:
            return price == threshold
        elif comparison == Comparison.GREATER_EQUAL:
            return price >= threshold
        elif comparison == Comparison.LESS_EQUAL:
            return price <= threshold
        return False
    
    @staticmethod
    def validate_volume_threshold(
        volume: float,
        threshold: float,
        comparison: Comparison
    ) -> bool:
        """Compare volume against threshold"""
        return Validator.validate_price_threshold(
            volume, threshold, comparison
        )
    
    @staticmethod
    def validate_ratio_threshold(
        ratio: float,
        threshold: float,
        comparison: Comparison = Comparison.GREATER
    ) -> bool:
        """Compare ratio (usually body_ratio) against threshold"""
        return Validator.validate_price_threshold(
            ratio, threshold, comparison
        )
    
    @staticmethod
    def validate_volume_multiplier(
        current_volume: float,
        average_volume: float,
        multiplier: float
    ) -> bool:
        """
        Check if current volume is X times the average.
        
        Args:
            current_volume: Current period volume
            average_volume: Average volume
            multiplier: How many times (e.g., 1.5)
        
        Returns:
            True if current >= average * multiplier
        """
        return current_volume >= average_volume * multiplier
    
    @staticmethod
    def validate_required_columns(
        dataframe: pd.DataFrame,
        required_columns: List[str]
    ) -> bool:
        """Check if DataFrame has all required columns"""
        return all(col in dataframe.columns for col in required_columns)
    
    @staticmethod
    def validate_minimum_window_size(
        dataframe: pd.DataFrame,
        min_size: int
    ) -> bool:
        """Check if DataFrame has minimum required rows"""
        return len(dataframe) >= min_size
    
    @staticmethod
    def validate_no_null_values(
        dataframe: pd.DataFrame,
        columns: List[str]
    ) -> bool:
        """Check if specified columns have no null values"""
        return not dataframe[columns].isnull().any().any()
    
    @staticmethod
    def validate_price_range(
        price: float,
        min_price: float,
        max_price: float
    ) -> bool:
        """Check if price is within range"""
        return min_price <= price <= max_price
    
    @staticmethod
    def validate_data_recency(
        last_timestamp: datetime,
        max_age_minutes: int
    ) -> bool:
        """Check if data is recent enough"""
        age = (datetime.now() - last_timestamp).total_seconds() / 60
        return age <= max_age_minutes
```

### Type-Safe Parameter Pattern

**❌ OLD WAY: String Parameters (Ambiguous)**
```python
# What does "greater" mean? Hard to remember, easy to typo
validator.validate_price_threshold(100.5, 100.0, "greater")
validator.validate_price_threshold(100.5, 100.0, "gt")
validator.validate_price_threshold(100.5, 100.0, ">")  # Inconsistent!
```

**✅ NEW WAY: Enum Parameters (Crystal Clear)**
```python
# No ambiguity, IDE autocomplete, type checking
validator.validate_price_threshold(100.5, 100.0, Comparison.GREATER)
validator.validate_price_threshold(100.5, 100.0, Comparison.GREATER_EQUAL)
validator.validate_price_threshold(100.5, 100.0, Comparison.LESS)
```

### Required Parameters (No Defaults!)

**❌ OLD WAY: Default Values (Silent Bugs)**
```python
def validate_price_threshold(price, threshold, comparison="greater"):
    # Developer forgets to specify comparison
    result = validator.validate_price_threshold(100.5, 100.0)
    # Silently uses "greater" - developer might expect different comparison!
```

**✅ NEW WAY: No Defaults (Explicit Required)**
```python
def validate_price_threshold(price: float, threshold: float, 
                            comparison: Comparison) -> bool:
    # No default - developer MUST specify
    # IDE catches if comparison forgotten
    result = validator.validate_price_threshold(100.5, 100.0)
    # ERROR: missing required argument 'comparison'
```

### Derived Validator: StrongCandleValidator

```python
class StrongCandleValidator(Validator):
    """
    Validator for STRONG_CANDLE approach.
    Inherits all 10 base methods.
    """
    
    # This approach reuses all 10 base methods
    # Inherits: validate_candle_color_consistency, validate_price_threshold,
    #           validate_volume_threshold, validate_ratio_threshold,
    #           validate_volume_multiplier, validate_required_columns,
    #           validate_minimum_window_size, validate_no_null_values,
    #           validate_price_range, validate_data_recency
    pass
```

### Extended Validator: ICHIMOKU Example

```python
class IchimokuValidator(Validator):
    """
    Validator for ICHIMOKU approach.
    Inherits 10 base methods + adds 3 custom methods.
    """
    
    # Inherits all 10 base methods automatically
    
    @staticmethod
    def validate_ichimoku_signal(
        current_price: float,
        senkou_a: float,
        senkou_b: float
    ) -> bool:
        """
        Validate Ichimoku signal: price above Senkou Span.
        
        Args:
            current_price: Current close price
            senkou_a: Senkou Span A value
            senkou_b: Senkou Span B value
        
        Returns:
            True if price > both Senkou values
        """
        upper_band = max(senkou_a, senkou_b)
        return current_price > upper_band
    
    @staticmethod
    def validate_tenkan_kijun_crossover(
        tenkan: float,
        kijun: float,
        is_bullish: bool
    ) -> bool:
        """
        Validate Tenkan-Kijun crossover.
        
        Args:
            tenkan: Tenkan-sen value
            kijun: Kijun-sen value
            is_bullish: True for bullish crossover (tenkan > kijun),
                       False for bearish (tenkan < kijun)
        
        Returns:
            True if crossover matches direction
        """
        if is_bullish:
            return tenkan > kijun
        else:
            return tenkan < kijun
    
    @staticmethod
    def validate_chikou_signal(
        chikou: float,
        current_price: float,
        is_above: bool
    ) -> bool:
        """
        Validate Chikou Span signal.
        
        Args:
            chikou: Chikou Span value
            current_price: Current close price
            is_above: True if chikou should be above price
        
        Returns:
            True if condition matches
        """
        if is_above:
            return chikou > current_price
        else:
            return chikou < current_price
```

### Usage in Executor

```python
# In StrongCandleExecutor.run():
check1 = self.validator.validate_candle_color_consistency(
    dataframe, CandleColor.GREEN
)
check2 = self.validator.validate_ratio_threshold(
    body_ratio, self.settings.min_body_ratio, Comparison.GREATER
)
check3 = self.validator.validate_volume_multiplier(
    current_volume, avg_volume, 1.5
)
```

---

## 🎯 Pattern Application Decision Tree

```
START: Need a new trading approach?
│
├─ Step 1: Identify base requirements
│   ├─ Uses OHLCV data? → YES
│   ├─ Needs color classification? → Probably YES
│   ├─ Needs threshold validation? → Probably YES
│   └─ Needs volume analysis? → Maybe
│
├─ Step 2: Review base Analyzer methods (9 available)
│   ├─ calculate_body_ratio ✓
│   ├─ calculate_body_size ✓
│   ├─ get_candle_color ✓
│   ├─ calculate_window_price_range ✓
│   ├─ get_max_volume_in_window ✓
│   ├─ get_trend_direction ✓
│   ├─ get_opposite_color_candles ✓
│   ├─ calculate_average_volume_in_window ✓
│   └─ get_price_at_position ✓
│
├─ Step 3: Review base Validator methods (10 available)
│   ├─ validate_candle_color_consistency ✓
│   ├─ validate_price_threshold ✓
│   ├─ validate_volume_threshold ✓
│   ├─ validate_ratio_threshold ✓
│   ├─ validate_volume_multiplier ✓
│   ├─ validate_required_columns ✓
│   ├─ validate_minimum_window_size ✓
│   ├─ validate_no_null_values ✓
│   ├─ validate_price_range ✓
│   └─ validate_data_recency ✓
│
├─ Step 4: Determine custom needs
│   ├─ Need custom analyzer methods? → Add to Analyzer
│   ├─ Need custom validator methods? → Add to Validator
│   └─ Need complex orchestration? → Expand Executor
│
├─ Step 5: Build structure
│   ├─ Create Executor (30-50 lines)
│   ├─ Create Analyzer (inherit or extend)
│   ├─ Create Validator (inherit or extend)
│   └─ Total: typically 75-230 lines (clean & maintainable)
│
└─ Step 6: Test
    ├─ Unit test Analyzer methods (pure functions)
    ├─ Unit test Validator methods (pure functions)
    ├─ Integration test Executor
    └─ Test on real data
```

---

## 📊 Real-World Example: STRONG_CANDLE Complete

### Before Pattern: Monolithic (454 lines)

```python
class StrongCandleAlert:  # 454 lines of everything!
    """All concerns mixed: data loading, calculations, validation, signals."""
    
    def run(self, dataframe):
        # Lines 1-50: Data loading and validation
        # Lines 51-150: Calculations (body_ratio, color, etc.)
        # Lines 151-350: Validation logic (if this then that)
        # Lines 351-400: Signal generation
        # Lines 401-454: Error handling
        pass
```

**Problems:**
- ❌ 454 lines in one class (hard to understand)
- ❌ Calculations mixed with validation (hard to test)
- ❌ Validation mixed with orchestration (hard to reuse)
- ❌ Error handling everywhere (hard to maintain)
- ❌ Cannot test individual pieces

### After Pattern: Modular (107 lines total)

**Executor** (43 lines):
```python
class StrongCandleExecutor:
    """43 lines: Pure orchestration."""
    
    def __init__(self, settings):
        self.settings = settings
        self.analyzer = StrongCandleAnalyzer()
        self.validator = StrongCandleValidator()
    
    def run(self, dataframe):
        latest = dataframe.iloc[-1]
        body_ratio = self.analyzer.calculate_body_ratio(latest)
        candle_color = self.analyzer.get_candle_color(latest)
        
        checks = [
            self.validator.validate_candle_color_consistency(
                dataframe, candle_color),
            self.validator.validate_ratio_threshold(
                body_ratio, self.settings.min_body_ratio)
        ]
        
        return Signal.SELL if all(checks) else Signal.NEUTRAL
```

**Analyzer** (29 lines):
```python
class StrongCandleAnalyzer(Analyzer):
    """29 lines: Inherits all 9 base methods."""
    pass  # That's it!
```

**Validator** (35 lines):
```python
class StrongCandleValidator(Validator):
    """35 lines: Inherits all 10 base methods."""
    pass  # That's it!
```

### Results Comparison

```
                Before    After    Reduction
────────────────────────────────────────────
Total Lines:    454       107      -76%
Complexity:     High      Low      Clear separation
Testability:    Difficult Easy     Pure functions
Reusability:    0%        100%     Inherits 19 methods
Readability:    Poor      Excellent <50 lines each
```

---

## ✅ Pattern Checklist

Use this checklist when implementing a new approach:

### Executor Implementation
- [ ] 30-50 lines maximum
- [ ] No calculations (delegated to Analyzer)
- [ ] No validation logic (delegated to Validator)
- [ ] Clear orchestration flow (easy to follow)
- [ ] Initializes Analyzer and Validator
- [ ] Calls analyzer for all calculations
- [ ] Calls validator for all checks
- [ ] Combines results into final signal
- [ ] Handles errors gracefully
- [ ] No hardcoded values (uses settings)

### Analyzer Implementation
- [ ] All methods are `@staticmethod`
- [ ] No instance state
- [ ] No conditional logic based on thresholds
- [ ] Returns values (numbers, colors, DataFrames)
- [ ] Uses enums (CandleColumn, CandleColor)
- [ ] Pure functions (same input → same output)
- [ ] Inherits all 9 base methods
- [ ] Custom methods only if truly needed
- [ ] All methods documented with type hints
- [ ] 20-80 lines total

### Validator Implementation
- [ ] All methods are `@staticmethod`
- [ ] No instance state
- [ ] No calculations (only comparisons)
- [ ] Returns boolean only
- [ ] Uses enums (Comparison, CandleColor)
- [ ] Required parameters (no defaults)
- [ ] Pure functions (no side effects)
- [ ] Inherits all 10 base methods
- [ ] Custom methods only if truly needed
- [ ] All methods documented with type hints
- [ ] 25-100 lines total

### Type Safety
- [ ] No magic strings for colors
- [ ] No magic strings for comparisons
- [ ] No magic strings for columns
- [ ] All enums used correctly
- [ ] Type hints on all parameters
- [ ] Return types specified
- [ ] IDE autocomplete works

### Testing
- [ ] All Analyzer methods have unit tests
- [ ] All Validator methods have unit tests
- [ ] Executor tested with mock Analyzer/Validator
- [ ] Integration tests on real data
- [ ] Edge cases covered (empty data, null values, etc.)
- [ ] Performance tests (no N² algorithms)

---

## 🔗 Related Documentation

- **DESIGN_PATTERNS_GUIDE.md** (root) - Pattern overview and philosophy
- **EAV_PATTERN_STEP_BY_STEP.md** - Implementation walkthrough
- **CODE_QUALITY_STANDARDS.md** - All code quality requirements
- **EXECUTOR_PATTERN_OVERVIEW.md** - Pattern diagrams and examples
- **ABSTRACT_BASE_CLASSES_ARCHITECTURE.md** - All 19 base methods

---

## 📝 Summary

The **Executor-Analyzer-Validator (EAV) Pattern** provides a proven, scalable approach for implementing trading strategies:

1. **Executor** orchestrates, doesn't implement (30-50 lines)
2. **Analyzer** calculates, has no side effects (20-80 lines)
3. **Validator** verifies, returns booleans (25-100 lines)
4. **Result**: 75-230 lines, clean, testable, reusable code
5. **Inheritance**: 19 common methods available in base classes
6. **Type Safety**: Enums throughout, no magic strings
7. **Maintenance**: Changes to base classes benefit all approaches

---

**Status**: ✅ Complete technical reference  
**Recommended Reading Time**: 30-40 minutes  
**Difficulty Level**: Intermediate (assumes OOP knowledge)  
**Next**: See EAV_PATTERN_STEP_BY_STEP.md for implementation walkthrough
