# src/stockreports/config/settings.py
"""
Main configuration file for the stock reporting and alerting application.
This file contains high-level settings for API access, operational mode,
notifications, and market-specific details.
"""

# --- Symbol and API Configuration ---

# Primary Stock Symbol
# Meaning: The main stock symbol or index to monitor and analyze. This value is used throughout the application, including for API requests and report naming.
# Guidance: Change this to the ticker symbol you want to track (e.g., "AAPL", "VNINDEX"). Ensure it matches the symbol expected by the API.
# Example: `SYMBOL = "VN30"`
# Symbols: "41I1FA000","VIC","VCB"
# Always include the derivative symbol is the FIRST symbol
SYMBOLS = ["VN30F1M", "VN30", "BTCUSDT"]

# List of symbols that have a significant impact on the market.
IMPACT_SYMBOLS = ["VIC", "VHM"]


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

# --- Data Processing Configuration ---

# Data Processing Transformations
# Meaning: Configuration for enabling/disabling specific data transformations in the DataProcessor layer.
#          This allows fine-grained control over which business logic transformations are applied to raw provider data.
# Guidance:
#   - Each transformation can be independently toggled
#   - All are enabled by default (True) to ensure consistent data quality
#   - Disable transformations only for debugging or special use cases
#   - New transformations can be added here as they are implemented
# Example:
#   DATA_PROCESSING = {
#       "timezone_conversion": True,
#       "price_adjustment": True,
#       "volume_normalization": False,  # Future feature
#   }
DATA_PROCESSING = {
    "timezone_conversion": True,      # Convert index to market timezone
    "price_adjustment": True,         # Apply symbol-specific price adjustments
}


# --- Real-time Monitoring Configuration ---

# Monitoring Interval (Seconds)
# Meaning: The time in seconds the script will wait between fetching new data when running in DEPLOYMENT mode.
# Guidance: A shorter interval (e.g., 5-10 seconds) provides more real-time data but increases API usage. A longer interval (e.g., 60 seconds) is less resource-intensive. Do not set this lower than the data resolution (e.g., don't check every 5 seconds for 1-minute data).
# Range: Integer > 0.
# Example: `MONITORING_INTERVAL_SECONDS = 5`
MONITORING_INTERVAL_SECONDS = 57


# --- General Alerting & Reporting ---

# High-Confidence Threshold Percentage
# Meaning: A threshold used by some analysis scripts. A signal precursor or pattern is considered "High-Confidence" if its historical frequency is above this percentage.
# Guidance: A higher threshold (e.g., 15.0) makes it harder for a signal to be classified as high-confidence, leading to fewer but potentially more reliable alerts.
# Range: 0.0 to 100.0.
# Example: `HIGH_CONFIDENCE_THRESHOLD_PERCENT = 10.0`
HIGH_CONFIDENCE_THRESHOLD_PERCENT = 10.0

# Latest Report Pattern
# Meaning: A file glob pattern used to find the most recent combined analysis report. The asterisk (*) is a wildcard.
# Guidance: Only change this if you alter the naming convention of the main analysis reports.
# Example: `LATEST_REPORT_PATTERN = "combined_analysis_report_*.md"`
LATEST_REPORT_PATTERN = "combined_analysis_report_*.md"

# Logs Directory
# Meaning: The name of the top-level folder where all log files will be saved.
# Guidance: You can change this to organize your logs differently. The path is relative to the project root.
# Example: `LOGS_DIR = "logs"`
LOGS_DIR = "logs"

# Logging Level
# Meaning: The minimum level of log messages to be recorded.
# Guidance: "INFO" provides a good balance of detail. "DEBUG" is very verbose and useful for troubleshooting. "WARNING" will only show potential problems.
# Range: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL".
# Example: `LOG_LEVEL = "INFO"`
LOG_LEVEL = "DEBUG"


# --- Data Source & Operational Mode ---

# Mode
# Meaning: Determines the operational mode of the alerter.
# "DEVELOPMENT": Runs on historical data from local files. Useful for testing, validation, and debugging.
# "DEPLOYMENT": Runs in a real-time loop, fetching live data from the API. Use this for live monitoring.
# Guidance: Always use "DEVELOPMENT" for testing changes. Switch to "DEPLOYMENT" for actual use.
# Range: "DEVELOPMENT" or "DEPLOYMENT".
# Example: `MODE = "DEVELOPMENT"`
MODE = "DEPLOYMENT"

# GOOGLE CLOUD RUN STORAGE SETTINGS
# Name of the Google Cloud Storage bucket for report uploads
GCS_REPORT_BUCKET_NAME = "stock-trading-2"
# Enable or disable Google Cloud Storage for report uploads
# Set to True to upload reports to GCS, False to skip GCS upload
ENABLE_GCS_REPORT_STORAGE = False

# Data Directory
# Meaning: The relative path from the project root to the folder containing historical data JSON files.
# Guidance: Only change this if you restructure the project's data folders.
# Example: `DATA_DIR = "src/stockreports/data"`
DATA_DIR = "src/stockreports/data"

