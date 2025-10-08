import json, pandas as pd, numpy as np, pytz
from datetime import datetime, timezone
from scipy.signal import find_peaks
import os
import glob

# Determine the root directory of the project
# This assumes the script is in 'src/stockreports/analysis'
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..', '..', '..'))

# --- Load and Merge All Data Files ---
data_dir = os.path.join(project_root, "src", "stockreports", "data", "VN30")
file_paths = glob.glob(os.path.join(data_dir, "*.json"))

if not file_paths:
    raise SystemExit(f"No JSON data files found in '{data_dir}'.")

all_dfs = []
for path in file_paths:
    with open(path, "r") as f:
        data = json.load(f)

    # Basic validation for current file
    keys = ["t", "o", "h", "l", "c", "v"]
    if not all(k in data for k in keys):
        print(f"Warning: Skipping file {path} due to missing required keys.")
        continue

    min_len = min(len(data[k]) for k in keys)
    times_raw = data["t"][:min_len]

    times = []
    for t in times_raw:
        try:
            times.append(pd.to_datetime(int(t), unit="s", utc=True))
        except (ValueError, TypeError):
            times.append(pd.to_datetime(t, utc=True))

    df_single = pd.DataFrame({
        "time": times,
        "open": data["o"][:min_len],
        "high": data["h"][:min_len],
        "low": data["l"][:min_len],
        "close": data["c"][:min_len],
        "volume": data["v"][:min_len],
    })
    all_dfs.append(df_single)

if not all_dfs:
    raise SystemExit("No valid data could be loaded from any file.")

# Concatenate, sort, and remove duplicates
df = pd.concat(all_dfs, ignore_index=True)
df = df.sort_values("time").reset_index(drop=True)
df.drop_duplicates(subset=['time'], keep='first', inplace=True)

# Convert time to Vietnam time (UTC+7)
df['time'] = df['time'].dt.tz_convert('Asia/Ho_Chi_Minh')
df['date'] = df['time'].dt.date

# --- 1) Detect significant pivots using scipy.signal.find_peaks ---
pivots = []
# Prominence: How much a peak stands out from the surrounding baseline.
# A good starting point is a fraction of the daily price range.
price_range = (df['high'] - df['low']).mean()
prominence = price_range * 0.2  # Adjust this factor to control sensitivity

# Distance: Minimum number of data points between peaks (e.g., 60 minutes)
distance = 60

# Find tops (peaks) and their properties
top_indices, top_props = find_peaks(df['high'], prominence=prominence, distance=distance)

# Find bottoms (troughs) by inverting the series
bottom_indices, bottom_props = find_peaks(-df['low'], prominence=prominence, distance=distance)

for i, prom in zip(top_indices, top_props['prominences']):
    pivots.append({"time": df.iloc[i]["time"], "type": "top", "price": df.iloc[i]["high"], "index": i, "prominence": prom})

for i, prom in zip(bottom_indices, bottom_props['prominences']):
    pivots.append({"time": df.iloc[i]["time"], "type": "bottom", "price": df.iloc[i]["low"], "index": i, "prominence": prom})

df_pivots = pd.DataFrame(pivots).sort_values('time').reset_index(drop=True)

# --- Peak and Trough Time Zones (5-min intervals) ---
if not df_pivots.empty:
    df_pivots['time_5min'] = df_pivots['time'].dt.floor('5min').dt.time
    pivot_zones = df_pivots.groupby(['time_5min', 'type']).size().reset_index(name='count')
    top_zones = pivot_zones[pivot_zones['type'] == 'top'].sort_values('count', ascending=False)
    bottom_zones = pivot_zones[pivot_zones['type'] == 'bottom'].sort_values('count', ascending=False)
else:
    top_zones = pd.DataFrame(columns=['time_5min', 'type', 'count'])
    bottom_zones = pd.DataFrame(columns=['time_5min', 'type', 'count'])

# --- 2) Consistent Trend Interval Analysis (5-min) ---
# Ensure 'time' is the index for resampling
df_resample = df.set_index('time')

# Resample into 5-minute intervals and get the first and last close price
df_5min = df_resample['close'].resample('5T').agg(['first', 'last']).dropna()

# Determine the trend for each interval
df_5min['trend'] = 'flat'
df_5min.loc[df_5min['last'] > df_5min['first'], 'trend'] = 'up'
df_5min.loc[df_5min['last'] < df_5min['first'], 'trend'] = 'down'

# Extract date and time parts
df_5min['date'] = df_5min.index.date
df_5min['time_interval'] = df_5min.index.time

# Count the number of unique days in the dataset
num_days = df['time'].dt.date.nunique()

