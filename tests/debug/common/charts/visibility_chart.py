# --- Python Standard Library ---
import os
import json
from typing import Tuple, Optional

# --- Third-Party Libraries ---
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertData
from src.stockreports.alert.common.constants import Signal, CandleColumn
from src.stockreports.utils.symbol_utils import sanitize_symbol_for_filename

def calculate_best_close_price(df: pd.DataFrame, alert_time: pd.Timestamp, signal_type: str) -> Tuple[Optional[float], Optional[pd.Timestamp], Optional[int]]:
    """
    Calculate the best close price opportunity after the alert candle.
    
    For SELL signals: Find the lowest low after the alert candle
    For BUY signals: Find the highest high after the alert candle
    
    Args:
        df (pd.DataFrame): DataFrame with columns [time, low, high, close, open]
        alert_time (pd.Timestamp): The time of the alert
        signal_type (str): Signal.BUY or Signal.SELL
    
    Returns:
        Tuple of (best_price, validation_time, time_to_close_minutes) or (None, None, None) if no future candles
    """
    try:
        # Find alert candle index
        alert_candle_idx = df[df['time'] <= alert_time].index.max()
        
        if pd.isna(alert_candle_idx):
            return None, None, None
        
        # Get candles after alert
        post_alert_df = df.iloc[int(alert_candle_idx) + 1:]
        
        if len(post_alert_df) == 0:
            return None, None, None  # No future candles
        
        if signal_type == Signal.SELL:
            # Find lowest low after alert
            best_idx = post_alert_df[CandleColumn.LOW].idxmin()
            best_price = post_alert_df.loc[best_idx, CandleColumn.LOW]
        else:  # BUY
            # Find highest high after alert
            best_idx = post_alert_df[CandleColumn.HIGH].idxmax()
            best_price = post_alert_df.loc[best_idx, CandleColumn.HIGH]
        
        validation_time = df.loc[best_idx, 'time']
        alert_time_ts = df.iloc[int(alert_candle_idx)]['time']
        
        # Calculate time difference in minutes
        time_to_close = int((validation_time - alert_time_ts).total_seconds() / 60)
        
        return best_price, validation_time, time_to_close
    except Exception as e:
        print(f"Error calculating best close price: {e}")
        return None, None, None

