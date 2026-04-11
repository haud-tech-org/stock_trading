"""REVERSAL_ANCHOR_SIGNAL_CANDLE approach module.

Detects potential trend reversals by analyzing anchor candles with large bodies,
signal candles with high volume, and alert candles with specific wick characteristics.
"""

from src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.executor import (
    ReversalAnchorSignalCandleExecutor,
)
from src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.analyzer import (
    ReversalAnchorSignalCandleAnalyzer,
)
from src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.validator import (
    ReversalAnchorSignalCandleValidator,
)
from src.stockreports.alert.approach.REVERSAL_ANCHOR_SIGNAL_CANDLE.settings import (
    ReversalAnchorSignalCandleSettings,
)

__all__ = [
    "ReversalAnchorSignalCandleExecutor",
    "ReversalAnchorSignalCandleAnalyzer",
    "ReversalAnchorSignalCandleValidator",
    "ReversalAnchorSignalCandleSettings",
]
