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
        # },
    }
    ```

### Step 5: Implement the `executor.py` Using the Class-Based Template

Copy and adapt the following template for your `executor.py`. **Note:** This template uses the `AlertData` model. Executors **MUST** create and return `AlertData` objects, not `Alert` objects, to prevent circular import errors.

```python
# src/stockreports/alert/approach/YOUR_APPROACH_NAME/executor.py

import pandas as pd
import logging
import json
from typing import list

# --- Standard Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertData # CORRECT: Use AlertData
from src.stockreports.alert.common.constants import Approach, Mode
# ... other common imports

# --- Custom Approach Imports ---
from .settings import YourApproachNameSettings

logger = logging.getLogger(__name__)

class YourApproachNameExecutor(Executor):
    APPROACH_NAME = Approach.YOUR_APPROACH_NAME

    def __init__(self, symbol: str, data: pd.DataFrame, mode: Mode):
        super().__init__(symbol, data, mode)
        self.settings = YourApproachNameSettings(symbol)
        self.logger = logging.getLogger(__name__)

    # 1. MAIN ENTRY POINT
    def run(self) -> list[AlertData]:
        """
        Entry point for the YOUR_APPROACH_NAME approach.
        """
        alerts = []
        self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")
        
        # --- Core Logic ---
        # Your unique pattern detection logic goes here.
        # It should return a signal ("BUY" or "SELL") or None.
        # Example: confirmation_result = self.confirmation.confirm(self.data)
        confirmation_result = None # Placeholder

        if confirmation_result:
            alert = self._create_alert(confirmation_result)
            alerts.append(alert)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts)} alerts.")
        else:
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found 0 alerts.")

        return alerts

    # 2. ALERT CREATION HELPER
    def _create_alert(self, confirmation_result) -> AlertData:
        last_candle = self.data.iloc[-1]
        reversal_candle = self.data.loc[confirmation_result.reversal_time]
        
        alert_time = last_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))
        magnitude = round(abs(last_candle['close'] - reversal_candle['close']), 2)

        details = { "parameter_1": self.settings.parameter_1 }

        return AlertData(
            id=alert_id,
            symbol=self.symbol,
            signal=confirmation_result.signal,
            alert_time=alert_time,
            alert_price=last_candle['close'],
            approach=self.APPROACH_NAME,
            start_time=confirmation_result.reversal_time,
            start_price=reversal_candle['close'],
            magnitude=magnitude,
            details=json.dumps(details)
        )

        # --- Unified Reverse Loop for both DEPLOYMENT and DEVELOPMENT modes ---
        # 1. Define loop_end (most recent index to scan)
        #    - Subtract any forward-looking offset (e.g., confirmation candles) here.
        offset = confirmation_candles if use_confirmation_filter else 0
        loop_end = len(df_indexed) - 1 - offset
        
        # 2. Define min_scan_index (absolute minimum index required for lookback)
        min_scan_index = required_lookback - 1
        
        # 3. Define loop_start (oldest index to scan) based on mode
        if is_development_mode:
            loop_start = min_scan_index
        else:
            # In DEPLOYMENT, we only scan the 'new_candle_count' range.
            # We also subtract the offset to ensure we stop early enough for forward checks.
            loop_start = max(min_scan_index, len(df_indexed) - new_candle_count - offset)

        # 4. Execute the Loop
        for i in range(loop_end, loop_start - 1, -1):
            alert = self._analyze_candle(df_indexed, i, ...)
            if alert:
                alerts.append(alert)
                # Optimization: In deployment, we only need the most recent alert.
                if not is_development_mode:
                    return alerts
```

### Step 6: Enable the Approach in `settings.py`

**CRITICAL ACTIVATION STEP:** This step makes your new approach live.

1.  Open `src/stockreports/config/settings.py`.
2.  Add your approach's string name to the `ALERT_APPROACHES` list.

### Step 7: Create Documentation and Debug Script

These steps are still **MANDATORY**.
-   **Algorithm Documentation**: Create a markdown file in `docs/algorithms/` explaining your strategy. You can reference the existing documentation for other algorithms in this directory for examples.
-   **Window Analysis Documentation**: Update `docs/window/APPROACH_LOOKBACK_FORWARD_ANALYSIS.md` and `docs/window/APPROACH_ANALYSIS_SUMMARY.md` to include your new approach's lookback and pattern length analysis. This is critical for deployment logic.
-   **Debug Script**: Follow the updated guide at `docs/prompts/DEBUG_SCRIPT_GENERATION_GUIDE.md` to create a script that instantiates and runs your new `Executor` class.

---

## Non-Negotiable Rules for Implementation (Class-Based)

These rules are adapted for the new class-based architecture.

### 1. Column Name Consistency
-   **Rule**: Standardize column names to lowercase as the very first step inside the `try` block of the public `run` method.
-   **Implementation**: `df.columns = [col.lower() for col in df.columns]`

### 2. Data Handling and Validation
-   **Rule 1**: Use the centralized `can_apply_analysis` check at the beginning of your private `_find_*_alerts` function before any looping.
-   **Rule 2**: Trust the DataFrame Index. The `run` method receives a DataFrame with a valid `DatetimeIndex`. Do not manually set the index or perform timezone localization within the executor.

### 3. Data Flow Integrity
-   **Rule**: Any helper function that modifies a DataFrame (e.g., `prepare_indicators`) **MUST** return it, and the caller **MUST** use the returned object. `df = prepare_indicators(df)`.

### 4. Error Handling and Type Safety
-   **Rule 1**: The public `run` method **MUST** be wrapped in a `try...except Exception as e` block. This is the global safety net for the entire approach. Do not add extra `try...except` blocks inside the core logic.
-   **Rule 2**: Maintain type consistency, especially with Enums (`Signal.BUY`, `Trend.UPTREND`, etc.).

### 5. Configuration and Code Structure
-   **Rule 1**: Create a dedicated settings class for your approach (e.g., `MyApproachSettings`) to load all parameters from `signal_settings.py`. Instantiate this class in your executor's `__init__` method.
-   **Rule 2**: The `APPROACH_NAME` **MUST** be a class-level constant in your executor, assigned from the `Approach` enum (e.g., `APPROACH_NAME = Approach.MY_APPROACH`).
-   **Rule 3**: Executors **MUST** create and return `AlertData` objects from `src.stockreports.alert.model.models`. They **MUST NOT** import or instantiate the `Alert` class directly. This prevents circular dependency errors.

### 6. Verbose Debug Logging for Validation
-   **Rule**: Every validation check that can cause a window to be rejected **MUST** be accompanied by a `self.logger.debug()` message explaining the exact reason for the failure. This is critical for debugging and fine-tuning the approach.
-   **Implementation**:
    -   The log message **MUST** start with the window identifier: `f"Window ending {window.index[-1]}: ..."`
    -   It **MUST** clearly state the name of the failed check (ideally matching the config key): `... Failed {CHECK_NAME}. ...`
    -   It **MUST** provide the actual and expected values for comparison: `... Got {actual_value}, required {expected_value}."`
-   **Example**:
    ```python
    min_ratio = self.CONFIG.get("MIN_CLUSTERED_CANDLE_RATIO")
    if is_clustered.mean() < min_ratio:
        self.logger.debug(f"Window ending {window.index[-1]}: Failed MIN_CLUSTERED_CANDLE_RATIO. "
                        f"Got {is_clustered.mean():.2f}, need {min_ratio}.")
        return None # Stop processing this window
    ```
