# src/stockreports/config/signal_settings.py
"""
Centralized settings for all signal calculation logic.
This ensures consistency between backtesting and real-time monitoring.
"""

# --- Signal Indicator Parameters ---

# Moving Averages

# Short-Term Moving Average Period
# Meaning: The lookback period for the fastest moving average, used to detect immediate price momentum.
# Guidance: A smaller value (e.g., 5) makes it very sensitive to recent price changes. A larger value (e.g., 10) makes it smoother and less reactive.
# Range: Integer > 0.
# Example: `MA_SHORT_PERIOD = 5`
MA_SHORT_PERIOD = 5

# Medium-Term Moving Average Period
# Meaning: The lookback period for the medium-speed moving average, often used to confirm the primary trend direction.
# Guidance: This should be significantly larger than the short period to provide a stable trend baseline.
# Range: Integer > MA_SHORT_PERIOD.
# Example: `MA_MEDIUM_PERIOD = 20`
MA_MEDIUM_PERIOD = 20 # For trend confirmation

# Long-Term Moving Average Period
# Meaning: The lookback period for the slowest moving average, used to gauge the long-term, overarching trend.
# Guidance: This value is often used in strategies to ensure short-term signals align with the major market direction.
# Range: Integer > MA_MEDIUM_PERIOD.
# Example: `MA_LONG_PERIOD = 50`
MA_LONG_PERIOD = 10

# Ichimoku Cloud

# Tenkan-sen (Conversion Line) Period
# Meaning: The lookback period for the Tenkan-sen line, representing the midpoint of the last 9 candles. It indicates short-term momentum.
# Guidance: Standard value is 9. Changing this alters the sensitivity of the line.
# Range: Integer > 0.
# Example: `ICHIMOKU_TENKAN_PERIOD = 9`
ICHIMOKU_TENKAN_PERIOD = 9

# Kijun-sen (Base Line) Period
# Meaning: The lookback period for the Kijun-sen line, representing the midpoint of the last 26 candles. It acts as a measure of medium-term momentum and a level of support/resistance.
# Guidance: Standard value is 26.
# Range: Integer > 0.
# Example: `ICHIMOKU_KIJUN_PERIOD = 26`
ICHIMOKU_KIJUN_PERIOD = 26

# Senkou Span B (Leading Span B) Period
# Meaning: The lookback period for Senkou Span B, which forms the slower boundary of the Kumo (cloud). It represents the midpoint of the last 52 candles and is a measure of long-term momentum.
# Guidance: Standard value is 52.
# Range: Integer > 0.
# Example: `ICHI_SENKOU_B_PERIOD = 52`
ICHI_SENKOU_B_PERIOD = 52

# Chikou Span (Lagging Span) Lag
# Meaning: The number of periods the Chikou Span (current closing price) is shifted back in time. It's used to compare the current price with past price action.
# Guidance: Standard value is 26, matching the Kijun-sen period.
# Range: Integer > 0.
# Example: `ICHI_CHIKOU_LAG = 26`
ICHI_CHIKOU_LAG = 26

# Kijun-sen Proximity Range
# Meaning: For a signal to be valid, the price must be within a certain percentage distance from the Kijun-sen. This prevents taking signals when the price has moved too far, too fast.
# Guidance: The tuple represents (min_distance_pct, max_distance_pct). A range of (0.1, 3.5) means the price must be between 0.1% and 3.5% away from the Kijun line.
# Example: `ICHI_MAX_KIJUN_DISTANCE_PCT_RANGE = (0.1, 3.5)`
ICHI_MAX_KIJUN_DISTANCE_PCT_RANGE = (0.1, 3.5)  # Price should be within 0.1% to 3.5% of the Kijun-sen.

# Strong Close Condition

