# Prompt Guide: Generating a New Trading Approach (Class-Based Executors)

## 1. Objective

This document provides a comprehensive template and a step-by-step guide for creating a new trading approach by inheriting from the base `Executor` class. By following this pattern, developers can ensure that new strategies are consistent, maintainable, and integrate seamlessly with the existing alert generation, configuration, and analysis systems.

## 2. Core Principles of an Approach Executor

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
    -   `_create_alert`: A private helper function to standardize `AlertData` object creation.
-   **Standardized Filtering**: Optional filters (Volume, RSI, etc.) should be applied *after* the core pattern has been identified, using common functions from `src/stockreports/alert/common/`.
-   **Class-Level Constants**: The `APPROACH_NAME` **MUST** be defined as a class-level constant.

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

## 6. Case Studies: Common Pitfalls to Avoid

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
