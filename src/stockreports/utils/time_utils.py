"""
Time and date utility functions for the stock reporting application.

This module centralizes all logic related to timezones, market trading hours,
and other time-based calculations.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pytz

from src.stockreports.config import loader

# --- Settings Loader ---
settings = loader.get_settings()

# --- Market and Timezone Configuration from Settings ---
MARKET_CONFIG = settings.TRADING_HOURS.get(settings.MARKET_COUNTRY_CODE, {})
TIMEZONE_STR = MARKET_CONFIG.get("timezone", "UTC")
SESSIONS = MARKET_CONFIG.get("sessions", {})

# Time format strings
TIME_FORMATS = {
    'datetime_display': '%Y-%m-%d %H:%M:%S',
    'date_only': '%Y-%m-%d',
    'time_only': '%H:%M:%S',
    'filename_timestamp': '%Y-%m-%d-%H-%M-%S'
}


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
        # More robust way to get current time in the target timezone
        check_time = datetime.now(pytz.utc).astimezone(market_tz)
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
