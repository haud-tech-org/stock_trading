"""
BaseTrading - Abstract base class for all trading platforms.
"""

# --- Python Standard Library ---
from abc import ABC, abstractmethod
from typing import Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertData
from src.stockreports.model.trading import TradeResult
from src.stockreports.utils.time_utils import TimeSimulator

class BaseTrading(ABC):
    @abstractmethod
    def orchestrate_bracket_order(self, alert: AlertData, tp_price: float = None, sl_price: float = None, time_simulator: Optional[TimeSimulator] = None):
        """
        Place main order, then TP and SL orders as a bracket. Waits for main order to be FILLED before placing TP/SL.
        Args:
            alert (AlertData): Alert data containing symbol and order info.
            tp_price (float): Take profit price.
            sl_price (float): Stop loss price.
            time_simulator (TimeSimulator | None): Optional simulator for replay/live time control.
                In replay mode: advance() steps simulated time, no real sleep occurs.
                In live mode (None or is_replay_mode()=False): real time.sleep() is used.
        Returns:
            dict: Results of the main, take profit, and stop loss orders.
        """
        pass
