# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1872.3,
        "fixed_levels": [1850.0, 1830.0, 1800.0, 1900.0, 1920.0],
        "absolute_interval": 9.0,
    },
    "41I1FB000": {
        "reference_price": 1870.6,
        "fixed_levels": [1850.0, 1830.0, 1800.0, 1900.0, 1920.0],
        "absolute_interval": 9.0,
    },
    # Example for another symbol
    # "AAPL": {
    #     "reference_price": 170.0,
    #     "fixed_levels": [175.0, 180.0],
    #     "absolute_interval": 2.5,
    # }
}
