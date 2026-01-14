# Guide: Generating a Debug Script and Advanced Visibility Chart

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

## Mandatory Rule: Advanced Visibility Chart Generation

To ensure high visibility and simplify debugging, every debug script **must** integrate with the advanced, configuration-driven charting system. This system is designed to be modular, reusable, and easy to extend.

### Core Architecture:

1.  **`visibility_chart.py` (The Generator)**:
    *   This script contains the `VisibilityChartGenerator` class.
    *   Its responsibility is to load data, create a subplot layout, and iterate through a list of enabled plots, delegating the actual plotting logic to helper methods. It orchestrates the chart generation process.

2.  **`configs/plot_config.py` (The Configuration Builder)**:
    *   This script contains the `PlotConfigurations` class.
    *   It uses constants defined in `constants_charts.py` to build detailed configuration dictionaries for each type of plot (e.g., Price vs. MA, RSI vs. Threshold). It defines the `confirmation_check` logic and dynamically assembles plot properties, including whether to display a candlestick trace.

3.  **`common/constants_charts.py` (The Single Source of Truth)**:
    *   This file centralizes all "magic strings" and settings for charting. It defines plot types, trace types, colors, line styles, and the hierarchical structure for plot configurations (`PlotConfigs`). A key constant is `HAS_PRICE_TRACE_VALUE`, which controls whether a plot includes the main price candlestick chart.

This architecture creates a powerful, repeatable workflow: run one command to get the analysis, the raw data, and a rich, multi-panel visual chart explaining each step of the confirmation process.

### `configs/plot_config.py` Template

This class builds the specific configurations for each plot using a unified function.

```python
# tests/debug/common/charts/configs/plot_config.py
from src.stockreports.config import loader
from src.stockreports.alert.common.constants_charts import PlotConfigs, ChartDefaults, PlotKeys, Chart, PlotConfigKeys

class PlotConfigurations:
    """
    A class to generate plot configurations for the visibility chart.
    It encapsulates the logic for creating different plot types based on signal settings.
    """
    def __init__(self, signal_type='BUY'):
        """
        Initializes the PlotConfigurations class.

        Args:
            signal_type (str): The type of signal ('BUY' or 'SELL').
        """
        self.signal_type = signal_type
        self.signal_settings = loader.get_signal_settings()
        self.plot_keys = PlotConfigKeys

    def _create_plot_config(self, cfg):
        """Creates a generic plot configuration."""
        traces = []
        if cfg.HAS_PRICE_TRACE_VALUE:
            traces.append({
                self.plot_keys.TYPE: Chart.CANDLESTICK,
                self.plot_keys.Y_COL: ['open', 'high', 'low', 'close'],
                self.plot_keys.NAME: cfg.PRICE_NAME_VALUE,
                self.plot_keys.INCREASING_LINE_COLOR: cfg.PRICE_INCREASING_COLOR,
                self.plot_keys.DECREASING_LINE_COLOR: cfg.PRICE_DECREASING_COLOR
            })

        plot_type = Chart.PRICE_INDICATOR if cfg.HAS_PRICE_TRACE_VALUE else Chart.INDICATOR_THRESHOLD
        check_function = None
        plot_specific_props = {}

        if cfg.KEY in [PlotKeys.SHORT_MA, PlotKeys.LONG_MA, PlotKeys.PRIMARY_MA]:
            traces.append({
                self.plot_keys.TYPE: Chart.SCATTER,
                self.plot_keys.Y_COL: cfg.INDICATOR_COL_VALUE,
                self.plot_keys.NAME: cfg.NAME_VALUE,
                self.plot_keys.MODE: PlotConfigKeys.MODES_LINES,
                self.plot_keys.LINE: {self.plot_keys.COLOR: cfg.COLOR_VALUE}
            })
            def check(breakout_candle, price_at_breakout):
                indicator_val = breakout_candle[cfg.INDICATOR_COL_VALUE]
                is_confirmed = price_at_breakout > indicator_val if self.signal_type == 'BUY' else price_at_breakout < indicator_val
                return is_confirmed, price_at_breakout
            check_function = check
            plot_specific_props[self.plot_keys.ANNOTATION_YSHIFT] = 15

        elif cfg.KEY in [PlotKeys.RSI, PlotKeys.ADX]:
            # ... (Implementation for threshold plots like RSI, ADX)
            pass

        elif cfg.KEY == PlotKeys.MACD:
            # ... (Implementation for cross plots like MACD)
            pass

        base_config = {
            self.plot_keys.TITLE: cfg.TITLE_VALUE,
            self.plot_keys.TYPE: plot_type,
            self.plot_keys.INDICATOR_COL: cfg.INDICATOR_COL_VALUE,
            self.plot_keys.Y_TITLE: cfg.Y_TITLE_VALUE,
            self.plot_keys.TRACES: traces,
            self.plot_keys.CONFIRMATION_CHECK: check_function,
        }
        base_config.update(plot_specific_props)
        return base_config

    def get_all_configs(self):
        """
        Assembles and returns a dictionary of all plot configurations.
        """
        return {
            PlotKeys.SHORT_MA: self._create_plot_config(PlotConfigs.SHORT_MA),
            PlotKeys.LONG_MA: self._create_plot_config(PlotConfigs.LONG_MA),
            PlotKeys.PRIMARY_MA: self._create_plot_config(PlotConfigs.PRIMARY_MA),
            PlotKeys.RSI: self._create_plot_config(PlotConfigs.RSI),
            PlotKeys.MACD: self._create_plot_config(PlotConfigs.MACD),
            PlotKeys.ADX: self._create_plot_config(PlotConfigs.ADX),
        }
```

