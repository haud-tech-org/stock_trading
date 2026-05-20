from dataclasses import dataclass, field, asdict
from typing import List, Optional
import pandas as pd
import logging
from datetime import datetime
from src.stockreports.alert.common.constants import ValidationStatus, Approach, Signal, Status, Trend, TREND_MAPPING, STATUS_MAPPING
from src.stockreports.alert.common.constants import RunMode
from src.stockreports.alert.common.environment import EnvironmentType


@dataclass
class NotificationContext:
    """
    Deployment and run-mode context appended at the bottom of every notification payload.

    Attributes:
        environment: Deployment environment from EnvironmentType
                     (e.g. EnvironmentType.LOCAL, EnvironmentType.GCP)
        run_mode:    RunMode.LIVE or "REPLAY (<timestamp>)"
    """
    environment: str = EnvironmentType.LOCAL
    run_mode: str = RunMode.LIVE

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
    details: Optional[str] = None  # The original, approach-specific dictionary as a JSON string
    trend: Optional[Trend] = None
    profit_loss: Optional[float] = None
    period_time: Optional[int] = None
    status: Optional[Status] = None
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

    @staticmethod
    def from_dict(alert_dict: dict) -> Optional['AlertData']:
        """
        Create an AlertData instance from a dictionary (typically from JSON).
        
        Handles type conversion for enum-like constants:
        - approach: Converts to Approach constant (e.g., Approach.ICHIMOKU)
        - signal: Converts to Signal constant (e.g., Signal.BUY)
        - trend: Converts to Trend constant (e.g., Trend.UPTREND)
        - status: Converts to Status constant (e.g., Status.SUCCESS)
        
        Also handles timestamp parsing for multiple formats:
        - ISO 8601 strings
        - datetime objects
        - pd.Timestamp objects
        
        Args:
            alert_dict: Dictionary containing alert data from JSON file
            
        Returns:
            AlertData object or None if conversion fails
        """
        try:
            # Parse alert_time - handle both string and datetime objects
            alert_time = alert_dict.get('alert_time')
            if isinstance(alert_time, str):
                from dateutil import parser as date_parser
                alert_time = date_parser.isoparse(alert_time)
            elif isinstance(alert_time, datetime):
                alert_time = pd.Timestamp(alert_time)
            elif not isinstance(alert_time, pd.Timestamp):
                logging.warning(f"Invalid alert_time format: {type(alert_time)}")
                return None
            
            # Parse start_time - handle both string and datetime objects
            start_time = alert_dict.get('start_time')
            if isinstance(start_time, str):
                from dateutil import parser as date_parser
                start_time = date_parser.isoparse(start_time)
            elif isinstance(start_time, datetime):
                start_time = pd.Timestamp(start_time)
            elif not isinstance(start_time, pd.Timestamp):
                start_time = alert_time  # Use alert_time as fallback
            
            # Convert approach string to Approach constant
            approach_str = alert_dict.get('approach', 'UNKNOWN')
            approach_value = getattr(Approach, approach_str, approach_str)  # Falls back to string if constant not found
            
            # Convert signal string to Signal constant
            signal_str = alert_dict.get('signal', 'NEUTRAL')
            signal_value = getattr(Signal, signal_str, signal_str)  # Falls back to string if constant not found
            
            # Convert trend string to Trend constant if present
            trend_str = alert_dict.get('trend')
            trend_value = None
            if trend_str:
                trend_value = TREND_MAPPING.get(trend_str, trend_str)
            
            # Convert status string to Status constant if present
            status_str = alert_dict.get('status')
            status_value = None
            if status_str:
                status_value = STATUS_MAPPING.get(status_str, status_str)
            
            # Create AlertData with converted constant values
            alert_data = AlertData(
                approach=approach_value,
                signal=signal_value,
                alert_price=float(alert_dict.get('alert_price', 0)),
                alert_time=alert_time,
                start_price=float(alert_dict.get('start_price', 0)),
                start_time=start_time,
                id=alert_dict.get('id', ''),
                details=alert_dict.get('details'),
                trend=trend_value,
                status=status_value,
                symbol=alert_dict.get('symbol'),
                magnitude=float(alert_dict.get('magnitude', 0)) if alert_dict.get('magnitude') else None,
                suggested_profit_threshold=alert_dict.get('suggested_profit_threshold'),
                structural_suggested_price=alert_dict.get('structural_suggested_price'),
                performance_suggested_price=alert_dict.get('performance_suggested_price'),
                profit_loss=alert_dict.get('profit_loss'),
                period_time=alert_dict.get('period_time'),
                validation_price_time=alert_dict.get('validation_price_time'),
                time_to_best_price=alert_dict.get('time_to_best_price'),
                min_expected_profit_loss=alert_dict.get('min_expected_profit_loss'),
            )
            
            return alert_data
        except Exception as e:
            logging.error(f"Failed to convert alert dictionary to AlertData: {e}", exc_info=True)
            return None

