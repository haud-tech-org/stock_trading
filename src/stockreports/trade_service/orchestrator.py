"""
TradingServiceOrchestrator - Main public API for trading services.

Facade for all trading operations. Exposes only the order book method.
"""

# --- Python Standard Library ---
import logging
import threading
from typing import Optional

# --- Third-Party Libraries ---

# --- Project Imports ---
from src.stockreports.alert.model.models import AlertData
from src.stockreports.model.trading import TradeResult
from src.stockreports.utils.time_utils import TimeSimulator
from ._internal.coordinator import TradingCoordinator

logger = logging.getLogger(__name__)

class TradingServiceOrchestrator:
    """
    Facade for trading operations. Exposes only the public order book methods.
    """
    _coordinator = None  # class-level singleton

    def __init__(self):
        if TradingServiceOrchestrator._coordinator is None:
            TradingServiceOrchestrator._coordinator = TradingCoordinator()

    def place_order(self, alert: AlertData):
        """
        Place a DCA ladder order using the correct trading platform for the alert's symbol.
        Runs in a new daemon thread (fire-and-forget). Does not return anything.
        No-ops silently if no platform is registered for the symbol.
        """
        trading_platform = TradingServiceOrchestrator._coordinator.get_trading_platform(alert)
        if trading_platform is None:
            logger.warning(f"place_order skipped: no platform registered for '{alert.symbol}'.")
            return
        thread = threading.Thread(
            target=trading_platform.place_order,
            args=(alert,),
            daemon=True,
            name=f"trade-ladder-{alert.symbol}",
        )
        thread.start()

    def orchestrate_bracket_order(self, alert: AlertData, time_simulator: Optional[TimeSimulator] = None):
        """
        Run the full DCA ladder + dynamic bracket lifecycle for an alert.

        Delegates to ``BinancePerpetualTrading.orchestrate_bracket_order`` which:
        1. Sets leverage.
        2. Places all DCA ladder LIMIT orders.
        3. Enters ``_monitor_ladder`` — a blocking loop that re-brackets on every
           fill event and exits only when all open orders are gone or the safety
           timeout elapses.

        Because ``_monitor_ladder`` is long-running (up to ``oco_max_wait`` seconds),
        this method dispatches in a dedicated daemon thread so the alerter's main
        monitoring loop is never blocked.

        No-ops silently if no platform is registered for the symbol.

        Args:
            alert: The ``AlertData`` whose ``signal``, ``alert_price``, and
                   ``symbol`` drive order placement.
            time_simulator: Optional ``TimeSimulator`` instance from the alerter's
                   monitoring session.  In replay mode, ``_monitor_ladder`` calls
                   ``advance()`` instead of ``time.sleep()`` so the bracket lifecycle
                   runs at simulated speed.  Pass ``None`` (default) for live trading.
        """
        trading_platform = TradingServiceOrchestrator._coordinator.get_trading_platform(alert)
        if trading_platform is None:
            logger.warning(f"orchestrate_bracket_order skipped: no platform registered for '{alert.symbol}'.")
            return
        thread = threading.Thread(
            target=trading_platform.orchestrate_bracket_order,
            args=(alert,),
            kwargs={"time_simulator": time_simulator},
            daemon=True,
            name=f"trade-bracket-{alert.symbol}",
        )
        thread.start()
