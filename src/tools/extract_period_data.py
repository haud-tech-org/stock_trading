# src/tools/extract_period_data.py
import argparse
import json
import pandas as pd
import pytz
from pathlib import Path

def extract_data_in_period(input_file, output_file_path, start_time_str, end_time_str, timezone_str='Asia/Ho_Chi_Minh'):
    """
    Extracts historical trading data for a specific time period and saves it to a CSV file.

    Args:
        input_file (str): Path to the input JSON data file.
        output_file_path (str): Path to the output CSV file.
        start_time_str (str): Start of the time range (HH:MM).
        end_time_str (str): End of the time range (HH:MM).
        timezone_str (str): The timezone for displaying the time.
    """
    try:
        # --- 1. Load and Validate Data ---
        print(f"Reading data from {input_file}...")
        with open(input_file, 'r') as f:
            data = json.load(f)

        if data.get('s') != 'ok' or not all(k in data for k in ['t', 'o', 'h', 'l', 'c', 'v']):
            print(f"Error: Invalid or incomplete data format in {input_file}")
            return

        # --- 2. Create and Process DataFrame ---
        df = pd.DataFrame({
            'Timestamp': pd.to_datetime(data['t'], unit='s'),
            'Open': data['o'],
            'High': data['h'],
            'Low': data['l'],
            'Close': data['c'],
            'Volume': data['v']
        })

        # Convert UTC timestamps to the desired timezone
        tz = pytz.timezone(timezone_str)
        df['Timestamp'] = df['Timestamp'].dt.tz_localize('UTC').dt.tz_convert(tz)

        # --- 3. Filter by Time Range ---
        start_time = pd.to_datetime(start_time_str).time()
        end_time = pd.to_datetime(end_time_str).time()

        filtered_df = df[df['Timestamp'].dt.time.between(start_time, end_time)]

        if filtered_df.empty:
            print("Warning: No data found in the specified time range.")
            return

        # Format the timestamp for readability in the final CSV
        filtered_df['Time (UTC+7)'] = filtered_df['Timestamp'].dt.strftime('%H:%M:%S')
        
        # Reorder and select final columns
        final_df = filtered_df[['Time (UTC+7)', 'Open', 'High', 'Low', 'Close', 'Volume']]

        # --- 4. Save to CSV ---
        output_path = Path(output_file_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        final_df.to_csv(output_path, index=False)
        print(f"Successfully extracted data to {output_path}")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_file}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extracts a specific time period from a historical data file and saves it as a CSV in the same directory.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--input-file',
        required=True,
        help="Path to the input historical data file (e.g., src/stockreports/data/VN30/vn30_response_251114.json)"
    )
    parser.add_argument(
        '--start-time',
        required=True,
        help="Start time in HH:MM format (e.g., '13:40')"
    )
    parser.add_argument(
        '--end-time',
        required=True,
        help="End time in HH:MM format (e.g., '13:58')"
    )

    args = parser.parse_args()

    # Automatically determine the output file path
    input_path = Path(args.input_file)
    output_dir = input_path.parent
    start_time_str = args.start_time.replace(':', '')
    end_time_str = args.end_time.replace(':', '')
    output_filename = f"{input_path.stem}_{start_time_str}_to_{end_time_str}.csv"
    output_path = output_dir / output_filename

    extract_data_in_period(
        input_file=args.input_file,
        output_file_path=output_path,
        start_time_str=args.start_time,
        end_time_str=args.end_time
    )
