# Prompt Guide: Generating a New Trading Approach (Class-Based Executors)

## 1. Objective

This document provides a comprehensive template and a step-by-step guide for creating a new trading approach by inheriting from the base `Executor` class. By following this pattern, developers can ensure that new strategies are consistent, maintainable, and integrate seamlessly with the existing alert generation, configuration, and analysis systems.

## 2. Core Principles of an Approach Executor

Every approach executor (`executor.py`) **MUST** be a class that inherits from `src.stockreports.alert.executor.Executor` and adheres to the following principles:

-   **Configuration-Driven**: All key parameters (lookback periods, thresholds, feature flags) **MUST** be defined in `src/stockreports/config/signal_settings.py` and loaded via a dedicated settings class for the approach. Hard-coded "magic numbers" are **STRICTLY FORBIDDEN**.
-   **Stateful but Pure Analysis**: The `Executor` instance holds state for a single symbol (like the last alert time), but the core analysis logic within the `run` method should be pure. Given the same DataFrame and configuration, it **MUST** always produce the same `AlertResult`.
-   **Unified Reverse Loop**: The main loop for finding alerts **MUST** be a **reverse loop** (from the latest candle to the oldest). This single loop must efficiently handle both `DEVELOPMENT` mode (find all historical alerts) and `DEPLOYMENT` mode (find only the most recent alert and exit immediately).
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

Create a settings class to provide a structured way to access configuration from `signal_settings.py`.

```python
# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/settings.py
from src.stockreports.config import loader

signal_settings = loader.get_signal_settings()

class ConsolidationBreakoutSettings:
    def __init__(self, symbol: str):
        self.primary_symbol = symbol
        # Load the specific config for this symbol, with a fallback to "default"
        self.approach_settings = signal_settings.APPROACH_CONFIG.get('CONSOLIDATION_BREAKOUT', {}).get(symbol, 
            signal_settings.APPROACH_CONFIG.get('CONSOLIDATION_BREAKOUT', {}).get('default', {})
        )
        
        # --- Core Logic Parameters ---
        self.lookback_period = self.approach_settings.get("LOOKBACK_PERIOD", 25)
        self.min_clustered_candle_ratio = self.approach_settings.get("MIN_CLUSTERED_CANDLE_RATIO", 0.8)
        
        # --- Standard Optional Filter Flags ---
        self.use_volume_confirmation = self.approach_settings.get("USE_VOLUME_CONFIRMATION", True)
```

### Step 4: Configure the Approach in `signal_settings.py`

1.  Open `src/stockreports/config/signal_settings.py`.
2.  Add a new configuration dictionary for your approach.

    ```python
    # src/stockreports/config/signal_settings.py
    APPROACH_CONFIG = {
        # ...
        "CONSOLIDATION_BREAKOUT": {
            "default": {
                "LOOKBACK_PERIOD": 25,
                "MIN_CLUSTERED_CANDLE_RATIO": 0.8,
                "USE_VOLUME_CONFIRMATION": True,
            },
            "VN30": { # Symbol-specific override
                "LOOKBACK_PERIOD": 30,
            }
        },
    }
    ```

### Step 5: Implement the `executor.py` Using the Class-Based Template

Copy and adapt the following template for your `executor.py`.

