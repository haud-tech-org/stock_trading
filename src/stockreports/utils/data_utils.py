"""
Data processing utilities for stock market data aggregation.

This module contains column mappings, data structure definitions,
and utility functions for processing financial data.
"""

import requests
import time
from datetime import datetime
import pytz
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
import logging

from src.stockreports.config import settings

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

# Time format strings
TIME_FORMATS = {
    'datetime_display': '%Y-%m-%d %H:%M:%S',
    'date_only': '%Y-%m-%d',
    'time_only': '%H:%M:%S',
    'filename_timestamp': '%Y-%m-%d-%H-%M-%S'
}


# --- Market and Timezone Configuration from Settings ---

# Get the market-specific configuration from the central settings file.
MARKET_CONFIG = settings.TRADING_HOURS.get(settings.MARKET_COUNTRY_CODE, {})
TIMEZONE_STR = MARKET_CONFIG.get("timezone", "UTC")
SESSIONS = MARKET_CONFIG.get("sessions", {})


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


def is_trading_hours(dt_object: Optional[datetime] = None) -> bool:
    """
    Checks if the given datetime is within any of the market's trading sessions.
    If no datetime is provided, it checks the current time in the market's timezone.

    Args:
        dt_object (Optional[datetime]): The datetime to check. If timezone-aware, it's used directly.
                                         If naive, it's assumed to be in the market's timezone.

    Returns:
        True if within trading hours, False otherwise.
    """
    if not SESSION_MINUTES:
        logging.warning("No trading sessions defined in settings. Cannot check trading hours.")
        return False

    market_tz = pytz.timezone(TIMEZONE_STR)

    if dt_object is None:
        check_time = datetime.now(market_tz)
    elif dt_object.tzinfo is None:
        check_time = market_tz.localize(dt_object)
    else:
        check_time = dt_object.astimezone(market_tz)

    # Check if the day is a weekday (Monday=0, Sunday=6)
    if check_time.weekday() >= 5:
        return False

    current_minute = check_time.hour * 60 + check_time.minute

    # Check if the current time falls within any session
    for start_minute, end_minute in SESSION_MINUTES:
        if start_minute <= current_minute <= end_minute:
            return True

    return False


def get_trading_hours_info() -> Dict[str, str]:
    """
    Get formatted trading hours information from the central settings.

    Returns:
        A dictionary with formatted trading hours strings.
    """
    if not SESSIONS:
        return {
            'start_time': 'N/A',
            'end_time': 'N/A',
            'display_range': 'Not Configured',
            'description': 'Trading hours not configured in settings.py'
        }

    # Find the earliest start and latest end time across all sessions
    all_starts = [times['start'] for times in SESSIONS.values()]
    all_ends = [times['end'] for times in SESSIONS.values()]
    
    start_time = min(all_starts)
    end_time = max(all_ends)
    market_name = MARKET_CONFIG.get('name', 'Market')

    return {
        'start_time': start_time,
        'end_time': end_time,
        'display_range': f"{start_time} - {end_time}",
        'description': f"Trading hours for {market_name} ({start_time} - {end_time})"
    }


def get_market_timezone_str() -> str:
    """
    Get the market's timezone string from settings.
    
    Returns:
        The IANA timezone string (e.g., 'Asia/Ho_Chi_Minh').
    """
    return TIMEZONE_STR


def _execute_api_request(symbol: str, from_timestamp: int, to_timestamp: int) -> Optional[Dict[str, Any]]:
    """
    Executes a data request to the API with explicit parameters.

    Args:
        symbol (str): The stock symbol to fetch.
        from_timestamp (int): The start of the time window as a Unix timestamp.
        to_timestamp (int): The end of the time window as a Unix timestamp.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
    """
    try:
        params = settings.API_PARAMS.copy()
        params.update({
            "symbol": symbol,
            "from": from_timestamp,
            "to": to_timestamp
        })

        response = requests.get(
            settings.API_BASE_URL,
            params=params,
            headers=settings.API_HEADERS,
            timeout=15
        )
        response.raise_for_status()

        data = response.json()
        if data.get("s") != "ok" or not data.get("t"):
            logging.warning(f"API returned no data for {symbol}. Status: {data.get('s')}")
            return None

        logging.info(f"Successfully fetched {len(data['t'])} data points for {symbol} from API.")
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"API request for {symbol} failed: {e}")
        return None
    except (ValueError, KeyError) as e:  # Handles JSON decoding errors or missing keys
        logging.error(f"Error processing API response for {symbol}: {e}")
        return None


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
        return _execute_api_request(symbol, from_timestamp, to_timestamp)

    except ValueError as e:
        logging.error(f"Error preparing request for {symbol} on {date_str}: {e}")
        return None