@dataclass
class AlertResult:
    """
    Standard data object for returning results from an alert approach executor.
    
    REFACTORED (v2.0): Uses confirmed_alerts (List[AlertData]) as primary source.
    The alerts DataFrame is generated on-demand for backward compatibility.
    
    Attributes:
        approach_name: Name of the alert approach that generated these results
        confirmed_alerts: List of typed AlertData objects (PRIMARY DATA SOURCE)
                         Can be None or empty list if no alerts found or error occurred
        status: Status.SUCCESS or Status.FAILED
        message: Error message if status is Status.FAILED
    """
    approach_name: str
    confirmed_alerts: Optional[List[AlertData]] = None
    status: Status = Status.SUCCESS
    message: str = ""

    def __post_init__(self):
        """Normalize and validate confirmed_alerts at construction time."""
        # Normalize None to empty list for consistency
        if self.confirmed_alerts is None:
            self.confirmed_alerts = []
        
        # Validate that confirmed_alerts is a list
        if not isinstance(self.confirmed_alerts, list):
            raise TypeError(
                f"confirmed_alerts must be List[AlertData] or None, "
                f"got {type(self.confirmed_alerts).__name__}"
            )
        
        # Validate that all items in list are AlertData
        for item in self.confirmed_alerts:
            if not isinstance(item, AlertData):
                raise TypeError(
                    f"All items in confirmed_alerts must be AlertData, "
                    f"got {type(item).__name__}"
                )

    @property
    def has_alerts(self) -> bool:
        """
        Checks if any alerts were generated.
        
        Returns:
            bool: True if confirmed_alerts list is not empty
        """
        return len(self.confirmed_alerts) > 0 if self.confirmed_alerts else False
    
    @property
    def alerts(self) -> pd.DataFrame:
        """
        DEPRECATED: Use confirmed_alerts instead.
        
        Returns DataFrame representation of confirmed_alerts.
        Generated on-demand for backward compatibility only.
        
        WARNING: This property will be removed in v3.0.
        Migrate code to use confirmed_alerts directly.
        
        Returns:
            pd.DataFrame: Tabular representation of confirmed_alerts (empty if None or empty)
        """
        import warnings
        warnings.warn(
            "AlertResult.alerts DataFrame property is deprecated. "
            "Use confirmed_alerts (List[AlertData]) instead. "
            "This property will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2
        )
        return self.to_dataframe()
    
    def to_dataframe(self) -> pd.DataFrame:
        """
        Convert confirmed_alerts list to DataFrame.
        
        Explicit method for converting typed list to DataFrame format.
        Use this when you need DataFrame operations (grouping, sorting, etc).
        Prefer using confirmed_alerts directly when possible.
        
        Returns:
            pd.DataFrame: Each row is an alert with all AlertData fields
                         Empty DataFrame if confirmed_alerts is None or empty
            
        Example:
            >>> result = executor.run(df, new_candle_count)
            >>> if result.has_alerts:
            ...     df = result.to_dataframe()
            ...     latest = df.sort_values('alert_time').iloc[-1]
        """
        if not self.confirmed_alerts:
            return pd.DataFrame()
        return pd.DataFrame([alert.to_dict() for alert in self.confirmed_alerts])

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
