# src/stockreports/config/settings.py
"""
Main configuration file for the stock reporting and alerting application.
This file contains high-level settings ALERT_APPROACHES = [
    "RCM",
    "CONSISTENT_MOMENTUM",
    "ICHIMOKU",
    "STRONG_CANDLE"
]I access, operational mode,
notifications, and market-specific details.
"""

# --- Symbol and API Configuration ---

# Primary Stock Symbol
# Meaning: The main stock symbol or index to monitor and analyze. This value is used throughout the application, including for API requests and report naming.
# Guidance: Change this to the ticker symbol you want to track (e.g., "AAPL", "VNINDEX"). Ensure it matches the symbol expected by the API.
# Example: `SYMBOL = "VN30"`
SYMBOL = "VN30"

# API Base URL
# Meaning: The root URL for the historical data API endpoint.
# Guidance: Do not change this unless the API provider changes their URL structure.
# Example: `API_BASE_URL = "https://api.vietstock.vn/tvnew/history"`
API_BASE_URL = "https://api.vietstock.vn/tvnew/history"

# API Parameters
# Meaning: The query parameters sent with each API request. The 'symbol' is dynamically set from the `SYMBOL` variable above.
# Guidance: The 'resolution' determines the time interval of the data candles. "1" typically means 1-minute candles. Refer to the API documentation for other possible values (e.g., "5", "60", "D").
# Example: `API_PARAMS = {"symbol": SYMBOL, "resolution": "1"}`
API_PARAMS = {
    "symbol": SYMBOL,
    "resolution": "1", # 1-minute resolution
}

# API Headers
# Meaning: HTTP headers sent with each API request to mimic a legitimate browser client.
# Guidance: These may need to be updated if the API provider changes their security requirements or if requests start failing. You can find these values by inspecting network traffic in a web browser while visiting the stock chart page.
API_HEADERS = {
    "Accept": "*/*",
    "Origin": "https://stockchart.vietstock.vn",
    "Referer": "https://stockchart.vietstock.vn/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3.1 Safari/605.1.15",
}


# --- Real-time Monitoring Configuration ---

# Monitoring Interval (Seconds)
# Meaning: The time in seconds the script will wait between fetching new data when running in DEPLOYMENT mode.
# Guidance: A shorter interval (e.g., 5-10 seconds) provides more real-time data but increases API usage. A longer interval (e.g., 60 seconds) is less resource-intensive. Do not set this lower than the data resolution (e.g., don't check every 5 seconds for 1-minute data).
# Range: Integer > 0.
# Example: `MONITORING_INTERVAL_SECONDS = 5`
MONITORING_INTERVAL_SECONDS = 5


# --- General Alerting & Reporting ---

# High-Confidence Threshold Percentage
# Meaning: A threshold used by some analysis scripts. A signal precursor or pattern is considered "High-Confidence" if its historical frequency is above this percentage.
# Guidance: A higher threshold (e.g., 15.0) makes it harder for a signal to be classified as high-confidence, leading to fewer but potentially more reliable alerts.
# Range: 0.0 to 100.0.
# Example: `HIGH_CONFIDENCE_THRESHOLD_PERCENT = 10.0`
HIGH_CONFIDENCE_THRESHOLD_PERCENT = 10.0

# Report Directory
# Meaning: The name of the top-level folder where all generated reports and alert summaries will be saved.
# Guidance: You can change this to organize your output differently. The path is relative to the project root.
# Example: `REPORTS_DIR = "reports"`
REPORTS_DIR = "reports"

# Latest Report Pattern
# Meaning: A file glob pattern used to find the most recent combined analysis report. The asterisk (*) is a wildcard.
# Guidance: Only change this if you alter the naming convention of the main analysis reports.
# Example: `LATEST_REPORT_PATTERN = "combined_analysis_report_*.md"`
LATEST_REPORT_PATTERN = "combined_analysis_report_*.md"

# Logging Level
# Meaning: The minimum level of log messages to be recorded.
# Guidance: "INFO" provides a good balance of detail. "DEBUG" is very verbose and useful for troubleshooting. "WARNING" will only show potential problems.
# Range: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
# Example: `LOG_LEVEL = "INFO"`
LOG_LEVEL = "INFO"


# --- Notification Configuration ---

# Email Enabled
# Meaning: A master switch to enable or disable all email notifications.
# Guidance: Set to `False` to quickly turn off all emails without removing your credentials.
# Range: `True` or `False`.
# Example: `EMAIL_ENABLED = True`
EMAIL_ENABLED = True

# Email SMTP Server / Port
# Meaning: The server and port for your email provider's SMTP service.
# Guidance: These values are standard for major providers. For Gmail, it's "smtp.gmail.com" and 587. Check your email provider's documentation for others.
EMAIL_SMTP_SERVER = "smtp.gmail.com"
EMAIL_SMTP_PORT = 587

