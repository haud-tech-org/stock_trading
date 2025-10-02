# src/stockreports/config/settings.py

# API Configuration
API_BASE_URL = "https://api.vietstock.vn/tvnew/history"
API_PARAMS = {
    "symbol": "VN30",
    "resolution": "1", # 1-minute resolution
}

API_HEADERS = {
    "Accept": "*/*",
    "Origin": "https://stockchart.vietstock.vn",
    "Referer": "https://stockchart.vietstock.vn/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3.1 Safari/605.1.15",
}

# Real-time Monitoring Configuration
MONITORING_INTERVAL_SECONDS = 5  # Time in seconds between each data fetch
BIG_TREND_LOOKBACK_MINUTES = 5
BIG_TREND_PRICE_CHANGE_THRESHOLD = 5.0

# Precursor Signal Confidence Threshold
# A precursor combination is considered "High-Confidence" if its frequency
# in the historical analysis report is above this value.
HIGH_CONFIDENCE_THRESHOLD_PERCENT = 10.0

# Report Configuration
REPORTS_DIR = "reports"
LATEST_REPORT_PATTERN = "combined_analysis_report_*.md"

# Logging Configuration
LOG_LEVEL = "INFO"