# Strong Close Threshold
# Meaning: Defines what qualifies as a "strong" close. For a buy signal, the close must be in the upper portion of the candle's high-low range. For a sell, it must be in the lower portion.
# Guidance: A value of (0.6, 1.0) means the close must be in the top 40% of the candle's range for a buy. (0.0, 0.4) would be the bottom 40% for a sell.
# Example: `STRONG_CLOSE_THRESHOLD_RANGE = (0.6, 1.0)`
STRONG_CLOSE_THRESHOLD_RANGE = (0.5, 1.0)  # Close must be in the top 60-100% of the candle's range for buys, or bottom for sells.

# Strong Close Tail Ratio
# Meaning: The maximum allowed ratio of the candle's "tail" (wick) to its "body". A smaller ratio ensures the candle has a decisive body and is not a doji or spinning top.
# Guidance: A lower value (e.g., 0.4) enforces a stronger, more decisive candle shape.
# Range: 0.0 to 1.0+.
# Example: `TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO = 0.4`
TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO = 0.4 # Ratio of wick to body for a strong close

# Volume

# Average Volume Period
# Meaning: The lookback period for calculating the moving average of volume.
# Guidance: A common value is 20 periods. This helps to normalize volume and identify unusual spikes.
# Range: Integer > 0.
# Example: `AVG_VOLUME_PERIOD = 20`
AVG_VOLUME_PERIOD = 20

# Volume Spike Multiplier Range
# Meaning: To qualify as a "volume spike," the current candle's volume must be a certain multiple of the average volume.
# Guidance: A range of (2.0, 5.0) means the volume must be between 2 and 5 times the average. A higher lower bound makes the signal rarer and more significant.
# Example: `VOLUME_SPIKE_MULTIPLIER_RANGE = (2.0, 5.0)`
VOLUME_SPIKE_MULTIPLIER_RANGE = (2.0, 5.0) # Volume must be 2.0x to 5.0x the average.

# Trend Strength Signal (Original)

# Sequential Candles for Trend Strength
# Meaning: The number of consecutive candles in the same direction required to trigger a basic trend strength signal.
# Guidance: A value of 3 means three consecutive green candles (for an uptrend) are needed.
# Range: Integer > 1.
# Example: `TREND_STRENGTH_SEQ_CANDLES = 3`
TREND_STRENGTH_SEQ_CANDLES = 3

# Trend Strength Signal (Bollinger Band Squeeze)

# Squeeze Lookback Period
# Meaning: The lookback period for calculating Bollinger Bands to detect a volatility squeeze.
# Guidance: 20 is a standard period. This should be long enough to establish a baseline for volatility.
# Range: Integer > 0.
# Example: `TREND_SQUEEZE_LOOKBACK_PERIOD = 20`
TREND_SQUEEZE_LOOKBACK_PERIOD = 20

# Squeeze Check Window
# Meaning: The number of recent candles to examine for a low-volatility (squeeze) condition.
# Guidance: A value of 3 means the script will check if any of the last 3 candles met the squeeze criteria.
# Range: Integer > 0.
# Example: `TREND_SQUEEZE_CHECK_WINDOW = 3`
TREND_SQUEEZE_CHECK_WINDOW = 3 # How many recent candles to check for a squeeze condition.

# Bollinger Band Squeeze Width Range
# Meaning: The percentage range for the Bollinger Band width that is considered a "squeeze" (low volatility).
# Guidance: A smaller upper bound (e.g., 0.1) requires a tighter squeeze, indicating very low volatility and a potential for a strong breakout.
# Example: `TREND_SQUEEZE_BB_WIDTH_RANGE = (0.001, 0.1)`
TREND_SQUEEZE_BB_WIDTH_RANGE = (0.001, 0.1) # Range for what's considered a "low volatility" squeeze.

# Bollinger Band Breakout Nearness Factor
# Meaning: A percentage value determining how close the price must be to the upper or lower band to be considered a breakout.
# Guidance: A value of 0.005 means the price must be within 0.5% of the band. A smaller value requires a more definitive breakout.
# Example: `BB_BREAKOUT_NEARNESS_FACTOR = 0.005`
BB_BREAKOUT_NEARNESS_FACTOR = 0.005 # How close to the band the price needs to be to be considered a breakout (0.5%)