# Email Sender / Receiver
# Meaning: The email address that sends the alerts and the address that receives them. They can be the same.
# Guidance: Ensure the sender email is the one associated with the `EMAIL_APP_PASSWORD`.
EMAIL_SENDER = "haud.tech@gmail.com"
EMAIL_RECEIVER = "haud.tech@gmail.com"

# Email App Password
# Meaning: An "App Password" generated from your email account (e.g., Google Account settings). This is NOT your regular login password.
# Guidance: Using an App Password is more secure. It's highly recommended to load this from an environment variable instead of hardcoding it.
# Example: `EMAIL_APP_PASSWORD = "your_generated_app_password"`
EMAIL_APP_PASSWORD = "hqtlxfixexiudmcu"

# ntfy Push Notification Enabled
# Meaning: A master switch to enable or disable push notifications via the ntfy.sh service.
# Guidance: Set to `False` to turn off push notifications.
# Range: `True` or `False`.
# Example: `NTFY_ENABLED = True`
NTFY_ENABLED = True

# ntfy Topic
# Meaning: The name of the ntfy.sh topic to publish alerts to. You will subscribe to this same topic in the ntfy app on your phone.
# Guidance: Use a random, hard-to-guess string for privacy. Anyone who knows the topic name can see your alerts.
# Example: `NTFY_TOPIC = "stock_alerts_a1b2c3d4"`
NTFY_TOPIC = "vn30_alerts_f8a9b2c1"


# --- Data Source & Operational Mode ---

# Mode
# Meaning: Determines the operational mode of the alerter.
# "DEVELOPMENT": Runs on historical data from local files. Useful for testing, validation, and debugging.
# "DEPLOYMENT": Runs in a real-time loop, fetching live data from the API. Use this for live monitoring.
# Guidance: Always use "DEVELOPMENT" for testing changes. Switch to "DEPLOYMENT" for actual use.
# Range: "DEVELOPMENT" or "DEPLOYMENT".
# Example: `MODE = "DEVELOPMENT"`
MODE = "DEVELOPMENT"

# Data Directory
# Meaning: The relative path from the project root to the folder containing historical data JSON files.
# Guidance: Only change this if you restructure the project's data folders.
# Example: `DATA_DIR = "src/stockreports/data"`
DATA_DIR = "src/stockreports/data"

# Data Date
# Meaning: Specifies a single date to process. Its behavior depends on the `MODE`.
# - In `DEVELOPMENT` mode: The script will only process data for this specific date from the local files. If `None`, it processes all dates found.
# - In `DEPLOYMENT` mode: The script will fetch live data for this date. If `None`, it defaults to the current date.
# Guidance: Use this in `DEVELOPMENT` to debug a specific day's signals. Set to `None` in `DEPLOYMENT` for normal operation.
# Range: A string in 'YYYY-MM-DD' format or `None`.
# Example: `DATA_DATE = "2025-10-08"`
DATA_DATE = "2025-10-08"


# --- Alerting Strategy Configuration ---

# Alert Approaches
# Meaning: A list of the alert generation strategies (approaches) to run. The names correspond to modules in the `src/stockreports/alert/approach/` directory.
# Guidance: You can add or remove approach names from this list to enable or disable them. The names are case-insensitive.
# Example: `ALERT_APPROACHES = ["RCM"]` would run only the RCM strategy.
# Example: `ALERT_APPROACHES = ["RCM"]` would run only the RCM strategy.
ALERT_APPROACHES = [
    "RCM",
    "CONSISTENT_MOMENTUM",
    # "ICHIMOKU",
    # "STRONG_CANDLE", # NEED IMPROVEMENT - UNSTABLE TO SUPPORT NOW (2025/10/08)
    # "MA_CROSS", # Disabled as it's a confirmation signal, not a primary approach
]



# --- Market Hours Configuration ---

# Market Country Code
# Meaning: The country code for the primary market being monitored. This is used as a key to look up the correct trading hours and timezone from the `TRADING_HOURS` dictionary.
# Guidance: Change this to match the market you are trading (e.g., "US" for United States).
# Example: `MARKET_COUNTRY_CODE = "VN"`
MARKET_COUNTRY_CODE = "VN"

# Trading Hours
# Meaning: A dictionary defining the trading sessions for different markets. The alerter uses this in `DEPLOYMENT` mode to only fetch data when the market is open.
# Guidance: You can add new market configurations here. Ensure the `timezone` is a valid IANA timezone name (e.g., 'America/New_York', 'Asia/Ho_Chi_Minh'). Session times are in 24-hour format.
TRADING_HOURS = {
    "VN": {
        "name": "Vietnam",
        "timezone": "Asia/Ho_Chi_Minh",
        "sessions": {
            "morning": {"start": "08:45", "end": "11:30"},
            "afternoon": {"start": "13:00", "end": "14:45"},
        }
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
