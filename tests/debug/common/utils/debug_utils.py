"""
Utilities specifically designed for debugging and test script execution.
"""
import os
import pandas as pd
from src.stockreports.config import loader

def save_debug_data(df: pd.DataFrame, symbol: str, start_time: pd.Timestamp, end_time: pd.Timestamp, project_root: str):
    """
    Saves a DataFrame to a standardized CSV and JSON file in the 'tests/debug/data' directory.

    Args:
        df (pd.DataFrame): The DataFrame to save, with a DatetimeIndex.
        symbol (str): The ticker symbol for the data.
        start_time (pd.Timestamp): The start time of the data window (in local timezone).
        end_time (pd.Timestamp): The end time of the data window (in local timezone).
        project_root (str): The absolute path to the project's root directory.
    
    Returns:
        str: The path to the saved JSON file, or None if saving failed.
    """
    json_file_path = None  # Initialize to None
    try:
        settings = loader.get_settings()
        timezone = settings.TRADING_HOURS[settings.MARKET_COUNTRY_CODE]['timezone']

        # Format the filename
        start_str = start_time.strftime('%Y%m%d_%H%M')
        end_str = end_time.strftime('%Y%m%d_%H%M')
        
        # Create a specific directory for debug data if it doesn't exist
        debug_data_dir = os.path.join(project_root, 'tests', 'debug', 'data')
        os.makedirs(debug_data_dir, exist_ok=True)
        
        # Create a copy for file saving to avoid modifying the original df
        df_to_save = df.copy()

        # Reset index to make 'time' a column
        df_to_save.reset_index(inplace=True)

        # Ensure the 'time' column is in the correct local timezone before saving
        if df_to_save['time'].dt.tz is None:
            df_to_save['time'] = df_to_save['time'].dt.tz_localize('UTC').dt.tz_convert(timezone)
        else:
            df_to_save['time'] = df_to_save['time'].dt.tz_convert(timezone)

        # --- Save to CSV with local timezone ---
        csv_filename = f"debug_data_{symbol}_{start_str}_to_{end_str}_intraday.csv"
        csv_file_path = os.path.join(debug_data_dir, csv_filename)
        # For CSV, it's often fine to leave timestamps as objects, but for consistency let's format them
        df_to_save.to_csv(csv_file_path, index=False)
        print(f"Data saved to {csv_file_path}")

        # --- Save to JSON with local timezone ---
        json_filename = f"debug_data_{symbol}_{start_str}_to_{end_str}_intraday.json"
        json_file_path = os.path.join(debug_data_dir, json_filename)
        
        # Create a separate copy for JSON to handle specific formatting like ISO strings for dates
        df_for_json = df_to_save.copy()
        df_for_json['time'] = df_for_json['time'].apply(lambda x: x.isoformat())
        
        df_for_json.to_json(json_file_path, orient='records', indent=4)
        print(f"Data saved to {json_file_path}")

    except Exception as e:
        print(f"ERROR: An error occurred during data saving: {e}")
    
    return json_file_path
