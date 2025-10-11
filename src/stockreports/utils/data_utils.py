"""
Data processing utilities for stock market data aggregation.

This module contains column mappings, data structure definitions,
and utility functions for processing financial data.
"""

import time
from datetime import datetime
import pytz
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
import logging
import os
import glob
import json

from src.stockreports.config import loader
from src.stockreports.alert.common.validation.price_adjustment import adjust_prices_by_symbol
from src.stockreports.utils.time_utils import TIMEZONE_STR, SESSIONS
from src.stockreports.utils.api_request_utils import execute_api_request

# Standard column mapping for financial data
STANDARD_COLUMN_MAP = {
    't': 'Date Time',
    'o': 'Open', 
    'h': 'High',
    'l': 'Low', 
    'c': 'Close',
    'v': 'Volume'
}

# Extended column mapping for additional financial data fields
EXTENDED_COLUMN_MAP = {
    'vw': 'Volume Weighted',
    'n': 'Number of Transactions',
    'bid': 'Bid',
    'ask': 'Ask',
    'spread': 'Spread',
    'adj_close': 'Adjusted Close',
    'dividend': 'Dividend',
    'split': 'Stock Split'
}

# Combined column mapping dictionary
ALL_COLUMN_MAP = {**STANDARD_COLUMN_MAP, **EXTENDED_COLUMN_MAP}

# Column display order preference (for consistent table headers)
COLUMN_DISPLAY_ORDER = ['t', 'o', 'h', 'l', 'c', 'v', 'vw', 'n', 'bid', 'ask', 'spread']

# --- Market and Timezone Configuration from Settings ---
settings = loader.get_settings()


def _get_session_minutes() -> List[Tuple[int, int]]:
    """
    Parses session start/end times from settings and converts them to minutes from midnight.
    Returns a list of tuples, where each tuple is a (start_minute, end_minute) pair.
    """
    session_minutes = []
    for session_name, times in SESSIONS.items():
        try:
            start_h, start_m = map(int, times['start'].split(':'))
            end_h, end_m = map(int, times['end'].split(':'))
            session_minutes.append((start_h * 60 + start_m, end_h * 60 + end_m))
        except (KeyError, ValueError) as e:
            logging.error(f"Could not parse session '{session_name}': {e}. Check settings.py format.")
    return session_minutes

SESSION_MINUTES = _get_session_minutes()


def get_available_columns(data_sample: Dict[str, Any]) -> Dict[str, str]:
    """
    Detect available columns from a data sample.
    
    Args:
        data_sample: Sample data structure from JSON response
        
    Returns:
        Dictionary mapping column keys to readable names
    """
    if not data_sample:
        return {}
    
    available_columns = {}
    
    for key, readable_name in ALL_COLUMN_MAP.items():
        if key in data_sample and isinstance(data_sample[key], list):
            available_columns[key] = readable_name
    
    return available_columns


def get_ordered_columns(columns: Dict[str, str]) -> List[str]:
    """
    Return columns in preferred display order.
    
    Args:
        columns: Dictionary of available columns
        
    Returns:
        Ordered list of column keys
    """
    # Order columns according to preference, then alphabetically for others
    ordered = []
    
    # Add columns in preferred order if they exist
    for col in COLUMN_DISPLAY_ORDER:
        if col in columns:
            ordered.append(col)
    
    # Add any remaining columns alphabetically
    remaining = sorted([col for col in columns.keys() if col not in ordered])
    ordered.extend(remaining)
    
    return ordered


