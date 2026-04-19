"""
Trading Hours model - Centralized representation of market trading hours.

Defines when trading occurs for a symbol, including timezone and sessions.
This is a core domain model used across the entire system.
"""

from dataclasses import dataclass
from typing import Dict, List

from .session import Session


@dataclass(frozen=True)
class TradingHoursConfig:
    """
    Immutable representation of complete market trading hours.
    
    Trading hours define when trading can occur for a symbol, including
    multiple sessions, timezone information, and session details.
    
    Attributes:
        name: Trading hours identifier (e.g., "VIETNAM_STOCK", "CRYPTO_24H")
        timezone: IANA timezone string (e.g., "Asia/Ho_Chi_Minh", "UTC")
        sessions: List of trading sessions within a day
        trading_days: List of integers representing trading days (Monday=0, ..., Sunday=6)
    
    Example:
        vn_hours = TradingHoursConfig(
            name="VIETNAM_STOCK",
            timezone="Asia/Ho_Chi_Minh",
            sessions=[
                Session("morning", "03:00", "12:00"),
                Session("afternoon", "12:10", "22:30")
            ],
            trading_days=[0, 1, 2, 3, 4]
        )
    """
    name: str
    timezone: str
    sessions: List[Session]
    trading_days: List[int]
    
    def __post_init__(self):
        """Validate trading hours structure"""
        if not self.name:
            raise ValueError("Trading hours name is required")
        if not self.timezone:
            raise ValueError("Timezone is required")
        if not self.sessions or len(self.sessions) == 0:
            raise ValueError("At least one trading session is required")
        if not hasattr(self, 'trading_days') or self.trading_days is None:
            raise ValueError("trading_days is required (list of integers, Monday=0 ... Sunday=6)")
        if not isinstance(self.trading_days, list) or not all(isinstance(d, int) for d in self.trading_days):
            raise ValueError("trading_days must be a list of integers")
        if not all(0 <= d <= 6 for d in self.trading_days):
            raise ValueError("trading_days values must be in range 0 (Monday) to 6 (Sunday)")
    
    def get_sessions_summary(self) -> str:
        """
        Get human-readable summary of trading sessions for logging.
        
        Returns a formatted string with timezone and session times.
        
        Format: "TRADING_HOURS_NAME [timezone]: session1 (start-end), session2 (start-end)"
        
        Returns:
            Human-readable string describing all trading sessions
            
        Example:
            trading_hours = TradingHoursConfig(...)
            summary = trading_hours.get_sessions_summary()
            # "VIETNAM_STOCK [Asia/Ho_Chi_Minh]: morning (03:00-12:00), afternoon (12:10-22:30)"
        """
        sessions_dict = self.to_sessions_dict()
        sessions_str = ", ".join([
            f"{name} ({times['start']}-{times['end']})"
            for name, times in sessions_dict.items()
        ])
        return f"{self.name} [{self.timezone}]: {sessions_str}"
    
    def to_sessions_dict(self) -> Dict[str, Dict[str, str]]:
        """
        Convert sessions to dict format compatible with time_utils.SESSIONS.
        
        Returns a dictionary where:
        - Keys: session names (e.g., "morning", "afternoon")
        - Values: dicts with "start" and "end" time strings
        
        Format:
            {
                "morning": {"start": "03:00", "end": "12:00"},
                "afternoon": {"start": "12:10", "end": "22:30"}
            }
        
        Returns:
            Dictionary of sessions in SESSIONS format
            
        Example:
            trading_hours = TradingHoursConfig(...)
            sessions_dict = trading_hours.to_sessions_dict()
            # Use with time_utils functions
            is_trading_hours(..., sessions=sessions_dict)
        """
        return {
            session.name: session.to_dict()
            for session in self.sessions
        }
