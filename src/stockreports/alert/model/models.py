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
        """Converts the dataclass to a dictionary for JSON serialization, ensuring ISO 8601 for times."""
        d = asdict(self)
        # Ensure ISO 8601 string for alert_time and start_time
        if isinstance(d["alert_time"], pd.Timestamp):
            d["alert_time"] = d["alert_time"].isoformat()
        if isinstance(d["start_time"], pd.Timestamp):
            d["start_time"] = d["start_time"].isoformat()
        if d.get("validation_price_time") and isinstance(d["validation_price_time"], pd.Timestamp):
            d["validation_price_time"] = d["validation_price_time"].isoformat()
        return d

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
class ConfirmationResult:
    """
    Represents the outcome of a signal confirmation check.
    """
    trend: str
    signal: str
    reversal_time: Optional[pd.Timestamp] = None

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
    actual_profit_loss: float
    status: str
    entry_source_symbol: str
    exit_source_symbol: str
    entry_signal_status: str
    exit_signal_status: str
    improvement_suggestion: str
    best_possible_entry_price: float
    best_possible_exit_price: float
    worst_loss_price: float
    best_profit_price: float

@dataclass
class ProfitabilityReport:
    """Encapsulates the full summary of a trading simulation for a day."""
    total_trades: int
    successful_trades: int
    failed_trades: int
    ignored_trades: int
    success_rate: str
    failure_rate: str
    total_actual_profit_loss: float
    total_best_profit_price: float
    total_worst_loss_price: float
    trades: List[Trade]

    def to_dict(self):
        """Converts the report to a dictionary for JSON serialization."""
        return asdict(self)
