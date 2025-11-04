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


def fetch_intraday_data(symbol: str, from_timestamp: int, to_timestamp: int) -> Optional[Dict[str, Any]]:
    """
    Fetches intraday trading data for a specific symbol and time window.

    Args:
        symbol (str): The stock symbol to fetch (e.g., "VN30").
        from_timestamp (int): The start of the time window as a Unix timestamp.
        to_timestamp (int): The end of the time window as a Unix timestamp.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
    """
    try:
        market_tz = pytz.timezone(TIMEZONE_STR)
        from_dt = datetime.fromtimestamp(from_timestamp, tz=market_tz)
        to_dt = datetime.fromtimestamp(to_timestamp, tz=market_tz)

        logging.info(f"Requesting data for {symbol} from {from_dt} to {to_dt}")
        return execute_api_request(symbol, from_timestamp, to_timestamp)

    except ValueError as e:
        logging.error(f"Error preparing request for {symbol}: {e}")
        return None


def load_data_for_development(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> pd.DataFrame:
    """
    Loads and consolidates data for a symbol in development mode by fetching it from the API
    for a specified date range.
    """
    logger = logging.getLogger(__name__)
    
    # Use provided dates or fall back to settings
    if not start_date or not end_date:
        date_range = settings.DEV_DATA_DATE_RANGE
        start_date_str = date_range.get("start_date")
        end_date_str = date_range.get("end_date")
    else:
        start_date_str = start_date
        end_date_str = end_date

    if not start_date_str or not end_date_str:
        logger.error("Date range is not configured correctly in settings or passed as arguments.")
        return pd.DataFrame()

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except ValueError:
        logger.error("Invalid date format. Use YYYY-MM-DD.")
        return pd.DataFrame()

    all_dfs = []
    for date_to_fetch in pd.date_range(start_date, end_date):
        date_str = date_to_fetch.strftime('%Y-%m-%d')
        logger.info(f"Fetching development data for {symbol} on {date_str}...")
        
        # Calculate timestamps for the entire trading day
        market_tz = pytz.timezone(TIMEZONE_STR)
        all_starts = [times['start'] for times in SESSIONS.values()]
        all_ends = [times['end'] for times in SESSIONS.values()]
        start_time_str = min(all_starts)
        end_time_str = max(all_ends)
        start_h, start_m = map(int, start_time_str.split(':'))
        end_h, end_m = map(int, end_time_str.split(':'))
        from_dt = market_tz.localize(date_to_fetch.replace(hour=start_h, minute=start_m, second=0))
        to_dt = from_dt.replace(hour=end_h, minute=end_m, second=1)
        from_timestamp = int(from_dt.timestamp())
        to_timestamp = int(to_dt.timestamp())

        raw_data = fetch_intraday_data(symbol, from_timestamp, to_timestamp)
        
        if not raw_data or raw_data.get('s') != 'ok':
            logger.warning(f"No data fetched for {date_str}.")
            continue

        # Save the raw response if enabled
        if settings.SAVE_DEV_API_RESPONSE_TO_FILE:
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
            data_path = os.path.join(project_root, settings.DATA_DIR, symbol)
            os.makedirs(data_path, exist_ok=True)
            
            file_date_str = date_to_fetch.strftime('%y%m%d')
            file_path = os.path.join(data_path, f"{symbol.lower()}_response_{file_date_str}.json")
            
            try:
                with open(file_path, 'w') as f:
                    json.dump(raw_data, f, indent=4)
                logger.info(f"Successfully saved API response to {file_path}")
            except IOError as e:
                logger.error(f"Failed to save API response to {file_path}: {e}")

        keys = ["t", "o", "h", "l", "c", "v"]
        min_len = min(len(raw_data.get(k, [])) for k in keys)
        if min_len == 0:
            continue
            
        df_single = pd.DataFrame({
            "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
            "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
            "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
            "volume": raw_data["v"][:min_len],
        })
        all_dfs.append(df_single)

    if not all_dfs:
        logger.warning(f"No data loaded for {symbol} in the specified date range.")
        return pd.DataFrame()

    df = pd.concat(all_dfs, ignore_index=True).drop_duplicates(subset=['time'], keep='first').sort_values(by='time').reset_index(drop=True)
    
    if not df.empty:
        market_tz = pytz.timezone(TIMEZONE_STR)
        df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(market_tz)
        df = adjust_prices_by_symbol(df, symbol)
        
    return df


def load_live_data(symbol: str, from_timestamp: int, to_timestamp: int) -> pd.DataFrame:
    """
    Fetches live data for a symbol in a specific time window and processes it.
    """
    logger = logging.getLogger(__name__)
    raw_data = fetch_intraday_data(symbol, from_timestamp, to_timestamp)

    if not raw_data or raw_data.get('s') != 'ok':
        logger.error("Failed to fetch or process live data.")
        return pd.DataFrame()

    keys = ["t", "o", "h", "l", "c", "v"]
    try:
        min_len = min(len(raw_data.get(k, [])) for k in keys)
    except TypeError:
        logger.warning("Response format is not as expected (e.g., not a list).")
        return pd.DataFrame()
        
    if min_len == 0:
        logger.warning("No data points in the live response.")
        return pd.DataFrame()

    df = pd.DataFrame({
        "time": pd.to_datetime(raw_data["t"][:min_len], unit="s"),
        "open": raw_data["o"][:min_len], "high": raw_data["h"][:min_len],
        "low": raw_data["l"][:min_len], "close": raw_data["c"][:min_len],
        "volume": raw_data["v"][:min_len],
    })

    # Adjust timezone and prices
    df['time'] = df['time'].dt.tz_localize('UTC').dt.tz_convert(pytz.timezone(TIMEZONE_STR))
    df = adjust_prices_by_symbol(df, symbol)

    return df
