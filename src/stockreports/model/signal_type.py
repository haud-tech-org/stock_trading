"""
SignalType Enum - Centralized mapping for all notification signals.

Provides a single source of truth for all supported notification signals (Trade, Price Movement, etc.)
with static methods for config mapping and validation.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, List

class SignalType(Enum):
    # Trade signals
    BUY = "BUY"
    SELL = "SELL"
    CLOSE_POSITION = "CLOSE_POSITION"
    ORDER_REMINDER = "ORDER_REMINDER"
    # Price movement signals (extend as needed)
    PRICE_UP = "PRICE_UP"
    PRICE_DOWN = "PRICE_DOWN"
    # Add more as needed

    @staticmethod
    def from_str(signal_str: str) -> Optional[SignalType]:
        """
        Map a config string to a SignalType enum value.
        Returns None if not recognized.
        """
        normalized = signal_str.strip().upper().replace(" ", "_")
        for signal in SignalType:
            if signal.value == normalized:
                return signal
        return None

    @staticmethod
    def all_trade_signals() -> list[SignalType]:
        return [SignalType.BUY, SignalType.SELL, SignalType.CLOSE_POSITION, SignalType.ORDER_REMINDER]

    @staticmethod
    def all_price_movement_signals() -> list[SignalType]:
        return [SignalType.PRICE_UP, SignalType.PRICE_DOWN]

    @staticmethod
    def is_trade_signal(signal: SignalType) -> bool:
        return signal in SignalType.all_trade_signals()

    @staticmethod
    def is_price_movement_signal(signal: SignalType) -> bool:
        return signal in SignalType.all_price_movement_signals()
