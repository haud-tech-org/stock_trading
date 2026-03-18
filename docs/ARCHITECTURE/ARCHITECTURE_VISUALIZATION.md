# Architecture Visualization - Diagrams and Integration Examples

**Status**: ✅ Complete Reference Document  
**Purpose**: Visual representation of system architecture and component interactions  
**Audience**: Architects, developers, and stakeholders  
**Last Updated**: March 12, 2026

---

## 🎯 System Architecture Diagram

### Overall System Flow

```
┌────────────────────────────────────────────────────────────────────────┐
│                         ALERT DETECTION SYSTEM                         │
└────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ EXTERNAL INTERFACE                                                      │
│ (REST API / Direct Python Call)                                         │
│                                                                          │
│  POST /api/analyze or call executor.run(df, new_candle_count)         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ APPROACH EXECUTOR (e.g., VraExecutor, IchimokuExecutor)                 │
│                                                                          │
│  def run(df, new_candle_count):                                        │
│  ├─ Log execution start                                                │
│  ├─ Call _find_alerts(df, new_candle_count) ◄─── Customization Hook  │
│  ├─ Format results into AlertResult                                    │
│  └─ Return with error handling                                         │
└──────────────────────────────┬──────────────────────────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
        ┌──────────────────┐   ┌──────────────────┐
        │ ANALYZER         │   │ VALIDATOR        │
        │ (Calculations)   │   │ (Verification)   │
        │                  │   │                  │
        │ • Body Ratio     │   │ • Consistency    │
        │ • Candle Color   │   │ • Thresholds     │
        │ • Window Size    │   │ • Ratios         │
        │ • Max Volume     │   │ • Volume Check   │
        └──────────────────┘   └──────────────────┘
                    │                     │
                    └──────────┬──────────┘
                               │
                               ▼
        ┌──────────────────────────────────────┐
        │ RESULTS AGGREGATION                  │
        │ ├─ List[AlertData]                   │
        │ └─ Sorted by timestamp               │
        └──────────────────────────────────────┘
                               │
                               ▼
        ┌──────────────────────────────────────┐
        │ RETURN AlertResult                   │
        │ ├─ alerts: pd.DataFrame              │
        │ ├─ confirmed_alerts: list[AlertData] │
        │ ├─ status: 'SUCCESS' or 'FAILED'     │
        │ └─ message: str                      │
        └──────────────────────────────────────┘
```

---

## 🏗️ EAV Pattern Architecture

### Executor → Analyzer → Validator

```
                     TRADING APPROACH
                            │
         ┌──────────────────┴──────────────────┐
         │                                     │
         ▼                                     │
    ┌─────────────────────────────────────┐   │
    │  EXECUTOR (Orchestration)           │   │
    │  ─────────────────────────────────  │   │
    │                                     │   │
    │  Responsibilities:                  │   │
    │  • Load market data (OHLCV)        │   │
    │  • Apply settings/configuration     │   │
    │  • Manage execution flow            │   │
    │  • Handle errors & edge cases       │   │
    │  • Return final trading signal      │   │
    │  • Manage state and logging         │   │
    │                                     │   │
    │  Key Methods:                       │   │
    │  • run()        - Template method   │   │
    │  • _find_alerts() - Hook method     │   │
    │  • _step_*()    - Validation steps  │   │
    └────────┬────────────────────────────┘   │
             │                                │
             │  Calls                         │
             │                                │
    ┌────────┴──────────┬─────────────────┐   │
    │                   │                 │   │
    ▼                   ▼                 │   │
┌──────────────┐  ┌──────────────┐       │   │
│  ANALYZER    │  │  VALIDATOR   │       │   │
│  ───────────  │  │  ──────────  │       │   │
│              │  │              │       │   │
│ Calculates:  │  │ Validates:   │       │   │
│              │  │              │       │   │
│ • Body ratio │  │ • Colors     │       │   │
│ • Body size  │  │ • Ratios     │       │   │
│ • Colors     │  │ • Thresholds │       │   │
│ • Ranges     │  │ • Volumes    │       │   │
│ • Volumes    │  │ • Trends     │       │   │
│              │  │              │       │   │
│ Returns:     │  │ Returns:     │       │   │
│ • Floats     │  │ • Booleans   │       │   │
│ • Strings    │  │ • True/False │       │   │
│ • DataFrames │  │              │       │   │
└──────────────┘  └──────────────┘       │   │
    │                   │                │   │
    └───────┬───────────┘                │   │
            │                            │   │
            │ Results Combined          │   │
            │                            │   │
            └─────────────────┬──────────┼───┘
                              │          │
                              ▼          │
                    ┌──────────────────┐ │
                    │ FINAL SIGNAL     │ │
                    │ or ALERT LIST    │ │
                    └──────────────────┘ │
                                         │
                    Return to Executor ◄─┘
```

