# src/stockreports/config/signal_settings.py
"""
Centralized settings for all signal calculation logic.
This ensures consistency between backtesting and real-time monitoring.
"""

# --- Signal Indicator Parameters ---

# -- Moving Averages --
MA_SHORT_PERIOD = 5  # Lookback for fastest moving average (immediate momentum).
MA_LONG_PERIOD = 10 # Lookback for slowest moving average (long-term trend).
MA_LONG_TERM_PERIOD = 50 # Lookback for the primary trend direction filter.

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

# -- ADX (Average Directional Index) settings --
ADX_PERIOD = 14  # Lookback period for calculating ADX (trend strength).
ADX_CONFIRMATION_THRESHOLD = 21 # Minimum ADX value to consider a trend strong enough for confirmation.

# -- RSI (Relative Strength Index) settings --
RSI_PERIOD = 14 # Lookback period for calculating RSI.
RSI_BULLISH_THRESHOLD = 50 # RSI must be above this value for bullish confirmation.
RSI_BEARISH_THRESHOLD = 50 # RSI must be below this value for bearish confirmation.

# -- MACD (Moving Average Convergence Divergence) settings --
MACD_FAST_PERIOD = 12   # Lookback for the fast EMA.
MACD_SLOW_PERIOD = 26   # Lookback for the slow EMA.
MACD_SIGNAL_PERIOD = 9  # Lookback for the signal line EMA.

# -- Bollinger Bands --
BBANDS_PERIOD = 20
BBANDS_STDDEV = 2.0


# -- Volume Settings --
VOLUME_MULTIPLIER = 2.0 # Default multiplier for volume profile validation.


# --- SUPPORT_BREAKDOWN Specific Settings ---
# Lookback period for average volume to confirm a breakdown.
# If set to None, the average is calculated from the start of the trading day.
# If set to an integer, it's a fixed lookback period of that many candles.
SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD = None
# Breakdown candle volume must be at least 1.5x the average volume.
SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER = 1.2

# --- Close Position Scheduler ---
# The number of minutes to wait after a signal is sent before sending a "Close Position" notification.
# This also serves as the validation period in development mode.
# Set to None to disable the scheduler.
CLOSE_POSITION_DELAY_MINUTES = 10


