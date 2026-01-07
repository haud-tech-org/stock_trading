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

PERFORMANCE_BY_APPROACH = {
    'VOLUME_SPIKE_CONFIRMATION': {'avg_worst_loss_price': 1.8},
    'PROMINENT_PEAK_REVERSAL': {'avg_worst_loss_price': 1.7},
    'ICHIMOKU': {'avg_worst_loss_price': 0.8},
    'STRONG_CANDLE': {'avg_worst_loss_price': 7.75}
}