```python
# src/stockreports/alert/approach/CONSOLIDATION_BREAKOUT/executor.py

import pandas as pd
import logging
import json
from typing import Optional

# --- Standard Imports ---
from src.stockreports.alert.executor import Executor
from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Approach, Mode
from src.stockreports.alert.common.data_utils import can_apply_analysis
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators
# --- Custom Approach Imports ---
from .settings import ConsolidationBreakoutSettings

logger = logging.getLogger(__name__)

class ConsolidationBreakoutExecutor(Executor):
    APPROACH_NAME = Approach.CONSOLIDATION_BREAKOUT
    LATEST_ALERT_TIMESTAMP: Optional[pd.Timestamp] = None # Use a class variable for global cooldown

    def __init__(self, symbol: str, debug: bool = False):
        super().__init__(symbol)
        self.settings = ConsolidationBreakoutSettings(symbol)
        self.logger = logging.getLogger(__name__)
        self.debug = debug # Enable verbose logging for debug scripts

    # 1. MAIN ENTRY POINT
    def run(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        """
        Entry point for the CONSOLIDATION_BREAKOUT approach.
        """
        try:
            # MANDATORY: Standardize column names immediately.
            df.columns = [col.lower() for col in df.columns]
            self.logger.info(f"Running '{self.APPROACH_NAME}' approach for symbol {self.symbol}...")

            alerts_data = self._find_consolidation_breakout_alerts(df, new_candle_count)
            self.logger.info(f"'{self.APPROACH_NAME}' approach for {self.symbol} found {len(alerts_data)} alerts.")

            alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])

            return AlertResult(
                approach_name=self.APPROACH_NAME,
                alerts=alerts_df
            )
        except Exception as e:
            self.logger.error(f"An error occurred during '{self.APPROACH_NAME}' execution for {self.symbol}: {e}", exc_info=True)
            return AlertResult(approach_name=self.APPROACH_NAME, alerts=pd.DataFrame(), status="FAILED", message=str(e))

    # 2. PRIMARY FINDER FUNCTION (WITH UNIFIED REVERSE LOOP)
    def _find_consolidation_breakout_alerts(self, df: pd.DataFrame, new_candle_count: int) -> list[AlertData]:
        alerts = []
        is_development_mode = self.settings.MODE == Mode.DEVELOPMENT
        
        df = prepare_indicators(df)
        
        required_lookback = self.settings.lookback_period
        if not can_apply_analysis(df, required_rows=required_lookback):
            self.logger.warning(f"{self.APPROACH_NAME}: Insufficient data. Required: {required_lookback}, have: {len(df)}.")
            return alerts

        df_indexed = df.set_index('time')

        loop_end = len(df_indexed) - 1
        loop_start = required_lookback - 1
        active_region_start = len(df_indexed) - new_candle_count - required_lookback

        for i in range(loop_end, loop_start - 1, -1):
            if not is_development_mode and i < active_region_start:
                break

            # --- Cooldown Check ---
            current_candle_time = df_indexed.index[i]
            if ConsolidationBreakoutExecutor.LATEST_ALERT_TIMESTAMP is not None:
                time_since_last = (current_candle_time - ConsolidationBreakoutExecutor.LATEST_ALERT_TIMESTAMP).total_seconds() / 60
                if time_since_last < self.settings.cooldown_period:
                    continue

            window = df_indexed.iloc[i - required_lookback + 1 : i + 1].copy()
            
            # --- Core Logic ---
            # Your unique pattern detection logic goes here.
            # Example: is_breakout = self._check_pattern(window)
            is_breakout, signal = True, "BUY" # Placeholder
            
            if is_breakout:
                alert = self._create_alert(window, signal)
                alerts.append(alert)
                ConsolidationBreakoutExecutor.LATEST_ALERT_TIMESTAMP = alert.alert_time
                if not is_development_mode:
                    return alerts # Exit after first alert in deployment
        
        return alerts[::-1]

    # 3. ALERT CREATION HELPER
    def _create_alert(self, window: pd.DataFrame, signal: str) -> AlertData:
        start_candle = window.iloc[0]
        end_candle = window.iloc[-1]
        alert_time = end_candle.name
        alert_id = str(int(alert_time.tz_convert('UTC').timestamp()))

        details = { "lookback_period": self.settings.lookback_period }

        return AlertData(
            approach=self.APPROACH_NAME,
            id=alert_id,
            symbol=self.symbol,
            signal=signal,
            alert_price=end_candle['close'],
            alert_time=alert_time,
            start_price=start_candle['open'],
            start_time=start_candle.name,
            magnitude=round(abs(end_candle['close'] - start_candle['open']), 2),
            details=json.dumps(details)
        )
```

### Step 6: Enable the Approach in `settings.py`

This step remains the same. Add your approach's string name to the `ALERT_APPROACHES` list in `src/stockreports/config/settings.py`.

### Step 7: Create Documentation and Debug Script

These steps are still **MANDATORY**.
-   **Documentation**: Create a markdown file in `docs/algorithms/` explaining your strategy. You can reference the existing documentation for other algorithms in this directory for examples.
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
-   **Rule 2**: The `APPROACH_NAME` **MUST** be a class-level constant in your executor. For global state like a cooldown, use a class-level variable (e.g., `LATEST_ALERT_TIMESTAMP`).
