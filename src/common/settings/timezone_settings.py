
# --- Market Hours Configuration ---

# Market Country Code
# Meaning: The country code for the primary market being monitored. This is used as a key to look up the correct trading hours and timezone from the `TRADING_HOURS` dictionary.
# Guidance: Change this to match the market you are trading (e.g., "US" for United States).
# Example: `MARKET_COUNTRY_CODE = "VN"`
MARKET_COUNTRY_CODE = "VN"

TIMEZONE_BY_COUNTRY_CODE = {
    "VN": {
        "name": "Vietnam",
        "timezone": "Asia/Ho_Chi_Minh",
    },
    # Example for another market:
    # "US": {
    #     "name": "United States (NYSE)",
    #     "timezone": "America/New_York",
    #     "sessions": {
    #         "main": {"start": "09:30", "end": "16:00"}
    #     }
    # }
}

FROM_COUNTRY_CODE = "VN"  # The country code to use for determining the timezone

DATE_CONVERT = "2025-10-09 11:31:00"
