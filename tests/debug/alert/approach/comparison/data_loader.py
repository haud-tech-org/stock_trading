import pandas as pd
import json

def load_trading_view_json(file_path: str) -> pd.DataFrame:
    """
    Loads data from a TradingView-style JSON file into a pandas DataFrame.

    The JSON is expected to have keys 't', 'o', 'h', 'l', 'c', 'v' for
    timestamp, open, high, low, close, and volume respectively.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        pd.DataFrame: A DataFrame with standardized lowercase column names
                      ('time', 'open', 'high', 'low', 'close', 'volume').
    """
    with open(file_path, 'r') as f:
        data = json.load(f)

    # Check for 's' status key, if 'no_data', return empty
    if data.get('s') == 'no_data':
        return pd.DataFrame()

    df = pd.DataFrame({
        'time': pd.to_datetime(data['t'], unit='s'),
        'open': data['o'],
        'high': data['h'],
        'low': data['l'],
        'close': data['c'],
        'volume': data['v']
    })
    
    return df
