class Approach:
    STRONG_CANDLE = "STRONG_CANDLE"
    CONSISTENT_MOMENTUM = "CONSISTENT_MOMENTUM"
    ICHIMOKU = "ICHIMOKU"
    VOLUME_SPIKE_CONFIRMATION = "VOLUME_SPIKE_CONFIRMATION"
    VRA = "VRA"
    CONSISTENT_VOLUME_ANCHOR = "CONSISTENT_VOLUME_ANCHOR"

class Mode:
    DEVELOPMENT = "DEVELOPMENT"
    DEPLOYMENT = "DEPLOYMENT"

class Signal:
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"

class Trend:
    UPTREND = "uptrend"
    DOWNTREND = "downtrend"
    NEUTRAL = "neutral"

class CandleColor:
    """Candle color classification constants."""
    GREEN = "GREEN"
    RED = "RED"
    NEUTRAL = "NEUTRAL"

class Comparison:
    """Comparison operator constants."""
    GREATER = "greater"
    LESS = "less"
    EQUAL = "equal"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"

class AlertKeys:
    TREND = "trend"
    SIGNAL = "signal"

class PeakTrough:
    PEAK = "PEAK"
    TROUGH = "TROUGH"

class PriceColumn:
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"

class CandleColumn:
    """Candle column name constants for OHLCV data access."""
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"

class ValidationStatus():
    PASSED = "Passed"
    FAILED = "Failed"
    IN_PROGRESS = "In-Progress"

class LogLevel():
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
