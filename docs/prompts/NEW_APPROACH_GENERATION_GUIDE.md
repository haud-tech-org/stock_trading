# Prompt Guide: Generating a New Trading Approach

## 1. Objective

This document provides a comprehensive template and a step-by-step guide for creating a new trading approach within the existing framework. By following this pattern, developers can ensure that new strategies are consistent, maintainable, and integrate seamlessly with the existing alert generation, configuration, and analysis systems.

## 2. Core Principles of an Approach Executor

Every approach executor (`executor.py`) **MUST** adhere to the following set of core principles to ensure stability, consistency, and maintainability.

-   **Configuration-Driven**: All key parameters (lookback periods, thresholds, feature flags) **MUST** be defined in `src/stockreports/config/signal_settings.py`. The configuration for the specific approach should be loaded **ONCE** as a **module-level constant** (`CONFIG`). Hard-coded "magic numbers" are **STRICTLY FORBIDDEN**.
-   **Stateless Analysis**: The analysis function must be pure. Given the same DataFrame and configuration, it **MUST** always produce the same `AlertResult`. It must not rely on any external state or variables modified in previous runs.
-   **Unified Reverse Loop**: The main loop for finding alerts **MUST** be a **reverse loop** (from the latest candle to the oldest). This single loop must efficiently handle both `DEVELOPMENT` mode (find all historical alerts) and `DEPLOYMENT` mode (find only the most recent alert and exit immediately).
-   **Modular Logic**: The code should be broken down into logical functions:
    -   `run_analysis`: The main entry point.
    -   `_find_*_alerts`: The function containing the main reverse loop and core logic.
    -   `_create_alert`: A helper function to standardize alert object creation.
-   **Standardized Filtering**: Optional filters (Volume, RSI, standard indicators like MA/MACD) should be applied *after* the core pattern has been identified, using the common functions from `src/stockreports/alert/common/`.
-   **Module-Level Constants**: The `APPROACH_NAME` and `CONFIG` **MUST** be defined as module-level constants to ensure they are loaded only once and are used consistently throughout the file.

## 3. Step-by-Step Implementation Guide

### Step 1: Define the Approach Name

1.  Open `src/stockreports/alert/common/constants.py`.
2.  Add your new approach's name to the `Approach` enum. The name should be descriptive and in `UPPER_SNAKE_CASE` (e.g., `CONSOLIDATION_BREAKOUT`).

    ```python
    # src/stockreports/alert/common/constants.py
    class Approach(Enum):
        # ... existing approaches
        CONSOLIDATION_BREAKOUT = "CONSOLIDATION_BREAKOUT"
    ```

### Step 2: Create the Executor File Structure

1.  Navigate to `src/stockreports/alert/approach/`.
2.  Create a new directory with the same name as your approach (e.g., `CONSOLIDATION_BREAKOUT/`).
3.  Inside this new directory, create two files:
    -   `__init__.py` (can be empty)
    -   `executor.py`

### Step 3: Configure the Approach in `signal_settings.py`

1.  Open `src/stockreports/config/signal_settings.py`.
2.  Add a new configuration dictionary for your approach within the `APPROACH_CONFIG`.

    ```python
    # src/stockreports/config/signal_settings.py

    APPROACH_CONFIG = {
        # ... existing configs
        "CONSOLIDATION_BREAKOUT": {
            # --- Core Logic Parameters ---
            "LOOKBACK_PERIOD": 25,
            "MIN_CLUSTERED_CANDLE_RATIO": 0.8,
            "MAX_DEVIATION_FROM_CENTER": 0.01,
            "BREAKOUT_CONFIRMATION_CANDLES": 3,
            "BREAKOUT_STRENGTH_FACTOR": 1.5,

            # --- Standard Optional Filter Flags ---
            "USE_CONFIRMATION_CANDLE_FILTER": True,
            "USE_VOLUME_CONFIRMATION": True,
            "USE_INCREASING_VOLUME_CONFIRMATION": True,
        },
    }
    ```