# Find intervals that are consistently 'up' or 'down' across all days
consistent_trends = []
# Group by the time interval (e.g., 09:00:00, 09:05:00, etc.)
for time_interval, group in df_5min.groupby('time_interval'):
    
    # Count the occurrences of each trend for this interval
    trend_counts = group['trend'].value_counts()
    
    # Check for 'up' trend consistency
    if trend_counts.get('up', 0) == num_days and 'down' not in trend_counts and 'flat' not in trend_counts:
        consistent_trends.append({
            'Time Interval': time_interval.strftime('%H:%M'),
            'Consistent Trend': 'up',
            'Frequency (Days)': num_days
        })
        
    # Check for 'down' trend consistency
    if trend_counts.get('down', 0) == num_days and 'up' not in trend_counts and 'flat' not in trend_counts:
        consistent_trends.append({
            'Time Interval': time_interval.strftime('%H:%M'),
            'Consistent Trend': 'down',
            'Frequency (Days)': num_days
        })

df_consistent_trends = pd.DataFrame(consistent_trends)

# --- Additional indicators: MA crossovers and volume spikes ---
df["ma5"] = df["close"].rolling(5, min_periods=1).mean()
df["ma20"] = df["close"].rolling(20, min_periods=1).mean()

# --- Ichimoku Cloud Calculation ---
# Tenkan-sen (Conversion Line): 9-period
nine_period_high = df['high'].rolling(window=9).max()
nine_period_low = df['low'].rolling(window=9).min()
df['tenkan_sen'] = (nine_period_high + nine_period_low) / 2

# Kijun-sen (Base Line): 26-period
twenty_six_period_high = df['high'].rolling(window=26).max()
twenty_six_period_low = df['low'].rolling(window=26).min()
df['kijun_sen'] = (twenty_six_period_high + twenty_six_period_low) / 2

# Senkou Span A (Leading Span A) - Plotted 26 periods in the future
df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)

# Senkou Span B (Leading Span B): 52-period - Plotted 26 periods in the future
fifty_two_period_high = df['high'].rolling(window=52).max()
fifty_two_period_low = df['low'].rolling(window=52).min()
df['senkou_span_b'] = ((fifty_two_period_high + fifty_two_period_low) / 2).shift(26)

crosses = []
for i in range(1,len(df)):
    prev_diff = df.iloc[i-1]["ma5"] - df.iloc[i-1]["ma20"]
    cur_diff  = df.iloc[i]["ma5"] - df.iloc[i]["ma20"]
    if prev_diff <= 0 and cur_diff > 0:
        crosses.append({"time": df.iloc[i]["time"], "type":"golden_cross", "price": df.iloc[i]["close"]})
    elif prev_diff >= 0 and cur_diff < 0:
        crosses.append({"time": df.iloc[i]["time"], "type":"death_cross", "price": df.iloc[i]["close"]})
df_crosses = pd.DataFrame(crosses)

# --- New: Trend Strength Signal ---
df['trend_strength'] = False
for i in range(1, len(df)):
    prev_candle = df.iloc[i-1]
    latest_candle = df.iloc[i]

    latest_is_up = latest_candle['close'] > latest_candle['open']
    prev_is_up = prev_candle['close'] > prev_candle['open']
    latest_is_down = latest_candle['close'] < latest_candle['open']
    prev_is_down = prev_candle['close'] < prev_candle['open']

    sequential_trend = (latest_is_up and prev_is_up) or (latest_is_down and prev_is_down)

    if sequential_trend:
        latest_body = abs(latest_candle['close'] - latest_candle['open'])
        prev_body = abs(prev_candle['close'] - prev_candle['open'])
        increased_momentum = latest_body > prev_body

        if increased_momentum:
            candle_range = latest_candle['high'] - latest_candle['low']
            if candle_range > 0:
                if latest_is_up:
                    # Closing price is in the top 25% of the candle's range
                    confirmation = (latest_candle['close'] - latest_candle['low']) / candle_range > 0.75
                else: # latest_is_down
                    # Closing price is in the bottom 25% of the candle's range
                    confirmation = (latest_candle['high'] - latest_candle['close']) / candle_range > 0.75
                
                if confirmation:
                    # Use .loc with the DataFrame's index to ensure correct assignment
                    df.loc[df.index[i], 'trend_strength'] = True

df_trend_strength = df[df['trend_strength']][['time']].copy()

# --- MA Crossover Time Zone Analysis ---
if not df_crosses.empty:
    df_crosses['time_5min'] = df_crosses['time'].dt.floor('5min').dt.time
    cross_zones = df_crosses.groupby(['time_5min', 'type']).size().reset_index(name='count')
    golden_cross_zones = cross_zones[cross_zones['type'] == 'golden_cross'].sort_values('count', ascending=False)
    death_cross_zones = cross_zones[cross_zones['type'] == 'death_cross'].sort_values('count', ascending=False)
