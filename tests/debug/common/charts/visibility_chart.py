import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import argparse
import os
import numpy as np
from src.stockreports.config import loader
# NEW: Import the preparation function directly from the confirmation script
from src.stockreports.alert.common.constants_charts import ChartDefaults, PlotKeys, PlotConfigKeys, Chart
from tests.debug.common.charts.configs.plot_config import PlotConfigurations
import copy
import json
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from mplfinance.original_flavor import candlestick_ohlc

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
