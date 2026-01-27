import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse
import os
import numpy as np
from src.stockreports.config import loader
# NEW: Import the preparation function directly from the confirmation script
from src.stockreports.alert.common.confirmation.confirmation import prepare_indicators
from src.stockreports.alert.common.constants_charts import ChartDefaults, PlotKeys, PlotConfigKeys, Chart
from tests.debug.common.charts.configs.plot_config import PlotConfigurations
import copy
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

class VisibilityChartGenerator:
    def __init__(self, approach_name, signal_type='BUY'):
        self.approach_name = approach_name
        self.signal_type = signal_type
        self.signal_settings = loader.get_signal_settings()
        self.approach_config = self._load_approach_config()

    def _load_approach_config(self):
        try:
            return self.signal_settings.APPROACH_CONFIG.get(self.approach_name, self.signal_settings.APPROACH_CONFIG['default'])
        except AttributeError:
            print(f"ERROR: Could not find APPROACH_CONFIG in signal_settings.py")
            return None
        except KeyError:
            print(f"ERROR: Approach '{self.approach_name}' not found in APPROACH_CONFIG. Using 'default'.")
            return self.signal_settings.APPROACH_CONFIG['default']

    def has_enabled_plots(self) -> bool:
        """
        Checks if there are any confirmation plots enabled for the current approach.
        """
        if not self.approach_config:
            return False
            
        enabled_plot_keys = self._get_enabled_plot_keys()
        return len(enabled_plot_keys) > 0

    def _get_enabled_plot_keys(self) -> list:
        """
        Returns a list of keys for plots that are enabled in the approach configuration.
        """
        if not self.approach_config:
            return []

        enabled_keys = []
        if self.approach_config.get("USE_SHORT_TERM_MA_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.SHORT_MA)
        if self.approach_config.get("USE_MA_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.LONG_MA)
        if self.approach_config.get("USE_LONG_TERM_MA_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.PRIMARY_MA)
        if self.approach_config.get("USE_RSI_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.RSI)
        if self.approach_config.get("USE_MACD_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.MACD)
        if self.approach_config.get("USE_ADX_CONFIRMATION", False):
            enabled_keys.append(PlotKeys.ADX)
        return enabled_keys

    def _add_confirmation_plot(self, fig, df, breakout_candle, breakout_time, price_at_breakout, plot_info, row):
        """
        Internal helper to add a subplot for a specific confirmation indicator.
        """
        # --- Determine confirmation status using the config's own logic ---
        is_confirmed, status_text_y_pos = plot_info[PlotConfigKeys.CONFIRMATION_CHECK](breakout_candle, price_at_breakout)
        plot_type = plot_info[PlotConfigKeys.TYPE]

        status = ChartDefaults.STATUS_PASSED if is_confirmed else ChartDefaults.STATUS_FAILED
        status_color = ChartDefaults.COLOR_GREEN if is_confirmed else ChartDefaults.COLOR_RED

        # --- Add traces to the figure ---
        for trace in plot_info[PlotConfigKeys.TRACES]:
            trace_args = trace.copy()
            trace_type = trace_args.pop(PlotConfigKeys.TYPE)
            y_col = trace_args.pop(PlotConfigKeys.Y_COL, None)

            if trace_type == Chart.CANDLESTICK:
                if isinstance(y_col, list) and len(y_col) == 4:
                    o, h, l, c = y_col
                    fig.add_trace(go.Candlestick(x=df.index, open=df[o], high=df[h], low=df[l], close=df[c], **trace_args), row=row, col=1)
                else:
                    # Fallback or error for misconfigured candlestick
                    print(f"Warning: Candlestick trace for '{plot_info.get(PlotConfigKeys.TITLE)}' is misconfigured. Missing y_col list.")
            elif trace_type == Chart.SCATTER:
                if y_col:
                    fig.add_trace(go.Scatter(x=df.index, y=df[y_col], **trace_args), row=row, col=1)
                else:
                    print(f"Warning: Scatter trace for '{plot_info.get(PlotConfigKeys.TITLE)}' is missing y_col.")
            elif trace_type == Chart.HLINE:
                fig.add_hline(y=plot_info[PlotConfigKeys.THRESHOLD], **trace_args, row=row, col=1)

        # --- Add annotations and lines ---
        # NEW: Manually add the subplot title as an annotation
        y_ref_str = f"y{row}" if row > 1 else "y"
        fig.add_annotation(
            text=f"<b>{plot_info[PlotConfigKeys.TITLE]}</b>",
            xref="paper", yref=f"{y_ref_str} domain",
            x=0.5, y=1.05,
            showarrow=False,
            font=dict(size=16, family=ChartDefaults.ANNOTATION_FONT_FAMILY),
            xanchor='center',
            yanchor='bottom'
        )

        fig.add_vline(x=breakout_time, line_width=1, line_dash=ChartDefaults.VLINE_DASH, line_color=status_color, row=row, col=1)
        fig.add_annotation(
            x=breakout_time,
            y=status_text_y_pos,
            text=f"{ChartDefaults.CHECK_TEXT_PREFIX}{status}",
            showarrow=False,
            yshift=plot_info.get(PlotConfigKeys.ANNOTATION_YSHIFT, 10),
            font=dict(color=status_color, size=14, family=ChartDefaults.ANNOTATION_FONT_FAMILY),
            bgcolor=ChartDefaults.ANNOTATION_BG_COLOR,
            row=row, col=1
        )
        fig.update_yaxes(title_text=plot_info[PlotConfigKeys.Y_TITLE], row=row, col=1)

    def generate(self, input_file, output_dir, breakout_time_str):
        """
        Generates a comprehensive chart visualizing all key confirmation steps
        that are enabled for the given approach.
        """
        if self.approach_config is None:
            return

        # --- 1. Load and Prepare Data ---
        df = pd.read_json(input_file)
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        df = prepare_indicators(df)

        # --- 2. Identify Breakout Point ---
        if not breakout_time_str:
            print("Error: Breakout time not provided. Cannot generate chart.")
            return
            
        breakout_time = pd.to_datetime(breakout_time_str).tz_localize(df.index.tz)
        
        if breakout_time not in df.index:
            print(f"Error: Breakout time {breakout_time} not found in the data index. Cannot generate chart.")
            return

        breakout_candle = df.loc[breakout_time]
        price_at_breakout = breakout_candle['close']

        # --- 3. Define Plot Configurations ---
        config_generator = PlotConfigurations(self.signal_type)
        plot_configs = config_generator.get_all_configs()

        # --- 4. Determine which plots are enabled ---
        enabled_plot_keys = self._get_enabled_plot_keys()

        if not enabled_plot_keys:
            print(f"No confirmation checks are enabled for the '{self.approach_name}' approach. No chart will be generated.")
            return

        # --- 5. Dynamically Create Subplots ---
        enabled_plots = [copy.deepcopy(plot_configs[key]) for key in enabled_plot_keys]
        num_plots = len(enabled_plots)
        row_heights = [0.5] + [0.25] * (num_plots - 1) if num_plots > 1 else [1.0]

        fig = make_subplots(
            rows=num_plots, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=row_heights
        )

        # --- 6. Add Traces for Enabled Plots ---
        for i, plot_info in enumerate(enabled_plots):
            current_row = i + 1
            # Update the title to include the plot number before passing it
            plot_info[PlotConfigKeys.TITLE] = f"{i+1}. {plot_info[PlotConfigKeys.TITLE]}"
            self._add_confirmation_plot(fig, df, breakout_candle, breakout_time, price_at_breakout, plot_info, current_row)

        # --- 7. Finalize and Save Chart ---
        fig.update_layout(
            title_text=f'Confirmation Analysis for {os.path.basename(input_file)} ({self.approach_name})',
            showlegend=False,
            xaxis_rangeslider_visible=False,
            template=ChartDefaults.TEMPLATE
        )

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        base_filename = os.path.splitext(os.path.basename(input_file))[0]
        output_filename = os.path.join(output_dir, f"{base_filename}_confirmation_chart.html")
        fig.write_html(output_filename)
        print(f"Chart saved to {output_filename}")


def generate_visibility_chart(input_file, output_dir, approach_name, signal_type='BUY', breakout_time_str=None):
    """
    Legacy function to maintain backward compatibility.
    Initializes and runs the VisibilityChartGenerator class.
    """
    chart_generator = VisibilityChartGenerator(approach_name, signal_type)
    # Pre-flight check before generating
    if not chart_generator.has_enabled_plots():
        print(f"No confirmation checks are enabled for the '{approach_name}' approach. No chart will be generated.")
        return

    chart_generator.generate(input_file, output_dir, breakout_time_str)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate visibility charts for stock signal confirmation steps.")
    parser.add_argument(
        '--input-file',
        type=str,
        required=True,
        help='Path to the input JSON data file from a debug run.'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='tests/debug/charts',
        help='Directory to save the output HTML file.'
    )
    parser.add_argument(
        '--approach-name',
        type=str,
        required=True,
        help='The name of the approach being debugged (e.g., "CONSOLIDATION_BREAKOUT").'
    )
    parser.add_argument(
        '--signal-type',
        type=str,
        default='BUY',
        choices=['BUY', 'SELL'],
        help='The type of signal being analyzed (BUY or SELL).'
    )
    parser.add_argument(
        '--breakout-time',
        type=str,
        required=True,
        help='The timestamp of the breakout candle to analyze (e.g., "2025-11-25 11:27:00").'
    )
    args = parser.parse_args()

    # Use the new class-based approach
    chart_generator = VisibilityChartGenerator(args.approach_name, args.signal_type)
    chart_generator.generate(args.input_file, args.output_dir, args.breakout_time)


def generate_alert_chart(input_file: str, output_dir: str, approach_name: str, alerts_df: pd.DataFrame, alert_time=None):
    """
    Generates a standardized visibility chart for any given approach.

    This function plots candlestick data and overlays markers for all BUY and SELL
    alerts found in the provided alerts DataFrame. The alert_time param highlights
    the alert candle with a different color.

    Args:
        input_file (str): Path to the JSON file containing the candlestick data.
        output_dir (str): Directory to save the generated chart.
        approach_name (str): The name of the alert approach.
        alerts_df (pd.DataFrame): DataFrame containing the alerts to plot.
        alert_time (datetime, optional): The alert time to highlight the candle.
    """
    try:
        with open(input_file, 'r') as f:
            data = json.load(f)
        
        df = pd.DataFrame(data)
        if df.empty:
            print("Dataframe is empty, skipping chart generation.")
            return
        symbol = os.path.basename(input_file).split('_')[0]

        # Data preparation for plotting
        df['time'] = pd.to_datetime(df['time'])
        df['time_numeric'] = df['time'].apply(mdates.date2num)

        # Plotting
        fig, ax = plt.subplots(figsize=(20, 10))

        # Highlight the alert candle if alert_time is provided
        highlight_idx = None
        if alert_time is not None:
            # Convert alert_time to pandas.Timestamp if needed
            if not isinstance(alert_time, pd.Timestamp):
                alert_time = pd.to_datetime(alert_time)
            # Find the index of the candle that matches the alert_time
            highlight_idx = df.index[df['time'] == alert_time]
            if len(highlight_idx) == 0:
                # If exact match not found, find the last candle before or at alert_time
                highlight_idx = df.index[df['time'] <= alert_time]
                if len(highlight_idx) > 0:
                    highlight_idx = [highlight_idx[-1]]
                else:
                    highlight_idx = None

        # Draw all candles, but highlight the alert candle
        candle_colors = []
        for i, row in df.iterrows():
            if highlight_idx is not None and i == highlight_idx[0]:
                candle_colors.append('magenta')  # Highlight color
            elif row['close'] >= row['open']:
                candle_colors.append('g')  # Up candle
            else:
                candle_colors.append('r')  # Down candle

        # Draw candles one by one to allow custom coloring
        width = 0.0005
        for i, row in df.iterrows():
            color = candle_colors[i]
            ax.plot([row['time_numeric'], row['time_numeric']], [row['low'], row['high']], color=color, linewidth=1)
            rect_bottom = min(row['open'], row['close'])
            rect_height = abs(row['close'] - row['open'])
            ax.add_patch(plt.Rectangle((row['time_numeric'] - width/2, rect_bottom), width, rect_height, color=color, alpha=0.8))

        # Plot alerts
        alerts_df['alert_time'] = pd.to_datetime(alerts_df['alert_time']).dt.tz_convert(df['time'].dt.tz)
        for _, alert in alerts_df.iterrows():
            alert_time_val = alert['alert_time']
            signal_type = alert['signal']
            alert_time_numeric = mdates.date2num(alert_time_val)
            candle = df[df['time'] <= alert_time_val].iloc[-1]
            marker = '^' if signal_type == 'BUY' else 'v'
            color = 'blue' if signal_type == 'BUY' else 'orange'
            y_pos = candle['high'] + (df['high'].max() - df['low'].min()) * 0.05
            ax.plot(alert_time_numeric, y_pos, marker, markersize=12, color=color, label=f'{signal_type} Alert')

        # Formatting: Show all time labels for each data point
        ax.set_xticks(df['time_numeric'])
        ax.set_xticklabels([dt.strftime('%Y-%m-%d %H:%M:%S') for dt in df['time']])
        fig.autofmt_xdate()

        ax.set_title(f'{symbol} - {approach_name} Alerts Analysis', fontsize=16)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)

        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        ax.legend(by_label.values(), by_label.keys(), loc='upper left')

        plt.tight_layout()

        os.makedirs(output_dir, exist_ok=True)

        chart_filename = os.path.join(output_dir, f"{symbol}_{approach_name}_visibility_chart.png")
        plt.savefig(chart_filename)
        plt.close(fig)

        print(f"Chart saved to {chart_filename}")
    except Exception as e:
        print(f"An error occurred during alert chart generation: {e}")
