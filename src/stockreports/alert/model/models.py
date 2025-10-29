from dataclasses import dataclass, field, asdict
from typing import List, Optional
import pandas as pd
import json

@dataclass
class AlertData:
    """
    A standardized dataclass for a single alert record.
    This ensures consistency across all approaches.
    """
    approach: str
    id: str
    signal: str
    alert_price: float
    alert_time: pd.Timestamp
    start_price: float
    start_time: pd.Timestamp
    magnitude: float
    details: str  # The original, approach-specific dictionary as a JSON string
    profit_loss: Optional[float] = None
    period_time: Optional[int] = None
    status: Optional[str] = None
    validation_price_time: Optional[pd.Timestamp] = None
    time_to_best_price: Optional[int] = None  # Time in minutes to reach best price
    min_expected_profit_loss: Optional[float] = None
    symbol: Optional[str] = None

    def to_dict(self):
        """Converts the dataclass to a dictionary for JSON serialization."""
        return asdict(self)

@dataclass
class AlertResult:
    """
    Standard data object for returning results from an alert approach executor.
    """
    approach_name: str
    alerts: pd.DataFrame
    status: str = "SUCCESS"
    message: str = ""

    @property
    def has_alerts(self) -> bool:
        """Checks if any alerts were generated."""
        return not self.alerts.empty

@dataclass
class AlertNotification:
    """
    A clean data model for a single alert, designed for notification purposes.
    """
    symbol: str
    signal: str
    approach: str
    alert_price: float
    alert_time: pd.Timestamp
    details: dict = field(default_factory=dict)
    suggested_price: Optional[float] = None

@dataclass
class AlertSummary:
    """Holds the summary of an alert generation run for a specific approach."""
    approach: str
    date: str
    total_alerts: int
    successful_alerts: int
    failed_alerts: int
    success_rate_pct: float
    average_profit_loss: Optional[float] = None
    avg_time_to_best_price: Optional[float] = None
    min_time_to_best_price: Optional[int] = None
    max_time_to_best_price: Optional[int] = None
    min_expected_profit_loss: Optional[float] = None

    def to_dict(self):
        """Converts the dataclass to a dictionary, handling nested dataclasses."""
        return asdict(self)

@dataclass
class Trade:
    """
    Represents a single simulated trade with an entry and an exit.
    """
    trade_index: int
    entry_signal: str
    entry_price: float
    entry_timestamp: str
    entry_approach: str
    exit_signal: str
    exit_price: float
    exit_timestamp: str
    exit_approach: str
    profit_loss: float
    status: str
    entry_source_symbol: Optional[str] = None  # New field for entry source
    exit_source_symbol: Optional[str] = None   # New field for exit source
    entry_suggested_price: Optional[float] = None # New field for entry suggested price
    exit_suggested_price: Optional[float] = None # New field for exit suggested price
    entry_best_profit: Optional[float] = None
    entry_worst_loss: Optional[float] = None
    exit_best_profit: Optional[float] = None
    exit_worst_loss: Optional[float] = None
    entry_signal_status: Optional[str] = None
    exit_signal_status: Optional[str] = None
    improvement_suggestion: Optional[str] = None

@dataclass
class ProfitabilityReport:
    """Encapsulates the full summary of a trading simulation for a day."""
    total_trades: int
    successful_trades: int
    failed_trades: int
    success_rate: str
    failure_rate: str
    total_profit_loss: float
    trades: List[Trade]

    def to_dict(self):
        """Converts the report to a dictionary for JSON serialization."""
        return asdict(self)
