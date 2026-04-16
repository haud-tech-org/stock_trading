"""
Session model - Centralized representation of a trading session.

Provides a normalized data model for trading sessions with conversion
methods to handle multiple input formats (TradeSessionConfig objects,
dictionaries, tuples, etc.).

This eliminates the need to have session-related logic scattered across
the codebase and provides a single source of truth for session data.
"""

from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional, Union
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Session:
    """
    Normalized representation of a single trading session.
    
    A trading session represents a continuous period during which trading
    occurs (e.g., "morning session" from 3 AM to 12 PM).
    
    This is the canonical model for sessions across the application.
    All session data should be converted to this model for consistency.
    
    Attributes:
        name: Session identifier (e.g., "morning", "afternoon", "24h")
        start_time: Session start time in HH:MM format (e.g., "03:00")
        end_time: Session end time in HH:MM format (e.g., "12:00")
    
    Examples:
        # Create directly
        morning = Session(name="morning", start_time="03:00", end_time="12:00")
        
        # Convert from TradeSessionConfig (alias for Session)
        # Note: Session is the primary class, TradeSessionConfig was a deprecated alias
        trade_config = Session("morning", "03:00", "12:00")
        session = Session.from_trade_session_config(trade_config)
        
        # Convert from dict
        session = Session.from_dict({"name": "morning", "start": "03:00", "end": "12:00"})
        
        # Convert from dict with "start"/"end" keys
        session = Session.from_sessions_dict_entry("morning", {"start": "03:00", "end": "12:00"})
        
        # Convert from tuple
        session = Session.from_tuple(("morning", "03:00", "12:00"))
    """
    
    name: str
    start_time: str
    end_time: str
    
    def __post_init__(self):
        """Validate session times are in valid HH:MM format."""
        self._validate_times()
    
    def _validate_times(self) -> None:
        """
        Validate that session times are in proper HH:MM format and reasonable.
        
        Raises:
            ValueError: If times are not in valid format or have invalid values
        """
        try:
            # Validate start time
            start_parts = self.start_time.split(':')
            if len(start_parts) != 2:
                raise ValueError(f"Start time must be HH:MM format, got: {self.start_time}")
            
            start_hour = int(start_parts[0])
            start_min = int(start_parts[1])
            
            if not (0 <= start_hour < 24 and 0 <= start_min < 60):
                raise ValueError(f"Invalid start time values: {self.start_time}")
            
            # Validate end time
            end_parts = self.end_time.split(':')
            if len(end_parts) != 2:
                raise ValueError(f"End time must be HH:MM format, got: {self.end_time}")
            
            end_hour = int(end_parts[0])
            end_min = int(end_parts[1])
            
            if not (0 <= end_hour < 24 and 0 <= end_min < 60):
                raise ValueError(f"Invalid end time values: {self.end_time}")
        
        except ValueError as e:
            raise ValueError(f"Session '{self.name}' has invalid times: {e}")
    
    # --- Conversion Methods ---
    
    def to_dict(self) -> Dict[str, str]:
        """
        Convert to dict format with "start" and "end" keys.
        
        This format is compatible with time_utils functions like
        is_trading_hours(), get_session_window(), etc.
        
        Returns:
            Dictionary with "start" and "end" time strings
            
        Example:
            session = Session("morning", "03:00", "12:00")
            d = session.to_dict()
            # {"start": "03:00", "end": "12:00"}
        """
        return {
            "start": self.start_time,
            "end": self.end_time
        }
    
    def to_tuple(self) -> Tuple[str, str, str]:
        """
        Convert to tuple format (name, start_time, end_time).
        
        Returns:
            Tuple with (name, start_time, end_time)
            
        Example:
            session = Session("morning", "03:00", "12:00")
            t = session.to_tuple()
            # ("morning", "03:00", "12:00")
        """
        return (self.name, self.start_time, self.end_time)
    
    def to_sessions_dict_entry(self) -> Tuple[str, Dict[str, str]]:
        """
        Convert to entry format for sessions dictionary.
        
        Returns:
            Tuple of (session_name, session_dict) suitable for
            building a SESSIONS dictionary
            
        Example:
            session = Session("morning", "03:00", "12:00")
            name, times = session.to_sessions_dict_entry()
            sessions = {name: times}
            # {"morning": {"start": "03:00", "end": "12:00"}}
        """
        return (self.name, self.to_dict())
    
    # --- Static Conversion Methods ---
    
    @staticmethod
    def from_trade_session_config(trade_config: Any) -> 'Session':
        """
        Convert from TradeSessionConfig object.
        
        Handles conversion from the executor configuration service's
        TradeSessionConfig dataclass.
        
        Args:
            trade_config: TradeSessionConfig object with name, start_time, end_time
            
        Returns:
            Session object with same data
            
        Raises:
            ValueError: If conversion fails or data is invalid
            TypeError: If input is not a TradeSessionConfig
            
        Example:
            # Convert from Session (primary class)
            trade_config = Session("morning", "03:00", "12:00")
            session = Session.from_trade_session_config(trade_config)
        """
        try:
            return Session(
                name=trade_config.name,
                start_time=trade_config.start_time,
                end_time=trade_config.end_time
            )
        except AttributeError as e:
            raise TypeError(f"Object does not have TradeSessionConfig structure: {e}")
        except Exception as e:
            raise ValueError(f"Failed to convert TradeSessionConfig: {e}")
    
    @staticmethod
    def from_dict(data: Dict[str, str]) -> 'Session':
        """
        Convert from dictionary with "name", "start_time", "end_time" keys.
        
        Flexible conversion that handles various dictionary keys:
        - "name", "start_time", "end_time" (preferred)
        - "name", "start", "end" (alternate)
        
        Args:
            data: Dictionary with session data
            
        Returns:
            Session object with converted data
            
        Raises:
            ValueError: If required keys are missing or data is invalid
            TypeError: If input is not a dictionary
            
        Example:
            session = Session.from_dict({
                "name": "morning",
                "start_time": "03:00",
                "end_time": "12:00"
            })
        """
        if not isinstance(data, dict):
            raise TypeError(f"Expected dict, got {type(data).__name__}")
        
        try:
            # Try to get name
            name = data.get("name")
            if not name:
                raise ValueError("Missing required key: 'name'")
            
            # Try to get start time (support both 'start_time' and 'start')
            start_time = data.get("start_time") or data.get("start")
            if not start_time:
                raise ValueError("Missing required key: 'start_time' or 'start'")
            
            # Try to get end time (support both 'end_time' and 'end')
            end_time = data.get("end_time") or data.get("end")
            if not end_time:
                raise ValueError("Missing required key: 'end_time' or 'end'")
            
            return Session(name=name, start_time=start_time, end_time=end_time)
        
        except ValueError as e:
            raise ValueError(f"Failed to convert dict to Session: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error converting dict: {e}")
    
    @staticmethod
    def from_sessions_dict_entry(name: str, times_dict: Dict[str, str]) -> 'Session':
        """
        Convert from a SESSIONS dictionary entry.
        
        Handles conversion from entries in the time_utils SESSIONS dictionary
        format where keys are session names and values are dicts with
        "start" and "end" keys.
        
        Args:
            name: Session name (key from SESSIONS dict)
            times_dict: Dictionary with "start" and "end" time strings
            
        Returns:
            Session object with combined data
            
        Raises:
            ValueError: If data is invalid
            TypeError: If inputs are wrong type
            
        Example:
            session = Session.from_sessions_dict_entry(
                "morning",
                {"start": "03:00", "end": "12:00"}
            )
        """
        if not isinstance(times_dict, dict):
            raise TypeError(f"Expected dict for times, got {type(times_dict).__name__}")
        
        try:
            start = times_dict.get("start")
            if not start:
                raise ValueError("Missing 'start' in times dict")
            
            end = times_dict.get("end")
            if not end:
                raise ValueError("Missing 'end' in times dict")
            
            return Session(name=name, start_time=start, end_time=end)
        
        except ValueError as e:
            raise ValueError(f"Failed to convert SESSIONS entry: {e}")
        except Exception as e:
            raise ValueError(f"Unexpected error converting SESSIONS entry: {e}")
    
    @staticmethod
    def from_tuple(data: Tuple[str, str, str]) -> 'Session':
        """
        Convert from tuple format (name, start_time, end_time).
        
        Args:
            data: Tuple with (name, start_time, end_time)
            
        Returns:
            Session object with tuple data
            
        Raises:
            ValueError: If tuple has wrong length or invalid values
            TypeError: If input is not a tuple
            
        Example:
            session = Session.from_tuple(("morning", "03:00", "12:00"))
        """
        if not isinstance(data, (tuple, list)):
            raise TypeError(f"Expected tuple or list, got {type(data).__name__}")
        
        if len(data) != 3:
            raise ValueError(f"Expected tuple of length 3, got {len(data)}")
        
        try:
            name, start_time, end_time = data
            return Session(name=name, start_time=start_time, end_time=end_time)
        except Exception as e:
            raise ValueError(f"Failed to convert tuple: {e}")
    
    @staticmethod
    def from_any(data: Any) -> 'Session':
        """
        Smart conversion from any supported format.
        
        Automatically detects the format and converts appropriately.
        Supports:
        - Session objects (returns as-is)
        - TradeSessionConfig objects
        - Dictionaries with various key formats
        - Tuples/lists with (name, start_time, end_time)
        
        Args:
            data: Data in any supported format
            
        Returns:
            Session object
            
        Raises:
            ValueError: If format not recognized or conversion fails
            TypeError: If data type not supported
            
        Example:
            # Auto-detect and convert any format
            session = Session.from_any(some_session_data)
        """
        # Already a Session object
        if isinstance(data, Session):
            return data
        
        # Dictionary format
        if isinstance(data, dict):
            # Check if it's a SESSIONS dict entry (only has "start" and "end")
            if set(data.keys()) <= {"start", "end"}:
                raise ValueError(
                    "Cannot convert dict with only 'start'/'end' to Session. "
                    "Use from_sessions_dict_entry() instead."
                )
            return Session.from_dict(data)
        
        # Tuple/list format
        if isinstance(data, (tuple, list)):
            return Session.from_tuple(data)
        
        # TradeSessionConfig format (has name, start_time, end_time attributes)
        if hasattr(data, 'name') and hasattr(data, 'start_time') and hasattr(data, 'end_time'):
            return Session.from_trade_session_config(data)
        
        raise TypeError(
            f"Cannot convert {type(data).__name__} to Session. "
            "Supported formats: Session, TradeSessionConfig, dict, tuple, list"
        )
    
    # --- Utility Methods ---
    
    def __str__(self) -> str:
        """Get human-readable string representation."""
        return f"{self.name} ({self.start_time}-{self.end_time})"
    
    def __repr__(self) -> str:
        """Get detailed string representation."""
        return f"Session(name='{self.name}', start_time='{self.start_time}', end_time='{self.end_time}')"
