# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

# Cooldown period (in minutes) after an alert triggers for a level before it can trigger again.
# Default: 60 minutes. Prevents alert spam for volatile price levels.
LEVEL_ALERT_COOLDOWN_MINUTES = 3

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 2051.62,
        "fixed_levels": [1730.64, 1739.24, 1768.49, 1798.52, 1805.63, 1828.46, 1839.58, 1848.4, 1861.33, 1871.43, 1880.92, 1892.37, 1903.01, 1912.84, 1924.3, 1933.2, 1943.74, 1966.33, 1976.72, 1993.29, 2002.81, 2013.84, 2023.26, 2030.64, 2044.52, 2054.16, 2063.27, 2076.97, 2096.88, 2103.31],
        "absolute_interval": 9.0,
    },
    "VN30F1M": {
        "reference_price": 2049.1,
        "fixed_levels": [1736.6, 1773.65, 1798.08, 1829.1, 1839.51, 1853.5, 1863.65, 1875.05, 1883.15, 1896.56, 1906.48, 1915.33, 1928.89, 1941.44, 1952.82, 1976.93, 1986.35, 2007.39, 2024.14, 2032.98, 2044.62, 2056.1, 2098.72],
        "absolute_interval": 9.0,
    }
}

# This flag determines whether to use the performance-based suggested price (if available)
# or default to the structural price.
USE_PERFORMANCE_BY_APPROACH = True

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.3},
    'STRONG_CANDLE': {'avg_worst_loss_price': 0.8},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 0.5},
    'VRA': {'avg_worst_loss_price': 1.3},
    'CONSISTENT_VOLUME_ANCHOR': {'avg_worst_loss_price': 0.9},
    'ICHIMOKU': {'avg_worst_loss_price': 1.4}
}

# Approach-specific profit threshold configuration for alert notifications.
# This dictionary defines the suggested_profit_threshold for each alert approach.
# Values are in percentage points or absolute price points (as configured for each approach).
PROFIT_THRESHOLD_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': 3.5,
    'STRONG_CANDLE': 4.0,
    'CONSISTENT_MOMENTUM': 3.15,
    'VRA': 4.5,
    'CONSISTENT_VOLUME_ANCHOR': 2.75,
    'ICHIMOKU': 6.0
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
