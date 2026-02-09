# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1969.3,
        "fixed_levels": [1804.57, 1846.13, 1877.78, 1902.37, 1913.03, 1923.6, 1943.18, 1974.36, 1987.27, 1997.86, 2012.03, 2021.85, 2063.27, 2076.97, 2096.88, 2103.31],
        "absolute_interval": 9.0,
    },
    "VN30F1M": {
        "reference_price": 1972.2,
        "fixed_levels": [1852.56, 1879.48, 1897.5, 1911.6, 1928.46, 1939.87, 1983.3, 1991.07, 2005.32, 2023.62, 2040.73, 2052.2, 2098.72],
        "absolute_interval": 9.0,
    }
}

# This flag determines whether to use the performance-based suggested price (if available)
# or default to the structural price.
USE_PERFORMANCE_BY_APPROACH = True

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.4},
    'PROMINENT_PEAK_REVERSAL': {'avg_worst_loss_price': 0.0},
    'STRONG_CANDLE': {'avg_worst_loss_price': 0.5},
    'CONSECUTIVE_POWER_CANDLES': {'avg_worst_loss_price': 0.0},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 0.0},
    'RCM': {'avg_worst_loss_price': 0.0},
    'PRICE_GAP': {'avg_worst_loss_price': 0.0},
    'VRA': {'avg_worst_loss_price': 1.3},
    'COMPARISON': {'avg_worst_loss_price': 0.0},
    'TREND_REVERSAL': {'avg_worst_loss_price': 1.3},
    'VOLUME_REVERSAL': {'avg_worst_loss_price': 0.8},
    'SESSION_EXTREME_VOLUME_REVERSAL': {'avg_worst_loss_price': 1.4},
    'CONSISTENT_VOLUME_ANCHOR': {'avg_worst_loss_price': 1.3}
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