# == Development Mode Settings ==
# Defines the date range for fetching data when running in DEVELOPMENT mode.
# Format: YYYY-MM-DD
DEV_DATA_DATE_RANGE = {
    "start_date": "2025-11-05",
    "end_date": "2025-11-13"
}

# If True, saves the raw JSON response to a file when running in DEVELOPMENT mode.
SAVE_DEV_API_RESPONSE_TO_FILE = True


# --- Alerting Strategy Configuration ---

# Alert Approaches (LEGACY - Kept for backward compatibility)
# Meaning: A list of the alert generation strategies (approaches) to run. The names correspond to modules in the `src/stockreports/alert/approach/` directory.
# Guidance: This configuration is now legacy. For new projects, use SYMBOL_ALERT_APPROACHES instead to configure approaches per symbol.
#           This is kept as a fallback for backward compatibility with existing configurations.
# Example: `ALERT_APPROACHES = ["RCM"]` would run only the RCM strategy.
ALERT_APPROACHES = [
    "VOLUME_SPIKE_CONFIRMATION",
    "VRA",
    "CONSISTENT_VOLUME_ANCHOR",
    #"MA_CROSS", # Disabled as it's a confirmation signal, not a primary approach
]


# --- Symbol-Specific Alert Approaches Configuration ---

# Symbol-Specific Alert Approaches
# Meaning: A dictionary mapping each symbol to its specific list of alert generation strategies.
#          This allows different symbols to run different approaches based on their characteristics.
# Guidance: 
#   - Define an entry for each symbol that needs custom approach configuration
#   - Approach names must correspond to modules in `src/stockreports/alert/approach/`
#   - Symbols not defined here will use ALERT_APPROACHES_DEFAULT
#   - This provides fine-grained control over which strategies run for which symbols
# Example:
#   SYMBOL_ALERT_APPROACHES = {
#       "VN30F1M": ["STRONG_CANDLE", "CONSISTENT_MOMENTUM", "PRICE_GAP"],
#       "VN30": ["STRONG_CANDLE", "VOLUME_SPIKE_CONFIRMATION"],
#       "VCB": ["STRONG_CANDLE"],
#   }
SYMBOL_ALERT_APPROACHES = {
    "VN30F1M": [
        #"CONSISTENT_MOMENTUM",
        #"STRONG_CANDLE",
        #"VOLUME_SPIKE_CONFIRMATION",
        #"VRA",
        #"CONSISTENT_VOLUME_ANCHOR", 
        #"ICHIMOKU"
    ],
    "VN30": [
    ],
    "BTCUSDT": [
        "REVERSAL_ANCHOR_SIGNAL_CANDLE"
    ]
}

# Default Alert Approaches (Fallback)
# Meaning: Approaches to run for any symbol NOT explicitly defined in SYMBOL_ALERT_APPROACHES.
#          This acts as a default when a new symbol is added without a specific configuration.
# Guidance: Set this to a reasonable default. Typical values are ["STRONG_CANDLE"] or ["RCM"].
#          This setting provides backward compatibility and a sensible default for new symbols.
# Example: `ALERT_APPROACHES_DEFAULT = ["STRONG_CANDLE"]`
ALERT_APPROACHES_DEFAULT = [
    "VRA",
    "VOLUME_SPIKE_CONFIRMATION",
    "CONSISTENT_VOLUME_ANCHOR"
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
            "morning": {"start": "05:00", "end": "12:00"},
            "afternoon": {"start": "12:01", "end": "22:30"},
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


# --- Consolidated Profitability Simulation ---

# Consolidated Profitability
# Meaning: Configuration for running a special profitability simulation where alerts from multiple symbols are used to simulate trades on a single, different symbol.
# Guidance:
#   - ENABLED: Set to True to activate this feature. When False, this entire section is ignored.
#   - ALERT_SOURCE_SYMBOLS: A list of symbols whose alerts will be used as trade triggers.
#   - TRADE_EXECUTION_SYMBOL: The one symbol on which all trades will be simulated. This symbol's price data will be used to calculate profit/loss.
CONSOLIDATED_PROFITABILITY = {
    "ENABLED": True,
    "ALERT_SOURCE_SYMBOLS": ["VN30", "VN30F1M"],
    "TRADE_EXECUTION_SYMBOL": "VN30F1M"
}

# --- Debug Replay Configuration ---

# Replay Start Time
# Meaning: The specific date and time to start replaying historical data in DEVELOPMENT mode.
# Guidance: This is useful for testing how the system would have behaved in the past. Set this to a time within the `DEV_DATA_DATE_RANGE`.
# Format: "YYYY-MM-DD HH:MM:SS"
# Example: `DEBUG_REPLAY_START_TIME = "2026-01-08 09:05:00"`
DEBUG_REPLAY_START_TIME = "2026-04-10 22:27:00"
