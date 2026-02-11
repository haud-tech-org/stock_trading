# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1943.6,
        "fixed_levels": [1730.64, 1739.24, 1768.49, 1798.52, 1805.63, 1828.46, 1839.58, 1848.4, 1861.33, 1871.43, 1880.92, 1892.37, 1903.01, 1912.84, 1924.3, 1932.76, 1943.81, 1965.38, 1976.72, 1992.5, 2002.81, 2017.1, 2029.37, 2054.16, 2063.27, 2076.97, 2096.88, 2103.31],
        "absolute_interval": 9.0,
    },
    "VN30F1M": {
        "reference_price": 1968.2,
        "fixed_levels": [1736.6, 1773.65, 1798.08, 1829.1, 1839.51, 1853.5, 1863.65, 1875.05, 1883.15, 1896.56, 1906.48, 1915.33, 1928.73, 1941.44, 1953.0, 1983.3, 1991.07, 2004.88, 2024.02, 2039.44, 2052.2, 2098.72],
        "absolute_interval": 9.0,
    }
}

# This flag determines whether to use the performance-based suggested price (if available)
# or default to the structural price.
USE_PERFORMANCE_BY_APPROACH = True

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.4},
    'PROMINENT_PEAK_REVERSAL': {'avg_worst_loss_price': 0.0},
    'STRONG_CANDLE': {'avg_worst_loss_price': 0.8},
    'CONSECUTIVE_POWER_CANDLES': {'avg_worst_loss_price': 0.0},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 0.5},
    'RCM': {'avg_worst_loss_price': 0.0},
    'PRICE_GAP': {'avg_worst_loss_price': 0.0},
    'VRA': {'avg_worst_loss_price': 1.3},
    'COMPARISON': {'avg_worst_loss_price': 0.0},
    'TREND_REVERSAL': {'avg_worst_loss_price': 1.3},
    'VOLUME_REVERSAL': {'avg_worst_loss_price': 0.8},
    'SESSION_EXTREME_VOLUME_REVERSAL': {'avg_worst_loss_price': 1.5},
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