### Step 4: Implement the `executor.py` Using the Template

Copy and adapt the following template for your `executor.py`. The comments guide you on where to place your custom logic.

```python
# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/executor.py

import pandas as pd
import logging
import json

# --- Standard Imports ---
from src.stockreports.config import loader
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators, is_signal_confirmed, _is_rsi_not_exhausted
from src.stockreports.alert.common.volume import is_volume_spike_confirmed # Add other volume functions if needed

# --- Settings Loader ---
settings = loader.get_settings()
signal_settings = loader.get_signal_settings()
logger = logging.getLogger(__name__)

# --- Module-level constants ---
APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT
CONFIG = signal_settings.APPROACH_CONFIG.get(
    APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
)

# 1. MAIN ENTRY POINT
def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
    """
    Entry point for the CONSOLIDATION_BREAKOUT approach.
    """
    try:
        # --- A. Preparation ---
        # Standardize column names to lowercase to prevent KeyErrors due to inconsistent casing.
        df.columns = [col.lower() for col in df.columns]

        logger.info(f"Running '{APPROACH_NAME}' approach...")
        
        # The main logic is delegated to the finder function.
        # CONFIG is a module-level constant and does not need to be passed.
        alerts_data = _find_consolidation_breakout_alerts(df, new_candle_count)
        logger.info(f"'{APPROACH_NAME}' approach found {len(alerts_data)} alerts.")

        # Convert the list of AlertData objects to a DataFrame for the final result
        alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=alerts_df
        )
    except Exception as e:
        logger.error(f"An error occurred during '{APPROACH_NAME}' execution: {e}", exc_info=True)
        return AlertResult(
            approach_name=APPROACH_NAME,
            alerts=pd.DataFrame(),
            status="FAILED",
            message=str(e)
        )

# 2. PRIMARY FINDER FUNCTION (WITH UNIFIED REVERSE LOOP)
def _find_consolidation_breakout_alerts(df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
    """
    Finds alerts using a unified reverse loop, optimized for both DEPLOYMENT and DEVELOPMENT modes.
    """
    alerts = []
    is_development_mode = settings.MODE == Mode.DEVELOPMENT
    
    # --- A. Preparation ---
    # Prepare all indicators (like RSI, MACD, MAs) once for efficiency.
    df = prepare_indicators(df)
    
    # Determine the minimum amount of data needed for one calculation
    required_lookback = CONFIG.get("LOOKBACK_PERIOD", 25) + CONFIG.get("BREAKOUT_CONFIRMATION_CANDLES", 3)
    
    # Use the centralized data check
    if not can_apply_analysis(df, required_rows=required_lookback):
        logger.warning(f"{APPROACH_NAME}: DataFrame has less than {required_lookback} rows, cannot generate alerts.")
        return alerts

    df_indexed = df.set_index('time') # Use a time-indexed DataFrame for analysis

    # --- B. Unified Reverse Loop ---
    loop_end = len(df_indexed) - 1
    loop_start = required_lookback - 1
    
    # This calculation naturally handles the scan depth for both modes.
    active_region_start = len(df_indexed) - new_candle_count - required_lookback

    for i in range(loop_end, loop_start - 1, -1):
        if i < active_region_start:
            break # Stop searching if we are past the active region.

        # Define the window of data to be analyzed for the pattern.
        window = df_indexed.iloc[i - required_lookback + 1 : i + 1].copy()
        
        # --- C. Core Logic ---
        # This is where the unique logic of your new approach goes.
        # Check for your specific candle patterns, indicator values, or price action here.
        
        # --- D. Final Filtering & Alert Creation ---
        # If a pattern is found, create the alert object
        alert = _create_alert(window, signal)
        alerts.append(alert)
    
    # In DEVELOPMENT mode, the loop completes. Return all found alerts in chronological order.
    return alerts[::-1]

# 3. ALERT CREATION HELPER
def _create_alert(window: pd.DataFrame, signal: str) -> AlertData:
    """
    Creates and returns a standardized AlertData object.
    """
    start_candle = window.iloc[0]
    end_candle = window.iloc[-1]
    
    alert_time = end_candle.name
    alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

    details = {
        "reason": "A consolidation breakout pattern was detected.",
        "lookback_period": CONFIG.get("LOOKBACK_PERIOD"),
        "breakout_candle_close": end_candle['close']
    }

    return AlertData(
        approach=APPROACH_NAME, # Use module-level constant
        id=alert_id,
        signal=signal,
        alert_price=end_candle['close'],
        alert_time=alert_time,
        start_price=start_candle['open'],
        start_time=start_candle.name,
        magnitude=round(abs(end_candle['close'] - start_candle['open']), 2),
        details=json.dumps(details)
    )
```

