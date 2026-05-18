"""
TradeResult - Result of a trading operation.

Represents the result of a Binance USDT-margined futures order.

All numeric fields are stored as their proper Python types (int / float / bool)
so callers can use them directly in arithmetic without any casting or conversion.
Binance returns most numeric values as JSON strings (e.g. "0.001"); the
from_binance_response factory handles the conversion transparently.
"""

from dataclasses import dataclass
from typing import Optional

from src.stockreports.utils.conversion_data_utils import to_float, to_int


@dataclass
class TradeResult:
    # --- Identity ---
    order_id: Optional[int] = None
    client_order_id: Optional[str] = None
    symbol: Optional[str] = None

    # --- Order state ---
    status: Optional[str] = None
    side: Optional[str] = None
    position_side: Optional[str] = None
    type: Optional[str] = None
    orig_type: Optional[str] = None
    time_in_force: Optional[str] = None
    working_type: Optional[str] = None

    # --- Prices (float) ---
    price: Optional[float] = None           # limit / entry price
    avg_price: Optional[float] = None       # average fill price
    stop_price: Optional[float] = None      # trigger price for STOP / TAKE_PROFIT orders

    # --- Quantities (float) ---
    orig_qty: Optional[float] = None        # original order quantity
    executed_qty: Optional[float] = None    # quantity already filled
    cum_qty: Optional[float] = None         # cumulative filled quantity
    cum_quote: Optional[float] = None       # cumulative filled quote asset value

    # --- Flags (bool) ---
    reduce_only: Optional[bool] = None
    close_position: Optional[bool] = None
    price_protect: Optional[bool] = None

    # --- Misc ---
    price_match: Optional[str] = None
    self_trade_prevention_mode: Optional[str] = None
    update_time: Optional[int] = None
    good_till_date: Optional[int] = None

    @staticmethod
    def _common_fields(resp: dict) -> dict:
        """
        Extract fields whose key names are identical in both regular and algo
        order responses.  Returns a kwargs dict for unpacking into TradeResult().
        """
        return dict(
            symbol=resp.get("symbol"),
            side=resp.get("side"),
            position_side=resp.get("positionSide"),
            time_in_force=resp.get("timeInForce"),
            working_type=resp.get("workingType"),
            price=to_float(resp.get("price")),
            reduce_only=resp.get("reduceOnly"),
            close_position=resp.get("closePosition"),
            price_protect=resp.get("priceProtect"),
            price_match=resp.get("priceMatch"),
            self_trade_prevention_mode=resp.get("selfTradePreventionMode"),
            update_time=to_int(resp.get("updateTime")),
            good_till_date=to_int(resp.get("goodTillDate")),
        )

    @staticmethod
    def from_binance_response(resp: dict) -> 'TradeResult':
        """
        Create a TradeResult from a regular /fapi/v1/order response dict.
        Specific fields: orderId, status, type, stopPrice, origQty, avgPrice, etc.
        """
        return TradeResult(
            **TradeResult._common_fields(resp),
            # --- Regular-specific identity ---
            order_id=to_int(resp.get("orderId")),
            client_order_id=resp.get("clientOrderId"),
            # --- Regular-specific order state ---
            status=resp.get("status"),
            type=resp.get("type"),
            orig_type=resp.get("origType"),
            # --- Regular-specific prices ---
            avg_price=to_float(resp.get("avgPrice")),
            stop_price=to_float(resp.get("stopPrice")),
            # --- Regular-specific quantities ---
            orig_qty=to_float(resp.get("origQty")),
            executed_qty=to_float(resp.get("executedQty")),
            cum_qty=to_float(resp.get("cumQty")),
            cum_quote=to_float(resp.get("cumQuote")),
        )

    @staticmethod
    def from_algo_response(resp: dict) -> 'TradeResult':
        """
        Create a TradeResult from a /fapi/v1/algoOrder response dict.
        Specific fields: algoId, algoStatus, orderType, triggerPrice, quantity.
        """
        return TradeResult(
            **TradeResult._common_fields(resp),
            # --- Algo-specific identity ---
            order_id=to_int(resp.get("algoId")),
            client_order_id=resp.get("clientAlgoId"),
            # --- Algo-specific order state ---
            status=resp.get("algoStatus"),
            type=resp.get("orderType"),          # algo uses "orderType" not "type"
            # --- Algo-specific prices ---
            stop_price=to_float(resp.get("triggerPrice")),  # algo uses "triggerPrice"
            # --- Algo-specific quantities ---
            orig_qty=to_float(resp.get("quantity")),        # algo uses "quantity" not "origQty"
        )
