# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1899.93,
        "fixed_levels": [1804.57, 1877.78, 1896.05, 1905.4],
        "absolute_interval": 9.0,
    },
    "41I1FB000": {
        "reference_price": 1898.4,
        "fixed_levels": [1851.7, 1878.58, 1896.67, 1910.2],
        "absolute_interval": 9.0,
    },
    "VN30F2512": {
        "reference_price": 1888.0,
        "fixed_levels": [1847.27, 1877.45, 1894.25],
        "absolute_interval": 9.0,
    },
    "VIC": {
        "reference_price": 227.8,
        "fixed_levels": [203.8],
        "absolute_interval": 9.0,
    },
    "HPG": {
        "reference_price": 27.35,
        "fixed_levels": [25.99, 26.91, 27.12, 27.33],
        "absolute_interval": 9.0,
    }
}