### Step 5: Enable the Approach in `settings.py`

To activate your new approach so that it runs during analysis, you must add its name to the `ALERT_APPROACHES` list in the main settings file.

1.  Open `src/stockreports/config/settings.py`.
2.  Add the name of your approach (the string value from the `Approach` enum) to the `ALERT_APPROACHES` list.

    ```python
    # src/stockreports/config/settings.py
    ALERT_APPROACHES = [
        "RCM",
        "CONSISTENT_MOMENTUM",
        # ... other existing approaches
        "CONSOLIDATION_BREAKOUT"
    ]
    ```

### Step 6: Create Documentation

Finally, create a new markdown file in `docs/algorithms/` named `CONSOLIDATION_BREAKOUT.md`. Document the objective of your strategy, list all the parameters from `signal_settings.py` in a table, and provide a clear, step-by-step explanation of the logic. Include a Mermaid flow diagram to visually represent the process.

**New Case Studies Added (Nov 18, 2025):**
*   `docs/algorithms/MOMENTUM_EXHAUSTION.md`
*   `docs/algorithms/ICHIMOKU.md`

### Step 7: Create a Debug Script

**This step is MANDATORY.**

After implementing the core logic and documentation, you **MUST** create a debug script to validate your new approach. This script is essential for isolating and testing your logic against specific data scenarios by calling your main executor directly.

1.  **Follow the Updated Guide**: A detailed guide and template for creating this script is available at `docs/prompts/DEBUG_SCRIPT_GENERATION_GUIDE.md`. This guide has been recently updated with the latest best practices and includes case studies for common debugging challenges.
2.  **Purpose**: Use this script to verify your executor's behavior in `DEVELOPMENT` or `DEPLOYMENT` mode, test specific time windows, and ensure it behaves as expected before integration.

---

## Non-Negotiable Rules for Implementation (Derived from Case Studies)

Based on lessons learned from debugging multiple approaches, the following rules are **non-negotiable**. They are designed to prevent common, high-impact errors and build robust, predictable, and easy-to-debug approaches. **Failure to follow these rules will result in code rejection.**

### 1. Column Name Consistency

**Case Study**: The `COMPARISON` approach repeatedly failed with a `KeyError: 'close'`. Debugging revealed that the input DataFrame contained a 'Close' column (uppercase 'C'), but the code was trying to access `df['close']`. This happened because the upstream data source provided inconsistently cased column names.

-   **Rule: Standardize Column Names to Lowercase Immediately.** To prevent unpredictable `KeyError` exceptions, all DataFrame column names **MUST** be converted to lowercase as the very first step inside the `try` block of the `run_analysis` function. This creates a predictable and consistent data structure for all downstream logic.

-   **Implementation Pattern**:

    ```python
    # In the main entry point, right at the beginning
    def run_analysis(df: pd.DataFrame, new_candle_count: int = 0) -> AlertResult:
        """
        Entry point for the approach.
        """
        try:
            # MANDATORY: Standardize column names immediately.
            df.columns = [col.lower() for col in df.columns]
            
            logger.info(f"Running '{APPROACH_NAME}' approach...")
            # ... proceed with analysis ...
    ```

