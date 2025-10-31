"""
Time and date utility functions for the stock reporting application.

This module centralizes all logic related to timezones, market trading hours,
and other time-based calculations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import pytz

from src.stockreports.config import loader

# --- Settings Loader ---
settings = loader.get_settings()

# --- Market and Timezone Configuration from Settings ---
MARKET_CONFIG = settings.TRADING_HOURS.get(settings.MARKET_COUNTRY_CODE, {})
TIMEZONE_STR = MARKET_CONFIG.get("timezone", "UTC")
SESSIONS = MARKET_CONFIG.get("sessions", {})
TIMEZONE = pytz.timezone(TIMEZONE_STR)

# Time format strings
TIME_FORMATS = {
    'datetime_display': '%Y-%m-%d %H:%M:%S',
    'date_only': '%Y-%m-%d',
    'time_only': '%H:%M:%S',
    'filename_timestamp': '%Y-%m-%d-%H-%M-%S'
}


class TimeSimulator:
    """
    Manages time for the application, allowing for both live and simulated replay modes.
    """
    def __init__(self, replay_start_str: Optional[str], interval_seconds: int):
        self._is_replay = replay_start_str is not None
        self._interval = timedelta(seconds=interval_seconds)
        
        if self._is_replay:
            # Use pandas for robust datetime parsing
            self._current_time = pd.to_datetime(replay_start_str).tz_localize(TIMEZONE)
            self.processing_date = self._current_time.strftime('%Y-%m-%d')
            self.end_of_day = self._get_session_end(self._current_time)
            logging.info(f"TimeSimulator initialized in REPLAY mode. Start: {self._current_time}, End: {self.end_of_day}")
        else:
            self._current_time = self._get_live_time()
            self.processing_date = self._current_time.strftime('%Y-%m-%d')
            self.end_of_day = None # Not fixed in live mode
            logging.info("TimeSimulator initialized in LIVE mode.")

    def _get_live_time(self) -> datetime:
        return datetime.now(pytz.utc).astimezone(TIMEZONE)

    def _get_session_end(self, dt: datetime) -> datetime:
        """Calculates the end of the last trading session for the given datetime."""
        if not SESSIONS:
            # Default to 4 PM if no sessions are defined
            return dt.replace(hour=16, minute=0, second=0, microsecond=0)
        
        all_ends = [times['end'] for times in SESSIONS.values()]
        end_time_str = max(all_ends)
        h, m = map(int, end_time_str.split(':'))
        return dt.replace(hour=h, minute=m, second=0, microsecond=0)

    def get_current_time(self) -> datetime:
        """Returns the current time, either simulated or live."""
        if self._is_replay:
            return self._current_time
        return self._get_live_time()

    def advance(self):
        """Advances the simulated time by one interval."""
        if self._is_replay:
            self._current_time += self._interval

    def is_running(self) -> bool:
        """Checks if the simulation/monitoring should continue."""
        if self._is_replay:
            # Stop if the current time has passed the end of the trading day
            return self._current_time <= self.end_of_day
        return True # Live mode always runs indefinitely

    def is_replay_mode(self) -> bool:
        """Returns True if in replay mode."""
        return self._is_replay


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


def get_market_timezone() -> pytz.BaseTzInfo:
    """
    Get the market's timezone object.
    
    Returns:
        A pytz timezone object.
    """
    return TIMEZONE

# Utility to convert pandas Timestamp or datetime to ISO 8601 string with configured timezone
def to_iso8601_with_tz(ts):
    import pandas as pd
    from src.stockreports.utils.time_utils import TIMEZONE
    if isinstance(ts, pd.Timestamp):
        if ts.tzinfo is None:
            ts = ts.tz_localize(TIMEZONE)
        else:
            ts = ts.tz_convert(TIMEZONE)
        return ts.isoformat()
    return str(ts)