else:
    golden_cross_zones = pd.DataFrame(columns=['time_5min', 'type', 'count'])
    death_cross_zones = pd.DataFrame(columns=['time_5min', 'type', 'count'])

df['volume_spike'] = df['volume'] > (df['volume'].rolling(window=20).mean() + 2 * df['volume'].rolling(window=20).std())
df_volume_spikes = df[df['volume_spike']][['time', 'volume', 'close']].copy()

# --- Volume Spike Time Zone Analysis ---
if not df_volume_spikes.empty:
    df_volume_spikes['time_5min'] = df_volume_spikes['time'].dt.floor('5min').dt.time
    volume_spike_zones = df_volume_spikes.groupby('time_5min').size().reset_index(name='count').sort_values('count', ascending=False)
else:
    volume_spike_zones = pd.DataFrame(columns=['time_5min', 'count'])

# --- 4) Daily Summary: Highest Top and Lowest Bottom ---
if not df_pivots.empty:
    df_pivots['date'] = df_pivots['time'].dt.date
    daily_summary = []
    for date, day_df in df.groupby('date'):
        if not day_df.empty:
            highest_top = day_df.loc[day_df['high'].idxmax()]
            lowest_bottom = day_df.loc[day_df['low'].idxmin()]

            top_session = "Morning (9:00-11:30)" if highest_top['time'].hour < 12 else "Afternoon (13:00-14:45)"
            bottom_session = "Morning (9:00-11:30)" if lowest_bottom['time'].hour < 12 else "Afternoon (13:00-14:45)"

            daily_summary.append({
                "Date": date,
                "Highest Top Time": highest_top['time'].time(),
                "Highest Top Price": highest_top['high'],
                "Top Session": top_session,
                "Lowest Bottom Time": lowest_bottom['time'].time(),
                "Lowest Bottom Price": lowest_bottom['low'],
                "Bottom Session": bottom_session
            })

    df_daily_summary = pd.DataFrame(daily_summary)

    # --- Intraday Trend Analysis ---
    if not df_daily_summary.empty:
        bottom_to_top_days = (df_daily_summary['Lowest Bottom Time'] < df_daily_summary['Highest Top Time']).sum()
        top_to_bottom_days = (df_daily_summary['Highest Top Time'] < df_daily_summary['Lowest Bottom Time']).sum()

    # --- Intraday Pivot Switches ---
    if not df_pivots.empty:
        df_pivots['date'] = df_pivots['time'].dt.date
        daily_switches = []
        for date, day_pivots in df_pivots.groupby('date'):
            if len(day_pivots) > 1:
                switches = 0
                pivots_list = day_pivots.to_dict('records')
                for i in range(1, len(pivots_list)):
                    if pivots_list[i]['type'] != pivots_list[i-1]['type']:
                        switches += 1
                daily_switches.append({'Date': date, 'Switch Count': switches})
        
        df_daily_switches = pd.DataFrame(daily_switches)
        
        if not df_daily_switches.empty:
            switch_counts_summary = df_daily_switches['Switch Count'].value_counts().reset_index()
            switch_counts_summary.columns = ['Number of Switches', 'Number of Days']
            switch_counts_summary = switch_counts_summary.sort_values('Number of Switches')
    else:
        df_daily_switches = pd.DataFrame(columns=['Date', 'Switch Count'])
        switch_counts_summary = pd.DataFrame(columns=['Number of Switches', 'Number of Days'])

    # --- Intraday Most Prominent Pivots Summary ---
    if not df_pivots.empty:
        if 'date' not in df_pivots.columns:
            df_pivots['date'] = df_pivots['time'].dt.date
            
        prominent_pivot_summary = []
        for date, day_pivots in df_pivots.groupby('date'):
            tops = day_pivots[day_pivots['type'] == 'top']
            bottoms = day_pivots[day_pivots['type'] == 'bottom']
            
            peak_info = {}
            if not tops.empty:
                prominent_peak = tops.loc[tops['prominence'].idxmax()]
                peak_info = {
                    'Prominent Peak Time': prominent_peak['time'].time(), 
                    'Prominent Peak Price': prominent_peak['price'],
                    'Peak Prominence': prominent_peak['prominence']
                }
            else:
                peak_info = {'Prominent Peak Time': 'N/A', 'Prominent Peak Price': 'N/A', 'Peak Prominence': 'N/A'}

            trough_info = {}
            if not bottoms.empty:
                prominent_trough = bottoms.loc[bottoms['prominence'].idxmax()]
                trough_info = {
                    'Prominent Trough Time': prominent_trough['time'].time(), 
                    'Prominent Trough Price': prominent_trough['price'],
                    'Trough Prominence': prominent_trough['prominence']
                }
            else:
                trough_info = {'Prominent Trough Time': 'N/A', 'Prominent Trough Price': 'N/A', 'Trough Prominence': 'N/A'}
                
            prominent_pivot_summary.append({
                'Date': date,
                **peak_info,
                **trough_info
            })
        df_prominent_pivot_summary = pd.DataFrame(prominent_pivot_summary)
    else:
        df_prominent_pivot_summary = pd.DataFrame()


