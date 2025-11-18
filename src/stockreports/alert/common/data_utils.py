import pandas as pd
import logging
from src.stockreports.alert.common.constants import Approach
from src.stockreports.config import loader
from src.stockreports.config.signal_settings import APPROACH_CONFIG

signal_settings = loader.get_signal_settings()


def get_min_data_for_indicator_confirmation(approach_name: str) -> int:
    """
    Calculates and returns the minimum number of data points required for
    the specific confirmation indicators enabled for a given approach.

    Args:
        approach_name (str): The name of the approach (e.g., 'CONSOLIDATION_BREAKOUT').

    Returns:
        int: The maximum lookback period required among all enabled indicators for the approach.
    """
    config = APPROACH_CONFIG.get(approach_name, APPROACH_CONFIG["default"])
    required_periods = [1]  # Default to 1 to avoid errors with max() on an empty list

    # --- Ichimoku Cloud ---
    # Ichimoku has a unique lookback calculation due to its forward-shifting spans.
    # It's often a component of other strategies, so we calculate its requirement.
    kijun_period = getattr(signal_settings, 'KIJUN_PERIOD', 26)
    senkou_b_period = getattr(signal_settings, 'ICHI_SENKOU_B_PERIOD', 52)
    # The total lookback is the calculation period of the longest span (Senkou B)
    # plus the amount it's shifted forward (Kijun period).
    ichimoku_total_lookback = senkou_b_period + kijun_period
    required_periods.append(ichimoku_total_lookback)

    # --- Standard Indicator Checks ---
    if config.get("USE_SHORT_TERM_MA_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MA_SHORT_PERIOD', 5))

    if config.get("USE_MA_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MA_LONG_PERIOD', 10))

    if config.get("USE_LONG_TERM_MA_FILTER", False):
        required_periods.append(getattr(signal_settings, 'MA_LONG_TERM_PERIOD', 50))

    if config.get("USE_RSI_CONFIRMATION", False) or config.get("USE_RSI_EXHAUSTION_FILTER", False):
        required_periods.append(getattr(signal_settings, 'RSI_PERIOD', 14))

    if config.get("USE_MACD_CONFIRMATION", False):
        required_periods.append(getattr(signal_settings, 'MACD_SLOW_PERIOD', 26))

    if config.get("USE_ADX_CONFIRMATION", False) or config.get("USE_ADX_FILTER", False):
        # ADX needs more data to stabilize; 2x the period is a safe rule of thumb.
        required_periods.append(getattr(signal_settings, 'ADX_PERIOD', 14) * 2)
    
    if config.get("USE_BB_WIDTH_FILTER", False):
        required_periods.append(getattr(signal_settings, 'BBANDS_PERIOD', 20))

    return max(required_periods)


def can_apply_analysis(df: pd.DataFrame, approach_name: str, required_rows: int = 0) -> bool:
    """
    Checks if the dataframe has enough data to apply the analysis for a given approach.
    It considers both the requirements for technical indicators and any specific
    row count needed by the calling logic (e.g., a pattern window size).
    """
    # 1. Check for indicator confirmation data requirements
    min_indicator_len = get_min_data_for_indicator_confirmation(approach_name)

    # 2. Determine the overall minimum required length
    # This will be the larger of the indicator requirement or the specific row requirement
    min_len = max(min_indicator_len, required_rows)

    if len(df) < min_len:
        symbol = df.iloc[0]['symbol'] if 'symbol' in df.columns and not df.empty else 'N/A'
        logging.warning(
            f"Skipping '{approach_name}' for {symbol}: requires {min_len} candles, "
            f"but only {len(df)} are available. (Indicator requirement: {min_indicator_len}, "
            f"Pattern requirement: {required_rows})"
        )
        return False
    return True