### `visibility_chart.py` Template

This class uses the configurations to generate the chart.

```python
# tests/debug/common/charts/visibility_chart.py
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from src.stockreports.config import loader
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators
from src.stockreports.alert.common.constants_charts import ChartDefaults, PlotKeys, PlotConfigKeys, Chart
from tests.debug.common.charts.configs.plot_config import PlotConfigurations

class VisibilityChartGenerator:
    def __init__(self, approach_name, signal_type='BUY'):
        self.approach_name = approach_name
        self.signal_type = signal_type
        self.signal_settings = loader.get_signal_settings()
        self.approach_config = self._load_approach_config()

    def _load_approach_config(self):
        # ... (Loads approach-specific settings)
        pass

    def _add_confirmation_plot(self, fig, df, breakout_candle, breakout_time, price_at_breakout, plot_info, row):
        """
        Internal helper to add a subplot for a specific confirmation indicator.
        """
        is_confirmed, status_text_y_pos = plot_info[PlotConfigKeys.CONFIRMATION_CHECK](breakout_candle, price_at_breakout)
        status = ChartDefaults.STATUS_PASSED if is_confirmed else ChartDefaults.STATUS_FAILED
        status_color = ChartDefaults.COLOR_GREEN if is_confirmed else ChartDefaults.COLOR_RED

        # --- Add traces to the figure ---
        for trace in plot_info[PlotConfigKeys.TRACES]:
            # ... (Logic to add candlestick, scatter, hline etc.)
            pass

        # --- Add annotations and lines ---
        fig.add_vline(x=breakout_time, line_dash=ChartDefaults.VLINE_DASH, line_color=status_color, row=row, col=1)
        fig.add_annotation(
            x=breakout_time, y=status_text_y_pos, text=f"{ChartDefaults.CHECK_TEXT_PREFIX}{status}",
            # ... other annotation properties
        )
        fig.update_yaxes(title_text=plot_info[PlotConfigKeys.Y_TITLE], row=row, col=1)

    def generate(self, input_file, output_dir, breakout_time_str):
        # --- 1. Load and Prepare Data ---
        df = pd.read_json(input_file)
        # ... (prepare indicators)

        # --- 2. Identify Breakout Point ---
        breakout_time = pd.to_datetime(breakout_time_str).tz_localize(df.index.tz)
        breakout_candle = df.loc[breakout_time]
        price_at_breakout = breakout_candle['close']

        # --- 3. Define Plot Configurations ---
        config_generator = PlotConfigurations(self.signal_type)
        plot_configs = config_generator.get_all_configs()

        # --- 4. Determine which plots are enabled ---
        enabled_plot_keys = []
        if self.approach_config.get("USE_SHORT_TERM_MA_CONFIRMATION", False):
            enabled_plot_keys.append(PlotKeys.SHORT_MA)
        # ... (check other enabled plots)

        # --- 5. Dynamically Create Subplots ---
        enabled_plots = [plot_configs[key] for key in enabled_plot_keys]
        subplot_titles = [f"{i+1}. {p[PlotConfigKeys.TITLE]}" for i, p in enumerate(enabled_plots)]
        num_plots = len(enabled_plots)
        fig = make_subplots(rows=num_plots, cols=1, subplot_titles=subplot_titles)

        # --- 6. Add Traces for Enabled Plots ---
        for i, plot_info in enumerate(enabled_plots):
            self._add_confirmation_plot(fig, df, breakout_candle, breakout_time, price_at_breakout, plot_info, i + 1)

        # --- 7. Finalize and Save Chart ---
        # ... (update layout and save file)
        pass

def generate_visibility_chart(input_file, output_dir, approach_name, signal_type, breakout_time_str):
    chart_generator = VisibilityChartGenerator(approach_name, signal_type)
    chart_generator.generate(input_file, output_dir, breakout_time_str)
```

