# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 2039.79,
        "fixed_levels": [1804.57, 1846.13, 1877.78, 1902.37, 1913.03, 1923.6, 1943.18, 1977.31, 1995.91],
        "absolute_interval": 9.0,
    },
    "VN30F1M": {
        "reference_price": 2040.4,
        "fixed_levels": [1916.65, 1930.55, 1981.27, 2003.77],
        "absolute_interval": 9.0,
    }
}

# This flag determines whether to use the performance-based suggested price (if available)
# or default to the structural price.
USE_PERFORMANCE_BY_APPROACH = False

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.7826},
    'PROMINENT_PEAK_REVERSAL': {'avg_worst_loss_price': 3.9667},
    'STRONG_CANDLE': {'avg_worst_loss_price': 3.0435},
    'CONSECUTIVE_POWER_CANDLES': {'avg_worst_loss_price': 4.9667},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 1.375},
    'RCM': {'avg_worst_loss_price': 3.7333},
    'PRICE_GAP': {'avg_worst_loss_price': 2.6},
    'VRA': {'avg_worst_loss_price': 5.2},
    'COMPARISON': {'avg_worst_loss_price': 5.8}
}

# A fixed offset added to all suggested price calculations to provide an extra buffer.
# For BUY signals, this offset is subtracted from the calculated structural price.
# For SELL signals, it's added.
PRICE_LEVEL_OFFSET_FIXED = 0.5

# The maximum and minimum required difference between the suggested price and the close price.
MAX_PRICE_ADJUSTMENT_OFFSET = 1.0
MIN_PRICE_ADJUSTMENT_OFFSET = 0.5
# ==============================================================================
# PERFORMANCE-BASED SUGGESTED PRICE SETTINGS
# ==============================================================================
