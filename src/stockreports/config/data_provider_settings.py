# src/stockreports/config/data_provider_settings.py
"""
Data Provider Configuration.

This module contains comprehensive configuration for all data providers including:
- Provider-specific settings (timeout, retries, cache TTL)
- Enabled providers list
- Symbol configurations per provider
- Supported symbols for validation

Single source of truth for all data provider configuration.

Provider Support Status:
- vietstock: ✅ Fully implemented and enabled
- binance_ccxt: ✅ Fully implemented and enabled
- binance: ⏳ Implemented but not yet enabled (future deployment)

At any deployment, exactly one provider is active for a given symbol.
Provider and symbol are consistently and dependently related (1:1 model).
"""

# Enabled Data Providers
# Meaning: List of providers that are initialized, registered, and ready to use.
# Currently Enabled: vietstock, binance_ccxt (fully implemented and tested)
# Future: binance (implementation complete, awaiting deployment)
# Guidance: Providers listed here will be registered and available for use.
#           Provider selection is explicit at each call site (no defaults).
ENABLED_DATA_PROVIDERS = ["vietstock", "binance", "binance_ccxt"]

# Provider-Specific Configuration
# Meaning: Configuration dictionary for each data provider. Allows customization of provider behavior.
# Guidance: Add settings specific to each provider here. These are passed to provider instances.
#           NOTE: The "enabled" flag is AUTOMATICALLY SET based on ENABLED_DATA_PROVIDERS above.
#                 To enable/disable providers, simply add/remove them from ENABLED_DATA_PROVIDERS.
#                 Do NOT manually edit the "enabled" field in DATA_PROVIDER_CONFIG.
#
# All three providers are fully implemented. Enable/disable by modifying ENABLED_DATA_PROVIDERS.
DATA_PROVIDER_CONFIG = {
    "vietstock": {
        "enabled": "vietstock" in ENABLED_DATA_PROVIDERS,  # Auto-sync with ENABLED_DATA_PROVIDERS
        "timeout": 15,
        "retries": 3,
        "cache_ttl": 300,  # Cache results for 5 minutes
        "description": "Vietnamese stock market data provider"
    },
    "binance": {
        "enabled": "binance" in ENABLED_DATA_PROVIDERS,  # Auto-sync with ENABLED_DATA_PROVIDERS
        "timeout": 10,
        "retries": 3,
        "cache_ttl": 60,
        "description": "Binance REST API provider"
    },
    "binance_ccxt": {
        "enabled": "binance_ccxt" in ENABLED_DATA_PROVIDERS,  # Auto-sync with ENABLED_DATA_PROVIDERS
        "timeout": 10,
        "retries": 3,
        "cache_ttl": 60,
        "description": "Binance CCXT unified library provider"
    }
}

DATA_PROVIDER_CACHE_TTL = 300

# --- Data Fetching Resolution Configuration ---
# Resolution for fetching OHLCV data in monitoring mode
# This determines the candle interval size when fetching market data
# Value: Minutes (int)
# Default: 1 minute candles
# Range: 1-1440 (1 minute to 1 day)
MONITORING_DATA_RESOLUTION_MINUTES = 1


# --- Provider Symbol Configurations ---
# Mapping of provider names to their supported symbols and metadata
# This is the single source of truth for which symbols are supported by each provider

PROVIDER_SYMBOLS_CONFIG = {
    "vietstock": {
        "name": "vietstock",
        "supported_symbols": [
            "VN30",      # VN30 Index
            "VN30F1M",   # VN30 Future - current month
            "VN30F2M",   # VN30 Future - next month
            "HPG",       # Hoa Phat Group
            "ACB",       # Asia Commercial Bank
            "VCB",       # Vietcombank
            "BID",       # BIDV
            "TCB",       # Techcombank
            "VHM",       # Vinamilk
            "SBT",       # Sabeco
            "VNM",       # Vinamilk
            "TPB",       # TPBank
        ],
        "description": "Vietnamese stock market symbols (HoSE, HNX)",
        "reference": "https://vietstock.vn"
    },
    "binance": {
        "name": "binance",
        "supported_symbols": [
            # Spot trading pairs
            "BTCUSDT",   # Bitcoin - Tether (Spot)
            "ETHUSDT",   # Ethereum - Tether
            "BNBUSDT",   # Binance Coin - Tether
            "BNBBUSD",   # Binance Coin - Binance USD
            "BUSDUSDT",  # Binance USD - Tether
            "XRPUSDT",   # Ripple - Tether
            "ADAUSDT",   # Cardano - Tether
            "DOGEUSDT",  # Dogecoin - Tether
            "SHIBUSDT",  # Shiba Inu - Tether
            # Perpetual Futures (USDT-margined)
            "BTCUSDT-PERP", # Bitcoin - Tether (USDT-Margined Perpetual Futures)
            # Add more _PERP symbols as needed
        ],
        "description": "Binance REST API trading pairs (crypto spot + USDT-margined perpetual futures)",
        "reference": "https://www.binance.com/en/trade"
    },
    "binance_ccxt": {
        "name": "binance_ccxt",
        "supported_symbols": [
            # Spot trading pairs
            "BTCUSDT",  # Bitcoin - Tether (Spot)
            "ETH/USDT",  # Ethereum - Tether (Spot)
            "BNB/USDT",  # Binance Coin - Tether (Spot)
            "ADA/USDT",  # Cardano - Tether (Spot)
            "DOG/USDT",  # Dogecoin - Tether (Spot, note: may vary)
            # Perpetual Futures (Linear - USDT margined)
            "BTC/USDT:USDT",  # Bitcoin Perpetual Futures
            "ETH/USDT:USDT",  # Ethereum Perpetual Futures
            "BNB/USDT:USDT",  # Binance Coin Perpetual Futures
            "ADA/USDT:USDT",  # Cardano Perpetual Futures
        ],
        "description": "Binance CCXT unified library trading pairs (crypto spot + perpetual futures)",
        "reference": "https://docs.ccxt.com/en/latest/manual/trading-pairs.html"
    }
}