---

## 🔄 Execution Flow Diagram

### Backward Loop Processing Pattern

```
                START
                 │
                 ▼
    ┌─────────────────────────────┐
    │ Load Configuration & Data   │
    │ • Symbol, date range        │
    │ • Settings, parameters      │
    │ • Historical candles        │
    └──────────┬──────────────────┘
               │
               ▼
    ┌─────────────────────────────┐
    │ Pre-execution Validation    │
    │ • Data sufficiency          │
    │ • Indicator calculations    │
    │ • Window size checks        │
    └──────────┬──────────────────┘
               │
               ▼
    ┌─────────────────────────────────────┐
    │ Setup Loop Boundaries               │
    │ • Start index (oldest candle)       │
    │ • End index (newest candle)         │
    │ • Lookback period                   │
    └──────────┬────────────────────────┬─┘
               │                        │
               │ Direction: BACKWARD    │
               │ (Latest → Oldest)      │
               │                        │
    ┌──────────▼─────────────────────────┐
    │ FOR each_candle in range(...)      │
    │                                    │
    │  ┌───────────────────────────────┐ │
    │  │ [Step 1] Extract Context      │ │
    │  │ • Set window                  │ │
    │  │ • Current candle              │ │
    │  │ • Lookback DataFrame          │ │
    │  └───────────────────────────────┘ │
    │                ▼                   │
    │  ┌───────────────────────────────┐ │
    │  │ [Step 2] First Validation     │ │
    │  │ • Threshold check             │ │
    │  │ • Initial filter              │ │
    │  └──────┬──────────────────────┬──┘ │
    │         │ FAIL                │      │
    │         │                     ▼      │
    │         │            ┌─────────────┐ │
    │         │            │ Continue    │ │
    │         │            │ to next     │ │
    │         │            │ candle      │ │
    │         │            └─────────────┘ │
    │         │ PASS                       │
    │         ▼                            │
    │  ┌───────────────────────────────┐ │
    │  │ [Step 3] Second Validation    │ │
    │  │ • Window analysis             │ │
    │  │ • Trend check                 │ │
    │  └──────┬──────────────────────┬──┘ │
    │         │ FAIL                │      │
    │         │                     ▼      │
    │         │            Continue loop   │
    │         │ PASS                       │
    │         ▼                            │
    │  ┌───────────────────────────────┐ │
    │  │ [Step N] Cooldown Check       │ │
    │  │ • Last alert time             │ │
    │  │ • Minimum window              │ │
    │  │ • Signal consistency          │ │
    │  └──────┬──────────────────────┬──┘ │
    │         │ IN COOLDOWN          │     │
    │         │                      ▼     │
    │         │              Continue loop │
    │         │ NOT IN COOLDOWN            │
    │         ▼                            │
    │  ┌───────────────────────────────┐ │
    │  │ Create Alert                  │ │
    │  │ • AlertData object            │ │
    │  │ • Details & metadata          │ │
    │  │ • Suggested prices            │ │
    │  └──────┬──────────────────────┬──┘ │
    │         │                      │    │
    │         └──────────┬───────────┘    │
    │                    ▼                │
    │         ┌──────────────────────┐   │
    │         │ Deployment Mode?     │   │
    │         └──────┬───────────┬───┘   │
    │              YES          NO       │
    │                │           │       │
    │                ▼           ▼       │
    │         Return Alert  Continue    │
    │         Immediately   Loop       │
    │                │           │       │
    │                └─────┬─────┘       │
    │                      ▼             │
    └──────────────────────────────────┘
               │
               ▼ (Loop End)
    ┌─────────────────────────────┐
    │ Aggregate Results           │
    │ • Reverse to chronological  │
    │ • Sort by timestamp         │
    │ • Filter duplicates         │
    └──────────┬──────────────────┘
               │
               ▼
    ┌─────────────────────────────┐
    │ Return AlertResult          │
    │ • List of alerts            │
    │ • Success/failure status    │
    │ • Error messages (if any)   │
    └──────────┬──────────────────┘
               │
               ▼
            SUCCESS
```

---

## 📊 Class Hierarchy Diagram

### Complete Executor Inheritance