# --- Approach-Specific Configurations ---
# This dictionary holds the detailed parameters for each alert approach.
# Fine-tunes parameters for each alerting strategy.
# The "default" block applies to any approach not explicitly defined.
APPROACH_CONFIG = {
    "default": {
        "PEAK_TROUGH_PROMINENCE": 5,
        "CONFIRMATION_WINDOW": 4,
        "CONFIRMATION_MIN_CONSISTENCY": 2
    },
    "RCM": {
        "PEAK_TROUGH_PROMINENCE": 2,
        "CONFIRMATION_WINDOW": 3,
        "CONFIRMATION_MIN_CONSISTENCY": 2,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_VOLUME_INCREASING_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "PEAK_BOTTOM_LOOKBACK_PERIOD": 30,
        "MIN_ALERT_MAGNITUDE": 2,
        "USE_DIVERGENCE_CONFIRMATION": False,
        "USE_MA_CONFIRMATION": True,
        "USE_ADX_CONFIRMATION": True,
        "USE_RSI_CONFIRMATION": False,
        "RSI_OVERSOLD_THRESHOLD": 30,
        "RSI_OVERBOUGHT_THRESHOLD": 70,
        "USE_SHORT_TERM_MA_CONFIRMATION": False,
        "USE_LONG_TERM_MA_CONFIRMATION": False,
        "USE_MACD_CONFIRMATION": False,
        "NUM_CANDLES_FOR_RSI_CHECK": 1
    },
    "CONSOLIDATION_BREAKOUT": {
        # --- Main Consolidation Logic: Price Clustering ---
        # Defines the range of window sizes (in candles) to check for consolidation.
        # The system will test every lookback period from the min to the max value.
        "CONSOLIDATION_LOOKBACK": [25, 30],
        # The maximum distance (in price points) a candle's close can be from the median
        # price of the window to be considered part of the "cluster".
        "MAX_DEVIATION_FROM_CENTER": 0.5,
        # The minimum percentage of candles within the window that must be inside the cluster
        # for the consolidation to be considered valid. (e.g., 0.7 = 70%).
        "MIN_CLUSTERED_CANDLE_RATIO": 0.7,

        # --- Oscillation & Sideways Movement Confirmation ---
        # The minimum number of valid peaks (highs) and troughs (lows) required in the window.
        # Confirms the price is oscillating and not just flat.
        "MIN_PEAKS_TROUGHS": 3,
        # If enabled, this enforces that the identified peaks and troughs must alternate.
        # (e.g., peak, trough, peak...). This ensures a true oscillating pattern.
        "USE_ALTERNATING_PEAKS_TROUGHS_CHECK": True,
        # How much a peak/trough must stand out from its surroundings to be considered valid.
        # Higher values reduce sensitivity to minor fluctuations.
        "PEAK_TROUGH_PROMINENCE": 1.0,

        # --- Balanced Sideways Movement Confirmation ---
        # Master switch to enable/disable the balanced sideways checks.
        "USE_BALANCED_SIDEWAYS_CHECK": True,
        # The maximum absolute slope of a linear regression line through the closing prices.
        # A value near 0 enforces a flat, horizontal trend.
        "MAX_REGRESSION_SLOPE": 0.1,
        # The maximum allowed deviation in time spent above vs. below the median price.
        # (e.g., 0.3 means the number of candles above vs. below cannot differ by more than 30% of the lookback).
        "MAX_TIME_BALANCE_DEVIATION_RATIO": 0.15,

        # --- Channel Consistency Confirmation ---
        # Master switch to enable/disable the channel consistency check.
        "USE_CHANNEL_CONSISTENCY_CHECK": True,
        # The maximum allowed ratio of "outlier" candles (candles that close outside the
        # core channel defined by the clustered candles). Prevents erratic price action.
        "MAX_CHANNEL_OUTLIER_RATIO": 0.2,

        # --- Consecutive Trend Confirmation ---
        # Master switch to enable/disable the consecutive trend check.
        "USE_CONSECUTIVE_TREND_CHECK": True,
        # The maximum number of consecutive candles allowed to move in the same direction.
        # Prevents slow, drifting consolidations.
        "MAX_CONSECUTIVE_TREND_CANDLES": 7,

        # --- Optional Indicator-based Filters ---
        # Master switch to enable/disable the ADX filter.
        "USE_ADX_FILTER": True,
        # The ADX value below which the market is considered non-trending.
        "ADX_THRESHOLD": 25,
        # The minimum ratio of candles in the window that must be "non-trending" (below ADX_THRESHOLD).
        "ADX_CONFIRMATION_RATIO": 0.7,

        # Master switch to enable/disable the Bollinger Band Width filter (squeeze).
        "USE_BB_WIDTH_FILTER": True,
        # The BB Width must be below this percentage of the middle band to be considered a "squeeze".
        "BB_WIDTH_THRESHOLD_PERCENT": 1.0,
        # The minimum ratio of candles in the window that must be in a "squeeze" state.
        "BB_SQUEEZE_CONFIRMATION_RATIO": 0.6,

        # --- Breakout Candle Confirmation ---
        # The number of candles to look at immediately following the consolidation window for a breakout.
        # Almost always set to 1.
        "BREAKOUT_CONFIRMATION_CANDLES": 1,

        # --- Volume Spike Confirmation ---
        # Master switch to enable/disable the volume spike check on the breakout candle.
        "USE_VOLUME_SPIKE_CONFIRMATION": True,
        # The breakout candle's volume must be at least this many times greater than the
        # average volume of the consolidation window. (e.g., 1.3 = 1.3x or 30% higher).
        "VOLUME_SPIKE_MULTIPLIER": 1.1,
        "MIN_VOLUME_SPIKE_CONFIRMATION_RATIO": 0.1,

        # --- General Indicator Confirmation ---
        # Master switch to enable the final signal confirmation step, which uses
        # a combination of indicators (MA, RSI, etc.) to validate the breakout.
        "USE_CONFIRMATION": True,
        "USE_SHORT_TERM_MA_CONFIRMATION": True,
        "USE_MA_CONFIRMATION": True
    },
    "CONSISTENT_MOMENTUM": {
        # --- Core Algorithm Parameters ---
        "LOOKBACK_WINDOW": 5,              # Number of candles to analyze for consistency
        "MIN_CONSISTENT_CANDLES": 3,       # Minimum consecutive consistent candles required
        "MAGNITUDE_THRESHOLD": 4.5,        # Fixed alert magnitude
        "COOLDOWN_WINDOW": 5,              # Minutes to wait before next alert of same signal
        # --- Volume Validation Parameters ---
        "MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD": 1.5,  # Max volume <= Min volume * this threshold
        # --- Confirmation Window Price Range Parameters ---
        "MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD": 1.0,    # Minimum price range in confirmation window
        "MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD": 4.0,    # Maximum price range in confirmation window
        # --- Confirmation Window Gap Validation Parameters ---
        "MAX_CONFIRMATION_GAP_THRESHOLD": 0.5              # Maximum allowed gap between consecutive candles in the confirmation window
    },
    "SUPPORT_RESISTANCE_BREAK": {
        "LOOKBACK_PERIOD": 50,
        "CONFIRMATION_WINDOW": 3,
        "CONSISTENCY_THRESHOLD": 2,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_VOLUME_INCREASING_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "USE_BB_SQUEEZE_CONFIRMATION": True,
        "BB_SQUEEZE_LOOKBACK": 40,
        "BB_SQUEEZE_THRESHOLD_RATIO": 0.08,
        "USE_MA_CONFIRMATION": True,
        "USE_ADX_CONFIRMATION": True,
        "USE_SHORT_TERM_MA_CONFIRMATION": True,
        "USE_LONG_TERM_MA_CONFIRMATION": False,
        "USE_MACD_CONFIRMATION": False,
        "USE_RSI_CONFIRMATION": False,
        "NUM_CANDLES_FOR_RSI_CHECK": 1,
        "RSI_OVERSOLD_THRESHOLD": 30,
        "RSI_OVERBOUGHT_THRESHOLD": 70
    },
    "ICHIMOKU": {
        "TENKAN_SEN_PERIOD": 9,
        "KIJUN_SEN_PERIOD": 26,
        "SENKOU_SPAN_B_PERIOD": 52,
        "CHIKOU_SPAN_PERIOD": 26,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_VOLUME_INCREASING_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": False,
        "SKIP_CHIKOU_CONFIRMATION": False,      # (optional, for future code support)
        "MIN_BARS_BETWEEN_ALERTS": 10,           # Minimum bars between consecutive alerts
        "USE_SHORT_TERM_MA_CONFIRMATION": False,
        "USE_ADX_CONFIRMATION": False,
        "USE_MA_CONFIRMATION": False,
        "USE_RSI_CONFIRMATION": True,
        "RSI_OVERSOLD_THRESHOLD": 30,
        "RSI_OVERBOUGHT_THRESHOLD": 70,
        "USE_MACD_CONFIRMATION": False,
        "USE_LONG_TERM_MA_CONFIRMATION": False,
        "NUM_CANDLES_FOR_RSI_CHECK": 1,
        "USE_DIVERGENCE_FILTER": False,
        "DIVERGENCE_LOOKBACK_PERIOD": 20,
        "DIVERGENCE_RSI_PERIOD": 14,
        "DIVERGENCE_PRICE_PROMINENCE": 0.5,
        "DIVERGENCE_RSI_PROMINENCE": 2.0,
        "USE_CONFIRMATION_CANDLE_FILTER": True,
        "CONFIRMATION_CANDLE_COUNT": 1
    },
    "STRONG_CANDLE": {
        "LOOKBACK_WINDOW": 6,
        "MIN_BODY_RATIO": 0.7,
        "MIN_BODY_SIZE": 2.1,
        "MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE": 1.0,
        "MIN_DIFFERENCE_PRICE_THRESHOLD": 3.0,
        "MAX_DIFFERENCE_PRICE_THRESHOLD": 5.5,
        "MAX_VOLUME_MULTIPLIER": 1.5,
        "MAGNITUDE_THRESHOLD": 4.5,
        "COOLDOWN_WINDOW": 3
    },
    "MOMENTUM_EXHAUSTION": {
        "LOOKBACK_WINDOW": 10,
        "PRE_WINDOW_VOLUME_MULTIPLIER": 3.0,
        "POST_WINDOW_VOLUME_MULTIPLIER": 3.5,
        "REVERSAL_VOLUME_MULTIPLIER": 1.2,
        "POST_CLIMAX_PRICE_PROXIMITY_THRESHOLD": 1.5,
        "COOLDOWN_WINDOW": 5
    },
    "CONSECUTIVE_POWER_CANDLES": {
        "LOOKBACK_WINDOW": 15,
        "CONSECUTIVE_WINDOW_SIZE": 2,
        "MIN_CONSOLIDATED_BODY_RATIO": 0.8,
        "MIN_CONSECUTIVE_CANDLE_BODY_SIZE": 2.0,
        "MIN_CONSOLIDATED_BODY_SIZE": 2.5,
        "MAX_CONDITIONAL_CANDLE_BODY_SIZE": 2.0,
        "MAX_DIFFERENCE_PRICE_THRESHOLD": 1.5,
        "TREND_WINDOW_EDGE_SLICE": 3,
        "MAX_VOLUME_MULTIPLIER": 1.5,
        "COOLDOWN_WINDOW": 3
    },
    "PRICE_GAP": {
        "LOOKBACK_WINDOW": 10,
        "MIN_GAP_CANDLE_SIZE": 2.0,
        "MIN_ALERT_BODY_SIZE": 1.0,
        "ENABLE_MARKET_TREND_VALIDATION": False,
        "IMPACT_SYMBOLS_MIN_BODY_TO_RANGE_RATIO": 0.3,
        "VOLUME_MULTIPLIER": 2.0,
        "COOLDOWN_WINDOW": 3,
    },
    # --- VRA (Volume-Reversal-Anchor) ---
    "VRA": {
        "LOOKBACK_WINDOW": 7,
        "VOLUME_MULTIPLIER": 4.5,
        "MIN_TREND_MAGNITUDE": 6.5,

        # --- VRA Trend Window Edge Slice ---
        "TREND_WINDOW_EDGE_SLICE": 3,  # Number of candles from the edge for open price extremes validation in VRA
        "COOLDOWN_WINDOW": 3
    },

    # --- COMPARISON ---
    "COMPARISON": {
        "PRIMARY_SYMBOL": "VN30F1M",
        "REFERENCE_SYMBOL": "VN30",
        "LOOKBACK_WINDOW": 20,
        "DISABLE_BUY_SIGNAL": False,
        "DISABLE_SELL_SIGNAL": False,
        "MAX_PRIMARY_TREND_MAGNITUDE": 2.5,
        "MIN_PRIMARY_TREND_MAGNITUDE": 0.2,
        "MIN_ALERT_BODY_SIZE": 0.5,
        "MAX_DISTANCE_CLOSE_PRICE": 2.0,
        "ENABLE_MARKET_TREND_VALIDATION": False,
        "MIN_MARKET_PRICE_CHANGE": 0.1,
        "COOLDOWN_WINDOW": 3,
        "IMPACT_SYMBOLS_MIN_BODY_TO_RANGE_RATIO": 0.3,
        "VOLUME_MULTIPLIER": 2.5
    },
    "PROMINENT_PEAK_REVERSAL": {
        "LOOKBACK_WINDOW": 30,
        "CONFIRMATION_WINDOW": 6,
        "PEAK_PROMINENCE": 6.0,
        "USE_PEAK_IN_LOOKBACK_VALIDATION": True,
        "WICK_TO_BODY_RATIO": 0.7,
        "MIN_BODY_POINT_PRICE": 1.0,
        "MIN_REVERSAL_PRICE_DIFF": 1.5,
        "VOLUME_MULTIPLIER": 1.5,
        "COOLDOWN_WINDOW": 5,
        "DISABLE_SELL_SIGNAL": False,
        "DISABLE_BUY_SIGNAL": False
    },
    "VOLUME_SPIKE_CONFIRMATION": {
        "LOOKBACK_WINDOW": 5,
        "COOLDOWN_WINDOW": 3,
        "MIN_TREND_WINDOW_SIZE": 5.0,
        "MIN_TREND_CANDLE_SLICE": 3,
        "TREND_VOLUME_MULTIPLIER": 5.0
    },
    # --- TREND REVERSAL ---
    "TREND_REVERSAL": {
        "LOOKBACK_WINDOW": 15,
        "MIN_PRE_VOLUME_MULTIPLIER": 5.0,
        "MIN_POST_VOLUME_MULTIPLIER": 2.0,
        "MIN_ADJACENT_VOLUME_MULTIPLIER": 2.0,
        "MIN_TREND_MAGNITUDE": 4.5,
        "COOLDOWN_WINDOW": 3
    },
    "VOLUME_REVERSAL": {
        "LOOKBACK_WINDOW": 5,
        "MAX_VOLUME_MULTIPLIER": 3.0,
        "MIN_VOLUME_MULTIPLIER": 2.0,
        "MAX_WINDOW_SIZE_THRESHOLD": 3.0,
        "MIN_WINDOW_SIZE_THRESHOLD": 0.5,
    },

    # --- SESSION EXTREME VOLUME REVERSAL ---
    "SESSION_EXTREME_VOLUME_REVERSAL": {
        # Minimum multiplier for alert candle volume vs. average session volume
        "MIN_VOLUME_MULTIPLIER": 3.5,
        "MAGNITUDE_THRESHOLD": 6.5,
        "LOOKBACK_WINDOW": 10,
        "COOLDOWN_WINDOW": 3
    },

    # --- CONSISTENT VOLUME ANCHOR (CVA) ---
    "CONSISTENT_VOLUME_ANCHOR": {
        # Lookback window to analyze volume patterns
        "LOOKBACK_WINDOW": 10,
        
        # Consistent volume window: from anchor to last candle - 1
        "MAX_CONSISTENT_VOLUME_MULTIPLIER": 1.3,  # max_vol <= 1.x * min_vol in window
        "CONSISTENT_CANDLE_PERCENTAGE": 0.7,  # xx% of candles must satisfy volume condition
        "MAX_CONSISTENT_WINDOW_SIZE": 1.5,  # max window size in price points
        
        # Consistent window body size validation
        "MAX_CONSISTENT_BODY_SIZE_CANDLE": 0.5,  # Max body size for candles in consistent window
        
        # Alert candle validation (last candle)
        "MIN_VOLUME_CONFIRMATION_MULTIPLIER": 1.5,  # alert_vol >= x.x * min_vol in consistent window
        "MIN_BODY_SIZE_ALERT_CANDLE": 0.3,  # minimum body size (in price points)
        
        # Alert magnitude
        "MIN_ALERT_MAGNITUDE": 2.5,  # Minimum window size (price range) for alert
        
        "COOLDOWN_WINDOW": 3
    },
}

