# src/stockreports/config/validation_settings.py
"""
Configuration settings for the alert validation script.
This script is used in DEVELOPMENT mode to assess the performance of generated alerts against historical data.
"""
from . import signal_settings
from . import settings

# --- Validation Parameters ---

# Validation Price Gain Threshold
# Meaning: The minimum increase in price (in points) after a BUY alert for the alert to be considered a "Success".
# Guidance: This defines your minimum profit target for a successful buy. A higher value demands a larger price move.
# Range: Float > 0.
# Example: `VALIDATION_PRICE_GAIN_THRESHOLD = 3.0` means the price must increase by at least 3.0 points.
VALIDATION_PRICE_GAIN_THRESHOLD = 3.0

# Validation Price Drop Threshold
# Meaning: The minimum decrease in price (in points) after a SELL alert for the alert to be considered a "Success".
# Guidance: This defines your minimum profit target for a successful sell. A higher value demands a larger price move.
# Range: Float > 0.
# Example: `VALIDATION_PRICE_DROP_THRESHOLD = 3.0` means the price must drop by at least 3.0 points.
VALIDATION_PRICE_DROP_THRESHOLD = 3.0

# Validation Time Window in Minutes
# Meaning: The number of minutes after an alert is generated to check if the profit target (gain/drop threshold) was met.
# Guidance: This sets the time horizon for your trade's success. A shorter window (e.g., 15) tests for immediate performance, while a longer window (e.g., 60) allows more time for the price to move.
# Range: Integer > 0.
# Example: `VALIDATION_TIME_WINDOW_MINUTES = 15`
VALIDATION_TIME_WINDOW_MINUTES = 10
VALIDATION_PERIOD_MINUTES = VALIDATION_TIME_WINDOW_MINUTES  # Alias for clarity in validation scripts

# Maximum Time to Trigger in Minutes
# Meaning: The maximum number of minutes allowed from alert generation to trade entry (price cross).
# Guidance: If a trade doesn't trigger within this window, it's considered missed and ignored.
# Range: Integer > 0.
# Example: `MAX_TIME_TO_TRIGGER_MINUTES = 5`
MAX_TIME_TO_TRIGGER_MINUTES = 5

# Validation Price Threshold for Take-Profit
# Meaning: The price difference from the entry point that triggers a "Success" (take-profit) exit.
# Guidance: Defines the reward target for a trade.
# Range: Float > 0.
VALIDATION_PRICE_THRESHOLD_PROFIT = [3.0, 3.5, 4.0, 4.5, 5.0, 6.0, 7.0, 8.0, 9.0]
# Validation Price Threshold for Stop-Loss
# Meaning: The price difference from the entry point that triggers a "Failed" (stop-loss) exit.
# Guidance: Defines the risk tolerance for a trade.
# Range: Float > 0.
VALIDATION_PRICE_THRESHOLD_LOSS = [2.5, 3.0, 3.5, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0]


# --- Data Source Configuration ---

# Validation Data Source
# Meaning: Determines where the validation script gets its data.
# 0 = Use live data fetched from the API. This is not typical for validation.
# 1 = Use historical data from local JSON files in the 'src/stockreports/data' directory. This is the standard for validation.
# Guidance: Always use 1 for backtesting and validation to ensure consistent, repeatable results.
# Range: 0 or 1.
# Example: `VALIDATION_DATA_SOURCE = 1`
VALIDATION_DATA_SOURCE = 1


# --- Date Filter Configuration ---

# Validation Date Filter
# Meaning: Allows you to run the validation on a specific date from your local dataset.
# Guidance: Set to a string in 'YYYY-MM-DD' format to test a single day. Set to `None` to run the validation across all dates found in the local data directory.
# Range: A string 'YYYY-MM-DD' or None.
# Example: `VALIDATION_DATE_FILTER = "2025-09-25"` will only validate alerts for September 25, 2025.
VALIDATION_DATE_FILTER = None


# --- Trend Identification Parameters ---

# Minimum Peak Price Change
# Meaning: The minimum percentage change required to identify a significant peak or trough in the historical data. This is used for high-level trend analysis during validation.
# Guidance: A higher value will only identify major turning points, ignoring minor fluctuations. A lower value is more sensitive.
# Range: Float > 0.
# Example: `MIN_PEAK_PRICE_CHANGE = 1.0` means a price swing must be at least 1% to be considered a significant peak or trough.
MIN_PEAK_PRICE_CHANGE = 1.0

# The minimum profit/loss required for an alert to be considered successful during validation.
# Alerts with a profit_loss below this value will be marked as 'Failed'.
MIN_EXPECTED_PROFIT_LOSS = 2.0

# --- Price Adjustment Configuration ---

# Symbols to Exclude from Price Adjustment
# Meaning: A list of symbols that should NOT have their price data divided by 1000.
# This is typically used for indices or other symbols with a different price scale than individual stocks.
# Guidance: Add any symbol (e.g., "VN30", "VNINDEX") that should be exempt from the standard price adjustment logic.
# Example: `PRICE_ADJUSTMENT_EXCLUSION_LIST = ["VN30"]`
PRICE_ADJUSTMENT_EXCLUSION_LIST = ["VN30","41I1FB000","VN30F2512", "VN30F1M"]