# --- Combined Precursor Signal Analysis ---
# This section is now integrated into the "Big Trend Analysis" and the new "Precursor Combination Analysis"
# The old "Reversal Signal Analysis" logic is removed for conciseness.
df_reversals = pd.DataFrame()

# --- Big Trend Analysis (Direct Method) ---
big_trends = []
# Use a 5-minute window to check for trends directly from the source df
window_size = "5min" 

# Iterate through the DataFrame in steps, examining a 5-minute window at each step
for i in range(len(df) - 1):
    start_time = df.iloc[i]['time']
    
    # Define the 5-minute window from the current point
    end_time = start_time + pd.Timedelta(minutes=5)
    
    # Get the data within this specific window
    window_df = df[(df['time'] >= start_time) & (df['time'] <= end_time)]
    
    if len(window_df) < 2:
        continue

    # Calculate price change within the window
    start_price = window_df.iloc[0]['close']
    end_price = window_df.iloc[-1]['close']
    price_change = end_price - start_price
    
    # Check if it meets the "big trend" criteria
    if abs(price_change) > 5:
        trend_type = "Uptrend" if price_change > 0 else "Downtrend"
        
        # --- Look-back analysis for combined precursors ---
        lookback_start_time = start_time - pd.Timedelta(minutes=5)
        lookback_end_time = start_time
        
        precursors_found = []

        # Check for MA Crossover
        ma_cross_df = df_crosses[
            (df_crosses['time'] > lookback_start_time) & 
            (df_crosses['time'] <= lookback_end_time)
        ]
        if not ma_cross_df.empty:
            cross_type = ma_cross_df.iloc[0]['type']
            if (trend_type == "Uptrend" and cross_type == "golden_cross") or \
               (trend_type == "Downtrend" and cross_type == "death_cross"):
                precursors_found.append("MA Cross")

        # Check for Volume Spike
        if not df_volume_spikes[
            (df_volume_spikes['time'] > lookback_start_time) & 
            (df_volume_spikes['time'] <= lookback_end_time)
        ].empty:
            precursors_found.append("Volume Spike")

        # Check for Trend Strength
        if not df_trend_strength[
            (df_trend_strength['time'] > lookback_start_time) &
            (df_trend_strength['time'] <= lookback_end_time)
        ].empty:
            precursors_found.append("Trend Strength")

        # Check for Ichimoku Signal
        lookback_window_df = df[
            (df['time'] > lookback_start_time) & 
            (df['time'] < start_time)
        ]
        if not lookback_window_df.empty:
            last_minute_before_trend = lookback_window_df.iloc[-1]
            price = last_minute_before_trend['close']
            tenkan = last_minute_before_trend['tenkan_sen']
            kijun = last_minute_before_trend['kijun_sen']
            span_a = last_minute_before_trend['senkou_span_a']
            span_b = last_minute_before_trend['senkou_span_b']

            if pd.notna(tenkan) and pd.notna(kijun) and pd.notna(span_a) and pd.notna(span_b):
                is_bullish_signal = (price > span_a) and (price > span_b) and (tenkan > kijun)
                is_bearish_signal = (price < span_a) and (price < span_b) and (tenkan < kijun)
                
                if trend_type == "Uptrend" and is_bullish_signal:
                    precursors_found.append("Ichimoku")
                elif trend_type == "Downtrend" and is_bearish_signal:
                    precursors_found.append("Ichimoku")

        # To avoid logging the same trend multiple times, we check if this trend is too similar to the last one found
        is_duplicate = False
        if big_trends:
            last_trend = big_trends[-1]
            if (start_time - last_trend['Trend Start Time']).total_seconds() < 60:
                is_duplicate = True

        if not is_duplicate:
            combination = ", ".join(precursors_found) if precursors_found else "None"
            big_trends.append({
                "Trend Start Time": start_time,
                "Trend End Time": window_df.iloc[-1]['time'],
                "Trend Type": trend_type,
                "Price Change": price_change,
                "Precursor Combination": combination,
                "Precursor Count": len(precursors_found)
            })

