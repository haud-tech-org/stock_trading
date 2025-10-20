# src/stockreports/config/price_alert_settings.py

# If False, an alert for a specific price level (e.g., 1950.0) is sent only once per day.
# If True, alerts are sent every time a level is crossed.
ALLOW_REPEATED_LEVEL_ALERTS = False

PRICE_ALERTS = {
    "VN30": {
        "reference_price": 1977.1,
        "fixed_levels": [1999.0, 2009.2, 2019.1, 1950.3, 1935.8],
        "absolute_interval": 9.0,
    },
    "41I1FB000": {
        "reference_price": 1968.0,
        "fixed_levels": [1978.1, 1998.3, 2009.0, 2031.8, 2041.8, 2051.8],
        "absolute_interval": 9.0,
    },
    # Example for another symbol
    # "AAPL": {
    #     "reference_price": 170.0,
    #     "fixed_levels": [175.0, 180.0],
    #     "absolute_interval": 2.5,
    # }
}
