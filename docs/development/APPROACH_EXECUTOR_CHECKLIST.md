# Approach Executor Script Checklist

This document serves as a standardized checklist for creating and validating new "approach" executor scripts. Its purpose is to ensure all scripts adhere to a common structure, error-handling pattern, and data model, which simplifies maintenance and debugging.

| Aspect | Requirement | Details & Best Practices |
| :--- | :--- | :--- |
| **File Location** | Must be in `src/stockreports/alert/approach/[APPROACH_NAME]/executor.py` | The directory name `[APPROACH_NAME]` must match the entry in `settings.ALERT_APPROACHES`. |
| **Imports** | Standard libraries, settings loader, and models | ```python<br>import pandas as pd<br>import logging<br>import json<br>from src.stockreports.config import loader<br>from src.stockreports.alert.models import AlertResult, AlertData<br>``` |
| **`run_analysis` Function** | Main entry point, must not be modified | - **Signature**: `def run_analysis(df: pd.DataFrame) -> AlertResult:`<br>- **Error Handling**: Must contain a `try...except` block that wraps all logic.<br>- **Logging**: Must log the start of the approach and any exceptions.<br>- **Return Value**: Must return an `AlertResult` object on both success and failure. |
| **Configuration Loading** | Load approach-specific config from `signal_settings` | ```python<br>config = signal_settings.APPROACH_CONFIG.get(<br>    approach_name, signal_settings.APPROACH_CONFIG.get("default", {})<br>)<br>``` |
| **Core Logic Function** | `_find_[approach]_alerts` | - **Signature**: `def _find_*_alerts(df: pd.DataFrame, config: dict) -> list[AlertData]:`<br>- This function contains the unique signal-finding logic for the approach. |
| **Data Validation** | Check for sufficient data length | Before processing, check if the DataFrame is long enough for the required indicator periods (e.g., `len(df) < required_period`). Log a warning and return an empty list if not. |
| **Indicator Calculation** | Use common functions or local calculations | If using standard indicators (MAs, Ichimoku, etc.), import and use `prepare_indicators` from `src.stockreports.alert.common.confirmation`. |
| **Alert Object** | Must create `AlertData` objects | - All alerts found by the core logic must be instantiated as `AlertData` objects.<br>- The `approach` attribute must be set to the approach's name. |
| **Alert ID** | Must be unique | Generate a unique ID for each alert, typically using timestamps. Example: `id=f"{start_timestamp}_{end_timestamp}"`. |
| **Alert Details** | Provide context in JSON format | The `details` field of `AlertData` should be a JSON string containing useful context for the alert (e.g., indicator values, reason for the signal). |
| **Return Type** | Return a list of `AlertData` objects | The core logic function (`_find_*_alerts`) must return a `list[AlertData]`. |
| **Final Conversion** | Convert `AlertData` list to DataFrame | In `run_analysis`, convert the list of `AlertData` objects into a DataFrame before passing it to the final `AlertResult`.<br>```python<br>alerts_df = pd.DataFrame([alert.to_dict() for alert in alerts_data])<br>``` |

This checklist is now in place. I will use it as a strict guide for generating the next executor scripts.

Shall I proceed with creating the `ICHIMOKU` executor now?
