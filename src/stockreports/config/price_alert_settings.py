# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1978.76,
        "fixed_levels": [1804.57, 1876.9, 1896.05, 1906.77, 1917.81, 1929.96],
        "absolute_interval": 9.0,
    },
    "VN30F2512": {
        "reference_price": 1976.3,
        "fixed_levels": [1847.27, 1877.45, 1894.25, 1903.67, 1913.9, 1929.8],
        "absolute_interval": 9.0,
    },
}
