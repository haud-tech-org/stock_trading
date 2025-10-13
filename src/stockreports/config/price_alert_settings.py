# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1980.0,
        "fixed_levels": [1984.0,1990.0, 1970.0, 1950.0, 1940.0, 1930.0],
        "absolute_interval": 9.0,
    },
    "41I1FA000": {
        "reference_price": 1975.0,
        "fixed_levels": [1973.7,1980.0, 1985.0, 1990.0, 1970.0, 1965.0, 1960.0, 1955.0, 1950.0, 1940.0],
        "absolute_interval": 9.0,
    },
    # Example for another symbol
    # "AAPL": {
    #     "reference_price": 170.0,
    #     "fixed_levels": [175.0, 180.0],
    #     "absolute_interval": 2.5,
    # }
}
