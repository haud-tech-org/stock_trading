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
from src.stockreports.model import (
    ApproachSymbolConfiguration,
    TradingHoursConfig,
    Session,
)

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
    
    Can work in two modes:
    1. With TradingHoursConfig: Uses symbol-specific trading hours/timezone
    2. Without trading hours: Uses global TIMEZONE and SESSIONS (backward compatible)
    
    Architecture:
    - TimeSimulator receives TradingHoursConfig (not ApproachSymbolConfiguration)
    - TradingHoursConfig contains timezone and sessions (symbol-level data)
    - This separation ensures TimeSimulator has only what it needs
    """
    def __init__(self, 
                 replay_start_str: Optional[str], 
                 interval_seconds: int,
                 trading_hours: Optional[TradingHoursConfig] = None):
        """
        Initialize TimeSimulator.
        
        Args:
            replay_start_str: Start time for replay mode (None = live mode)
            interval_seconds: Interval between time steps in seconds
            trading_hours: Optional TradingHoursConfig for symbol-specific timezone/sessions
        
        Example:
            # Get trading hours for symbol
            trading_hours = ExecutorConfigurationOrchestrator.get_symbol_trading_hours("BTC/USDT:USDT")
            
            # Create time simulator with symbol-specific trading hours
            simulator = TimeSimulator(
                replay_start_str=None,
                interval_seconds=60,
                trading_hours=trading_hours
            )
        """
        self._is_replay = replay_start_str is not None
        self._interval = timedelta(seconds=interval_seconds)
        self._trading_hours = trading_hours
        
        # Use trading_hours's timezone/sessions and trading_days if available, otherwise use global settings
        if trading_hours:
            self.timezone = pytz.timezone(trading_hours.timezone)
            self.sessions = trading_hours.sessions
            self.trading_days: List[int] = trading_hours.trading_days
        else:
            self.timezone = TIMEZONE
            self.sessions = [
                Session.from_any({"name": name, **times_dict})
                for name, times_dict in SESSIONS.items()
            ]
            self.trading_days: List[int] = [0, 1, 2, 3, 4]
        
        if self._is_replay:
            # Use pandas for robust datetime parsing
            self._current_time = pd.to_datetime(replay_start_str).tz_localize(self.timezone)
            self.processing_date = self._current_time.strftime('%Y-%m-%d')
            self.end_of_day = self._get_session_end(self._current_time)
            logging.info(f"TimeSimulator initialized in REPLAY mode. Start: {self._current_time}, End: {self.end_of_day}")
        else:
            self._current_time = self._get_live_time()
            self.processing_date = self._current_time.strftime('%Y-%m-%d')
            self.end_of_day = None # Not fixed in live mode
            logging.info("TimeSimulator initialized in LIVE mode.")

    def _get_live_time(self) -> datetime:
        return datetime.now(pytz.utc).astimezone(self.timezone)

    def _get_session_end(self, dt: datetime) -> datetime:
        """Calculates the end of the last trading session for the given datetime."""
        if not self.sessions:
            # Default to 4 PM if no sessions are defined
            return dt.replace(hour=16, minute=0, second=0, microsecond=0)
        
        # self.sessions is a List[Session] - extract end times from all sessions and find the latest
        all_ends = [session.end_time for session in self.sessions]
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

    def is_trading_hours(self, dt_object: Optional[datetime] = None) -> bool:
        """
        Check if the given datetime is within trading hours.
        
        Uses this simulator's configured sessions and timezone.
        
        Args:
            dt_object: Datetime to check. If None, uses current time.
            
        Returns:
            True if within trading hours, False otherwise.
            
        Example:
            simulator = TimeSimulator(None, 60, trading_hours)
            if simulator.is_trading_hours():
                print("Currently in trading hours")
        """
        market_tz = self.timezone
        
        # Convert sessions to minutes from midnight
        session_minutes = []
        for session in self.sessions:
            start_h, start_m = map(int, session.start_time.split(':'))
            end_h, end_m = map(int, session.end_time.split(':'))
            session_minutes.append((start_h * 60 + start_m, end_h * 60 + end_m))
        
        if not session_minutes:
            logging.warning("No trading sessions defined. Cannot check trading hours.")
            return False
        
        # Determine check time
        if dt_object is None:
            check_time = self._get_live_time()
        elif dt_object.tzinfo is None:
            check_time = market_tz.localize(dt_object)
        else:
            check_time = dt_object.astimezone(market_tz)
        
        # Check if the day is a valid trading day for this market
        if check_time.weekday() not in self.trading_days:
            return False
        
        # Check if time falls within any session
        current_minute = check_time.hour * 60 + check_time.minute
        for start_minute, end_minute in session_minutes:
            if start_minute <= current_minute <= end_minute:
                return True
        
        return False


def get_market_timezone_str(timezone_str: str = TIMEZONE_STR) -> str:
    """
    Get the market's timezone string from settings.
    
    Args:
        timezone_str: IANA timezone string (defaults to global TIMEZONE_STR from settings)
    
    Returns:
        The IANA timezone string (e.g., 'Asia/Ho_Chi_Minh').
    """
    return timezone_str


def get_market_timezone(timezone_str: str = TIMEZONE_STR) -> pytz.BaseTzInfo:
    """
    Get the market's timezone object.
    
    Args:
        timezone_str: IANA timezone string (defaults to global TIMEZONE_STR from settings)
    
    Returns:
        A pytz timezone object.
    """
    return pytz.timezone(timezone_str)

def convert_dataframe_to_market_timezone(df: pd.DataFrame, timezone_str: str = TIMEZONE_STR) -> pd.DataFrame:
    """
    Convert DataFrame index to market timezone.
    
    Handles both naive and timezone-aware indices:
    - If index is timezone-aware: converts to market timezone
    - If index is naive: localizes to UTC, then converts to market timezone
    
    Args:
        df: DataFrame with datetime index (naive or timezone-aware)
        timezone_str: IANA timezone string (defaults to global TIMEZONE_STR from settings)
        
    Returns:
        DataFrame with index converted to market timezone
        
    Raises:
        Exception: If timezone conversion fails
    """
    try:
        market_tz = pytz.timezone(timezone_str)
        
        # Check if index is already timezone-aware
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            # Convert from current timezone to market timezone
            df.index = df.index.tz_convert(market_tz)
        else:
            # Localize naive index to UTC, then convert to market timezone
            df.index = df.index.tz_localize('UTC')
            df.index = df.index.tz_convert(market_tz)
        
        return df
        
    except Exception as e:
        logging.error(f"Failed to convert DataFrame index to market timezone: {str(e)}", exc_info=True)
        raise