### 2. Data Handling and Validation

**Case Study**: The `CONSOLIDATION_BREAKOUT` alert failed silently because the main application had insufficient data for the *confirmation* step, even though it had enough for the *pattern detection* step. The `ICHIMOKU` approach crashed with a `KeyError` because it assumed a 'time' column existed when it was already the index.

-   **Rule 1: Use the Centralized Data Check.** At the beginning of your `_find_*_alerts` function, you **MUST** use `can_apply_analysis` to validate the DataFrame. This function handles both general data integrity and minimum row count checks.

-   **Implementation Pattern**:

    ```python
    # In the primary finder function (e.g., _find_consolidation_breakout_alerts)
    def _find_consolidation_breakout_alerts(df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        # ...
        required_lookback = CONFIG.get("LOOKBACK_PERIOD", 25)
        
        # MANDATORY: Use the single, centralized check.
        if not can_apply_analysis(df, required_rows=required_lookback):
            logger.warning(f"{APPROACH_NAME}: Insufficient data for analysis. Required: {required_lookback}, have: {len(df)}.")
            return [] # Return an empty list immediately.
        
        # ... proceed with analysis ...
    ```

-   **Rule 2: Trust the DataFrame Index.** Assume the input DataFrame `df` to `run_analysis` has a valid `DatetimeIndex`. **DO NOT** manually set the index (`df.set_index('time')`) or perform timezone localization within the executor. This is the responsibility of the upstream data loader. Your logic should use `candle.name` to get the timestamp.

### 3. Data Flow Integrity

**Case Study**: The application crashed with a `TypeError: object of type 'NoneType' has no len()` because the `prepare_indicators` function was modified and was not returning the DataFrame it had processed.

-   **Rule: Ensure Functions Always Return DataFrames.** Any function that receives a DataFrame, modifies it, or adds columns to it (like `prepare_indicators`) **MUST** return the modified DataFrame. The calling function **MUST** then use the returned object.

-   **Implementation Pattern**:

    ```python
    # WRONG (forgets to use the returned df)
    prepare_indicators(df) 
    # df might not have the new indicator columns here

    # CORRECT
    df = prepare_indicators(df)
    # df is now guaranteed to have the indicator columns
    ```

### 4. Error Handling and Type Safety

**Case Study**: The application crashed with an `AttributeError` because a function expected an enum object but received a string.

-   **Rule 1: Use `try...except` for the Main Entry Point.** The `run_analysis` function **MUST** be wrapped in a `try...except Exception as e` block. This is the global safety net for the entire approach, preventing one failure from crashing the whole system. **DO NOT** add extra `try...except` blocks inside the core logic unless absolutely necessary for a specific, recoverable error.

-   **Rule 2: Maintain Type Consistency.** When working with Enums (like `Signal.BUY`), pass the enum object directly to functions unless the function explicitly requires a primitive type (like its string value).

### 5. Configuration and Code Structure

-   **Rule 1: Centralize Configuration as Module-Level Constants.** All magic numbers **MUST** be in `signal_settings.py`. In your `executor.py`, load the configuration for your approach **ONCE** into a module-level `CONFIG` constant. The `APPROACH_NAME` **MUST** also be a module-level constant.

-   **Implementation Pattern**:
    ```python
    # At the top of executor.py
    settings = loader.get_settings()
    signal_settings = loader.get_signal_settings()
    logger = logging.getLogger(__name__)

    # CORRECT: Define as module-level constants
    APPROACH_NAME = Approach.MY_NEW_APPROACH
    CONFIG = signal_settings.APPROACH_CONFIG.get(
        APPROACH_NAME, signal_settings.APPROACH_CONFIG.get("default", {})
    )

    def run_analysis(df, new_candle_count):
        # Use the constants, do not reload them
        alerts_data = _find_my_alerts(df, new_candle_count)
        # ...
    ```
