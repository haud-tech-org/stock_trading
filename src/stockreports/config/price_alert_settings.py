# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "41I1G1000": {
        "reference_price": 2033.7,
        "fixed_levels": [1916.65, 1930.55, 1981.27],
        "absolute_interval": 9.0,
    },
    "VN30": {
        "reference_price": 2029.28,
        "fixed_levels": [1804.57, 1846.13, 1877.78, 1902.37, 1913.03, 1923.6, 1943.18, 1977.31, 1995.91],
        "absolute_interval": 9.0,
    }
}

# If True, the 'calculate_suggested_price' function will use the performance-based
# offsets defined below. If False, it will use the fallback logic.
USE_PERFORMANCE_BY_APPROACH = False

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.2667},
    'PROMINENT_PEAK_REVERSAL': {'avg_worst_loss_price': 4.85},
    'STRONG_CANDLE': {'avg_worst_loss_price': 3.3188},
    'CONSECUTIVE_POWER_CANDLES': {'avg_worst_loss_price': 7.85},
    'CONSISTENT_MOMENTUM': {'avg_worst_loss_price': 2.65},
    'RCM': {'avg_worst_loss_price': 2.4},
    'PRICE_GAP': {'avg_worst_loss_price': 1.7667}
}

# An offset to adjust the structural price.
# For BUY signals, this offset is subtracted from the calculated structural price.
# For SELL signals, it's added.
STRUCTURAL_PRICE_LEVEL_OFFSET = 0.0

# The minimum required difference between the structural suggested price and the close price.
MIN_STRUCTURAL_PRICE_OFFSET = 0.5
