from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd
import logging

from src.stockreports.alert.model.models import AlertResult, AlertData
from src.stockreports.alert.common.constants import Signal, PeakTrough, PriceColumn
from src.stockreports.alert.common.data_utils import find_extreme_point
from src.stockreports.alert.common.base_settings import BaseSettings


class Executor(ABC):
    def __init__(self, symbol: str, settings: Optional[BaseSettings] = None):
        self.symbol = symbol
        self.settings = settings

        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize context variables
        self.current_window_start_time: Optional[pd.Timestamp] = None
        self.current_window_end_time: Optional[pd.Timestamp] = None
        self.current_step: int = 0
        self.validation_step: int = 0

    def _confirm_breakout_price(self, df_indexed: pd.DataFrame, alert_candle_index: int, signal: Signal, lookback_period: int, prominence: float) -> bool:
        """
        Analyzes the backward window to find a breakout price and confirms if the alert candle breaks it.
        """
        alert_candle_time_for_log = df_indexed.index[alert_candle_index]

        # 1. Define the lookback period
        if lookback_period is None:
            lookback_df = df_indexed.iloc[:alert_candle_index]
        else:
            lookback_start_index = max(0, alert_candle_index - lookback_period)
            lookback_df = df_indexed.iloc[lookback_start_index:alert_candle_index]

        if lookback_df.empty:
            self.logger.debug(f"[{alert_candle_time_for_log}] No lookback history available.")
            return True # Bypass if no history

        # 2. Find the breakout price using the new utility function
        extreme_type = PeakTrough.PEAK if signal == Signal.BUY else PeakTrough.TROUGH
        extreme_point_info = find_extreme_point(lookback_df, PriceColumn.CLOSE, extreme_type, prominence)

        if extreme_point_info is None:
            self.logger.debug(f"[{alert_candle_time_for_log}] No peak/trough found; ignoring breakout confirmation.")
            return True

        breakout_price, _ = extreme_point_info
        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout price set to {breakout_price:.2f} for {signal} signal.")

        # 3. Confirm if the alert candle's price breaks the breakout price
        alert_candle = df_indexed.iloc[alert_candle_index]
        is_price_breakout = False
        if signal == Signal.BUY:
            is_price_breakout = alert_candle['close'] > breakout_price
        elif signal == Signal.SELL:
            is_price_breakout = alert_candle['close'] < breakout_price
        
        if not is_price_breakout:
            self.logger.debug(f"[{alert_candle_time_for_log}] Price breakout not confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
            return False

        self.logger.debug(f"[{alert_candle_time_for_log}] Breakout confirmed. Alert candle close {alert_candle['close']} vs breakout price {breakout_price}.")
        return True

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
    
    def next_step(self):
        """
        Increments the current step and resets validation_step to 1.
        Intended for use in derived classes to track validation/performance steps.
        """
        self.current_step += 1
        self.validation_step = 1