```
                        Executor (ABC)
                    [src/stockreports/alert/executor.py]
                              │
                    ┌─────────┼─────────┐
                    │         │         │
        ┌───────────┴──────┐  │  ┌──────┴──────────┐
        │                  │  │  │                 │
    VraExecutor      IchimokuExecutor  ...  StrongCandleExecutor
    [Implements       [Implements            [Implements
    _find_alerts()]   _find_alerts()]        _find_alerts()]
        │                  │                  │
     VraSettings      IchimokuSettings      StrongCandleSettings
        │                  │                  │
    VraAnalyzer      IchimokuAnalyzer      StrongCandleAnalyzer
        │                  │                  │
    VraValidator     IchimokuValidator     StrongCandleValidator
```

### Base Classes (Shared)

```
Analyzer (ABC)                      Validator (ABC)
[9 Common Methods]                  [10 Common Methods]
     │                                   │
     ├─ calculate_body_ratio()          ├─ validate_candle_color_consistency()
     ├─ calculate_body_size()           ├─ validate_opposite_color_exists()
     ├─ get_candle_color()              ├─ validate_price_threshold()
     ├─ get_window_size_and_trend()     ├─ validate_ratio_threshold()
     ├─ calculate_window_price_range()  ├─ validate_volume_threshold()
     ├─ get_max_volume_in_window()      ├─ validate_volume_multiplier()
     ├─ get_max_volume_in_conditional() ├─ validate_dataframe_not_empty()
     ├─ get_opposite_color_candles()    ├─ validate_required_columns()
     └─ ...                             └─ validate_window_size()
```

---

## 🔀 Data Flow Diagram

### From Market Data to Alerts

```
┌──────────────────────────────────────┐
│  INPUT: OHLCV DataFrame              │
│  ├─ Open                             │
│  ├─ High                             │
│  ├─ Low                              │
│  ├─ Close                            │
│  ├─ Volume                           │
│  └─ Timestamp (index)                │
└──────────────────┬───────────────────┘
                   │
                   ▼
    ┌──────────────────────────────┐
    │ EXECUTOR._find_alerts()      │
    │                              │
    │ Get loop boundaries          │
    │ Loop through candles         │
    └──────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
    ┌────────┐ ┌────────┐ ┌─────────┐
    │ Analyze│ │Validate│ │ Format  │
    │ Data   │ │Results │ │ Alert   │
    └────────┘ └────────┘ └─────────┘
        │          │          │
        └──────────┼──────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │ OUTPUT: AlertData                │
    │ ├─ symbol: str                   │
    │ ├─ approach: str                 │
    │ ├─ signal: Signal (BUY/SELL)     │
    │ ├─ alert_time: Timestamp         │
    │ ├─ magnitude: float              │
    │ ├─ confidence: float             │
    │ ├─ details: dict                 │
    │ ├─ structural_suggested_price    │
    │ ├─ performance_suggested_price   │
    │ └─ suggested_profit_threshold    │
    └──────────────────────────────────┘
                   │
                   ▼
    ┌──────────────────────────────────┐
    │ OUTPUT: AlertResult              │
    │ ├─ approach_name: str            │
    │ ├─ alerts: pd.DataFrame          │
    │ ├─ confirmed_alerts: List        │
    │ ├─ status: 'SUCCESS'/'FAILED'    │
    │ └─ message: str                  │
    └──────────────────────────────────┘
```

---

## 🎯 Template Method Pattern

### Executor Pattern Illustration

```
┌─────────────────────────────────────────────────┐
│ BASE CLASS: Executor                            │
│                                                 │
│ def run(df, new_candle_count):                 │
│     ┌─────────────────────────────────────┐   │
│     │ Template Method (Fixed)              │   │
│     │                                     │   │
│     │ 1. Log execution start              │   │
│     │ 2. Call _find_alerts() ◄───────┐   │   │
│     │ 3. Log results                  │   │   │
│     │ 4. Format output                │   │   │
│     │ 5. Return result                │   │   │
│     │                                 │   │   │
│     │ 6. Exception handling           │   │   │
│     └─────────────────────────────────┘   │   │
│                                         │   │   │
│ @abstractmethod                         │   │   │
│ def _find_alerts(...):                  │   │   │
│     pass  # Hook for customization ◄────┘   │   │
│                                             │   │
└─────────────────────────────────────────────┘
                    △
                    │ Inheritance
                    │
        ┌───────────┼───────────┐
        │           │           │
    ┌───┴────────┐  │  ┌────────┴───────┐
    │ VraExecutor│  │  │ IchimokuExecutor│
    │            │  │  │                 │
    │ # Does NOT │  │  │ # Does NOT      │
    │ # override │  │  │ # override      │
    │ # run()    │  │  │ # run()         │
    │            │  │  │                 │
    │ def _find_ │  │  │ def _find_      │
    │ alerts():  │  │  │ alerts():       │
    │   # VRA    │  │  │   # ICHIMOKU    │
    │   # logic  │  │  │   # logic       │
    └────────────┘  │  └─────────────────┘

---

## 🔌 Integration Example: VRA Approach

### Component Interaction

```
User calls VraExecutor.run(df)
        │
        ▼
