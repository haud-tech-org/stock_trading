from dataclasses import dataclass, field, asdict
from typing import List, Optional
import pandas as pd
from src.stockreports.alert.common.constants import ValidationStatus, Approach, Signal, Trend

@dataclass
class AlertData:
    """
    A standardized dataclass for a single alert record.
    This ensures consistency across all approaches.
    """
    approach: Approach
    id: str
    signal: Signal
    alert_price: float
    alert_time: pd.Timestamp
    start_price: float
    start_time: pd.Timestamp
    magnitude: float
    details: Optional[str] = None  # The original, approach-specific dictionary as a JSON string
    trend: Optional[Trend] = None
    profit_loss: Optional[float] = None
    period_time: Optional[int] = None
    status: Optional[str] = None
    validation_price_time: Optional[pd.Timestamp] = None
    time_to_best_price: Optional[int] = None  # Time in minutes to reach best price
    min_expected_profit_loss: Optional[float] = None
    symbol: Optional[str] = None
    magnitude: Optional[float] = None
    structural_suggested_price: Optional[float] = None
    performance_suggested_price: Optional[float] = None
    suggested_profit_threshold: Optional[float] = None  # Suggested profit at which to close the position

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
    confirmed_alerts: Optional[List[AlertData]] = None

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
    suggested_profit_threshold: Optional[float] = None

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
    best_possible_entry_price: Optional[float] = None
    best_possible_exit_price: Optional[float] = None
    worst_loss_price: Optional[float] = None
    best_profit_price: Optional[float] = None
    trigger_timestamp: Optional[str] = None
    time_to_trigger_minutes: Optional[float] = None
    time_in_trade_minutes: Optional[float] = None

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
    

class Validation:
    def __init__(self, step: int, validation: int, message: str, status: ValidationStatus, name: str = None):
        self._step = step
        self._validation = validation
        self._message = message
        self._status = status
        if name is not None:
            self._name = name
        else:
            self._name = f"step_{step}_validation_{validation}"

    def get_name(self) -> str:
        return self._name

    def get_step(self) -> int:
        return self._step

    def get_validation(self) -> int:
        return self._validation

    def get_message(self) -> str:
        return self._message

    def get_status(self) -> str:
        return self._status
    
    def to_json(self):
        return {
            "name": self.get_name(),
            "step": self.get_step(),
            "validation": self.get_validation(),
            "message": self.get_message(),
            "status": self.get_status()
        }