# "Big Trend" Confirmation Layer

# Big Trend Lookback Minutes
# Meaning: The number of minutes of data to analyze to determine the "big trend" by finding major peaks and troughs.
# Guidance: A value of 0 means it will use all data available since the start of the trading day. A specific value like 120 will limit the lookback to the last 2 hours.
# Range: Integer >= 0.
# Example: `BIG_TREND_LOOKBACK_MINUTES = 120`
BIG_TREND_LOOKBACK_MINUTES = 120  # How many minutes to look back for peaks/troughs. 0 means start of day.

# Big Trend Breakout Threshold
# Meaning: A percentage threshold. A new high must exceed the previous peak by this much to be considered a "breakout" in the big trend.
# Guidance: A lower value (e.g., 0.03, which is 3%) will detect breakouts more sensitively. A higher value requires a more significant price move.
# Example: `BIG_TREND_BREAKOUT_THRESHOLD = 0.03`
BIG_TREND_BREAKOUT_THRESHOLD = 0.03 # Lowered from 0.05 to catch breakouts earlier.

# Big Trend Reversal Threshold (Min/Max)
# Meaning: Defines the percentage retracement from a peak or trough that qualifies as a potential reversal of the big trend.
# Guidance: This helps filter out minor pullbacks. For example, the price must pull back at least 0.1% (min) but no more than 0.4% (max) from a peak to be considered a potential downward reversal.
# Example: `BIG_TREND_REVERSAL_MIN_THRESHOLD = 0.1`, `BIG_TREND_REVERSAL_MAX_THRESHOLD = 0.4`
BIG_TREND_REVERSAL_MIN_THRESHOLD = 0.1
BIG_TREND_REVERSAL_MAX_THRESHOLD = 0.4

# Big Trend Momentum Window
# Meaning: The number of recent candles to check for momentum confirming the direction of the big trend.
# Guidance: Works with `BIG_TREND_MOMENTUM_REQUIRED`. A window of 7 candles is a common short-term period.
# Range: Integer > 0.
# Example: `BIG_TREND_MOMENTUM_WINDOW = 7`
BIG_TREND_MOMENTUM_WINDOW = 7 # How many candles to look at for the momentum check.

# Big Trend Momentum Required
# Meaning: The minimum number of candles within the `BIG_TREND_MOMENTUM_WINDOW` that must be in the direction of the trend.
# Guidance: Requiring 3 of the last 7 candles to be bullish confirms underlying buying pressure in an uptrend.
# Range: Integer > 0, <= BIG_TREND_MOMENTUM_WINDOW.
# Example: `BIG_TREND_MOMENTUM_REQUIRED = 3`
BIG_TREND_MOMENTUM_REQUIRED = 3 # How many of those candles must be in the trend's direction.

# ADX (Average Directional Index) settings

# ADX Period
# Meaning: The lookback period for calculating the ADX, which measures trend strength (not direction).
# Guidance: 14 is the standard period used by the indicator's creator.
# Range: Integer > 0.
# Example: `ADX_PERIOD = 14`
ADX_PERIOD = 14

# ADX Threshold Range
# Meaning: The range of ADX values considered to indicate a "trending" market. Values below the minimum suggest a ranging or weak trend market. Values above the maximum may indicate an exhaustive trend.
# Guidance: A common interpretation is that an ADX above 25 indicates a trend. The range (16, 60) provides a wider filter.
# Example: `ADX_THRESHOLD_RANGE = (25, 75)`
ADX_THRESHOLD_RANGE = (16, 60)  # A value between 16 and 60 is considered a trending market.

# --- SUPPORT_BREAKDOWN Specific Settings ---

# Volume Confirmation Period for Support Breakdown
# Meaning: The lookback period for calculating the average volume used to confirm a breakdown.
# Guidance: A shorter period (e.g., 10) focuses on recent volume trends leading up to the breakdown.
# Range: Integer > 0.
# Example: `SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD = 10`
SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD = 10