### `debug_executor.py` Template

This script is the entry point for your debugging session.

```python
"""
A command-line tool for debugging the [YOUR_APPROACH_NAME] alert logic.

Usage:
    python3 tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py \\
        --symbol [SYMBOL_TICKER] \\
        --start-time [YYYY-MM-DD HH:MM:SS] \\
        --end-time [YYYY-MM-DD HH:MM:SS] \\
        --save-to-file \\
        --generate-chart

Example:
    export PYTHONPATH=$(pwd)
    python tests/debug/alert/approach/CONSOLIDATION_BREAKOUT/debug_executor.py \
        --symbol "VN30" \
        --start-time "2025-11-25 10:00:00" \
        --end-time "2025-11-25 11:30:00" \
        --save-to-file --generate-chart
"""
import sys
import os
import argparse
# ... other imports

# 1. Add project root to Python path
# ...

# 2. Import necessary components
from src.stockreports.config import loader
from src.stockreports.utils.data_utils import load_live_data
from tests.debug.common.utils.debug_utils import save_debug_data
from src.stockreports.alert.common.constants import Mode
# IMPORTANT: Update this to your executor class
from src.stockreports.alert.approach.CONSOLIDATION_BREAKOUT.executor import ConsolidationBreakoutExecutor
# NEW: Import the updated chart generation function
from tests.debug.common.charts.visibility_chart import generate_visibility_chart

# ... (logging setup)

def run_debug_analysis(symbol, start_time_str, end_time_str, save_to_file, generate_chart):
    # ... (Steps 1-3: Load config, fetch data, call executor)

    # --- 4. Report Results ---
    # ... (Print status and alerts)

    # --- 5. Generate Visibility Chart ---
    if generate_chart:
        if json_file_path:
            print("\n--- Generating visibility chart ---")
            # Construct a specific output directory for the chart
            chart_output_dir = os.path.join(project_root, 'tests', 'debug', 'data', 'charts', f"{symbol}_{start_str}_to_{end_str}")

            # Call the chart generator with all required parameters
            generate_visibility_chart(
                json_file_path, 
                chart_output_dir,
                approach_name="CONSOLIDATION_BREAKOUT", # Or your approach name
                signal_type="BUY", 
                breakout_time_str="2025-11-25 11:27:00" # IMPORTANT: Hardcoded for now
            )
        else:
            print("\n--- Skipping chart generation because --save-to-file was not used. ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug the [YOUR_APPROACH_NAME] logic.")
    # ... (Argument definitions for symbol, start-time, end-time, save-to-file, generate-chart)
    args = parser.parse_args()
    run_debug_analysis(args.symbol, args.start_time, args.end_time, args.save_to_file, args.generate_chart)
```

## How to Adapt the Templates

1.  **Centralize Charting Logic**: The files `visibility_chart.py`, `configs/plot_config.py`, and `common/constants_charts.py` should be placed in a common directory (e.g., `tests/debug/common/charts/`) so they can be reused by all debug executors.
2.  **Update `debug_executor.py`**:
    *   Save the template to `tests/debug/alert/approach/[YOUR_APPROACH_NAME]/debug_executor.py`.
    *   Change the import from `ConsolidationBreakoutExecutor` to your executor's class.
    *   In the "Instantiate and Call" section, change `ConsolidationBreakoutExecutor` to your executor's class name.
    *   In the `generate_visibility_chart` call, update the `approach_name` and be mindful of the hardcoded `breakout_time_str`.
3.  **Extend Chart Configurations**:
    *   If your approach uses new indicators, add new configuration classes to `PlotConfigs` in `constants_charts.py`. Make sure to set the `HAS_PRICE_TRACE_VALUE` flag correctly.
    *   Add corresponding keys to `PlotKeys`.
    *   Add the new plot to the dictionary returned by `PlotConfigurations.get_all_configs()`.
    *   Implement the specific logic for your new indicator inside `_create_plot_config`.
    *   Update `VisibilityChartGenerator` to check for the `USE_...` flag for your new plot.

This updated guide ensures your debug scripts are aligned with the new, more robust, object-oriented, and configuration-driven framework.

## References

- For real-world examples of issues encountered during debugging and their resolutions, consult the [Technical Case Studies & Issue Resolution Log](../case-studies/TECHNICAL_CASE_STUDIES.md). This can provide valuable context for troubleshooting.
