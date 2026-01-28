# Prompt Guide: Generating a New Trading Approach (Class-Based Executors)

## 0. Prompt for new Approach Code Generatiion
Here’s a standardized prompt you can use to request robust, precise, and constraint-driven code generation for a new approach:

---
> I want to add a new alert approach to the codebase (e.g., `src/stockreports/alert/approach/NEW_APPROACH`).  
> Please generate all necessary code, configuration, and documentation for this new approach, strictly following:
>
> - The rules and requirements in APPROACH_EXECUTOR_RULES.md
> - The stepwise guidance in NEW_APPROACH_GENERATION_GUIDE.md
> - Any relevant patterns and lessons from TECHNICAL_CASE_STUDIES.md
> - The structure and best practices from reference approaches (e.g., VRA, VOLUME_SPIKE_CONFIRMATION)
>
> **Constraints:**
> - Enforce all validation, logging, and output formatting rules as described in the prompts.
> - Use centralized settings and configuration patterns.
> - Ensure the debug script is standardized and compatible with the generic debug executor.
> - Keep code and documentation in sync.
> - Provide a summary of all steps, rationale, and any edge cases handled.
>
> **Deliverables:**
> - All code files for the new approach (executor, settings, etc.)
> - Any required updates to configuration or documentation
> - Example usage and test/debug instructions
> - A checklist showing how each prompt/rule/case study requirement was satisfied

---

You can copy, modify, and reuse this template for any future new approach requests to ensure strict, robust, and prompt-driven code generation.

## 1. Objective

This document provides a comprehensive template and a step-by-step guide for creating a new trading approach by inheriting from the base `Executor` class. By following this pattern, developers can ensure that new strategies are consistent, maintainable, and integrate seamlessly with the existing alert generation, configuration, and analysis systems.

## 2. Core Principles of an Approach Executor

> **STRICT RULE:** All new approach implementations must comply with [APPROACH_EXECUTOR_RULES.md](APPROACH_EXECUTOR_RULES.md). This document defines the mandatory patterns and requirements for all approach executors. Any deviation is not permitted.

### 2A. Standardized Validation Tracking and Serialization

All approach executors **MUST** follow these rules for validation tracking and serialization:

1. **Setting-Based Validation Only**: Only create `Validation` objects for checks that are directly tied to a configuration setting (e.g., thresholds, window sizes, multipliers). For logic-only checks (not tied to a setting), do **not** create a `Validation` object—log the failure only.
2. **Automated Naming**: Use the `varname` library's `nameof` function to set the `name` field of each `Validation` to the exact config variable name (e.g., `nameof(self.settings.volume_multiplier)`).
3. **Serialization**: When constructing `AlertData`, serialize all validations using `[v.to_json() for v in self.validations]` and include this in the `details` field (as a JSON array under the key `validations`).
4. **Canonical Example**: See the VRA executor for a reference implementation of this pattern.

#### Example:
```python
self.validations.append(Validation(
    name=nameof(self.settings.volume_multiplier),
    step=self.current_step,
    validation=self.validation_step,
    message="Volume ratio is significant.",
    status=ValidationStatus.PASSED
))

alert_data = AlertData(
    # ...
    details=json.dumps({
        # ...
        "validations": [v.to_json() for v in self.validations]
    })
)

5. **All structural, initialization, loop, context management, step function, alert creation, and configuration-driven logic must strictly follow the patterns and requirements defined in [APPROACH_EXECUTOR_RULES.md](APPROACH_EXECUTOR_RULES.md).**

```

### 2B. Structural inheritance class

Every approach executor (`executor.py`) **MUST** be a class that inherits from `src.stockreports.alert.executor.Executor` and adheres to the following principles:

