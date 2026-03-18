# Approach Executor Implementation Rules - REFERENCE DOCUMENTATION

⚠️ **Status**: ARCHIVED (Rules integrated into AI_APPROACH_GENERATION_PROMPT.md)

**Last Updated**: March 13, 2026  
**Deprecation Notice**: This document is maintained as a reference archive. For new approach development, use the unified prompt in `/APPROACH_GENERATION_CODE/AI_APPROACH_GENERATION_PROMPT.md` (PART 2: Architecture Context).

---

## Original Documentation

This document defines the mandatory rules and patterns for implementing and refactoring any trading approach executor in the codebase. All rules have been integrated into the comprehensive AI approach generation prompt (Part 2).

---

## 1. Inheritance & Initialization
- All approach executors **must** inherit from `Executor`.
- The constructor initializes a settings object for the symbol and calls `super().__init__` with symbol, approach name, and settings.
- Set up a logger for standardized logging.

## 2. Main Entry (`run` function)
- The `run` function orchestrates alert finding and result packaging.
- Calls `_find_alerts` with the relevant DataFrame and new candle count.
- Returns an `AlertResult` object containing all found alerts and metadata.

## 3. Alert-Finding (`_find_alerts` function)
- Implements the main reverse loop for alert detection.
- Uses base class utility `get_loop_setup` to prepare indexed DataFrame and loop boundaries.
- For each index in the reverse loop:
    - Uses `set_window_context` (or `get_window_context`) to extract lookback window and context variables.
    - Resets and manages context variables (`current_step`, `current_window_start_time`, `current_window_end_time`).
    - Sequentially calls step functions for validation and analysis.
    - Handles both DEVELOPMENT (all alerts) and DEPLOYMENT (first alert, immediate return) modes.

## 4. Step Functions & Abstract Method Implementation
- Implements stepwise validation and analysis as separate methods (e.g., `_step_volume_validation`, `_step_trend_and_magnitude_validation`, `_step_cooldown_check`).
- Each step function:
    - Increments `current_step`.
    - Performs a specific validation or analysis.
    - Appends `Validation` objects for config-tied checks using `nameof()` for the config variable name.
    - Logs failures and passes using the centralized `log()` factory.
- Implements all required abstract methods from the base `Executor` class.

## 5. Alert Creation
- After all validations pass, constructs alert details (including serialized validations).
- Calls `_create_alert_with_details` to build the `AlertData` object.
- Appends valid alerts to `self.alerts` and updates the class-level `LATEST_ALERT`.
- If alert creation fails, logs the event.

## 6. Reverse Loop
- The main loop iterates backwards from the newest to oldest candle.
- Loop boundaries are calculated up front; no manual breaks inside the loop.
- In DEPLOYMENT mode, returns immediately after the first valid alert.

## 7. Centralized Context Management
- Context variables (`current_step`, `current_window_start_time`, `current_window_end_time`) are managed and reset at each loop iteration.
- All logging and validation steps use these context variables for traceability.
- No manual extraction; always uses base class utilities.

## 8. Configuration-Driven Logic
- All configuration parameters must be loaded from settings classes, which in turn pull from centralized config files.
- No magic numbers allowed in executor logic.

## 9. Type Consistency & Enum Handling
- **Rule**: When using utility functions that return Enum members, be consistent with type usage:
  - Use Enum members for internal logic, type hints, and comparisons (e.g., `if trend == Trend.UPTREND:`).
  - Use `.value` **only** when serializing to JSON or when a primitive string type is explicitly required.
  - **Caution**: If a utility function can return mixed types (Enum or string) depending on code paths, **avoid calling `.value`** on the result. Instead, use the variable directly in f-strings or conditionals; Python handles both types automatically.
- **Anti-pattern to avoid**: Calling `.value` on a variable that might already be a string (e.g., `f"{variable.value}"`) will cause `AttributeError: 'str' object has no attribute 'value'`.
- **Best practice**: If a utility function returns mixed types, document this in its docstring. Consider refactoring the utility to always return a consistent type (preferably the Enum member with a fallback to a default Enum value rather than None or a string).

---

All approach implementation and refactoring must strictly follow these rules.
