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

# Trading hours configuration for Vietnamese stock market
TRADING_HOURS = {
    'start_hour': 9,      # 09:00
    'start_minute': 0,
    'end_hour': 14,       # 14:45
    'end_minute': 45,
    'start_minutes': 540,  # 09:00 in minutes from midnight
    'end_minutes': 885     # 14:45 in minutes from midnight
}

# Timezone configuration
VIETNAM_TIMEZONE = {
    'name': 'Asia/Ho_Chi_Minh',
    'offset_hours': 7,     # UTC+7
    'display_name': 'Vietnam Time'
}

# Time format strings
TIME_FORMATS = {
    'datetime_display': '%Y-%m-%d %H:%M:%S',
    'date_only': '%Y-%m-%d',
    'time_only': '%H:%M:%S',
    'filename_timestamp': '%Y-%m-%d-%H-%M-%S'
}


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


def is_trading_hours(hour: int, minute: int) -> bool:
    """
    Check if given time is within trading hours.
    
    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        
    Returns:
        True if within trading hours, False otherwise
    """
    hour_min = hour * 60 + minute
    return TRADING_HOURS['start_minutes'] <= hour_min <= TRADING_HOURS['end_minutes']


def get_trading_hours_info() -> Dict[str, str]:
    """
    Get formatted trading hours information.
    
    Returns:
        Dictionary with formatted trading hours strings
    """
    start_time = f"{TRADING_HOURS['start_hour']:02d}:{TRADING_HOURS['start_minute']:02d}"
    end_time = f"{TRADING_HOURS['end_hour']:02d}:{TRADING_HOURS['end_minute']:02d}"
    
    return {
        'start_time': start_time,
        'end_time': end_time,
        'display_range': f"{start_time} - {end_time}",
        'description': f"Trading hours ({start_time} - {end_time} {VIETNAM_TIMEZONE['display_name']})"
    }


def get_vietnam_timezone_offset() -> int:
    """
    Get Vietnam timezone offset in hours.
    
    Returns:
        Timezone offset in hours (UTC+7)
    """
    return VIETNAM_TIMEZONE['offset_hours']


def fetch_intraday_data(symbol: str, date_str: str) -> Optional[Dict[str, Any]]:
    """
    Fetches intraday trading data for a specific symbol and date from the API.

    Args:
        symbol (str): The stock symbol to fetch (e.g., "VN30").
        date_str (str): The date for which to fetch data, in "YYYY-MM-DD" format.

    Returns:
        A dictionary containing the API response data, or None if an error occurs.
    """
    try:
        vn_tz = pytz.timezone("Asia/Ho_Chi_Minh")
        
        # Create 'from' and 'to' timestamps for the specified date
        from_dt = vn_tz.localize(datetime.strptime(date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0))
        to_dt = from_dt.replace(hour=23, minute=59, second=59)

        params = settings.API_PARAMS.copy()
        params.update({
            "symbol": symbol,
            "from": int(from_dt.timestamp()),
            "to": int(to_dt.timestamp())
        })

        logging.info(f"Requesting data for {symbol} from {from_dt} to {to_dt}")
        
        response = requests.get(
            settings.API_BASE_URL,
            params=params,
            headers=settings.API_HEADERS,
            timeout=15 
        )
        response.raise_for_status()
        
        data = response.json()
        if data.get("s") != "ok" or not data.get("t"):
            logging.warning(f"API returned no data for {symbol} on {date_str}. Status: {data.get('s')}")
            return None
            
        logging.info(f"Successfully fetched {len(data['t'])} data points from API.")
        return data

    except requests.exceptions.RequestException as e:
        logging.error(f"API request for {symbol} on {date_str} failed: {e}")
        return None
    except (ValueError, KeyError) as e:
        logging.error(f"Error processing data for {symbol} on {date_str}: {e}")
        return None