df_big_trends = pd.DataFrame(big_trends)

# --- Big Trend Hotspot Analysis ---
if not df_big_trends.empty:
    df_big_trends['time_5min'] = df_big_trends['Trend Start Time'].dt.floor('5min').dt.time
    # Group by time and trend type, then unstack to create columns for Uptrend/Downtrend
    hotspot_details = df_big_trends.groupby(['time_5min', 'Trend Type']).size().unstack(fill_value=0)
    
    # Ensure both columns exist even if one type of trend didn't happen
    if 'Uptrend' not in hotspot_details:
        hotspot_details['Uptrend'] = 0
    if 'Downtrend' not in hotspot_details:
        hotspot_details['Downtrend'] = 0
    
    hotspot_details['Total'] = hotspot_details['Uptrend'] + hotspot_details['Downtrend']
    
    # Sort by total count and reset index to make 'time_5min' a column
    big_trend_hotspots = hotspot_details.sort_values('Total', ascending=False).reset_index()
else:
    big_trend_hotspots = pd.DataFrame(columns=['time_5min', 'Uptrend', 'Downtrend', 'Total'])


# --- Precursor Combination Analysis ---
if not df_big_trends.empty:
    total_big_trends = len(df_big_trends)
    combination_counts = df_big_trends['Precursor Combination'].value_counts().reset_index()
    combination_counts.columns = ['Combination', 'Count']
    combination_counts['Frequency'] = (combination_counts['Count'] / total_big_trends * 100).apply(lambda x: f"{x:.2f}%")
    # Sort by count to show the most frequent combinations first
    combination_counts.sort_values('Count', ascending=False, inplace=True)
else:
    combination_counts = pd.DataFrame(columns=['Combination', 'Count', 'Rate'])



# --- Output Markdown tables ---
# Create the reports directory if it doesn't exist
reports_dir = os.path.join(project_root, "reports")
os.makedirs(reports_dir, exist_ok=True)

timestamp = datetime.now(timezone.utc).astimezone(pytz.timezone('Asia/Ho_Chi_Minh')).strftime("%Y%m%d_%H%M%S")
if len(file_paths) > 1:
    base_name = "combined_analysis_report"
    report_title = "VN30 Intraday Analysis Report (Combined Data)"
    data_source_info = "Data from multiple files in `src/stockreports/data/`"
else:
    source_filename = os.path.basename(file_paths[0])
    base_name = f"{os.path.splitext(source_filename)[0]}_analysis_report"
    report_title = f"VN30 Intraday Analysis Report for {os.path.splitext(source_filename)[0]}"
    data_source_info = f"Data source: {source_filename}"

output_filename = f"{base_name}_{timestamp}.md"
output_path = os.path.join(reports_dir, output_filename)

