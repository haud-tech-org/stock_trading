# src/stockreports/config/signal_settings.py
"""
Centralized settings for all signal calculation logic.
This ensures consistency between backtesting and real-time monitoring.
"""

# --- Signal Indicator Parameters ---

# -- Moving Averages --
MA_SHORT_PERIOD = 5  # Lookback for fastest moving average (immediate momentum).
MA_MEDIUM_PERIOD = 20 # Lookback for medium moving average (trend confirmation).
MA_LONG_PERIOD = 10 # Lookback for slowest moving average (long-term trend).

# -- Ichimoku Cloud --
TENKAN_PERIOD = 9  # Tenkan-sen (Conversion Line) period.
KIJUN_PERIOD = 26  # Kijun-sen (Base Line) period.
ICHI_SENKOU_B_PERIOD = 52  # Senkou Span B (Leading Span B) period.
ICHI_CHIKOU_LAG = 26  # Chikou Span (Lagging Span) lag.

# -- Strong Close Condition --
# Defines a "strong" close. (0.5, 1.0) means close is in the top 50% of the candle's range for a buy.
STRONG_CLOSE_THRESHOLD_RANGE = (0.5, 1.0)
# Max allowed ratio of the candle's "tail" (wick) to its "body". Enforces a decisive candle shape.
TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO = 0.4

# -- Volume --
AVG_VOLUME_PERIOD = 20  # Lookback period for calculating the moving average of volume.
# Volume must be this multiple of the average to be a "spike". (2.0, 5.0) means 2x to 5x average volume.
VOLUME_SPIKE_MULTIPLIER_RANGE = (2.0, 5.0)

# -- Trend Strength Signal (Original) --
# Number of consecutive candles in the same direction to trigger a basic trend signal.
TREND_STRENGTH_SEQ_CANDLES = 3

# -- Trend Strength Signal (Bollinger Band Squeeze) --
TREND_SQUEEZE_LOOKBACK_PERIOD = 20  # Lookback period for Bollinger Bands to detect a squeeze.
TREND_SQUEEZE_CHECK_WINDOW = 3  # How many recent candles to examine for a squeeze condition.
# The BB width percentage range considered a "squeeze" (low volatility).
TREND_SQUEEZE_BB_WIDTH_RANGE = (0.001, 0.1)
# How close (as a percentage) the price must be to a band to be considered a breakout. 0.005 = 0.5%.
BB_BREAKOUT_NEARNESS_FACTOR = 0.005

# -- "Big Trend" Confirmation Layer --
# Minutes of data to analyze for the "big trend". 0 means all data since the start of the day.
BIG_TREND_LOOKBACK_MINUTES = 120
# A new high must exceed the previous peak by this percentage to be a "breakout". 0.03 = 3%.
BIG_TREND_BREAKOUT_THRESHOLD = 0.03
# Percentage retracement from a peak/trough that qualifies as a potential reversal.
BIG_TREND_REVERSAL_MIN_THRESHOLD = 0.1
BIG_TREND_REVERSAL_MAX_THRESHOLD = 0.4
# Number of recent candles to check for momentum confirming the big trend direction.
BIG_TREND_MOMENTUM_WINDOW = 7
# Minimum number of candles within the window that must be in the trend's direction.
BIG_TREND_MOMENTUM_REQUIRED = 3

# -- ADX (Average Directional Index) settings --
ADX_PERIOD = 14  # Lookback period for calculating ADX (trend strength).
# ADX values between 16 and 60 are considered to indicate a trending market.
ADX_THRESHOLD_RANGE = (16, 60)

# --- SUPPORT_BREAKDOWN Specific Settings ---
# Lookback period for average volume to confirm a breakdown.
SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD = 10
# Breakdown candle volume must be at least 1.5x the average volume.
SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER = 1.5


# --- Approach-Specific Configurations ---
# Fine-tunes parameters for each alerting strategy.
# The "default" block applies to any approach not explicitly defined.
APPROACH_CONFIG = {
    "RCM": {
        "PEAK_TROUGH_PROMINENCE": 4,         # How significant a peak/trough must be.
        "CONFIRMATION_WINDOW": 3,           # How many candles to wait for confirmation.
        "CONFIRMATION_MIN_CONSISTENCY": 4,  # How many of those candles must agree with the trend.
    },
    "CONSISTENT_MOMENTUM": {
        "CONFIRMATION_WINDOW": 3,           # Rolling window to check for momentum.
        "PEAK_BOTTOM_LOOKBACK_PERIOD": 30,  # Lookback period (minutes) for finding peaks/bottoms.
        "BODY_TO_RANGE_MIN_RATIO": 0.8,     # Avg body-to-range ratio required for the momentum window.
    },
    "ICHIMOKU": {
        "TENKAN_PERIOD": 9,
        "KIJUN_PERIOD": 26,
        "SENKOU_B_PERIOD": 52,
        "CHIKOU_LAG": 26,
        "MAX_KIJUN_DISTANCE_PCT_RANGE": (0.1, 3.5),
    },
    "STRONG_CANDLE": {
        # This approach dynamically checks for advanced confirmation availability.
        # No specific settings are needed here unless overriding defaults.
    },
    "SUPPORT_RESISTANCE_BREAK": {
        "PRICE_TOLERANCE": 0.0025,      # Max % difference between points in a level.
        "MIN_TOUCHES": 3,               # Min number of candles touching the level.
        "LOOKBACK_PERIOD": 60,          # How many candles back to look for a level.
        "COOLDOWN_PERIOD": 30,          # How many minutes to wait before a new alert.
        "CONFIRMATION_CANDLE_BODY_SELL": 0.5, # For SELL, confirmation candle closes in bottom 50% of range.
        "CONFIRMATION_CANDLE_BODY_BUY": 0.5,  # For BUY, confirmation candle closes in top 50% of range.
        "USE_VOLUME_CONFIRMATION": True,  # Master switch to enable/disable the volume check.
    },
    "default": {
        "PEAK_TROUGH_PROMINENCE": 5,
        "CONFIRMATION_WINDOW": 4,
        "CONFIRMATION_MIN_CONSISTENCY": 2,
    }
}

# --- Trend Validation Settings ---
# The minimum change in price points required for a trend to be considered significant.
TREND_MINIMUM_MAGNITUDE = 4

# --- Validation Settings ---
# Defines the time window in minutes after an alert to check its outcome (profit/loss).
# Used only in DEVELOPMENT mode against historical data.
VALIDATION_PERIOD_MINUTES = 10