┌─────────────────────────────────┐
│ Executor.run() (INHERITED)      │
│ [Base class - no override]      │
│                                 │
│ 1. Log "Running VRA..."         │
│ 2. Call self._find_alerts()     │
│    (Dispatches to VRA impl)     │
│ 3. Log "Found X alerts"         │
│ 4. Return AlertResult()         │
└──────────────┬──────────────────┘
               │
               ▼
    ┌──────────────────────────┐
    │ VraExecutor._find_alerts()│
    │ [VRA-specific]           │
    │                          │
    │ for each candle:         │
    │  ├─ Step 1: Volume       │
    │  │  analyzer.calc_vol()  │
    │  │  validator.valid_vol()│
    │  │                       │
    │  ├─ Step 2: Magnitude    │
    │  │  analyzer.calc_trend()│
    │  │  validator.valid_mag()│
    │  │                       │
    │  └─ Step 3: Cooldown     │
    │     (inherited utility)  │
    │                          │
    │ return alerts            │
    └──────────────────────────┘
```

---

## 📈 Configuration Flow

### Settings Propagation

```
┌─────────────────────────────────┐
│ VraSettings                     │
│ (Extends BaseSettings)          │
│                                 │
│ ├─ volume_multiplier: 1.5      │
│ ├─ lookback_period: 20         │
│ ├─ min_magnitude: 0.02         │
│ ├─ cooldown_window: 5          │
│ └─ ... (approach-specific)     │
└──────────────┬──────────────────┘
               │
               ▼
┌─────────────────────────────────┐
│ VraExecutor.__init__(symbol)    │
│                                 │
│ self.settings = VraSettings()   │
│ super().__init__(...)           │
│   self.APPROACH_NAME = VRA      │
│   self.settings = settings      │
│                                 │
└──────────────┬──────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Executor Base Class                  │
│                                      │
│ self.is_development_mode =           │
│   settings.MODE == Mode.DEVELOPMENT  │
│                                      │
│ Access anywhere in executor          │
│ via self.settings.X                  │
└──────────────────────────────────────┘
```

---

## 🧪 Testing Isolation

### Pure Function Testing

```
┌─────────────────────────────────────────┐
│ ANALYZER (Pure Static Functions)        │
│                                         │
│ def calculate_body_ratio(candle):      │
│   # No side effects                    │
│   # Same input → Same output always   │
│   # Trivial to unit test               │
│                                         │
│ ✅ Easy to test in isolation           │
│ ✅ No mocking required                 │
│ ✅ Deterministic output                │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ VALIDATOR (Pure Logic Functions)        │
│                                         │
│ def validate_price_threshold(price):   │
│   # Boolean return                     │
│   # No state mutations                 │
│   # Simple conditional logic           │
│                                         │
│ ✅ Easy to test in isolation           │
│ ✅ No complex setup                    │
│ ✅ Can test all branches               │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│ EXECUTOR (Orchestration)                │
│                                         │
│ def run(df):                           │
│   # Uses Analyzer & Validator          │
│   # Can mock both for isolation test   │
│   # Integration tests with real data   │
│                                         │
│ ✅ Integration test capability         │
│ ✅ Can mock dependencies               │
│ ✅ End-to-end flow validation          │
└─────────────────────────────────────────┘
```

---

## 🎯 Error Handling Flow

### Exception Path

```
VraExecutor.run(df)
    │
    ▼
try:
    ├─ Log start
    ├─ Call _find_alerts()
    │   │
    │   ├─ Calculation error?
    │   │   └─ ValueError raised
    │   │       │
    │   │       └─ Caught by except
    │   │
    │   └─ Success → alerts returned
    │       │
    │       ▼
    │   Format results
    │
    ├─ Log completion
    └─ Return AlertResult(
        alerts=df,
        status='SUCCESS')

except Exception as e:
    ├─ Log error details
    │  ├─ exc_info=True
    │  ├─ Exception message
    │  └─ Stack trace
    │
    └─ Return AlertResult(
        status='FAILED',
        message=str(e))
