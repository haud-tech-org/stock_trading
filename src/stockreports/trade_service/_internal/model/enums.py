
"""
Enums for Binance Perpetual Futures order types, time in force, position side, order status, and working type.
"""
from enum import Enum

class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP = "STOP"
    STOP_MARKET = "STOP_MARKET"
    TAKE_PROFIT = "TAKE_PROFIT"
    TAKE_PROFIT_MARKET = "TAKE_PROFIT_MARKET"
    TRAILING_STOP_MARKET = "TRAILING_STOP_MARKET"

class TimeInForce(str, Enum):
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate Or Cancel
    FOK = "FOK"  # Fill Or Kill
    GTX = "GTX"  # Good Till Crossing (Post Only)
    GTD = "GTD"  # Good Till Date

class PositionSide(str, Enum):
    BOTH = "BOTH"   # One-way Mode
    LONG = "LONG"   # Hedge Mode
    SHORT = "SHORT" # Hedge Mode

class OrderStatus(str, Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    NEW_INSURANCE = "NEW_INSURANCE"
    NEW_ADL = "NEW_ADL"
    UNKNOWN = "UNKNOWN"         # Fallback when order query fails or status is unrecognised
    WOULD_TRIGGER = "WOULD_TRIGGER"  # Internal: -2021 trigger price already met at placement time

class WorkingType(str, Enum):
    MARK_PRICE = "MARK_PRICE"
    CONTRACT_PRICE = "CONTRACT_PRICE"

class OcoOutcome(str, Enum):
    TP_FILLED          = "tp_filled"           # Take-profit hit; stop-loss cancelled.
    SL_FILLED          = "sl_filled"           # Stop-loss hit; take-profit cancelled.
    EXTERNAL_TERMINAL  = "external_terminal"   # One order cancelled/expired externally; both cancelled.
    TIMEOUT            = "timeout"             # max_wait elapsed without a fill; both cancelled.
