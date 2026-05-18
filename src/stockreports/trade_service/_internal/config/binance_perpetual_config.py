"""
Binance Perpetual Futures Trading Configuration

Contains all configuration for Binance USDT-margined perpetual futures trading,
including API endpoints, default parameters, and query parameter templates for order placement.

SECURITY NOTE:
All sensitive credentials are loaded from secure sources in the following priority order:
1. Environment Variables (production deployments)
2. Secret Management Services (Azure KeyVault, Google Secret Manager)
3. .env File (local development only - NEVER committed to Git)
4. Default values (non-sensitive configuration only)

DO NOT hardcode credentials in this file.
Required environment variables:
  BINANCE_API_KEY          — Live production API key
  BINANCE_API_SECRET       — Live production API secret
  BINANCE_DEMO_API_KEY     — Demo/paper-trading API key
  BINANCE_DEMO_API_SECRET  — Demo/paper-trading API secret
"""

import logging
from src.stockreports.trade_service._internal.model.enums import OrderType, TimeInForce, PositionSide
from src.stockreports.config.secrets_loader import SecretsLoader

logger = logging.getLogger(__name__)

_secrets_loader = SecretsLoader()

_use_demo: bool = True  # reflects the use_demo flag below; used to set required= correctly

BINANCE_PERPETUAL_CONFIG = {
    # Default leverage for all orders (can be overridden per symbol/order)
    "default_leverage": 20,
    # API endpoints
    "base_url": "https://fapi.binance.com",
    "demo_base_url": "https://demo-fapi.binance.com",  # Official demo/paper-trading endpoint (per Binance docs 2025+)
    "order_endpoint": "/fapi/v1/order",
    "open_orders_endpoint": "/fapi/v1/openOrders",
    "batch_orders_endpoint": "/fapi/v1/batchOrders",
    "position_risk_endpoint": "/fapi/v2/positionRisk",
    "use_demo": True,  # Set to True to use the demo/paper-trading endpoint instead of live

    # API keys — two sets: one for live production, one for demo/paper-trading.
    # Loaded securely from environment variables / secret manager (never hardcoded).
    # _resolve_base_url selects the correct pair based on use_demo + is_replay.
    "api_key": _secrets_loader.get_secret(
        "BINANCE_API_KEY",
        default="",
        required=False,
        is_sensitive=True,
    ) or "",
    "api_secret": _secrets_loader.get_secret(
        "BINANCE_API_SECRET",
        default="",
        required=False,
        is_sensitive=True,
    ) or "",
    "demo_api_key": _secrets_loader.get_secret(
        "BINANCE_DEMO_API_KEY",
        default="",
        required=False,
        is_sensitive=True,
    ) or "",
    "demo_api_secret": _secrets_loader.get_secret(
        "BINANCE_DEMO_API_SECRET",
        default="",
        required=False,
        is_sensitive=True,
    ) or "",

    # Default order parameters (can be overridden per request)
    # 'order_usdt_amount' drives quantity calculation: qty = order_usdt_amount / price.
    # This replaces the static 'quantity' field so every LIMIT order is sized in USDT
    # rather than a fixed coin amount, keeping exposure consistent across price levels.
    "order_usdt_amount": 200.0,   # USDT value per individual LIMIT order (order 1 × multiplier[i] for orders 2–N)
    # Decimal places to round computed quantities to before sending to Binance.
    # Must match the symbol's lot-size precision (BTCUSDT = 3 decimal places).
    # Exceeding this causes -1111 "Precision is over the maximum defined for this asset."
    "qty_precision": 3,
    "default_order_params": {
        "symbol": None,  # to be filled dynamically
        "side": None,    # BUY or SELL
        "type": OrderType.LIMIT,  # default to LIMIT, can be overridden
        "quantity": None,  # derived at runtime from order_usdt_amount / price
        "timestamp": None,  # to be filled dynamically
        "timeInForce": TimeInForce.GTC,  # default to GTC, can be overridden
        "recvWindow": 5000,  # Optional but recommended for timing tolerance
        # "price": None,    # for LIMIT orders
    },
    "default_order_type": OrderType.LIMIT,
    "default_time_in_force": TimeInForce.GTC,

    # Parameter templates for place_order
    "required_params": ["symbol", "side", "type", "quantity", "timestamp"],
    "optional_params": ["price", "timeInForce", "recvWindow"],

    # Polling interval for order status (seconds)
    "poll_interval": 2,

    # Maximum time (seconds) to wait for the main order to be FILLED before cancelling it
    "main_order_max_wait": 600,  # Default: 10 minutes

    # Take Profit and Stop Loss price difference (absolute value, e.g. in USDT)
    # Used to calculate TP/SL prices relative to main order price
    "tp_price_diff": 300.0,  # Example: 300 USDT above/below entry
    "sl_price_diff": 500.0,  # Example: 500 USDT below/above entry
    # If an existing same-side position's avg entry price differs from the new entry
    # price by more than this amount (absolute USDT), close it with a market order
    # before placing the new ladder so the bracket tracks a single clean entry.
    "same_side_price_level_diff": 100.0,

    # Decimal places to round TP/SL triggerPrice to before sending to Binance.
    # Must match the symbol's tick size (BTCUSDT futures tick = 0.1 → 1 decimal place).
    # Exceeding this causes -1111 "Precision is over the maximum defined for this asset."
    "price_precision": 1,

    # Maximum time (seconds) to monitor TP/SL orders for OCO behaviour before giving up
    "oco_max_wait": 4000,  # Default: 1 hour

    # DCA ladder configuration
    # base quantity for order 1 (×1); each subsequent order multiplies this by ladder_qty_multipliers[i]
    "ladder_base_qty": 0.001,
    # quantity multiplier per ladder order (orders 2–7); length determines number of ladder orders
    "ladder_qty_multipliers":      [2, 2, 3, 3, 4, 4],
    # century steps DOWN from entry_century for BUY (price = (entry_century - offset) * 100 + snap)
    "ladder_buy_century_offsets":  [1, 1, 5, 5, 6, 6],
    # century steps UP from entry_century for SELL (price = (entry_century + offset) * 100 + snap)
    "ladder_sell_century_offsets": [1, 1, 5, 5, 6, 6],
    # alternating last-2-digit snap values for BUY: index i → snaps[i % 2]
    "ladder_buy_snaps":            [54, 16],
    # alternating last-2-digit snap values for SELL: index i → snaps[i % 2]
    "ladder_sell_snaps":           [68, 94],
    # seconds before unfilled LIMIT ladder orders are cancelled inside _monitor_ladder
    "ladder_order_max_wait":       2000,   # Default: 5 minutes

    # Minimum safety buffer applied on top of the calculated required margin before
    # submitting any ladder order batch.  A value of 1.05 means the available USDT
    # balance must be at least 5 % above the total required margin; raise ValueError
    # if the check fails so no partial ladder is ever placed on an under-funded account.
    "min_balance_buffer_ratio": 1.5,

    # Position open confirmation (used in orchestrate_bracket_order, step 2b)
    # Maximum seconds to wait for at least one ladder order to fill and a position
    # to open before aborting.  If no position is detected within this window, all
    # ladder orders are cancelled and OcoOutcome.TIMEOUT is returned immediately.
    "position_open_wait": 3600,
    # Poll interval (seconds) while waiting for the position to open.
    "position_open_poll": 10,
}