def generate_alert_chart(input_file: str, output_dir: str, approach_name: str, alert: AlertData):
    """
    Generates a standardized visibility chart for any given approach.

    This function plots candlestick data and overlays markers for the alert.
    The alert candle is highlighted with a different color.

    Args:
        input_file (str): Path to the JSON file containing the candlestick data.
        output_dir (str): Directory to save the generated chart.
        approach_name (str): The name of the alert approach.
        alert (AlertData): AlertData object containing alert information including alert_price, alert_time, signal, etc.
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
        if alert is not None and hasattr(alert, 'alert_time') and alert.alert_time is not None:
            alert_time_check = alert.alert_time
            # Convert alert_time to pandas.Timestamp if needed
            if not isinstance(alert_time_check, pd.Timestamp):
                alert_time_check = pd.to_datetime(alert_time_check)
            # Find the index of the candle that matches the alert_time
            highlight_idx = df.index[df['time'] == alert_time_check]
            if len(highlight_idx) == 0:
                # If exact match not found, find the last candle before or at alert_time
                highlight_idx = df.index[df['time'] <= alert_time_check]
                if len(highlight_idx) > 0:
                    highlight_idx = [highlight_idx[-1]]
                else:
                    highlight_idx = None

        # Draw all candles, but highlight the alert candle
        candle_colors = []
        for i, row in df.iterrows():
            if highlight_idx is not None and i == highlight_idx[0]:
                candle_colors.append('magenta')  # Highlight color
            elif row[CandleColumn.CLOSE] >= row[CandleColumn.OPEN]:
                candle_colors.append('g')  # Up candle
            else:
                candle_colors.append('r')  # Down candle

        # Draw candles one by one to allow custom coloring
        width = 0.0005
        for i, row in df.iterrows():
            color = candle_colors[i]
            ax.plot([row['time_numeric'], row['time_numeric']], [row[CandleColumn.LOW], row[CandleColumn.HIGH]], color=color, linewidth=1)
            rect_bottom = min(row[CandleColumn.OPEN], row[CandleColumn.CLOSE])
            rect_height = abs(row[CandleColumn.CLOSE] - row[CandleColumn.OPEN])
            ax.add_patch(plt.Rectangle((row['time_numeric'] - width/2, rect_bottom), width, rect_height, color=color, alpha=0.8))

        # Plot alert with price level lines
        # Store legend entries to avoid duplicates
        legend_entries = {}
        
        # Process single alert object
        alert_time_val = alert.alert_time
        # Convert alert_time to match dataframe timezone if needed
        if alert_time_val.tzinfo is not None and df['time'].dt.tz is not None:
            alert_time_val = alert_time_val.astimezone(df['time'].dt.tz)
        
        signal_type = alert.signal.value if hasattr(alert.signal, 'value') else str(alert.signal)
        alert_time_numeric = mdates.date2num(alert_time_val)
        candle = df[df['time'] <= alert_time_val].iloc[-1]
        marker = '^' if signal_type == Signal.BUY else 'v'
        color = 'blue' if signal_type == Signal.BUY else 'orange'
        y_pos = candle[CandleColumn.HIGH] + (df[CandleColumn.HIGH].max() - df[CandleColumn.LOW].min()) * 0.05
        ax.plot(alert_time_numeric, y_pos, marker, markersize=12, color=color, label=f'{signal_type} Alert')
        
        # --- DRAW PRICE LEVEL LINES ---
        
        # 1. PRIMARY ENTRY PRICE (Alert Price) - Cyan Solid Line
        alert_price = alert.alert_price
        if alert_price is not None:
            line = ax.axhline(y=alert_price, color='cyan', linestyle='-', linewidth=1, alpha=0.6)
            if 'Alert Price (PRIMARY)' not in legend_entries:
                legend_entries['Alert Price (PRIMARY)'] = line
        
        # Calculate structural and performance prices if not provided
        # These are based on the price range and signal type
        structural_price = alert.structural_suggested_price
        
        # 2. STRUCTURAL SUGGESTED PRICE - Gold Solid Line (if available)
        if structural_price is not None and pd.notna(structural_price):
            line = ax.axhline(y=structural_price, color='gold', linestyle='-', linewidth=1.5, alpha=0.7)
            if 'Structural Entry' not in legend_entries:
                legend_entries['Structural Entry'] = line
        
        # 3. PERFORMANCE SUGGESTED PRICE - Purple Solid Line (if available)
        performance_price = alert.performance_suggested_price
        
        if performance_price is not None and pd.notna(performance_price):
            line = ax.axhline(y=performance_price, color='purple', linestyle='-', linewidth=1.5, alpha=0.7)
            if 'Performance Entry' not in legend_entries:
                legend_entries['Performance Entry'] = line
        
        # 4. BEST CLOSE PRICE - Light Solid Line (Green for BUY, Red for SELL)
        best_close_price, validation_time, time_to_close = calculate_best_close_price(df, alert_time_val, signal_type)
        if best_close_price is not None:
            close_color = 'green' if signal_type == Signal.BUY else 'red'
            line = ax.axhline(y=best_close_price, color=close_color, linestyle='-', linewidth=1, alpha=0.6)
            if 'Best Close Price' not in legend_entries:
                legend_entries['Best Close Price'] = line
        
        # --- ADD PROFIT ZONE SHADING ---
        # Shade the area between entry price and exit price
        if best_close_price is not None:
            # Determine zone color and profit direction
            if signal_type == Signal.SELL:
                # For SELL: profit zone is from alert_price DOWN to best_close_price
                zone_color = 'red'
                zone_min = min(best_close_price, alert_price)
                zone_max = max(best_close_price, alert_price)
            else:  # BUY
                # For BUY: profit zone is from alert_price UP to best_close_price
                zone_color = 'green'
                zone_min = min(best_close_price, alert_price)
                zone_max = max(best_close_price, alert_price)
            
            # Add shaded rectangle for profit zone
            # Rectangle spans entire x-axis width
            rect = plt.Rectangle(
                (df['time_numeric'].min(), zone_min),  # Bottom-left corner
                (df['time_numeric'].max() - df['time_numeric'].min()),  # Width
                (zone_max - zone_min),  # Height
                color=zone_color,
                alpha=0.35,  # Increased opacity to make lines behind less visible
                zorder=0  # Behind all other elements
            )
            ax.add_patch(rect)
            
            # Add zone label in the middle of the shaded area
            zone_mid_price = (zone_min + zone_max) / 2
            zone_mid_time = (df['time_numeric'].min() + df['time_numeric'].max()) / 2
            profit_amount = abs(alert_price - best_close_price)
            profit_pct = (profit_amount / alert_price) * 100
            
            ax.text(zone_mid_time, zone_mid_price, 
                   f'Profit Zone\n+{profit_amount:.0f} points ({profit_pct:.2f}%)',
                   fontsize=10, ha='center', va='center', 
                   color=zone_color, alpha=0.6, weight='bold',
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.7))
        
        # --- ADD DETAILED ANNOTATIONS AT KEY CANDLES ---
        
        # --- CREATE 3 MARKERS WITH TOOLTIPS AT ALERT CANDLE ---
        alert_candle_idx = df[df['time'] <= alert_time_val].index.max()
        if not pd.isna(alert_candle_idx):
            alert_candle = df.iloc[int(alert_candle_idx)]
            price_range = df[CandleColumn.HIGH].max() - df[CandleColumn.LOW].min()
            
            # 1. ALERT PRICE MARKER (Gold, Primary)
            if alert_price is not None:
                ax.plot(alert_time_numeric, alert_price, marker='|', markersize=15, color='gold', linewidth=2.5, zorder=5)
                # Add arrow pointer and price label to the right of the alert candle
                label_x = alert_time_numeric + (df['time_numeric'].max() - df['time_numeric'].min()) * 0.02
                label_offset = price_range * 0.02  # Offset for stacking labels
                ax.annotate(f'${alert_price:.2f}', 
                           xy=(alert_time_numeric, alert_price), 
                           xytext=(label_x, alert_price + label_offset),
                           fontsize=8, ha='left', va='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='gold', alpha=1.0, edgecolor='gold', linewidth=1),
                           arrowprops=dict(arrowstyle='->', color='gold', lw=1.5, alpha=1.0),
                           zorder=6)
            
            # 2. STRUCTURAL SUGGESTED PRICE MARKER (Cyan)
            if structural_price is not None and pd.notna(structural_price):
                ax.plot(alert_time_numeric, structural_price, marker='|', markersize=15, color='cyan', linewidth=2.5, zorder=5)
                # Add arrow pointer and price label to the right of the alert candle
                label_x = alert_time_numeric + (df['time_numeric'].max() - df['time_numeric'].min()) * 0.02
                ax.annotate(f'${structural_price:.2f}', 
                           xy=(alert_time_numeric, structural_price), 
                           xytext=(label_x, structural_price),
                           fontsize=8, ha='left', va='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='cyan', alpha=1.0, edgecolor='cyan', linewidth=1),
                           arrowprops=dict(arrowstyle='->', color='cyan', lw=1.5, alpha=1.0),
                           zorder=6)
            
            # 3. PERFORMANCE SUGGESTED PRICE MARKER (Purple)
            if performance_price is not None and pd.notna(performance_price):
                ax.plot(alert_time_numeric, performance_price, marker='|', markersize=15, color='purple', linewidth=2.5, zorder=5)
                # Add arrow pointer and price label to the right of the alert candle
                label_x = alert_time_numeric + (df['time_numeric'].max() - df['time_numeric'].min()) * 0.02
                label_offset = price_range * -0.02  # Negative offset for stacking labels
                ax.annotate(f'${performance_price:.2f}', 
                           xy=(alert_time_numeric, performance_price), 
                           xytext=(label_x, performance_price + label_offset),
                           fontsize=8, ha='left', va='center',
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='plum', alpha=1.0, edgecolor='purple', linewidth=1),
                           arrowprops=dict(arrowstyle='->', color='purple', lw=1.5, alpha=1.0),
                           zorder=6)
        
        # Annotation at Best Close Candle (if available)
        if best_close_price is not None and validation_time is not None:
            # Find the candle at validation_time
            best_candle_idx = df[df['time'] <= validation_time].index.max()
            if not pd.isna(best_candle_idx):
                best_candle = df.iloc[int(best_candle_idx)]
                best_candle_time_numeric = df.loc[best_candle_idx, 'time_numeric']
                
                # Calculate profit in points (not dollars)
                if signal_type == Signal.SELL:
                    profit_points = alert_price - best_close_price
                    profit_pct = (profit_points / alert_price) * 100 if alert_price != 0 else 0
                else:  # BUY
                    profit_points = best_close_price - alert_price
                    profit_pct = (profit_points / alert_price) * 100 if alert_price != 0 else 0

        # Formatting: Show all time labels for each data point
        ax.set_xticks(df['time_numeric'])
        ax.set_xticklabels([dt.strftime('%Y-%m-%d %H:%M:%S') for dt in df['time']])
        fig.autofmt_xdate()

        ax.set_title(f'{symbol} - {approach_name} Alerts Analysis', fontsize=16)
        ax.set_xlabel('Time', fontsize=12)
        ax.set_ylabel('Price', fontsize=12)

        # Update legend with all markers and price level lines
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        
        # Add price level lines to legend
        for label, handle in legend_entries.items():
            if label not in by_label:
                by_label[label] = handle
        
        ax.legend(by_label.values(), by_label.keys(), loc='upper left', fontsize=10, 
                 framealpha=1.0, edgecolor='black', fancybox=False)

        plt.tight_layout()

        os.makedirs(output_dir, exist_ok=True)

        sanitized_symbol = sanitize_symbol_for_filename(symbol)
        chart_filename = os.path.join(output_dir, f"{sanitized_symbol}_{approach_name}_visibility_chart.png")
        plt.savefig(chart_filename)
        plt.close(fig)

        print(f"Chart saved to {chart_filename}")
    except Exception as e:
        print(f"An error occurred during alert chart generation: {e}")
