# src/stockreports/alert/common/requirements.py
"""
This module dynamically calculates the data requirements for each analysis approach
based on its specific configuration in the signal settings. This avoids hardcoding
and ensures that requirements adapt automatically to configuration changes.
"""
from src.stockreports.config import loader

# Load settings once
signal_settings = loader.get_signal_settings()
settings = loader.get_settings()

def get_min_required_len(approach_name: str) -> int:
    """
    Calculates the minimum number of data candles required for a given approach to run
    by finding the maximum lookback period among all its configured dependencies.

    Args:
        approach_name (str): The name of the approach (e.g., "ICHIMOKU").

    Returns:
        int: The calculated minimum number of candles.
    """
    config = signal_settings.APPROACH_CONFIG.get(
        approach_name, signal_settings.APPROACH_CONFIG.get("default", {})
    )
    
    requirements = [0] # Start with a baseline

    # --- Gather Core Logic Requirements ---
    core_reqs = {
        "ICHIMOKU": [
            config.get('TENKAN_PERIOD', 9),
            config.get('KIJUN_PERIOD', 26),
            config.get('SENKOU_B_PERIOD', 52)
        ],
        "RCM": [
            config.get("PEAK_BOTTOM_LOOKBACK_PERIOD", 0)
        ],
        "STRONG_CANDLE": [
            # Its main dependency is advanced confirmation (MACD)
            signal_settings.MACD_SLOW_PERIOD + signal_settings.MACD_SIGNAL_PERIOD
        ],
        "CONSISTENT_MOMENTUM": [
            config.get("PEAK_BOTTOM_LOOKBACK_PERIOD", 0),
            config.get("CONFIRMATION_WINDOW", 0)
        ],
        "CONSECUTIVE_POWER_CANDLES": [
            config.get("CANDLE_COUNT", 3)
        ]
    }
    requirements.extend(core_reqs.get(approach_name, []))

    # --- Gather Optional Filter Requirements ---
    if config.get("USE_MARKET_REGIME_FILTER"):
        if config.get("USE_ADX_REGIME_FILTER"):
            requirements.append(config.get("REGIME_ADX_PERIOD", 14) * 2)
        if config.get("USE_MA_REGIME_FILTER"):
            requirements.append(config.get("REGIME_MA_PERIOD", 50))
        if config.get("USE_RSI_EXHAUSTION_FILTER"):
            requirements.append(signal_settings.RSI_PERIOD)
        if config.get("USE_MACD_CONFIRMATION_FILTER"):
            requirements.append(signal_settings.MACD_SLOW_PERIOD + signal_settings.MACD_SIGNAL_PERIOD)
        if config.get("USE_DIVERGENCE_FILTER"):
            requirements.append(config.get("DIVERGENCE_LOOKBACK_PERIOD", 20))

    # --- Determine Final Requirement ---
    if not requirements:
        return 20 # A safe default
        
    # Return the single longest requirement plus a small stability buffer
    return max(requirements) + 2