```

---

## 🏃 Execution Modes

### Development vs. Deployment

```
┌─────────────────────────────────────┐
│ DEVELOPMENT MODE                    │
│                                     │
│ Settings.MODE = Mode.DEVELOPMENT   │
│                                     │
│ Loop Behavior:                      │
│ • Process ALL candles              │
│ • Log each step                    │
│ • Keep all validation details      │
│ • Return ALL alerts found          │
│                                     │
│ Use Case:                           │
│ • Testing                           │
│ • Debugging                         │
│ • Strategy validation               │
│ • Backtesting                       │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ DEPLOYMENT MODE                     │
│                                     │
│ Settings.MODE = Mode.DEPLOYMENT    │
│                                     │
│ Loop Behavior:                      │
│ • Stop at FIRST alert found        │
│ • Minimal logging                  │
│ • Return immediately               │
│ • Only return most recent signal   │
│                                     │
│ Use Case:                           │
│ • Live trading                      │
│ • Real-time alerts                 │
│ • Production monitoring             │
│ • Performance optimization          │
└─────────────────────────────────────┘
```

---

## 📋 Validation Pipeline

### Multi-Step Validation Example (STRONG_CANDLE)

```
Input Candle (OHLCV)
        │
        ▼
┌─────────────────────────────────────┐
│ ANALYZER - Calculate               │
│                                     │
│ body_ratio = calc_body_ratio()      │
│ body_size = calc_body_size()        │
│ color = get_candle_color()          │
│ max_vol = get_max_volume()          │
│ opp_candles = get_opposite_colors() │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│ VALIDATOR - Verify Step 1          │
│                                     │
│ validate_alert_candle_body(        │
│   body_ratio, body_size)            │
│   → returns PASS/FAIL               │
└──────────────────┬──────────────────┘
                   │ PASS
                   ▼
┌─────────────────────────────────────┐
│ VALIDATOR - Verify Step 2          │
│                                     │
│ validate_alert_candle_volume(      │
│   volume, max_vol)                  │
│   → returns PASS/FAIL               │
└──────────────────┬──────────────────┘
                   │ PASS
                   ▼
┌─────────────────────────────────────┐
│ VALIDATOR - Verify Step 3          │
│                                     │
│ validate_window_color_consistency( │
│   lookback_df, color)               │
│   → returns PASS/FAIL               │
└──────────────────┬──────────────────┘
                   │ PASS
                   ▼
┌─────────────────────────────────────┐
│ EXECUTOR - Create Alert            │
│                                     │
│ AlertData(                          │
│   signal=BUY,                       │
│   magnitude=0.025,                  │
│   details={...})                    │
└──────────────────┬──────────────────┘
                   │
                   ▼
                 ALERT
```

---

## 🔗 File Organization

### Project Structure

```
src/stockreports/alert/
│
├── executor.py                    ← Base Executor (ABC)
├── analyzer.py                    ← Base Analyzer (ABC)
├── validator.py                   ← Base Validator (ABC)
│
├── model/
│   ├── models.py                  ← AlertData, AlertResult
│   └── validation.py              ← Validation tracking
│
├── common/
│   ├── constants.py               ← Enums & constants
│   ├── base_settings.py           ← BaseSettings
│   └── data_utils.py              ← Utilities
│
└── approach/
    ├── VRA/
    │   ├── executor.py            ← VraExecutor (inherits)
    │   ├── analyzer.py            ← VraAnalyzer (inherits)
    │   ├── validator.py           ← VraValidator (inherits)
    │   └── settings.py            ← VraSettings
    │
    ├── ICHIMOKU/
    │   ├── executor.py
    │   ├── analyzer.py
    │   ├── validator.py
    │   └── settings.py
    │
    └── ... (15+ more approaches)
```

---

## 🎓 Summary

The architecture visualization shows:

1. **Separation of Concerns**: Executor, Analyzer, Validator layers
2. **Template Method Pattern**: Base class `run()`, derived class `_find_alerts()`
3. **Pure Functions**: Analyzer and Validator contain no side effects
4. **Backward Loop Processing**: Standard pattern across all approaches
5. **Inheritance Hierarchy**: All approaches inherit from base classes
6. **Configuration Management**: Settings propagate through hierarchy
7. **Error Handling**: Consistent exception management in base class
8. **Multiple Execution Modes**: Development vs. Deployment differentiation
9. **Isolation Testing**: Each layer independently testable

---

**Status:** ✅ Complete Reference Document  
**Last Updated:** March 12, 2026  
**Related Files:** ARCHITECTURE_OVERVIEW.md, DESIGN_PATTERNS_GUIDE.md

