# Guide: Generating a Debug Script and Standardized Chart

## Purpose

When developing a new alert approach (e.g., `MyNewExecutor`), creating a corresponding debug script is **mandatory**. This script allows you to isolate and run your `Executor` class against a specific time window of data, using the same execution path as the main application.

This helps you:
-   Verify that your `run` method behaves as expected.
-   Pinpoint the exact time an alert is generated or why it fails.
-   Fine-tune parameters and test edge cases without running the entire application.
-   Ensure your logic works correctly in both `DEVELOPMENT` and `DEPLOYMENT` modes.

## Location

Place your new debug script in:
`tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`

## Mandatory Rule: Standardized Chart Generation

To ensure high visibility and simplify debugging, every debug script **must** use the standardized, common charting function.

### Core Architecture:

1.  **`debug_executor.py` (The Runner)**:
    *   This is your primary testing script.
    *   It must include `--save-to-file` and `--generate-chart` arguments.
    *   When `--generate-chart` is active, it calls the single, standardized `generate_alert_chart` function.

2.  **`visibility_chart.py` (The Charting Library)**:
    *   Located at `tests/debug/common/charts/visibility_chart.py`.
    *   This file contains the common `generate_alert_chart` function.
    *   This function is designed to be generic and work for any approach by plotting BUY/SELL signals from an alerts DataFrame.

### The Workflow:

1.  **Implement the Debug Script**: Create your `debug_executor.py` for your new approach.
2.  **Import the Standard Chart Function**: In your script, import the `generate_alert_chart` function:
    ```python
    from tests.debug.common.charts.visibility_chart import generate_alert_chart
    ```
3.  **Call it from the Debug Script**: In your `debug_executor.py`, call the function when the `--generate-chart` flag is present and alerts have been found.

This architecture creates a powerful, repeatable workflow: run one command to get the analysis, the raw data, and a rich visual chart that is consistent across all approaches.

### Example Usage:

```python
# In any tests/debug/alert/approach/[YOUR_APPROACH]/debug_executor.py

# ... imports ...
from tests.debug.common.charts.visibility_chart import generate_alert_chart

# ... inside run_debug_analysis ...
    if generate_chart:
        if json_file_path and not alerts_df.empty:
            # ... (define chart_output_dir) ...
            
            generate_alert_chart(
                input_file=json_file_path, 
                output_dir=chart_output_dir,
                approach_name=approach_name, # The name of your approach
                alerts_df=alerts_df
            )
```

By following this model, we ensure all approaches have consistent, high-quality debugging visuals while keeping the codebase clean and organized.