def validate_data_structure(data_sample: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Validate that the data structure contains expected fields.
    
    Args:
        data_sample: Sample data structure from JSON response
        
    Returns:
        Tuple of (is_valid, validation_message)
    """
    if not isinstance(data_sample, dict):
        return False, "Data sample is not a dictionary"
    
    # Check for at least one standard column
    has_standard_col = any(key in data_sample for key in STANDARD_COLUMN_MAP.keys())
    if not has_standard_col:
        return False, f"No standard columns found. Expected one of: {list(STANDARD_COLUMN_MAP.keys())}"
    
    # Check that detected columns are lists
    invalid_columns = []
    for key in data_sample:
        if key in ALL_COLUMN_MAP and not isinstance(data_sample[key], list):
            invalid_columns.append(key)
    
    if invalid_columns:
        return False, f"Expected list data for columns: {invalid_columns}"
    
    return True, "Data structure is valid"


def get_column_statistics_map() -> Dict[str, List[str]]:
    """
    Return mapping of column types to their statistical calculations.
    
    Returns:
        Mapping of column keys to their statistical significance
    """
    return {
        'price_columns': ['o', 'h', 'l', 'c', 'adj_close', 'bid', 'ask'],
        'volume_columns': ['v', 'vw'],
        'count_columns': ['n'],
        'time_columns': ['t']
    }


def fetch_intraday_data(symbol: str, date_str: str) -> Optional[Dict[str, Any]]:
    """
    Fetches intraday trading data for a specific symbol and date from the API.
    This function calculates the appropriate time window and uses a helper
    to execute the actual API request.

    Args:
        symbol (str): The stock symbol to fetch (e.g., "VN30").
        date_str (str): The date for which to fetch data, in "YYYY-MM-DD" format.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
    """
    try:
        market_tz = pytz.timezone(TIMEZONE_STR)

        if not SESSIONS:
            raise ValueError("No trading sessions defined in settings.py")

        all_starts = [times['start'] for times in SESSIONS.values()]
        all_ends = [times['end'] for times in SESSIONS.values()]

        start_time_str = min(all_starts)
        end_time_str = max(all_ends)

        start_h, start_m = map(int, start_time_str.split(':'))
        end_h, end_m = map(int, end_time_str.split(':'))

        from_dt = market_tz.localize(datetime.strptime(date_str, '%Y-%m-%d').replace(hour=start_h, minute=start_m, second=0))
        to_dt = from_dt.replace(hour=end_h, minute=end_m, second=1)
        
        from_timestamp = int(from_dt.timestamp())
        to_timestamp = int(to_dt.timestamp())

        logging.info(f"Requesting data for {symbol} from {from_dt} to {to_dt}")
        return execute_api_request(symbol, from_timestamp, to_timestamp)

    except ValueError as e:
        logging.error(f"Error preparing request for {symbol} on {date_str}: {e}")
        return None


def calculate_max_lookback_period() -> int:
    """
    Calculates the maximum data lookback period needed based on all active alert approaches.
    This ensures that enough historical data is available for all technical indicators.
    """
    signal_settings = loader.get_signal_settings()
    settings = loader.get_settings()
    logger = logging.getLogger(__name__)

    max_lookback = getattr(signal_settings, 'DEFAULT_LOOKBACK_PERIOD', 60)
    active_approaches = getattr(settings, 'ALERT_APPROACHES', [])
    lookbacks = [max_lookback]

    for approach in active_approaches:
        if approach.upper() == 'RCM':
            rcm_lookback = max(
                getattr(signal_settings, 'MA_LONG_PERIOD', 0),
                getattr(signal_settings, 'AVG_VOLUME_PERIOD', 0)
            )
            lookbacks.append(rcm_lookback)
        elif approach.upper() == 'CONSISTENT_MOMENTUM':
            try:
                cm_lookback = signal_settings.APPROACH_CONFIG['CONSISTENT_MOMENTUM']['MOMENTUM_PERIOD_MINUTES']
                lookbacks.append(cm_lookback)
            except (AttributeError, KeyError):
                logger.warning("Could not find settings for CONSISTENT_MOMENTUM lookback.")

    max_lookback = max(lookbacks) if lookbacks else 0
    logger.info(f"Calculated maximum required lookback period: {max_lookback} minutes.")
    return max_lookback


def load_all_data_from_files(symbol: str) -> pd.DataFrame:
    """
    Loads and consolidates all historical JSON data for a symbol from the local data directory.
    """
    logger = logging.getLogger(__name__)
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    data_path = os.path.join(project_root, settings.DATA_DIR, symbol)
    all_files = glob.glob(f"{data_path}/*.json")

    if not all_files:
        logger.warning(f"No JSON data files found in {data_path}")
        return pd.DataFrame()

    all_dfs = []
    for filename in sorted(all_files):
        with open(filename, 'r') as f:
            try:
                data = json.load(f)
                keys = ["t", "o", "h", "l", "c", "v"]
                if not all(k in data for k in keys):
                    continue
                min_len = min(len(data[k]) for k in keys)
                if min_len == 0:
                    continue
                df_single = pd.DataFrame({
                    "time": pd.to_datetime(data["t"][:min_len], unit="s"),
                    "open": data["o"][:min_len], "high": data["h"][:min_len],
                    "low": data["l"][:min_len], "close": data["c"][:min_len],
                    "volume": data["v"][:min_len],
                })
                all_dfs.append(df_single)
            except Exception as e:
                logger.error(f"Error processing {filename}: {e}")

    if not all_dfs:
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['time'], keep='first').sort_values(by='time').reset_index(drop=True)
    
    if not df.empty:
        market_tz = pytz.timezone(TIMEZONE_STR)
        df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(market_tz)
        df = adjust_prices_by_symbol(df, symbol)
        
    return df


def load_live_data(symbol: str, date_str: str) -> pd.DataFrame:
    """
    Fetches live data for a symbol and processes it into a clean DataFrame.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Fetching live data for {symbol} on {date_str}...")
    raw_data = fetch_intraday_data(symbol, date_str)

    if not raw_data or raw_data.get('s') != 'ok':
        logger.error("Failed to fetch or process live data.")
        return pd.DataFrame()

    keys = ["t", "o", "h", "l", "c", "v"]
    min_len = min(len(raw_data.get(k, [])) for k in keys)
    if min_len == 0:
        logger.warning("No data points in the live response.")
        return pd.DataFrame()

    df = pd.DataFrame({
        "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
        "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
        "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
        "volume": raw_data["v"][:min_len],
    })
    df.drop_duplicates(subset=['time'], keep='last', inplace=True)

    # Adjust timezone and prices
    df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(pytz.timezone(TIMEZONE_STR))
    df = adjust_prices_by_symbol(df, symbol)

    return df