with open(output_path, "w") as f:
    f.write(f"# {report_title}\n\n")
    f.write(f"Report generated on: {datetime.now(timezone.utc).astimezone(pytz.timezone('Asia/Ho_Chi_Minh')).strftime('%Y-%m-%d %H:%M:%S %Z')}\n\n")
    f.write(f"{data_source_info}\n\n")
    f.write("## Summary\n\n")
    f.write("This report provides an intraday analysis of the VN30 index based on 1-minute data. It identifies key patterns and signals to help new traders understand market behavior, including trend reversals, common trend durations, and potential times for buying and selling.\n\n")
    f.write("## Agenda\n\n")
    f.write("1.  [Consistent Trend Intervals (5-min)](#consistent-trend-intervals-5-min)\n")
    f.write("2.  [MA Crossover Time Zones (MA5 vs MA20)](#ma-crossover-time-zones-ma5-vs-ma20)\n")
    f.write("3.  [Volume Spike Hotspots](#volume-spike-hotspots)\n")
    f.write("4.  [Intraday Highest Top and Lowest Bottom Summary](#intraday-highest-top-and-lowest-bottom-summary)\n")
    f.write("5.  [Intraday Trend Guessing](#intraday-trend-guessing)\n")
    f.write("6.  [Peak and Trough Time Zones (5-minute intervals)](#peak-and-trough-time-zones-5-minute-intervals)\n")
    f.write("7.  [Intraday Pivot Switches](#intraday-pivot-switches)\n")
    f.write("8.  [Intraday Most Prominent Pivots](#intraday-most-prominent-pivots)\n")
    f.write("9. [Big Trend Analysis (Price Change > 5 in < 5 min)](#big-trend-analysis-price-change--5-in--5-min)\n")
    f.write("10. [Big Trend Hotspots](#big-trend-hotspots)\n")
    f.write("11. [Precursor Combination Analysis](#precursor-combination-analysis)\n")
    f.write("12. [Trading Suggestions for New Traders](#trading-suggestions-for-new-traders)\n\n")

    f.write("### Consistent Trend Intervals (5-min)\n\n")
    f.write("This table shows 5-minute time intervals that have demonstrated a *consistent* trend (either always 'up' or always 'down') across every single trading day in the dataset. If an interval appears here, it has historically been a very reliable period of directional movement.\n\n")
    if df_consistent_trends.empty:
        f.write("No 5-minute intervals with a perfectly consistent trend were found across all trading days.\n\n")
    else:
        f.write(df_consistent_trends.to_markdown(index=False))
        f.write("\n\n")

    f.write("### MA Crossover Time Zones (MA5 vs MA20)\n\n")
    f.write("This section identifies the 5-minute intervals when 'Golden Crosses' (bullish signal) and 'Death Crosses' (bearish signal) happen most frequently. This can help traders anticipate potential momentum shifts at specific times of the day.\n\n")
    
    if not golden_cross_zones.empty:
        f.write("- **Golden Cross Hotspots:** Golden crosses have most frequently occurred during the following 5-minute intervals:\n")
        for index, row in golden_cross_zones.head(5).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['count']} times\n")
        f.write("\n  - **Trader's Note:** Be watchful for buying opportunities or strengthening upward momentum during these time windows.\n\n")
    else:
        f.write("- **Golden Cross Hotspots:** No recurring time zones for golden crosses were found.\n\n")

    if not death_cross_zones.empty:
        f.write("- **Death Cross Hotspots:** Death crosses have most frequently occurred during the following 5-minute intervals:\n")
        for index, row in death_cross_zones.head(5).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['count']} times\n")
        f.write("\n  - **Trader's Note:** Be watchful for selling opportunities or strengthening downward momentum during these time windows.\n\n")
    else:
        f.write("- **Death Cross Hotspots:** No recurring time zones for death crosses were found.\n\n")


    f.write("### Volume Spike Hotspots\n\n")
    f.write("This section identifies the 5-minute intervals with the most frequent significant volume spikes. High volume often confirms the strength of a price move (either up or down) and can signal the start of a new trend or the climax of an existing one.\n\n")
    
    if not volume_spike_zones.empty:
        f.write("- **Volume Spike Hotspots:** Significant volume spikes have most frequently occurred during the following 5-minute intervals:\n")
        for index, row in volume_spike_zones.head(5).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['count']} times\n")
        f.write("\n  - **Trader's Note:** Pay close attention to price action during these high-volume periods. A spike can confirm the strength of a breakout or indicate a potential reversal if the price fails to follow through.\n\n")
    else:
        f.write("- **Volume Spike Hotspots:** No significant volume spike hotspots were found.\n\n")


    f.write("### Intraday Highest Top and Lowest Bottom Summary\n\n")
    f.write("This table summarizes the absolute highest and lowest points for each trading day and whether they occurred in the morning or afternoon session. This can help you identify if extreme price movements on a given day are more common in the morning or afternoon.\n\n")
    if df_daily_summary.empty:
        f.write("No daily summary available.\n\n")
    else:
        f.write(df_daily_summary.to_markdown(index=False))
        f.write("\n\n")

    f.write("### Intraday Trend Guessing\n\n")
    f.write("This section analyzes the daily summaries to guess the overall trend for a typical day.\n\n")
    if 'bottom_to_top_days' in locals() and 'top_to_bottom_days' in locals():
        total_days = len(df_daily_summary)
        f.write(f"- Out of {total_days} days analyzed:\n")
        f.write(f"  - **{bottom_to_top_days} days** showed a general **uptrend** (the day's low occurred before the day's high).\n")
        f.write(f"  - **{top_to_bottom_days} days** showed a general **downtrend** (the day's high occurred before the day's low).\n\n")
        if bottom_to_top_days > top_to_bottom_days:
            f.write("This suggests a slight tendency for the market to trend upwards throughout the day. A common pattern might be a low in the morning followed by a high in the afternoon.\n\n")
        elif top_to_bottom_days > bottom_to_top_days:
            f.write("This suggests a slight tendency for the market to trend downwards throughout the day. A common pattern might be a high in the morning followed by a low in the afternoon.\n\n")
        else:
            f.write("There is no clear tendency for the market to trend in one direction over the other throughout the day.\n\n")
    else:
        f.write("Could not determine intraday trend patterns.\n\n")

    f.write("### Peak and Trough Time Zones (5-minute intervals)\n\n")
    f.write("This section identifies the 5-minute intervals of the day that most frequently contain market tops (peaks) and bottoms (troughs).\n\n")
    if not top_zones.empty:
        f.write("- **Peak (Top) Zones:** Market tops have most frequently occurred during the following 5-minute intervals:\n")
        for index, row in top_zones.head(5).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['count']} times\n")
    else:
        f.write("- **Peak (Top) Zones:** No consistent peak zones found.\n")
    f.write("\n")
    if not bottom_zones.empty:
        f.write("- **Trough (Bottom) Zones:** Market bottoms have most frequently occurred during the following 5-minute intervals:\n")
        for index, row in bottom_zones.head(5).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['count']} times\n")
    else:
        f.write("- **Trough (Bottom) Zones:** No consistent trough zones found.\n")
    f.write("\n")

    f.write("### Intraday Pivot Switches\n\n")
    f.write("This section details the sequence of significant tops and bottoms for each day, giving an idea of the market's volatility and rhythm. A day with many switches is 'choppy', while a day with few suggests more sustained trends.\n\n")
    if 'df_pivots' in locals() and not df_pivots.empty:
        df_pivots_display = df_pivots[['date', 'time', 'type', 'price']].copy()
        df_pivots_display['time'] = df_pivots_display['time'].dt.strftime('%H:%M:%S')
        df_pivots_display.rename(columns={'date': 'Date', 'time': 'Time', 'type': 'Type', 'price': 'Price'}, inplace=True)
        f.write(df_pivots_display.to_markdown(index=False))
        f.write("\n\n")

        f.write("#### Daily Switch Summary\n\n")
        f.write("This table summarizes the number of significant pivots (switches) and the price range between the highest and lowest pivot for each day.\n\n")
        
        daily_switch_summary_data = []
        for date, day_pivots in df_pivots.groupby('date'):
            switch_count = len(day_pivots)
            
            # Get the full data for the current day to find the true high and low
            day_full_data = df[df['date'] == date]
            if not day_full_data.empty:
                highest_val = day_full_data['high'].max()
                lowest_val = day_full_data['low'].min()
                price_range_val = highest_val - lowest_val
                
                daily_switch_summary_data.append({
                    'Date': date,
                    'Switch Count': switch_count,
                    'Highest Value': highest_val,
                    'Lowest Value': lowest_val,
                    'Price Range': price_range_val
                })
        
        if daily_switch_summary_data:
            df_daily_switch_summary = pd.DataFrame(daily_switch_summary_data)
            # Rename columns for clarity in the report
            df_daily_switch_summary.rename(columns={
                'Highest Value': 'Day High', 
                'Lowest Value': 'Day Low'
            }, inplace=True)
            f.write(df_daily_switch_summary.to_markdown(index=False))
            f.write("\n\n")
        else:
            f.write("No daily switch summary available.\n\n")
    else:
        f.write("Could not analyze intraday pivot switches.\n\n")

    f.write("### Intraday Most Prominent Pivots\n\n")
    f.write("This table identifies the single most 'prominent' peak and trough for each day. Prominence measures how much a pivot stands out from the surrounding price action, indicating a very sharp and distinct turning point. This is different from the absolute highest/lowest price of the day.\n\n")
    if 'df_prominent_pivot_summary' in locals() and not df_prominent_pivot_summary.empty:
        f.write(df_prominent_pivot_summary.to_markdown(index=False))
        f.write("\n\n")
    else:
        f.write("Could not summarize prominent daily pivots.\n\n")


    f.write("### Big Trend Analysis (Price Change > 5 in < 5 min)\n\n")
    f.write("This section identifies significant, rapid price movements ('big trends'). The table also includes a 'look-back' analysis to identify which combination of precursor signals (MA Crossover, Volume Spike, Ichimoku) occurred in the 5 minutes *before* the trend began.\n\n")
    if not df_big_trends.empty:
        # Format time columns for better readability in the report
        df_big_trends_display = df_big_trends.copy()
        df_big_trends_display['Trend Start Time'] = df_big_trends_display['Trend Start Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_big_trends_display['Trend End Time'] = df_big_trends_display['Trend End Time'].dt.strftime('%Y-%m-%d %H:%M:%S')
        df_big_trends_display['Price Change'] = df_big_trends_display['Price Change'].round(2)
        # The duration column is no longer present, so we remove it from display
        # df_big_trends_display['Duration (min)'] = df_big_trends_display['Duration (min)'].round(2)
        f.write(df_big_trends_display.to_markdown(index=False))
        f.write("\n\n")
    else:
        f.write("No 'big trends' matching the criteria (price change > 5 in < 5 minutes) were found.\n\n")

    f.write("### Big Trend Hotspots\n\n")
    f.write("This section identifies the Top 10 5-minute intervals when 'big trends' (rapid, significant price movements) happen most frequently. It provides a breakdown of uptrends and downtrends for each interval, helping traders pinpoint when the market is most volatile.\n\n")
    
    if not big_trend_hotspots.empty:
        f.write("- **Top 10 Big Trend Hotspots:**\n")
        for index, row in big_trend_hotspots.head(10).iterrows():
            f.write(f"  - **{row['time_5min'].strftime('%H:%M')}**: {row['Total']} times (Uptrends: {row['Uptrend']}, Downtrends: {row['Downtrend']})\n")
        f.write("\n  - **Trader's Note:** Be extra vigilant during these periods, as the probability of a major, fast-moving trend is historically higher. These are prime times for breakout trading strategies.\n\n")
    else:
        f.write("- **Big Trend Hotspots:** No recurring time zones for big trends were found.\n\n")


    f.write("### Precursor Combination Analysis\n\n")
    f.write("This analysis examines which combination of signals (MA Crossover, Volume Spike, Ichimoku) occurred in the 5 minutes *before* a big trend started. The 'Frequency' column shows what percentage of all identified big trends were preceded by that specific combination. It is a measure of prevalence, not a formal accuracy score.\n\n")
    if not combination_counts.empty:
        f.write(f"**Total Big Trends Analyzed:** {total_big_trends}\n\n")
        f.write(combination_counts.to_markdown(index=False))
        f.write("\n\n")
        
        # Find the best combination (that isn't 'None')
        best_combo_df = combination_counts[combination_counts['Combination'] != 'None']
        if not best_combo_df.empty:
            best_combination = best_combo_df.iloc[0]
            f.write(f"**Conclusion:** The most effective predictor in this dataset is the **'{best_combination['Combination']}'** combination, which preceded **{best_combination['Frequency']}** of all big trends.\n\n")
        else:
            f.write("**Conclusion:** No reliable precursor combinations were found. Most big trends occurred without any of the monitored signals.\n\n")
    else:
        f.write("No data available for precursor combination analysis.\n\n")


    f.write("### Trading Suggestions for New Traders\n\n")
    f.write("Based on the historical data, here are some suggestions for timing your trades. These are synthesized from the most frequent time zones for pivots, MA crossovers, and volume spikes.\n\n")

    # Suggestion for Selling
    f.write("- **Considering Selling Opportunities (Tops & Bearish Signals):**\n")
    if not top_zones.empty:
        top_zone_time = top_zones.iloc[0]['time_5min'].strftime('%H:%M')
        f.write(f"  - Market tops have most frequently occurred around **{top_zone_time}**. This could be a primary window to watch for potential reversals to the downside.\n")
    else:
        f.write("  - No consistently recurring time zones for market tops were found.\n")

    if not death_cross_zones.empty:
        death_cross_time = death_cross_zones.iloc[0]['time_5min'].strftime('%H:%M')
        f.write(f"  - Bearish 'Death Crosses' have been most common around **{death_cross_time}**. A cross at this time could signal strengthening downward momentum.\n")
    else:
        f.write("  - No specific hotspots for 'Death Crosses' were identified.\n")
    f.write("\n")

    # Suggestion for Buying
    f.write("- **Considering Buying Opportunities (Bottoms & Bullish Signals):**\n")
    if not bottom_zones.empty:
        bottom_zone_time = bottom_zones.iloc[0]['time_5min'].strftime('%H:%M')
        f.write(f"  - Market bottoms have most frequently occurred around **{bottom_zone_time}**. This could be a primary window to watch for potential reversals to the upside.\n")
    else:
        f.write("  - No consistently recurring time zones for market bottoms were found.\n")

    if not golden_cross_zones.empty:
        golden_cross_time = golden_cross_zones.iloc[0]['time_5min'].strftime('%H:%M')
        f.write(f"  - Bullish 'Golden Crosses' have been most common around **{golden_cross_time}**. A cross at this time could signal strengthening upward momentum.\n")
    else:
        f.write("  - No specific hotspots for 'Golden Crosses' were identified.\n")
    f.write("\n")

    # Suggestion for Volume
    f.write("- **Confirmation with Volume:**\n")
    if not volume_spike_zones.empty:
        volume_spike_time = volume_spike_zones.iloc[0]['time_5min'].strftime('%H:%M')
        f.write(f"  - The most significant volume activity tends to happen around **{volume_spike_time}**. Use this as a confirmation signal. A price move (up or down) accompanied by high volume during this period is more likely to be significant.\n")
    else:
        f.write("  - No specific high-volume hotspots were identified.\n")


    f.write("\n**Disclaimer:** This is not financial advice. These are patterns observed in the provided historical data. Always use stop-losses and manage your risk. Past performance is not indicative of future results.\n\n")

print(f"Analysis report saved to {output_path}")
