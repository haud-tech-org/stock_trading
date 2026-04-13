# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

# Cooldown period (in minutes) after an alert triggers for a level before it can trigger again.
# Default: 60 minutes. Prevents alert spam for volatile price levels.
LEVEL_ALERT_COOLDOWN_MINUTES = 3

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1928.23,
        "fixed_levels": [1771.57, 1803.39, 1844.11, 1877.71, 1894.36, 1904.72, 1915.54, 1939.53, 1966.48, 2053.99],
        "absolute_interval": 9.0,
    },
    "VN30F1M": {
        "reference_price": 1931.0,
        "fixed_levels": [1767.58, 1832.97, 1855.58, 1874.7, 1895.83, 1924.3, 2043.83],
        "absolute_interval": 9.0,
    },
    "BTC/USDT:USDT": {
        "reference_price": 70800.0,
        "fixed_levels": [68000.0, 68500.0, 69000.0, 69500.0, 70000.0, 70500.0, 71000.0, 71500.0, 72000.0, 72500.0, 73000.0, 73500.0, 74000.0],
        "absolute_interval": 500.0,
    }
}

# This flag determines whether to use the performance-based suggested price (if available)
# or default to the structural price.
USE_PERFORMANCE_BY_APPROACH = True

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 3.6},
    'STRONG_CANDLE': {'avg_worst_loss_price': 0.8},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 0.5},
    'VRA': {'avg_worst_loss_price': 0.8},
    'CONSISTENT_VOLUME_ANCHOR': {'avg_worst_loss_price': 0.9},
    'ICHIMOKU': {'avg_worst_loss_price': 1.7},
    'REVERSAL_ANCHOR_SIGNAL_CANDLE': {'avg_worst_loss_price': 150}
}

# Approach-specific profit threshold configuration for alert notifications.
# This dictionary defines the suggested_profit_threshold for each alert approach.
# Values are in percentage points or absolute price points (as configured for each approach).
PROFIT_THRESHOLD_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': 3.5,
    'STRONG_CANDLE': 3.0,
    'CONSISTENT_MOMENTUM': 3.15,
    'VRA': 4.5,
    'CONSISTENT_VOLUME_ANCHOR': 2.75,
    'ICHIMOKU': 3.0,
    'REVERSAL_ANCHOR_SIGNAL_CANDLE': 250
}

# A fixed offset added to all suggested price calculations to provide an extra buffer.
# For BUY signals, this offset is subtracted from the calculated structural price.
# For SELL signals, it's added.
PRICE_LEVEL_OFFSET_FIXED = 0.1

# The maximum and minimum required difference between the suggested price and the close price.
MAX_PRICE_ADJUSTMENT_OFFSET = 5.0
MIN_PRICE_ADJUSTMENT_OFFSET = 0.2
# ==============================================================================
# PERFORMANCE-BASED SUGGESTED PRICE SETTINGS
# ==============================================================================
