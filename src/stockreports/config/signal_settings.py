# src/stockreports/config/signal_settings.py
"""
Centralized settings for all signal calculation logic.
This ensures consistency between backtesting and real-time monitoring.
"""

# --- Signal Indicator Parameters ---

# -- Moving Averages --
MA_SHORT_PERIOD = 5  # Lookback for fastest moving average (immediate momentum).
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


# --- SUPPORT_BREAKDOWN Specific Settings ---
# Lookback period for average volume to confirm a breakdown.
# If set to None, the average is calculated from the start of the trading day.
# If set to an integer, it's a fixed lookback period of that many candles.
SUPPORT_BREAKDOWN_VOLUME_AVG_PERIOD = None
# Breakdown candle volume must be at least 1.5x the average volume.
SUPPORT_BREAKDOWN_VOLUME_SPIKE_MULTIPLIER = 1.5


# --- Approach-Specific Configurations ---
# Fine-tunes parameters for each alerting strategy.
# The "default" block applies to any approach not explicitly defined.
APPROACH_CONFIG = {
    "default": {
        "PEAK_TROUGH_PROMINENCE": 5,
        "CONFIRMATION_WINDOW": 4,
        "CONFIRMATION_MIN_CONSISTENCY": 2
    },
    "RCM": {
        "PEAK_TROUGH_PROMINENCE": 3,
        "CONFIRMATION_WINDOW": 3,
        "CONFIRMATION_MIN_CONSISTENCY": 3,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_INCREASING_VOLUME_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "PEAK_BOTTOM_LOOKBACK_PERIOD": 60,
        "MIN_ALERT_MAGNITUDE": 4,
        "USE_MARKET_REGIME_FILTER": True,
        "USE_MA_REGIME_FILTER": True,
        "REGIME_MA_PERIOD": 50,
        "USE_ADX_REGIME_FILTER": True,
        "REGIME_ADX_PERIOD": 14,
        "REGIME_ADX_THRESHOLD": 20
    },
    "CONSISTENT_MOMENTUM": {
        "REVERSAL_CANDLE_BODY_RATIO": 0.3,
        "USE_MARKET_REGIME_FILTER": True,
        "REGIME_MA_PERIOD": 50,
        "REGIME_ADX_THRESHOLD": 20,
        "PEAK_TROUGH_PROMINENCE": 10,
        "USE_REALTIME_REVERSAL_CONFIRMATION": True,
        "REALTIME_REVERSAL_CONFIRMATION_WINDOW": 2,
        "PEAK_BOTTOM_LOOKBACK_PERIOD": 60,
        "CONFIRMATION_WINDOW": 3,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_INCREASING_VOLUME_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "BODY_TO_RANGE_MIN_RATIO": 0.3
    },
    "SUPPORT_RESISTANCE_BREAK": {
        "LOOKBACK_PERIOD": 50,
        "CONFIRMATION_WINDOW": 3,
        "CONSISTENCY_THRESHOLD": 2,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_INCREASING_VOLUME_CONFIRMATION": True,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "USE_BB_SQUEEZE_CONFIRMATION": True,
        "BB_SQUEEZE_LOOKBACK": 40,
        "BB_SQUEEZE_THRESHOLD_RATIO": 0.08,
        "USE_MARKET_REGIME_FILTER": True,
        "USE_MA_REGIME_FILTER": True,
        "REGIME_MA_PERIOD": 50,
        "USE_ADX_REGIME_FILTER": True,
        "REGIME_ADX_PERIOD": 14,
        "REGIME_ADX_THRESHOLD": 20
    },
    "ICHIMOKU": {
        "TENKAN_SEN_PERIOD": 9,
        "KIJUN_SEN_PERIOD": 26,
        "SENKOU_SPAN_B_PERIOD": 52,
        "CHIKOU_SPAN_PERIOD": 26,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_INCREASING_VOLUME_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "SKIP_CHIKOU_CONFIRMATION": False,      # (optional, for future code support)
        "MIN_BARS_BETWEEN_ALERTS": 10,           # Minimum bars between consecutive alerts
        "USE_MARKET_REGIME_FILTER": True,
        "USE_ADX_REGIME_FILTER": True,
        "REGIME_ADX_PERIOD": 14,
        "REGIME_ADX_THRESHOLD": 25,
        "USE_MA_REGIME_FILTER": False,
        "USE_RSI_EXHAUSTION_FILTER": True,
        "RSI_OVERSOLD_THRESHOLD": 30,
        "RSI_OVERBOUGHT_THRESHOLD": 70,
        "USE_MACD_CONFIRMATION_FILTER": True,
        "USE_DIVERGENCE_FILTER": True,
        "DIVERGENCE_LOOKBACK_PERIOD": 20,
        "DIVERGENCE_RSI_PERIOD": 14,
        "DIVERGENCE_PRICE_PROMINENCE": 0.5,
        "DIVERGENCE_RSI_PROMINENCE": 2.0,
        "USE_CONFIRMATION_CANDLE_FILTER": True,
        "CONFIRMATION_CANDLE_COUNT": 1
    },
    "STRONG_CANDLE": {
        "CONFIRMATION_WINDOW": 2,
        "CONSISTENCY_THRESHOLD": 2,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_INCREASING_VOLUME_CONFIRMATION": True,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        "MIN_ALERT_MAGNITUDE": 5,
        "USE_MARKET_REGIME_FILTER": True,
        "USE_MA_REGIME_FILTER": True,
        "REGIME_MA_PERIOD": 50,
        "USE_ADX_REGIME_FILTER": True,
        "REGIME_ADX_PERIOD": 14,
        "REGIME_ADX_THRESHOLD": 20
    },
    "MOMENTUM_EXHAUSTION": {
        "CONFIRMATION_WINDOW": 5,
        "MOMENTUM_CANDLE_COUNT": 5,
        "EXHAUSTION_CANDLE_COUNT": 5,
        "USE_VOLUME_CONFIRMATION": False,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": False,
        "SMA_SLOPE_THRESHOLD": 0.05
    },
    "CONSECUTIVE_POWER_CANDLES": {
        "CANDLE_COUNT": 2,
        "MIN_BODY_TO_RANGE_RATIO": 0.7,
        "USE_VOLUME_CONFIRMATION": True,
        "USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION": True,
        # Defines min body size for each candle *before* the final one.
        # The list length should be CANDLE_COUNT - 1.
        "MIN_PRE_CANDLE_BODY_SIZES": [1.5],
        "USE_MARKET_REGIME_FILTER": True,
        "REGIME_MA_PERIOD": 50,
        "USE_ADX_REGIME_FILTER": True,
        "REGIME_ADX_PERIOD": 14,
        "REGIME_ADX_THRESHOLD": 20
    }
}

# --- Trend Validation Settings ---
# The minimum change in price points required for a trend to be considered significant.
# TREND_MINIMUM_MAGNITUDE = 4

# --- Validation Settings ---
# Defines the time window in minutes after an alert to check its outcome (profit/loss).
# Used only in DEVELOPMENT mode against historical data.
VALIDATION_PERIOD_MINUTES = 10