-   **Configuration-Driven**: All key parameters (lookback periods, thresholds, feature flags) **MUST** be defined in `src/stockreports/config/signal_settings.py` and loaded via a dedicated settings class for the approach. Hard-coded "magic numbers" are **STRICTLY FORBIDDEN**.
-   **Stateful but Pure Analysis**: The `Executor` instance holds state for a single symbol (like the last alert time), but the core analysis logic within the `run` method should be pure. Given the same DataFrame and configuration, it **MUST** always produce the same `AlertResult`.
-   **Unified Reverse Loop**: The main loop for finding alerts **MUST** be a **reverse loop** (from the latest candle to the oldest). This single loop must efficiently handle both `DEVELOPMENT` mode (find all historical alerts) and `DEPLOYMENT` mode (find only the most recent alert and exit immediately).
    -   **Loop Logic**: The loop range should be calculated upfront.
        ```python
        # Calculate loop_start based on mode
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In deployment, scan only new candles (minus offset if needed)
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - offset)

        # Iterate backwards
        for i in range(loop_end, loop_start - 1, -1):
            # ... analysis ...
        ```
    -   **No Inner Breaks**: Do not use `if not is_development_mode and i < ...: break` inside the loop. The range control handles this efficiently.
    -   **Immediate Return in Deployment**: In `DEPLOYMENT` mode, the loop should typically return immediately after finding the first valid alert (since we iterate backwards from the newest data).
        ```python
        if alert:
            alerts.append(alert)
            if not is_development_mode:
                return alerts # Return immediately after first alert in deployment
        ```
-   **Clear Class Structure**: The logic must be encapsulated within the executor class:
    -   `__init__`: Initializes the executor for a specific symbol and loads its settings.
    -   `run`: The main public entry point that receives the DataFrame.
    -   `_find_*_alerts`: A private method containing the main reverse loop and core logic.
-   **Standardized Filtering**: Optional filters (Volume, RSI, etc.) should be applied *after* the core pattern has been identified, using common functions from `src/stockreports/alert/common/`.
-   **Class-Level Constants**: The `APPROACH_NAME` **MUST** be defined as a class-level constant.
-   **Standardized Logging and Context**: All executors **MUST** adhere to the "Standardized Logging and Centralized Context Management" pattern. This is a strict requirement for consistency and debugging.
    -   **Logging**: All logging related to the validation flow **MUST** use the `log()` factory from `src/stockreports/utils/log_factory.py`.
    -   **Context Variables**: The executor **MUST** implement and manage three class-level attributes for context:
        ```python
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0
        ```
    -   **Context Management**: These variables **MUST** be reset at the beginning of each iteration of the main analysis loop. The `self.current_step` counter must be incremented sequentially for each major validation step.
        ```python
        # In the _find_*_alerts method loop
        for i in range(loop_end, loop_start - 1, -1):
            # ...
            # --- Reset Context for New Window ---
            self.current_window_end_time = window_df.iloc[-1]['time']
            self.current_window_start_time = window_df.iloc[0]['time']
            self.current_step = 1

            # --- Step 1: First Validation ---
            if not condition:
                log(...) # Use self.current_step
                continue

            # --- Step 2: Second Validation ---
            self.current_step += 1
            if not other_condition:
                log(...) # Use self.current_step
                continue
        ```
-   **Standardized Logging and Context**: All executors **MUST** adhere to the "Standardized Logging and Centralized Context Management" pattern. This is a strict requirement for consistency and debugging.
    -   **Standardized Loop and Window Context Utilities**: All executors **MUST** use the base class utility functions for loop setup and window context extraction:
        - `get_loop_setup`: For preparing the indexed DataFrame and loop boundaries.
        - `get_window_context`: For extracting the lookback window, boundary candles, and context variables.
        - These calls must be accompanied by standardized comments explaining their purpose, e.g.:
            ```python
            # --- Standardized loop setup ---
            # Use base class utility to prepare indexed DataFrame and loop boundaries
            df_indexed, loop_start, loop_end = self.get_loop_setup(...)

            for i in range(loop_end, loop_start - 1, -1):
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
        - Manual extraction of loop boundaries or window context is forbidden; always use the base class utilities.

### 2C. Step and Validation Tracking Guidance

- Call `self.next_step()` at the start of each major step in the main alert-finding loop (e.g., `_find_*_alerts`).
- Call `self.next_validation()` immediately before each sub-validation or check inside step/helper functions.
- Do not call `next_step()` inside step/helper functions, and do not call `next_validation()` in the main loop.

## 3. Step-by-Step Implementation Guide

### Step 1: Define the Approach Name

1.  Open `src/stockreports/alert/common/constants.py`.
2.  Add your new approach's name to the `Approach` enum (e.g., `CONSOLIDATION_BREAKOUT`).

### Step 2: Create the Executor File Structure

1.  Navigate to `src/stockreports/alert/approach/`.
2.  Create a new directory with the same name as your approach (e.g., `CONSOLIDATION_BREAKOUT/`).
3.  Inside this new directory, create three files:
    -   `__init__.py` (can be empty)
    -   `executor.py` (will contain your `Executor` subclass)
    -   `settings.py` (will contain your dedicated settings class)

### Step 3: Create a Dedicated Settings Class

Create a settings class that inherits from `BaseSettings`. This provides automatic configuration loading and helper methods.

```python
# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/settings.py
from src.stockreports.alert.common.base_settings import BaseSettings