# Volume Confirmation Multiplier for Support Breakdown
# Meaning: The volume of the breakdown candle must be at least this multiple of the average volume.
# Guidance: A value of 1.5 means the breakdown volume must be 50% higher than the recent average. This filters out low-conviction breakdowns.
# Range: Float > 1.0.
# Example: `SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER = 1.5`
SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER = 1.5


# --- Approach-Specific Configurations ---
# Meaning: This dictionary allows for fine-tuning parameters for each specific alerting strategy (approach).
# Guidance: You can enable/disable advanced confirmation or tweak parameters like prominence and window sizes for each approach independently. The "default" block applies to any approach not explicitly defined.
APPROACH_CONFIG = {
    "RCM": {
        "USE_ADVANCED_CONFIRMATION": True,
        # How significant a peak/trough must be to be considered a reversal point. Higher values ignore minor fluctuations.
        "PEAK_TROUGH_PROMINENCE": 4,
        # How many candles to wait for confirmation
        "CONFIRMATION_WINDOW": 3,
        # How many of those candles must agree with the trend (for simple confirmation)
        "CONFIRMATION_MIN_CONSISTENCY": 4,
    },
    "CONSISTENT_MOMENTUM": {
        "USE_ADVANCED_CONFIRMATION": True,
        "CONFIRMATION_WINDOW": 3, # Rolling window to check for momentum
        "PEAK_BOTTOM_LOOKBACK_PERIOD": 30, # Lookback period (in minutes) for finding peaks/bottoms
        "BODY_TO_RANGE_MIN_RATIO": 0.8, # The average body-to-range ratio required for the momentum window
    },
    "ICHIMOKU": {
        "USE_ADVANCED_CONFIRMATION": True,
    },
    "STRONG_CANDLE": {
        "USE_ADVANCED_CONFIRMATION": True,
    },
    "SUPPORT_BREAKDOWN": {
        "PRICE_TOLERANCE": 0.0025, # Max % difference between lows in a support shelf
        "MIN_TOUCHES": 3,          # Min number of candles touching the support level
        "LOOKBACK_PERIOD": 60,     # How many candles back to look for a support shelf
        "COOLDOWN_PERIOD": 30,     # How many minutes to wait before generating a new alert
        "CONFIRMATION_CANDLE_BODY": 0.5, # The confirmation candle must close in the bottom 50% of its range
        "USE_VOLUME_CONFIRMATION": True, # Master switch to enable/disable the volume check
    },
    # A default block for any approach not explicitly listed
    "default": {
        "USE_ADVANCED_CONFIRMATION": True,
        "PEAK_TROUGH_PROMINENCE": 5,
        "CONFIRMATION_WINDOW": 4,
        "CONFIRMATION_MIN_CONSISTENCY": 2,
    }
}


# --- DEPRECATED: To be removed after full refactoring ---
# When True, the smart alerter will use MA Cross, Ichimoku Cross, or Strong Candle for confirmation.
# When False, it will use the simple logic of counting consistent candles.
USE_ADVANCED_CONFIRMATION = True

# --- Simple Confirmation Settings (for when USE_ADVANCED_CONFIRMATION is False) ---
CONFIRMATION_WINDOW = 1  # How many candles to wait for confirmation
CONFIRMATION_MIN_CONSISTENCY = 3  # How many of those candles must agree with the trend

# --- Trend Validation Settings ---

# Minimum Trend Magnitude
# Meaning: The minimum change in price points (e.g., index points) required for a detected trend to be considered valid and significant.
# Guidance: This acts as a filter to ignore very small, insignificant price movements. Set to 0 to disable this check.
# Range: Integer >= 0.
# Example: `TREND_MINIMUM_MAGNITUDE = 3`
TREND_MINIMUM_MAGNITUDE = 4  # The minimum point change required to validate a trend

# --- Validation Settings ---
# Defines the time window in minutes after an alert is generated to check its outcome (profit/loss).
# This is only used when running in DEVELOPMENT mode against historical "truth" data.
VALIDATION_PERIOD_MINUTES = 10
