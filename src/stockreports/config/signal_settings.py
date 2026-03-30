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
    "CONSISTENT_MOMENTUM": {
        # --- Core Algorithm Parameters ---
        "LOOKBACK_WINDOW": 5,              # Number of candles to analyze for consistency
        "MIN_CONSISTENT_CANDLES": 3,       # Minimum consecutive consistent candles required
        "MAGNITUDE_THRESHOLD": 6.5,        # Fixed alert magnitude
        "COOLDOWN_WINDOW": 5,              # Minutes to wait before next alert of same signal
        # --- Volume Validation Parameters ---
        "MAX_MULTIPLIER_DIFFERENCE_VOLUME_THRESHOLD": 1.5,  # Max volume <= Min volume * this threshold
        # --- Confirmation Window Price Range Parameters ---
        "MIN_CONFIRMATION_WINDOW_PRICE_THRESHOLD": 1.0,    # Minimum price range in confirmation window
        "MAX_CONFIRMATION_WINDOW_PRICE_THRESHOLD": 4.0,    # Maximum price range in confirmation window
        # --- Confirmation Window Gap Validation Parameters ---
        "MAX_CONFIRMATION_GAP_THRESHOLD": 0.5              # Maximum allowed gap between consecutive candles in the confirmation window
    },
    "ICHIMOKU": {
        "TENKAN_PERIOD": 9,
        "KIJUN_PERIOD": 26,
        "SENKOU_B_PERIOD": 52,
        "CHIKOU_PERIOD": 26,
        "SENKOU_SHIFT_PERIOD": 26,
        "SKIP_CHIKOU_CONFIRMATION": False,
        "SKIP_CLOUD_VALIDATION": False,
        "MAGNITUDE_THRESHOLD": 8.5,        # Fixed alert magnitude for Ichimoku signals
    },
    "STRONG_CANDLE": {
        "LOOKBACK_WINDOW": 6,
        "MIN_BODY_RATIO": 0.7,
        "MIN_BODY_SIZE": 2.1,
        "MAX_OPPOSITE_COLOR_CANDLE_BODY_SIZE": 1.0,
        "MIN_DIFFERENCE_PRICE_THRESHOLD": 3.0,
        "MAX_DIFFERENCE_PRICE_THRESHOLD": 5.5,
        "MAX_VOLUME_MULTIPLIER": 1.5,
        "MAGNITUDE_THRESHOLD": 6.5,
        "COOLDOWN_WINDOW": 10
    },
    # --- VRA (Volume-Reversal-Anchor) ---
    "VRA": {
        "LOOKBACK_WINDOW": 15,
        "VOLUME_MULTIPLIER": 6.0,
        "MIN_TREND_MAGNITUDE": 9.5,

        # --- VRA Trend Window Edge Slice ---
        "TREND_WINDOW_EDGE_SLICE": 3,  # Number of candles from the edge for open price extremes validation in VRA
        
        # --- VRA Confirmation Window Validation ---
        "MIN_CONFIRMATION_WINDOW_CANDLES": 3,  # Minimum candles required in confirmation window (from max volume to end) for reversal consistency validation
        
        # --- VRA Max Volume to Alert Candle Validation ---
        "VOLUME_MULTIPLIER_BY_REVERSAL_TREND": 2.0,  # Multiplier for validating max candle volume >= alert candle volume * this factor
        
        # --- VRA Peak/Trough Prominence Validation ---
        "MIN_PEAK_TROUGH_PROMINENCE": 1.5,  # Minimum prominence required for anchor candle (peak for uptrend, trough for downtrend)
        "MAX_PEAK_TROUGH_PROMINENCE": 3.0,  # Maximum prominence allowed for anchor candle (peak for uptrend, trough for downtrend)
        
        "COOLDOWN_WINDOW": 3
    },
    "VOLUME_SPIKE_CONFIRMATION": {
        "LOOKBACK_WINDOW": 5,
        "COOLDOWN_WINDOW": 3,
        "MIN_TREND_WINDOW_SIZE": 6.5,
        "MIN_TREND_CANDLE_SLICE": 3,
        "TREND_VOLUME_MULTIPLIER": 5.0
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
        "MIN_BODY_RATIO": 0.6,  # Minimum body ratio (body / (high - low)) for alert candle
        
        # Alert magnitude
        "MIN_ALERT_MAGNITUDE": 2.5,  # Minimum window size (price range) for alert
        
        "COOLDOWN_WINDOW": 3
    },
}