class ConsolidationBreakoutSettings(BaseSettings):
    def __init__(self, symbol: str):
        # Initialize BaseSettings with the symbol and the approach name (key in signal_settings.py)
        super().__init__(symbol, "CONSOLIDATION_BREAKOUT")
        
        # --- Core Logic Parameters ---
        # Use self.get(key, default) to access settings safely
        self.lookback_period = self.get("LOOKBACK_PERIOD", 25)
        self.min_clustered_candle_ratio = self.get("MIN_CLUSTERED_CANDLE_RATIO", 0.8)
        
        # --- Standard Optional Filter Flags ---
        self.use_volume_confirmation = self.get("USE_VOLUME_CONFIRMATION", True)
```

### Step 4: Configure the Approach in `signal_settings.py`

1.  Open `src/stockreports/config/signal_settings.py`.
2.  Add a new configuration dictionary for your approach.

    ```python
    # src/stockreports/config/signal_settings.py
    APPROACH_CONFIG = {
        # ...
        # Pattern 1: Flat Structure (Default)
        "CONSOLIDATION_BREAKOUT": {
            "LOOKBACK_PERIOD": 25,
            "MIN_CLUSTERED_CANDLE_RATIO": 0.8,
            "USE_VOLUME_CONFIRMATION": True,
        },

        # Pattern 2: Symbol-Specific Structure (Use ONLY if logic depends on specific symbols)
        # "CONSOLIDATION_BREAKOUT": {
        #     "default": { "LOOKBACK_PERIOD": 25 },
        #     "VN30": { "LOOKBACK_PERIOD": 30 }
        # }
    }
    ```

### Step 5: Implement the Executor Class

This is the core of the work. Follow the template below, ensuring you adhere to the principles outlined in Section 2.

```python
# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/executor.py
import pandas as pd
import logging
from typing import Optional

# --- Project Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.config import loader
from src.stockreports.alert.common.constants import Approach, Mode, Signal
from src.stockreports.alert.model.models import AlertResult, AlertData
from .settings import ConsolidationBreakoutSettings

