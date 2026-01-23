# Prompt Guide: Refactoring an Existing Alert Approach

## 1. Objective

The goal of this task is to refactor an existing alert approach executor to align it with the latest architectural standards and best practices of the project. This ensures all executors are consistent, maintainable, reliable, and easy to debug.

## 2. Mandatory Rules & Best Practices

Before making any code changes, you **must** review the [Technical Case Studies & Issue Resolution Log](../case-studies/TECHNICAL_CASE_STUDIES.md). The patterns documented in this file are not suggestions; they are **mandatory rules** for all executors.

The refactoring must strictly adhere to the following:

-#### Rule 1: Implement Standardized Logging and Centralized Context Management
-   **Reference**: Case Study `1. Standardized Logging and Centralized Context Management`.
-   **Action**: The executor **MUST** be refactored to use the project's standard logging and context management pattern. This is the highest priority.
#### Rule 1: Implement Standardized Logging, Loop, and Window Context Management
   **Reference**: Case Study `1. Standardized Logging and Centralized Context Management`.
   **Action**: The executor **MUST** be refactored to use the project's standard logging, loop setup, and window context management pattern. This is the highest priority.
    -   All logging calls **MUST** use the `log()` factory from `src/stockreports/utils/log_factory.py`.
    -   The class **MUST** implement and use the `current_step`, `current_window_start_time`, and `current_window_end_time` attributes.
    -   The main loop **MUST** use the base class utility `get_loop_setup` to prepare the indexed DataFrame and loop boundaries, with standardized comments:
        ```python
        # --- Standardized loop setup ---
        # Use base class utility to prepare indexed DataFrame and loop boundaries
        df_indexed, loop_start, loop_end = self.get_loop_setup(...)
        ```
    -   Each window iteration **MUST** use the base class utility `get_window_context` to extract the lookback window, boundary candles, and context variables, with standardized comments:
        ```python
        # --- Standardized window context extraction ---
        # Use base class utility to extract lookback window, boundary candles, and context variables
        (
            lookback_window_df,
            first_candle,
            last_candle,
            self.current_window_start_time,
            self.current_window_end_time,
            self.current_step
        ) = self.get_window_context(i, df_indexed, lookback_window_size)
        ```
    -   Manual extraction of loop boundaries or window context is forbidden; always use the base class utilities.
    -   These context variables **MUST** be reset at the beginning of each main loop iteration.
    -   The `current_step` **MUST** be incremented sequentially for each validation step.

#### Rule 2: Implement Standardized Logging and Centralized Context Management
-   **Reference**: Case Study `1. Standardized Logging and Centralized Context Management`.
-   **Action**: The executor **MUST** be refactored to use the project's standard logging and context management pattern. This is the highest priority.
    -   All logging calls **MUST** use the `log()` factory from `src/stockreports/utils/log_factory.py`.
    -   The class **MUST** implement and use the `current_step`, `current_window_start_time`, and `current_window_end_time` attributes.
    -   These context variables **MUST** be reset at the beginning of each main loop iteration.
    -   The `current_step` **MUST** be incremented sequentially for each validation step.

#### Rule 3: Implement the Standardized Cooldown Logic
-   **Reference**: Case Study `c. Standardized Cooldown Logic for Alert Generation`.
-   **Action**: The executor **must** use the standard cooldown pattern. This includes:
    -   A class-level `LATEST_ALERT: Optional[AlertData]` variable.
    -   A pre-alert check that validates both the `cooldown_window` and the `signal` type.
    -   Updating `LATEST_ALERT` only after a new alert is successfully generated.

#### Rule 4: Encapsulate AlertData Creation
-   **Reference**: Case Study `d. Best Practice: Encapsulate Complex Object Creation`.
-   **Action**: The creation of `AlertData` objects **must** be moved into a dedicated private helper method (e.g., `_create_alert_data`). The main algorithm loop should be clean and focused on signal detection, not object population.

#### Rule 5: Prioritize Shared Utilities
-   **Reference**: Case Study `e. Best Practice: Prioritize Shared Utilities Over Custom Logic`.
-   **Action**: You **must** identify any custom or duplicated logic within the executor that could be replaced by a shared utility. For example, if the executor has its own reversal logic, it must be replaced with a call to the standard `validate_reversal_confirmation` function.

#### Rule 6: Adhere to the Standard Documentation Format
-   **Reference**: [VRA Approach Documentation](../algorithms/VRA.md)
-   **Action**: Any new or updated documentation for an approach **must** follow the established content structure. This includes the `Objective`, `Key Parameters` (in a table), `Step-by-Step Logic`, and `Flow Diagram` sections.

#### Rule 7: Ensure Complete and Consistent Data
-   **Action**: Every `AlertData` object generated by the executor **must** be fully populated. This includes, but is not limited to, `start_time`, `start_price`, and `magnitude`. The logic for calculating these values must be consistent with the definitions established in other standardized executors.

## 3. Refactoring Workflow

Follow these steps to perform the refactoring:

1.  **Analyze**: Thoroughly read the target executor's source code and compare its implementation against the mandatory rules outlined above.
2.  **Identify Deviations**: Create a mental or written list of all the parts of the code that do not conform to the established patterns.
3.  **Refactor**: Modify the code to implement the required changes. This may involve:
    -   Adding or modifying the settings in the approach's `settings.py` and the main `signal_settings.py`.
    -   Restructuring the main execution loop.
    -   Creating new helper methods.
    -   Replacing custom logic with calls to shared utilities.
4.  **Validate**: After refactoring, run the corresponding debug script for the approach to ensure that it still functions correctly and that no regressions have been introduced.

## 4. References

- For a log of common technical issues and their resolutions, which can help in avoiding common pitfalls, refer to the [Technical Case Studies & Issue Resolution Log](../case-studies/TECHNICAL_CASE_STUDIES.md).
- For an example of a standardized, well-structured documentation file for an approach, see the [Price Gap Approach Documentation](../algorithms/PRICE_GAP.md).

## Pre-refactoring Checklist
1.  **Review Case Studies**: Before modifying any code, consult the **[Technical Case Studies & Issue Resolution Log](../../case-studies/TECHNICAL_CASE_STUDIES.md)** and the **[Code Generation Guidelines](./CODE_GENERATION_GUIDELINES.md)** to internalize past lessons and current best practices.
2.  **Identify the Target**: Confirm with the user the specific approach to be refactored (e.g., `VRA`, `PriceGap`).
3.  **Understand the Goal**: Ask the user for the primary objective of the refactoring. Is it to:
    -   Improve performance?
    -   Reduce complexity?
    -   Fix bugs?
    -   Align with new business requirements?
4.  **Backup the Original**: Ensure that the original code is backed up or version-controlled before any changes are made.
5.  **Communicate**: Keep open lines of communication with the user for clarifications and updates throughout the refactoring process.
