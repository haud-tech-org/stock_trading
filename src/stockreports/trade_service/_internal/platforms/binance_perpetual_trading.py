"""
BinancePerpetualTrading - Trading implementation for Binance USDT-margined perpetual futures.
"""

# --- Python Standard Library ---
import json
import time
import logging
import hmac
import hashlib
from enum import Enum
from typing import List, Optional
from urllib.parse import urlencode

# --- Third-Party Libraries ---
import requests

# --- Project Imports ---
from src.stockreports.trade_service._internal.base_trading import BaseTrading
from src.stockreports.trade_service._internal.model.enums import OrderType, TimeInForce, OrderStatus, OcoOutcome
from src.stockreports.trade_service._internal.config.binance_perpetual_config import BINANCE_PERPETUAL_CONFIG
from src.stockreports.model.trading import TradeResult
from src.stockreports.alert.model.models import AlertData
from src.stockreports.alert.common.constants import Signal
from src.stockreports.utils.alert_utils import get_reversal_signal, get_primary_suggested_price
from src.stockreports.utils.time_utils import TimeSimulator


class BinancePerpetualTrading(BaseTrading):
    _leveraged_symbols: set = set()  # shared across all instances — leverage is set once per symbol

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._server_time_offset_ms = self._fetch_server_time_offset()

    # -------------------------------------------------------------------------
    # Public orchestration
    # -------------------------------------------------------------------------

    def orchestrate_bracket_order(self, alert: AlertData, tp_price: float = None, sl_price: float = None, time_simulator: Optional[TimeSimulator] = None):
        """
        Entry point for DCA ladder bracket order management:
          1. Resolve entry price from the alert.
          2. Place a DCA ladder of LIMIT orders via POST /fapi/v1/batchOrders.
          3. Run a unified monitoring loop (_monitor_ladder) that:
               - Cancels unfilled LIMIT orders after ladder_order_max_wait seconds.
               - Tracks cumulative open position qty on every poll.
               - On every qty change, fetches the actual average entry price from
                 positionRisk and recalculates TP/SL from config diffs.
               - Re-places the TP/SL bracket with the freshly computed prices.
               - Performs inline OCO monitoring on the active bracket.
               - On TP/SL fill, cancels the other leg; remaining LIMIT orders stay open (Option B).
               - Exits only when no LIMIT, TAKE_PROFIT_MARKET, or STOP_MARKET orders remain.
        Note: tp_price / sl_price params are accepted for API compatibility but are unused —
        TP/SL are always derived from the real average fill price inside _monitor_ladder.
        Args:
            time_simulator (TimeSimulator | None): Optional simulator for replay/live time control.
                Passed through to _monitor_ladder to control sleep/advance behaviour.
        """
        # Re-resolve connection attributes now that we know the time_simulator context
        # (replay mode vs. live); use_demo always takes precedence.
        self._resolve_base_url(time_simulator)

        symbol = alert.symbol.replace("-PERP", "")
        self._ensure_leverage(symbol)

        # 1. Resolve entry price — anchor for TP/SL diff calculation
        entry_price: float = get_primary_suggested_price(alert) or alert.alert_price
        if not entry_price:
            raise ValueError(
                "AlertData has no usable entry price. "
                "Ensure alert_price, structural_suggested_price, or performance_suggested_price is set."
            )

        # 2. Place DCA ladder — order 1 at entry_price, orders 2-N at computed ladder levels
        self.logger.info(f"Placing DCA ladder for {symbol} | signal={alert.signal} | entry={entry_price}")
        ladder_results: List[TradeResult] = self.place_order(alert)
        placed = [r for r in ladder_results if r.order_id]
        if not placed:
            raise Exception("All DCA ladder orders failed — no orders were accepted by the exchange")

        # 2b. Wait for at least one ladder order to fill and open a position.
        #     The monitoring loop should not start until we have a real position to
        #     bracket — entering it on an empty book wastes the oco_max_wait budget
        #     and risks placing TP/SL against stale prices.
        position_open_wait: int = BINANCE_PERPETUAL_CONFIG.get("position_open_wait", 3600)
        position_open_poll: int = BINANCE_PERPETUAL_CONFIG.get("position_open_poll", 10)
        waited: int = 0
        position_confirmed: bool = False
        self.logger.info(
            f"Waiting up to {position_open_wait}s for a position to open for {symbol}..."
        )
        while waited < position_open_wait:
            if time_simulator and time_simulator.is_replay_mode():
                time_simulator.advance()
            else:
                time.sleep(position_open_poll)
            waited += position_open_poll
            try:
                qty, avg_entry = self._get_position_info(symbol)
                if qty > 0:
                    self.logger.info(
                        f"Position confirmed for {symbol}: qty={qty} avg_entry={avg_entry} "
                        f"after ~{waited}s"
                    )
                    position_confirmed = True
                    break
            except ValueError:
                pass  # no position yet — keep polling
            except RuntimeError as e:
                self.logger.warning(
                    f"orchestrate_bracket_order: position check error for {symbol}: {e}"
                )

        if not position_confirmed:
            self.logger.warning(
                f"orchestrate_bracket_order: no position opened for {symbol} within "
                f"{position_open_wait}s — cancelling all ladder orders and aborting."
            )
            self._cancel_ladder_orders(symbol)
            return {
                "main": ladder_results,
                "oco_outcome": OcoOutcome.TIMEOUT,
            }

        # 3. Unified monitoring loop — TP/SL are recalculated from the actual average
        #    fill price each time the position qty changes, so we don't pass static prices.
        self.logger.info(
            f"Starting ladder monitor for {symbol} | "
            f"{len(placed)}/{len(ladder_results)} ladder orders placed"
        )
        oco_outcome: OcoOutcome = self._monitor_ladder(symbol, alert.signal, time_simulator)

        return {
            "main": ladder_results,       # List[TradeResult] — all ladder order placement results
            "oco_outcome": oco_outcome,   # OcoOutcome: TP_FILLED | SL_FILLED | EXTERNAL_TERMINAL | TIMEOUT
        }

    # -------------------------------------------------------------------------
    # Order placement
    # -------------------------------------------------------------------------

    def place_order(self, alert: AlertData) -> List[TradeResult]:
        symbol = alert.symbol.replace("-PERP", "")

        entry_price: float = get_primary_suggested_price(alert) or alert.alert_price
        if not entry_price:
            raise ValueError(
                "AlertData has no usable entry price. "
                "Ensure alert_price, structural_suggested_price, or performance_suggested_price is set."
            )

        # Derive base quantity from the configured USDT amount so every order is
        # sized by value rather than a fixed coin amount.
        order_usdt_amount: float = BINANCE_PERPETUAL_CONFIG.get("order_usdt_amount", 200.0)
        qty_precision: int = BINANCE_PERPETUAL_CONFIG.get("qty_precision", 3)
        base_qty: float = round(order_usdt_amount / entry_price, qty_precision)

        # Fetch positions once — shared by both same-side and opposite-side checks below.
        positions: List[dict] = self._fetch_position_risk(symbol)

        # Same-side divergence guard: close any existing same-side position whose
        # avg entry price has drifted too far from the new signal's entry level.
        self._close_diverged_same_side_position(symbol, alert.signal, entry_price, positions)

        # Order 1: entry price — accumulate any existing opposite-side position so
        # it is closed and the new position opened in a single net-settling order.
        opposite_qty: float = self._get_opposite_side_qty(alert.signal, positions)
        first_qty: float = round(base_qty + opposite_qty, 8)
        if opposite_qty > 0:
            self.logger.info(
                f"place_order: absorbing opposite-side position into first order for {symbol} | "
                f"base_qty={base_qty} + opposite_qty={opposite_qty} → first_qty={first_qty}"
            )

        order_dicts: List[dict] = [
            {
                "symbol": symbol,
                "side": alert.signal,
                "type": OrderType.LIMIT,
                "price": str(entry_price),
                "quantity": str(first_qty),
                "timeInForce": TimeInForce.GTC,
            }
        ]

        # Orders 2–N: computed from century-offset + snap formula
        for price, qty in self._build_ladder_levels(entry_price, alert.signal):
            order_dicts.append({
                "symbol": symbol,
                "side": alert.signal,
                "type": OrderType.LIMIT,
                "price": str(price),
                "quantity": str(qty),
                "timeInForce": TimeInForce.GTC,
            })

        self.logger.info(
            f"Placing {len(order_dicts)} DCA ladder orders for {symbol} | "
            f"entry={entry_price} order_usdt_amount={order_usdt_amount} "
            f"first_qty={first_qty} (incl. opposite_qty={opposite_qty})"
        )
        self._assert_sufficient_balance(symbol, order_dicts)
        return self._place_orders_batch(symbol, order_dicts)

    # -------------------------------------------------------------------------
    # Private helpers
    # -------------------------------------------------------------------------

    def _fetch_available_balance(self, asset: str = "USDT") -> float:
        """
        Query available wallet balance for ``asset`` via GET /fapi/v2/balance.
        Returns the ``availableBalance`` field as a float, or 0.0 on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Futures-Account-Balance-V2
        """
        params = {"timestamp": self._now_ms()}
        params = self._sign_params(params)
        try:
            resp = requests.get(
                self.base_url + "/fapi/v2/balance",
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            for entry in resp.json():
                if entry.get("asset") == asset:
                    return float(entry.get("availableBalance", 0))
        except Exception as e:
            self.logger.warning(
                f"_fetch_available_balance: could not fetch balance for {asset}: {e}. "
                "Defaulting to 0.0."
            )
        return 0.0

    def _assert_sufficient_balance(self, symbol: str, order_dicts: List[dict]) -> None:
        """
        Verify that the available USDT balance covers the total required margin for
        all pending ladder orders before submitting them to the exchange.

        Required margin per order  = (price × qty) / leverage
        Total required margin      = sum over all orders
        Threshold                  = total_required × min_balance_buffer_ratio (config, default 1.05)

        Raises ValueError if available balance is below the threshold so that no
        partial ladder is ever placed on an under-funded account.

        Uses the ``price`` field from each order dict for LIMIT orders.  Orders
        without a ``price`` key (e.g. MARKET) are skipped — their notional is
        unknown at submission time.
        """
        leverage: int = BINANCE_PERPETUAL_CONFIG.get("default_leverage", 20)
        buffer: float = BINANCE_PERPETUAL_CONFIG.get("min_balance_buffer_ratio", 1.5)

        total_notional: float = sum(
            float(o["price"]) * float(o["quantity"])
            for o in order_dicts
            if "price" in o and "quantity" in o
        )
        required_margin: float = total_notional / leverage
        threshold: float = required_margin * buffer

        available: float = self._fetch_available_balance("USDT")
        self.logger.info(
            f"_assert_sufficient_balance: symbol={symbol} | "
            f"total_notional={total_notional:.2f} | leverage={leverage}x | "
            f"required_margin={required_margin:.4f} | "
            f"threshold(×{buffer})={threshold:.4f} | available={available:.4f} USDT"
        )
        if available < threshold:
            raise ValueError(
                f"Insufficient USDT balance for {symbol}: "
                f"available={available:.4f}, required={threshold:.4f} "
                f"(notional={total_notional:.2f} / leverage={leverage} × buffer={buffer}). "
                "Top up your account or reduce ladder quantities."
            )

    def _build_ladder_levels(self, entry_price: float, signal: str) -> List[tuple]:
        """
        Compute (price, qty) for each ladder order (orders 2–N).

        Formula:
            entry_century = int(entry_price // 100)
            BUY  → price = (entry_century - offset) * 100 + snap   (step down)
            SELL → price = (entry_century + offset) * 100 + snap   (step up)
            snap alternates per index: snaps[i % 2]
            qty  = round((order_usdt_amount × ladder_qty_multipliers[i]) / price, qty_precision)
                   Each level's USDT exposure scales by its multiplier, then is
                   converted to coin units at the level's own price.

        Config keys used:
            ladder_buy_century_offsets / ladder_sell_century_offsets
            ladder_buy_snaps           / ladder_sell_snaps
            ladder_qty_multipliers     / order_usdt_amount / qty_precision

        Raises ValueError if offsets and multipliers differ in length.
        """
        is_buy: bool = (signal == Signal.BUY)
        offsets: List[int] = BINANCE_PERPETUAL_CONFIG[
            "ladder_buy_century_offsets" if is_buy else "ladder_sell_century_offsets"
        ]
        snaps: List[int] = BINANCE_PERPETUAL_CONFIG[
            "ladder_buy_snaps" if is_buy else "ladder_sell_snaps"
        ]
        multipliers: List[int] = BINANCE_PERPETUAL_CONFIG["ladder_qty_multipliers"]
        order_usdt_amount: float = BINANCE_PERPETUAL_CONFIG.get("order_usdt_amount", 200.0)
        qty_precision: int = BINANCE_PERPETUAL_CONFIG.get("qty_precision", 3)

        if len(offsets) != len(multipliers):
            raise ValueError(
                f"_build_ladder_levels: length mismatch — "
                f"offsets={len(offsets)} multipliers={len(multipliers)}. "
                "Ensure ladder_*_century_offsets and ladder_qty_multipliers have the same length."
            )

        entry_century: int = int(entry_price // 100)
        levels: List[tuple] = []
        for i, offset in enumerate(offsets):
            century = entry_century - offset if is_buy else entry_century + offset
            snap = snaps[i % 2]
            price = float(century * 100 + snap)
            qty = round((order_usdt_amount * multipliers[i]) / price, qty_precision)
            levels.append((price, qty))
        return levels

    def _place_orders_batch(self, symbol: str, order_dicts: List[dict]) -> List[TradeResult]:
        """
        Submit a list of order dicts via POST /fapi/v1/batchOrders in chunks of 5 (API limit).
        Strips None values and injects a fresh timestamp per chunk.
        Each response entry is either a full order object (success) or
        {"code":..., "msg":...} (error) — both are parsed into TradeResult.
        Returns the flat List[TradeResult] in the original input order.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Place-Multiple-Orders
        """
        results: List[TradeResult] = []

        def _parse(raw: dict) -> TradeResult:
            if "code" in raw:
                self.logger.error(f"_place_orders_batch: order rejected for {symbol}: {raw}")
                return TradeResult(status="ERROR", symbol=symbol)
            return TradeResult.from_binance_response(raw)

        for i in range(0, len(order_dicts), 5):
            chunk = [{k: v for k, v in o.items() if v is not None} for o in order_dicts[i:i + 5]]
            params = {
                "batchOrders": json.dumps(chunk),
                "timestamp": self._now_ms(),
            }
            params = self._sign_params(params)
            try:
                resp = requests.post(
                    self.base_url + BINANCE_PERPETUAL_CONFIG["batch_orders_endpoint"],
                    headers=self._build_headers(),
                    data=params,
                )
                resp.raise_for_status()
                results.extend(_parse(raw) for raw in resp.json())
            except Exception as e:
                self.logger.error(f"_place_orders_batch: chunk {i // 5 + 1} failed for {symbol}: {e}")
                results.extend(TradeResult(status="ERROR", symbol=symbol) for _ in chunk)

        return results

    def _fetch_open_orders(self, symbol: str) -> List[dict]:
        """
        Fetch all open orders for symbol via GET /fapi/v1/openOrders.
        Returns the raw list of order dicts. Returns empty list on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-All-Open-Orders
        """
        params = {"symbol": symbol, "timestamp": self._now_ms()}
        params = self._sign_params(params)
        try:
            resp = requests.get(
                self.base_url + BINANCE_PERPETUAL_CONFIG["open_orders_endpoint"],
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.warning(f"_fetch_open_orders failed for {symbol}: {e}")
            return []

    def _cancel_orders_by_ids(self, symbol: str, order_ids: List[int], caller: str = "") -> int:
        """
        Cancel a list of order IDs via DELETE /fapi/v1/batchOrders in chunks of 10 (API limit).
        Returns the count of successfully cancelled orders.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Multiple-Orders
        """
        if not order_ids:
            return 0
        cancelled = 0
        for i in range(0, len(order_ids), 10):
            chunk = order_ids[i:i + 10]
            params = {
                "symbol": symbol,
                "orderIdList": json.dumps(chunk),
                "timestamp": self._now_ms(),
            }
            params = self._sign_params(params)
            try:
                resp = requests.delete(
                    self.base_url + BINANCE_PERPETUAL_CONFIG["batch_orders_endpoint"],
                    headers=self._build_headers(content_type=False),
                    params=params,
                )
                resp.raise_for_status()
                for result in resp.json():
                    if "orderId" in result:
                        cancelled += 1
                    else:
                        self.logger.warning(
                            f"{caller}: could not cancel order for {symbol}: {result}"
                        )
            except Exception as e:
                self.logger.error(
                    f"{caller}: batch cancel failed for {symbol} chunk {chunk}: {e}"
                )
        return cancelled

    def _cancel_tp_sl_orders(self, symbol: str) -> int:
        """
        Cancel all open CONDITIONAL algo TP/SL orders (TAKE_PROFIT_MARKET and
        STOP_MARKET) for the symbol.  These are algo orders so they are fetched
        from GET /fapi/v1/openAlgoOrders and cancelled via DELETE /fapi/v1/algoOrder.
        Returns the number of successfully cancelled orders.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-All-Algo-Open-Orders
             https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Algo-Order
        """
        tp_sl_types = {OrderType.TAKE_PROFIT_MARKET.value, OrderType.STOP_MARKET.value}
        open_algo_orders = self._fetch_open_algo_orders(symbol)
        tp_sl_algo_ids: List[int] = [
            o["algoId"] for o in open_algo_orders if o.get("orderType") in tp_sl_types
        ]
        if not tp_sl_algo_ids:
            self.logger.info(f"No existing TP/SL algo orders to cancel for {symbol}")
            return 0
        self.logger.info(
            f"Cancelling {len(tp_sl_algo_ids)} TP/SL algo order(s) for {symbol}: {tp_sl_algo_ids}"
        )
        return sum(1 for algo_id in tp_sl_algo_ids if self._cancel_algo_order(symbol, algo_id))

    def _cancel_ladder_orders(self, symbol: str) -> int:
        """
        Cancel all open LIMIT orders for the symbol (unfilled ladder entries).
        Called when ladder_order_max_wait elapses inside _monitor_ladder.
        Returns the number of successfully cancelled orders.
        """
        open_orders = self._fetch_open_orders(symbol)
        limit_ids: List[int] = [
            o["orderId"] for o in open_orders if o.get("type") == OrderType.LIMIT
        ]
        if not limit_ids:
            self.logger.info(f"No open LIMIT orders to cancel for {symbol}")
            return 0
        self.logger.info(f"Cancelling {len(limit_ids)} LIMIT order(s) for {symbol}: {limit_ids}")
        return self._cancel_orders_by_ids(symbol, limit_ids, "_cancel_ladder_orders")

    def _get_open_limit_order_ids(self, symbol: str) -> List[int]:
        """Return the orderId list of all open LIMIT orders for the symbol."""
        return [
            o["orderId"]
            for o in self._fetch_open_orders(symbol)
            if o.get("type") == OrderType.LIMIT
        ]

    def _get_open_tp_sl_order_ids(self, symbol: str) -> List[int]:
        """Return the algoId list of all open TAKE_PROFIT_MARKET and STOP_MARKET algo orders."""
        tp_sl_types = {OrderType.TAKE_PROFIT_MARKET.value, OrderType.STOP_MARKET.value}
        return [
            o["algoId"]
            for o in self._fetch_open_algo_orders(symbol)
            if o.get("orderType") in tp_sl_types
        ]

    def _fetch_position_risk(self, symbol: str) -> List[dict]:
        """
        Fetch the raw position risk list for ``symbol`` via GET /fapi/v2/positionRisk.
        Returns the list of position dicts on success, or an empty list on failure.
        Shared by ``_get_position_info``, ``_get_opposite_side_qty``, and
        ``_get_same_side_position`` to avoid duplicate API calls.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V2
        """
        params = {"symbol": symbol, "timestamp": self._now_ms()}
        params = self._sign_params(params)
        try:
            resp = requests.get(
                self.base_url + BINANCE_PERPETUAL_CONFIG["position_risk_endpoint"],
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.warning(
                f"_fetch_position_risk: could not fetch positionRisk for {symbol}: {e}. "
                "Returning empty list."
            )
            return []

    def _get_position_info(self, symbol: str) -> tuple:
        """
        Query the current open position via GET /fapi/v2/positionRisk.
        Returns (qty, avg_entry_price) where qty = abs(positionAmt).
        Raises ValueError if no non-zero position is found (nothing to hedge).
        Raises RuntimeError on request failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Position-Information-V2
        """
        positions = self._fetch_position_risk(symbol)
        if not positions:
            raise RuntimeError(
                f"_get_position_info: failed to fetch position risk for {symbol}"
            )

        for pos in positions:
            qty = abs(float(pos.get("positionAmt", 0)))
            if qty > 0:
                avg_entry_price = float(pos.get("entryPrice", 0))
                return qty, avg_entry_price

        raise ValueError(
            f"_get_position_info: no open position found for {symbol}. "
            "Ensure the main order is fully filled before placing a bracket."
        )

    def _close_diverged_same_side_position(
        self,
        symbol: str,
        signal: str,
        entry_price: float,
        positions: List[dict],
    ) -> None:
        """
        Close an existing same-side position with a reduceOnly MARKET order when
        its average entry price differs from ``entry_price`` by more than
        ``same_side_price_level_diff`` (config, default 100).

        Does nothing if:
          - no same-side position exists, or
          - the price difference is within the configured tolerance.

        Called from ``place_order`` using the pre-fetched ``positions`` list so
        no additional API call is needed.
        """
        same_side_level_diff: float = BINANCE_PERPETUAL_CONFIG.get("same_side_price_level_diff", 100.0)
        same_side_qty, same_side_avg = self._get_same_side_position(signal, positions)
        if same_side_qty <= 0:
            return

        price_diff = abs(same_side_avg - entry_price)
        if price_diff > same_side_level_diff:
            self.logger.warning(
                f"_close_diverged_same_side_position: same-side avg_entry={same_side_avg} "
                f"diverges from new entry={entry_price} by {price_diff:.2f} > "
                f"{same_side_level_diff} for {symbol} — "
                f"closing qty={same_side_qty} with market order before placing new ladder."
            )
            self._place_single_order({
                "symbol": symbol,
                "side": get_reversal_signal(signal),
                "type": OrderType.MARKET,
                "quantity": str(same_side_qty),
                "reduceOnly": "true",
            })
        else:
            self.logger.info(
                f"_close_diverged_same_side_position: same-side avg_entry={same_side_avg} "
                f"is within {same_side_level_diff} of new entry={entry_price} "
                f"(diff={price_diff:.2f}) for {symbol} — keeping position open."
            )

    def _get_opposite_side_qty(self, signal: str, positions: List[dict]) -> float:
        """
        Return the absolute quantity of any open position on the **opposite** side
        from ``signal``.  Used by ``place_order`` to size the first ladder order so
        that it simultaneously closes the existing counter-position and opens the new
        one in a single net-settling LIMIT order (no ``reduceOnly`` needed).

        Logic:
            positionAmt > 0  → currently LONG  (BUY side)
            positionAmt < 0  → currently SHORT (SELL side)
            signal = BUY  → opposite is SHORT → return abs(positionAmt) if positionAmt < 0
            signal = SELL → opposite is LONG  → return positionAmt       if positionAmt > 0

        ``positions`` is the pre-fetched list from ``_fetch_position_risk`` so that
        ``place_order`` only calls the API once for both position queries.

        Returns 0.0 if there is no position, if the existing position is on the same
        side, or if the list is empty — so the caller always gets a safe addend.
        """
        is_buy: bool = (signal == Signal.BUY)
        for pos in positions:
            signed_qty: float = float(pos.get("positionAmt", 0))
            if is_buy and signed_qty < 0:
                # We are going BUY; existing SHORT needs to be absorbed
                return abs(signed_qty)
            if not is_buy and signed_qty > 0:
                # We are going SELL; existing LONG needs to be absorbed
                return signed_qty
        return 0.0

    def _get_same_side_position(self, signal: str, positions: List[dict]) -> tuple:
        """
        Return (qty, avg_entry_price) of any open position on the **same** side as
        ``signal``, or (0.0, 0.0) if none exists.

        Logic:
            positionAmt > 0  → currently LONG  (BUY side)
            positionAmt < 0  → currently SHORT (SELL side)
            signal = BUY  → same side if positionAmt > 0
            signal = SELL → same side if positionAmt < 0

        ``positions`` is the pre-fetched list from ``_fetch_position_risk`` so that
        ``place_order`` only calls the API once for both position queries.
        """
        is_buy: bool = (signal == Signal.BUY)
        for pos in positions:
            signed_qty: float = float(pos.get("positionAmt", 0))
            if is_buy and signed_qty > 0:
                return signed_qty, float(pos.get("entryPrice", 0))
            if not is_buy and signed_qty < 0:
                return abs(signed_qty), float(pos.get("entryPrice", 0))
        return 0.0, 0.0

    def _place_tp_sl_batch(
        self,
        symbol: str,
        quantity: float,
        tp_price: float,
        sl_price: float,
        side: str,
    ) -> tuple:
        """
        Place TAKE_PROFIT_MARKET and STOP_MARKET orders via POST /fapi/v1/algoOrder
        (algoType=CONDITIONAL).  /fapi/v1/order rejects these types with -4120.

        Key difference from regular orders:
          • endpoint  : /fapi/v1/algoOrder (not /fapi/v1/order or batchOrders)
          • trigger   : triggerPrice       (not stopPrice)
          • id field  : algoId             (not orderId)

        Returns (tp_result, sl_result) as TradeResult objects where order_id holds
        the algoId.  Caller must check result.order_id to detect placement failures.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order
        """
        # Round to the symbol's tick size before serialising to string.
        # Float arithmetic (avg_entry ± diff) produces values like 80365.829999...
        # which exceed BTCUSDT's 1-decimal tick precision and cause -1111.
        price_precision: int = BINANCE_PERPETUAL_CONFIG.get("price_precision", 1)
        tp_price_str = str(round(tp_price, price_precision))
        sl_price_str = str(round(sl_price, price_precision))

        tp_result = self._place_algo_order({
            "algoType": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "type": OrderType.TAKE_PROFIT_MARKET,
            "quantity": str(quantity),
            "triggerPrice": tp_price_str,
            "reduceOnly": "true",
        })
        # If TP already triggered, skip placing SL — the monitor will resolve immediately.
        if tp_result.status == OrderStatus.WOULD_TRIGGER:
            self.logger.warning(
                f"_place_tp_sl_batch: TP triggerPrice={tp_price_str} already triggered for "
                f"{symbol} — skipping SL placement"
            )
            return tp_result, TradeResult(status=OrderStatus.WOULD_TRIGGER, symbol=symbol)

        sl_result = self._place_algo_order({
            "algoType": "CONDITIONAL",
            "symbol": symbol,
            "side": side,
            "type": OrderType.STOP_MARKET,
            "quantity": str(quantity),
            "triggerPrice": sl_price_str,
            "reduceOnly": "true",
        })
        # Symmetrical guard: if SL already triggered, cancel the live TP and short-circuit.
        if sl_result.status == OrderStatus.WOULD_TRIGGER:
            self.logger.warning(
                f"_place_tp_sl_batch: SL triggerPrice={sl_price_str} already triggered for "
                f"{symbol} — cancelling TP and short-circuiting"
            )
            if tp_result.order_id:
                self._cancel_algo_order(symbol, tp_result.order_id)
            return TradeResult(status=OrderStatus.WOULD_TRIGGER, symbol=symbol), sl_result

        return tp_result, sl_result

    def _place_algo_order(self, order_dict: dict) -> TradeResult:
        """
        Place a conditional algo order via POST /fapi/v1/algoOrder.

        Required for TAKE_PROFIT_MARKET and STOP_MARKET — /fapi/v1/order returns
        -4120 for these types and redirects to the algo endpoint.

        Normalises enum values to plain strings before signing to avoid the
        str(Enum) repr issue on Python < 3.11.  Stores algoId as order_id and
        algoStatus as status in the returned TradeResult so that _monitor_ladder
        can treat it identically to a regular order result.

        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/New-Algo-Order
        """
        symbol = order_dict.get("symbol", "")
        params = {
            k: (v.value if isinstance(v, Enum) else v)
            for k, v in order_dict.items()
            if v is not None
        }
        params["timestamp"] = self._now_ms()
        params = self._sign_params(params)
        query_string = urlencode(params)
        try:
            resp = requests.post(
                self.base_url + "/fapi/v1/algoOrder?" + query_string,
                headers=self._build_headers(content_type=False),
            )
            raw = resp.json()
            # -2021: triggerPrice condition already satisfied — market moved past it.
            # Return WOULD_TRIGGER so the caller can resolve the bracket outcome immediately.
            if isinstance(raw.get("code"), int) and raw["code"] == -2021:
                self.logger.warning(
                    f"_place_algo_order: triggerPrice={order_dict.get('triggerPrice')} already "
                    f"met for {symbol} (price passed trigger before order landed) — "
                    f"returning WOULD_TRIGGER"
                )
                return TradeResult(status=OrderStatus.WOULD_TRIGGER, symbol=symbol)
            # All other negative codes are hard errors
            if isinstance(raw.get("code"), int) and raw["code"] < 0:
                self.logger.error(
                    f"_place_algo_order: rejected for {symbol} [HTTP {resp.status_code}]: {raw}"
                )
                return TradeResult(status="ERROR", symbol=symbol)
            # Map algo-specific fields → TradeResult via dedicated factory
            return TradeResult.from_algo_response(raw)
        except Exception as e:
            self.logger.error(f"_place_algo_order: request failed for {symbol}: {e}")
            return TradeResult(status="ERROR", symbol=symbol)

    def _place_single_order(self, order_dict: dict) -> TradeResult:
        """
        Place a single order via POST /fapi/v1/order.
        Used for order types not supported by /fapi/v1/batchOrders
        (e.g. TAKE_PROFIT_MARKET, STOP_MARKET).
        Returns a TradeResult; status="ERROR" on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Place-New-Order
        """
        symbol = order_dict.get("symbol", "")
        # Normalise enum values to their plain string .value so that urlencode
        # does not call str(enum) which produces "OrderType.TAKE_PROFIT_MARKET"
        # instead of "TAKE_PROFIT_MARKET" on Python < 3.11.
        params = {
            k: (v.value if isinstance(v, Enum) else v)
            for k, v in order_dict.items()
            if v is not None
        }
        params["timestamp"] = self._now_ms()
        params = self._sign_params(params)
        # Build the query string directly so the byte sequence sent to Binance
        # is identical to the one that was signed — avoids any dict-ordering or
        # re-encoding mismatch that causes -1022.
        query_string = urlencode(params)
        try:
            resp = requests.post(
                self.base_url + "/fapi/v1/order?" + query_string,
                headers=self._build_headers(content_type=False),
            )
            raw = resp.json()
            if "code" in raw:
                self.logger.error(
                    f"_place_single_order: order rejected for {symbol} "
                    f"[HTTP {resp.status_code}]: {raw}"
                )
                return TradeResult(status="ERROR", symbol=symbol)
            return TradeResult.from_binance_response(raw)
        except Exception as e:
            self.logger.error(f"_place_single_order: request failed for {symbol}: {e}")
            return TradeResult(status="ERROR", symbol=symbol)

    def _monitor_ladder(
        self,
        symbol: str,
        signal: str,
        time_simulator: Optional[TimeSimulator] = None,
    ) -> OcoOutcome:
        """
        Unified monitoring loop that drives the full DCA bracket lifecycle.

        Responsibilities
        ----------------
        1. **LIMIT timeout** — when ``ladder_order_max_wait`` elapses without a
           bracket being placed, cancel all remaining LIMIT orders and wait for
           any active bracket to resolve (or break if none exists).
        2. **Position tracking** — poll ``_get_position_info`` each cycle.
           Whenever the filled quantity increases, fetch the actual average entry
           price from positionRisk, recalculate TP/SL using the same diff formula
           as ``orchestrate_bracket_order``, tear down stale TP/SL orders and
           re-place a fresh bracket via ``_place_tp_sl_batch``.
        3. **Inline OCO check** — once a bracket is live, query both the TP and
           SL orders every cycle.  On a fill, cancel the loser and record the
           outcome.  Option B: surviving LIMIT orders are *not* cancelled; they
           can still fill and trigger the next bracket re-placement.
        4. **Exit condition** — loop terminates only when *both*
           ``_get_open_limit_order_ids`` and ``_get_open_tp_sl_order_ids``
           return empty lists.

        Time control
        ------------
        When ``time_simulator`` is provided and in replay mode:
          - ``time_simulator.advance()`` steps the simulated clock forward by
            ``interval_seconds`` instead of a real ``time.sleep()``.
          - ``elapsed`` is derived from ``(get_current_time() - loop_start).total_seconds()``
            so timeouts are driven by simulated time, not wall-clock time.
        When ``time_simulator`` is None or in live mode, real ``time.sleep()`` is
        used and ``elapsed`` is accumulated by ``poll_interval`` as before.

        Returns
        -------
        OcoOutcome
            TP_FILLED / SL_FILLED / EXTERNAL_TERMINAL if a bracket resolved, or
            TIMEOUT if ``oco_max_wait`` elapsed first (rare safety guard).
        """
        poll_interval: int = BINANCE_PERPETUAL_CONFIG.get("poll_interval", 2)
        ladder_max_wait: int = BINANCE_PERPETUAL_CONFIG.get("ladder_order_max_wait", 900)
        oco_max_wait: int = BINANCE_PERPETUAL_CONFIG.get("oco_max_wait", 3600)
        tp_price_diff: float = BINANCE_PERPETUAL_CONFIG.get("tp_price_diff")
        sl_price_diff: float = BINANCE_PERPETUAL_CONFIG.get("sl_price_diff")
        terminal_statuses = {OrderStatus.CANCELED, OrderStatus.EXPIRED}

        # Time-control setup: replay mode skips real sleep and drives elapsed via
        # simulated clock; live mode (time_simulator=None) uses time.sleep as before.
        is_replay: bool = time_simulator is not None and time_simulator.is_replay_mode()
        loop_start = time_simulator.get_current_time() if is_replay else None
        last_sim_time = loop_start

        # Reversal side: BUY position is exited with SELL orders and vice-versa.
        reversal_side: str = get_reversal_signal(signal)
        is_buy: bool = (signal == Signal.BUY)

        last_qty: float = 0.0
        tp_result: Optional[TradeResult] = None
        sl_result: Optional[TradeResult] = None
        oco_outcome: Optional[OcoOutcome] = None

        elapsed: int = 0
        ladder_cancelled: bool = False

        while True:
            # --- Time advance / sleep ---
            if is_replay:
                current_sim_time = time_simulator.get_current_time()
                if current_sim_time == last_sim_time:
                    self.logger.warning(
                        f"_monitor_ladder: simulated time has not advanced "
                        f"(still {current_sim_time}) — outer loop may have stalled. "
                        f"Sleeping {poll_interval}s before retrying."
                    )
                    time_simulator.advance()
                    continue

                elapsed = int((current_sim_time - loop_start).total_seconds())
                last_sim_time = current_sim_time
            else:
                time.sleep(poll_interval)
                elapsed += poll_interval

            # ── 1. LIMIT timeout ───────────────────────────────────────────
            if not ladder_cancelled and elapsed >= ladder_max_wait:
                self.logger.info(
                    f"_monitor_ladder: ladder timeout after {elapsed}s — "
                    f"cancelling remaining LIMIT orders for {symbol}"
                )
                self._cancel_ladder_orders(symbol)
                ladder_cancelled = True

            # ── 2. Position quantity tracking ─────────────────────────────
            try:
                current_qty, avg_entry_price = self._get_position_info(symbol)
            except ValueError:
                current_qty, avg_entry_price = 0.0, 0.0
            except RuntimeError as e:
                self.logger.warning(f"_monitor_ladder: position query error: {e}")
                current_qty = last_qty  # keep last known so we don't spuriously reset
                avg_entry_price = 0.0

            if current_qty != last_qty and current_qty > 0:
                # Recalculate TP/SL from the actual average fill price
                tp_price = (
                    avg_entry_price + tp_price_diff
                    if is_buy
                    else avg_entry_price - tp_price_diff
                )
                sl_price = (
                    avg_entry_price - sl_price_diff
                    if is_buy
                    else avg_entry_price + sl_price_diff
                )
                self.logger.info(
                    f"_monitor_ladder: qty changed {last_qty} → {current_qty} for {symbol} | "
                    f"avg_entry={avg_entry_price} TP={tp_price} SL={sl_price}. Re-placing bracket."
                )
                self._cancel_tp_sl_orders(symbol)
                tp_result, sl_result = self._place_tp_sl_batch(
                    symbol, current_qty, tp_price, sl_price, reversal_side
                )
                last_qty = current_qty
                oco_outcome = None  # reset so we poll the new bracket

                # ── Immediate-trigger guard ─────────────────────────────
                # -2021: market already past triggerPrice at placement time.
                # Resolve the bracket outcome now without waiting for the poll loop.
                if tp_result and tp_result.status == OrderStatus.WOULD_TRIGGER:
                    self.logger.warning(
                        f"_monitor_ladder: TP triggerPrice {tp_price} already met for {symbol} "
                        f"— treating as TP_FILLED and cancelling SL"
                    )
                    if sl_result and sl_result.order_id:
                        self._cancel_algo_order(symbol, sl_result.order_id)
                    oco_outcome = OcoOutcome.TP_FILLED
                    tp_result = sl_result = None
                elif sl_result and sl_result.status == OrderStatus.WOULD_TRIGGER:
                    self.logger.warning(
                        f"_monitor_ladder: SL triggerPrice {sl_price} already met for {symbol} "
                        f"— treating as SL_FILLED and cancelling TP"
                    )
                    if tp_result and tp_result.order_id:
                        self._cancel_algo_order(symbol, tp_result.order_id)
                    oco_outcome = OcoOutcome.SL_FILLED
                    tp_result = sl_result = None

            # ── 3. Inline OCO check ────────────────────────────────────────
            if tp_result and sl_result and tp_result.order_id and sl_result.order_id:
                tp_order = self._query_algo_order(symbol, tp_result.order_id)
                sl_order = self._query_algo_order(symbol, sl_result.order_id)
                tp_status: OrderStatus = tp_order.status if tp_order else OrderStatus.UNKNOWN
                sl_status: OrderStatus = sl_order.status if sl_order else OrderStatus.UNKNOWN

                self.logger.debug(
                    f"_monitor_ladder OCO [{elapsed}s]: TP={tp_status} SL={sl_status}"
                )

                if tp_status == OrderStatus.FILLED:
                    self.logger.info(
                        f"TP algo order {tp_result.order_id} FILLED — cancelling SL"
                    )
                    self._cancel_algo_order(symbol, sl_result.order_id)
                    oco_outcome = OcoOutcome.TP_FILLED
                    tp_result = sl_result = None

                elif sl_status == OrderStatus.FILLED:
                    self.logger.info(
                        f"SL algo order {sl_result.order_id} FILLED — cancelling TP"
                    )
                    self._cancel_algo_order(symbol, tp_result.order_id)
                    oco_outcome = OcoOutcome.SL_FILLED
                    tp_result = sl_result = None

                elif tp_status in terminal_statuses or sl_status in terminal_statuses:
                    self.logger.warning(
                        f"_monitor_ladder: external terminal — TP={tp_status} SL={sl_status}. "
                        "Cancelling any non-terminal bracket algo orders."
                    )
                    if tp_status not in terminal_statuses:
                        self._cancel_algo_order(symbol, tp_result.order_id)
                    if sl_status not in terminal_statuses:
                        self._cancel_algo_order(symbol, sl_result.order_id)
                    oco_outcome = OcoOutcome.EXTERNAL_TERMINAL
                    tp_result = sl_result = None

            # ── 4. Exit condition ──────────────────────────────────────────
            open_limits = self._get_open_limit_order_ids(symbol)
            open_tp_sl = self._get_open_tp_sl_order_ids(symbol)
            if not open_limits and not open_tp_sl:
                self.logger.info(
                    f"_monitor_ladder: no open orders remain for {symbol}. Exiting loop."
                )
                break

            # ── 5. Overall safety timeout ──────────────────────────────────
            if elapsed >= oco_max_wait:
                self.logger.warning(
                    f"_monitor_ladder: overall timeout ({oco_max_wait}s) reached for {symbol}. "
                    "Cancelling all remaining orders and closing any open position."
                )
                self._cancel_ladder_orders(symbol)
                self._cancel_tp_sl_orders(symbol)
                # Close any residual open position with a market order
                try:
                    pos_qty, _ = self._get_position_info(symbol)
                    if pos_qty > 0:
                        self.logger.warning(
                            f"_monitor_ladder: open position qty={pos_qty} found for {symbol} "
                            "after timeout — closing with market order."
                        )
                        self._place_single_order({
                            "symbol": symbol,
                            "side": reversal_side,
                            "type": OrderType.MARKET,
                            "quantity": str(pos_qty),
                            "reduceOnly": "true",
                        })
                except ValueError:
                    self.logger.info(
                        f"_monitor_ladder: no open position to close for {symbol} at timeout."
                    )
                except Exception as e:
                    self.logger.error(
                        f"_monitor_ladder: failed to close position for {symbol} at timeout: {e}"
                    )
                return OcoOutcome.TIMEOUT

        return oco_outcome or OcoOutcome.TIMEOUT

    def _query_order(self, symbol: str, order_id: int) -> Optional[TradeResult]:
        """
        Fetch the full current snapshot of an order via GET /fapi/v1/order.
        Returns a TradeResult with all fields populated (including status, avg_price,
        executed_qty, etc.) so a single call serves both status checks and data reads.
        Returns None on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Query-Order
        """
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": self._now_ms(),
        }
        params = self._sign_params(params)
        try:
            resp = requests.get(
                self.base_url + "/fapi/v1/order",
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            return TradeResult.from_binance_response(resp.json())
        except Exception as e:
            self.logger.warning(f"_query_order failed for order {order_id} ({symbol}): {e}")
            return None

    def _cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        Cancel an open order via DELETE /fapi/v1/order.
        Returns True on success, False on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Order
        """
        params = {
            "symbol": symbol,
            "orderId": order_id,
            "timestamp": self._now_ms(),
        }
        params = self._sign_params(params)
        try:
            resp = requests.delete(
                self.base_url + "/fapi/v1/order",
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            self.logger.info(f"Order {order_id} cancelled successfully for {symbol}")
            return True
        except Exception as e:
            self.logger.error(f"_cancel_order failed for order {order_id} ({symbol}): {e}")
            return False

    def _fetch_open_algo_orders(self, symbol: str) -> List[dict]:
        """
        Fetch all open CONDITIONAL algo orders for a symbol via GET /fapi/v1/openAlgoOrders.
        Returns the raw list of algo order dicts. Returns empty list on failure.
        Algo orders (TAKE_PROFIT_MARKET, STOP_MARKET) do NOT appear in the regular
        /fapi/v1/openOrders endpoint — this is their dedicated listing endpoint.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Current-All-Algo-Open-Orders
        """
        params = {
            "symbol": symbol,
            "algoType": "CONDITIONAL",
            "timestamp": self._now_ms(),
        }
        params = self._sign_params(params)
        try:
            resp = requests.get(
                self.base_url + "/fapi/v1/openAlgoOrders",
                headers=self._build_headers(content_type=False),
                params=params,
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            self.logger.warning(f"_fetch_open_algo_orders failed for {symbol}: {e}")
            return []

    def _query_algo_order(self, symbol: str, algo_id: int) -> Optional[TradeResult]:
        """
        Query an algo order via GET /fapi/v1/algoOrder.
        Maps algoStatus → OrderStatus so _monitor_ladder can use the same comparisons
        it uses for regular orders:
            NEW / WORKING → OrderStatus.NEW
            FILLED        → OrderStatus.FILLED
            CANCELLED     → OrderStatus.CANCELED  (Binance double-L → single-L)
            EXPIRED       → OrderStatus.EXPIRED
        Returns None on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Query-Algo-Order
        """
        params = {
            "algoId": algo_id,
            "timestamp": self._now_ms(),
        }
        params = self._sign_params(params)
        query_string = urlencode(params)
        try:
            resp = requests.get(
                self.base_url + "/fapi/v1/algoOrder?" + query_string,
                headers=self._build_headers(content_type=False),
            )
            resp.raise_for_status()
            raw = resp.json()
            result = TradeResult.from_algo_response(raw)
            # Normalise CANCELLED (Binance double-L) → CANCELED (single-L, matches OrderStatus enum)
            if result.status == "CANCELLED":
                result.status = OrderStatus.CANCELED
            # Map WORKING → NEW so _monitor_ladder comparisons work uniformly
            elif result.status == "WORKING":
                result.status = OrderStatus.NEW
            return result
        except Exception as e:
            self.logger.warning(f"_query_algo_order failed for algo {algo_id} ({symbol}): {e}")
            return None

    def _cancel_algo_order(self, symbol: str, algo_id: int) -> bool:
        """
        Cancel an active algo order via DELETE /fapi/v1/algoOrder.
        Returns True on success, False on failure.
        Ref: https://developers.binance.com/docs/derivatives/usds-margined-futures/trade/rest-api/Cancel-Algo-Order
        """
        params = {
            "algoId": algo_id,
            "timestamp": self._now_ms(),
        }
        params = self._sign_params(params)
        query_string = urlencode(params)
        try:
            resp = requests.delete(
                self.base_url + "/fapi/v1/algoOrder?" + query_string,
                headers=self._build_headers(content_type=False),
            )
            raw = resp.json()
            # Success response: {"algoId": ..., "code": "200", "msg": "success"}
            if raw.get("msg") == "success" or str(raw.get("code")) == "200":
                self.logger.info(f"Algo order {algo_id} cancelled successfully for {symbol}")
                return True
            # -2011: order already gone — treat as success (idempotent cancel)
            if raw.get("code") == -2011:
                self.logger.info(
                    f"_cancel_algo_order: algo {algo_id} ({symbol}) already gone (−2011), treating as success."
                )
                return True
            self.logger.warning(
                f"_cancel_algo_order: unexpected response for algo {algo_id} ({symbol}): {raw}"
            )
            return False
        except Exception as e:
            self.logger.error(f"_cancel_algo_order failed for algo {algo_id} ({symbol}): {e}")
            return False

    def _ensure_leverage(self, symbol: str):
        """
        Set leverage for the symbol once per process lifetime.
        Uses the class-level ``_leveraged_symbols`` set so the API call is
        skipped on every subsequent invocation for the same symbol, regardless
        of which instance calls this method.
        """
        if symbol in BinancePerpetualTrading._leveraged_symbols:
            return
        leverage = BINANCE_PERPETUAL_CONFIG.get("default_leverage", 20)
        try:
            self._set_leverage(symbol, leverage)
            BinancePerpetualTrading._leveraged_symbols.add(symbol)
        except Exception as e:
            self.logger.warning(f"Could not set leverage for {symbol}: {e}. Proceeding anyway.")

    def _set_leverage(self, symbol: str, leverage: int):
        """
        Set leverage for a symbol via POST /fapi/v1/leverage.
        Retries up to 3 times before raising an exception.
        """
        url = self.base_url + "/fapi/v1/leverage"
        headers = self._build_headers(content_type=False)
        params = {"symbol": symbol, "leverage": leverage}
        last_exception = None

        for attempt in range(3):
            self.logger.info(f"Attempt {attempt + 1}/3: Setting leverage {leverage} for {symbol}")
            params["timestamp"] = self._now_ms()
            params = self._sign_params(params)
            try:
                response = requests.post(url, headers=headers, params=params)
                response.raise_for_status()
                resp_json = response.json()
                if str(resp_json.get("leverage")) == str(leverage):
                    self.logger.info(f"Leverage {leverage} set for {symbol} on attempt {attempt + 1}")
                    return resp_json
                last_exception = Exception(
                    f"Leverage mismatch for {symbol}: requested {leverage}, got {resp_json.get('leverage')}"
                )
                self.logger.warning(str(last_exception))
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Attempt {attempt + 1}: _set_leverage failed for {symbol}: {e}")
            time.sleep(1)

        self.logger.error(f"Failed to set leverage for {symbol} after 3 attempts: {last_exception}")
        raise Exception(f"Failed to set leverage for {symbol} after 3 attempts: {last_exception}")

    def _resolve_base_url(self, time_simulator: Optional[TimeSimulator] = None) -> None:
        """
        Resolve and assign all connection-related instance attributes.

        Sets:
          - ``self.use_demo``   — whether the demo/paper-trading endpoint is active
          - ``self.api_key``    — selected based on active mode
          - ``self.api_secret`` — selected based on active mode
          - ``self.base_url``   — selected REST base URL per this decision matrix:

              | use_demo | is_replay | base_url       | keys             |
              |----------|-----------|----------------|------------------|
              | False    | False     | base_url       | live keys        |
              | True     | any       | demo_base_url  | demo keys        |
              | any      | True      | demo_base_url  | demo keys        |

        Called once from ``__init__`` (no ``time_simulator``) for cold-start setup,
        and again at the top of ``orchestrate_bracket_order`` with the live
        ``time_simulator`` so that the correct endpoint is locked in for the
        full orchestration run.
        """
        self.use_demo: bool = BINANCE_PERPETUAL_CONFIG.get("use_demo", False)
        is_replay: bool = time_simulator is not None and time_simulator.is_replay_mode()

        if not self.use_demo and not is_replay:
            self.api_key: str = BINANCE_PERPETUAL_CONFIG["api_key"]
            self.api_secret: str = BINANCE_PERPETUAL_CONFIG["api_secret"]
            self.base_url: str = BINANCE_PERPETUAL_CONFIG["base_url"]
        else:
            self.api_key: str = BINANCE_PERPETUAL_CONFIG["demo_api_key"]
            self.api_secret: str = BINANCE_PERPETUAL_CONFIG["demo_api_secret"]
            self.base_url: str = BINANCE_PERPETUAL_CONFIG["demo_base_url"]

    def _sign_params(self, params: dict) -> dict:
        """
        Add a Binance HMAC-SHA256 signature to the params dict and return it.
        Any stale signature is removed before recomputing to ensure correctness.
        """
        params.pop("signature", None)
        query_string = urlencode(params)
        params["signature"] = hmac.new(
            self.api_secret.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()
        return params

    def _build_headers(self, content_type: bool = True) -> dict:
        """
        Return Binance API request headers.
        Set content_type=False for GET/DELETE requests.
        """
        headers = {"X-MBX-APIKEY": self.api_key}
        if content_type:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        return headers
    
    def _fetch_server_time_offset(self) -> int:
        """
        Query GET /fapi/v1/time and return the difference (ms) between Binance
        server time and local time.

        Used once at construction so that every subsequent ``_now_ms()`` call
        produces a timestamp inside Binance's ``recvWindow``, regardless of how
        much the local system clock drifts.

        Falls back to 0 (no correction) if the request fails so that the
        instance is still usable and the error is logged rather than raised.
        """
        try:
            url = self.base_url + "/fapi/v1/time"
            local_before = int(time.time() * 1000)
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            server_time: int = resp.json()["serverTime"]
            local_after = int(time.time() * 1000)
            # Use the midpoint of the round-trip to minimise network latency bias
            local_midpoint = (local_before + local_after) // 2
            offset = server_time - local_midpoint
            self.logger.info(
                f"Server time sync: serverTime={server_time}, "
                f"localMidpoint={local_midpoint}, offset={offset:+d} ms"
            )
            return offset
        except Exception as e:
            self.logger.warning(
                f"Could not fetch server time offset (falling back to 0 ms): {e}"
            )
            return 0

    def _now_ms(self) -> int:
        """
        Return the current time in milliseconds, corrected by the server time
        offset computed at startup.  Use this everywhere instead of the raw
        ``int(time.time() * 1000)`` so that all signed requests carry a
        server-synchronised timestamp and avoid error -1021.
        """
        return int(time.time() * 1000) + self._server_time_offset_ms