class ConsolidationBreakoutExecutor(Executor):
    APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT
    LATEST_ACCEPTED_ALERT: Optional[AlertData] = None

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.settings = ConsolidationBreakoutSettings(symbol)
        self.logger = logging.getLogger(__name__)

    def run(self, df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        # ... (try/except block) ...
        # ... (call to _find_consolidation_breakout_alerts) ...

    def _find_consolidation_breakout_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        # ... (main reverse loop logic) ...

    def _analyze_window(self, window: pd.DataFrame) -> Optional[AlertData]:
        # ... (core analysis for a single window) ...
```

### Step 6: Create the Documentation File

-   **Path**: `docs/algorithms/APPROACH_NAME.md`
-   **Action**: Create a detailed documentation file for the new approach.
-   **Mandatory Format**: The documentation **must** adhere to the standard content structure, as seen in the [VRA Approach Documentation](../../algorithms/VRA.md). It must include the following sections:
    1.  **Objective**: A high-level summary of the strategy.
    2.  **Key Parameters**: A markdown table listing all configuration parameters, their default values, and descriptions.
    3.  **Step-by-Step Logic**: A detailed breakdown of the algorithm's execution flow.
    4.  **Flow Diagram**: A `mermaid` diagram visualizing the logic.

## 4. Case Studies: Common Pitfalls to Avoid

This section documents real errors made during development to serve as learning examples.

### Case Study 1: The Phantom Deletion During Refactoring

*   **Scenario**: An agent was tasked with refactoring a single, complex function within an `Executor` class (`_confirm_reversal_in_forward_window`). The goal was to split the function's logic into two new, smaller helper methods.
*   **The Error**: During the `insert_edit_into_file` operation, the agent's provided code block was incomplete. It correctly showed the changes for the target function and the new helper methods but **omitted several other essential, unrelated methods** that were present in the original file (e.g., `_find_consistent_momentum_alerts`). The edit tool, following instructions, replaced a large chunk of the file with the provided code, inadvertently deleting the omitted methods.
*   **The Symptom**: The application immediately failed at runtime with an `AttributeError: 'ConsistentMomentumExecutor' object has no attribute '_find_consistent_momentum_alerts'`, because the main alert-finding loop method had been accidentally deleted.
*   **The Lesson**:
    *   **Scope of Edits is Critical**: When using file editing tools, be acutely aware of the context you provide. Omitting code that should remain is as destructive as adding incorrect code. The tool assumes the provided snippet is the desired final state for the specified range.
    *   **Always Account for `...existing code...`**: The `// ...existing code...` marker is a crucial instruction to the editing tool to preserve the surrounding, unchanged code. Ensure that all parts of the file that are not being changed are correctly framed by these markers. A missing marker can lead to large, unintended deletions.
    *   **Review the Diff**: After an edit is applied, the resulting diff is the ground truth. A large number of deletions in unexpected places is a major red flag that warrants an immediate revert and review. Do not proceed if you see unexpected deletions.
    *   **Refactor Incrementally**: Instead of one massive edit that refactors a function and adds two new ones, consider a multi-step approach:
        1.  Add the new, empty helper methods first in one edit.
        2.  Move the logic into the helper methods one by one in subsequent edits.
        3.  Finally, update the original function to be a dispatcher.
        This reduces the risk of large-scale accidental deletions and makes errors easier to pinpoint.

## References

- For a log of common technical issues and their resolutions, which can help in avoiding common pitfalls, refer to the [Technical Case Studies & Issue Resolution Log](../case-studies/TECHNICAL_CASE_STUDIES.md).
- For an example of a standardized, well-structured documentation file for an approach, see the [Price Gap Approach Documentation](../algorithms/PRICE_GAP.md).

# Guide to Generating a New Alert Approach

## Objective
To create all the necessary files and boilerplate code for a new alert generation approach. This guide ensures that new approaches are structured consistently and integrate seamlessly into the existing system.

## Pre-generation Checklist
1.  **Review Case Studies**: Before writing any code, consult the **[Technical Case Studies & Issue Resolution Log](../../case-studies/TECHNICAL_CASE_STUDIES.md)** and the **[Code Generation Guidelines](./CODE_GENERATION_GUIDELINES.md)** to avoid repeating past mistakes.

## Step-by-Step File Generation

### 1. Define the Approach Name
-   **Action**: Ask the user for the name of the new approach (e.g., "TrendReversal", "MarketMomentum").
-   **Details**: The name should be descriptive of the strategy and follow the existing naming conventions. Avoid generic names; be as specific as possible about the strategy's intent.
-   **Example**: For a strategy based on moving average crossovers, a suitable name might be "MACrossOverStrategy".

### 2. Create the Executor File Structure
-   **Action**: Generate the necessary file and folder structure for the new approach.
-   **Details**: This includes creating a new folder under `src/stockreports/alert/approach/` with the approach name, and inside it, creating `__init__.py`, `executor.py`, and `settings.py` files.
-   **Example**: For the "MACrossOverStrategy", the structure would be:
    ```
    src/
    └── stockreports/
        └── alert/
            └── approach/
                └── MACrossOverStrategy/
                    ├── __init__.py
                    ├── executor.py
                    └── settings.py
    ```

### 3. Create a Dedicated Settings Class
-   **Action**: Define a new settings class for the approach in `settings.py`.
-   **Details**: This class should inherit from `BaseSettings` and define all necessary parameters for the approach, using sensible defaults. Parameters should be documented with comments.
-   **Example**: A settings class for the moving average crossover might look like:
    ```python
    from src.stockreports.alert.common.base_settings import BaseSettings

    class MACrossOverSettings(BaseSettings):
        def __init__(self, symbol: str):
            super().__init__(symbol, "MACROSSOVERSTRATEGY")
            self.short_window = self.get("SHORT_WINDOW", 50)
            self.long_window = self.get("LONG_WINDOW", 200)
    ```

### 4. Configure the Approach in `signal_settings.py`
-   **Action**: Create a file at `src/stockreports/config/signal_settings.py` (if it doesn't exist) and add a new dictionary key for the approach. Populate it with all the parameters defined in the `settings.py` file, along with their default values.

### 5. Create the Documentation File
-   **Path**: `docs/algorithms/APPROACH_NAME.md`
-   **Action**: Create a detailed documentation file for the new approach.
-   **Mandatory Format**: The documentation **must** adhere to the standard content structure, as seen in the [VRA Approach Documentation](../../algorithms/VRA.md). It must include the following sections:
    1.  **Objective**: A high-level summary of the strategy.
    2.  **Key Parameters**: A markdown table listing all configuration parameters, their default values, and descriptions.
    3.  **Step-by-Step Logic**: A detailed breakdown of the algorithm's execution flow.
    4.  **Flow Diagram**: A `mermaid` diagram visualizing the logic.

### 6. Implement the Executor Class
-   **Action**: Develop the main executor class for the approach in `executor.py`.
-   **Details**: The class should inherit from `Executor` and implement the `run` method, calling private methods for the main logic. Ensure proper error handling and logging.
-   **Example**: A skeleton for the moving average crossover executor might look like:
    ```python
    import pandas as pd
    import logging
    from typing import Optional
    from src.stockreports.alert.executor import Executor
    from .settings import MACrossOverSettings

    class MACrossOverExecutor(Executor):
        APPROACH_NAME = "MACROSSOVERSTRATEGY"

        def __init__(self, symbol: str):
            super().__init__(symbol)
            self.settings = MACrossOverSettings(symbol)
            self.logger = logging.getLogger(__name__)

        def run(self, df: pd.DataFrame, new_candle_count: int = 0):
            # Main execution logic
            pass

        def _analyze_window(self, window: pd.DataFrame) -> Optional[AlertData]:
            # Analysis logic for a single window
            pass
    ```

### 7. Test the New Approach
-   **Action**: Validate the new approach with historical data to ensure it behaves as expected.
-   **Details**: Run the approach in a development environment, review the generated alerts, and adjust the logic or settings as necessary. Pay close attention to the performance and accuracy of the alerts.
-   **Example**: For the moving average crossover, check that the alerts are triggered at the correct points based on historical price data.

### 8. Document the Approach
-   **Action**: Create a documentation file for the new approach.
-   **Details**: This should include an overview of the strategy, how to configure it, and examples of the generated alerts. Follow the documentation standards used in existing approaches.
-   **Example**: A Markdown file `MACROSSOVERSTRATEGY.md` in the `docs` folder, with sections for **Overview**, **Configuration**, **Examples**, and **Backtesting Results**.

### 9. Review and Refactor
-   **Action**: Conduct a thorough review of the new approach's code and documentation.
-   **Details**: Refactor any parts of the code that can be improved, ensure all new files are included in version control, and update any relevant documentation or diagrams.
-   **Example**: Use code review tools to check for common issues, and manually inspect the documentation for clarity and completeness.

### 10. Deploy the New Approach
-   **Action**: Deploy the new approach to the live environment.
-   **Details**: Follow the deployment procedures used for other approaches, monitor the deployment for any issues, and be prepared to roll back if necessary.
-   **Example**: Deploy the "MACrossOverStrategy" and monitor the initial alerts closely to ensure everything is functioning correctly.

## References
-   **Code Generation Guidelines**: Detailed guidelines on generating code for new approaches, including naming conventions, file structures, and coding standards.
-   **Technical Case Studies & Issue Resolution Log**: A log of common technical issues and their resolutions, which can help in avoiding common pitfalls.
-   **Existing Approach Documentation**: Examples of standardized, well-structured documentation files for existing approaches, serving as a reference for documenting new approaches.
