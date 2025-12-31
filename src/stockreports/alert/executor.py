from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import logging

from src.stockreports.alert.model.models import AlertResult, AlertData


class Executor(ABC):
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def run(self, df: pd.DataFrame, new_candle_count: int) -> AlertResult:
        pass

    def is_in_cooldown(
        self,
        latest_alert_timestamp: Optional[pd.Timestamp],
        current_time: pd.Timestamp,
        cooldown_period: int
    ) -> bool:
        """
        Checks if the approach is in a cooldown period based on a timestamp.
        Returns True if in cooldown, False otherwise.
        """
        if latest_alert_timestamp is None:
            return False

        last_alert_time = latest_alert_timestamp.tz_convert(None)
        current_time_naive = current_time.tz_convert(None)
        time_since_last_alert = (current_time_naive - last_alert_time).total_seconds() / 60

        return time_since_last_alert < cooldown_period
