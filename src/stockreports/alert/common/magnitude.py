"""
This module provides functions to check the magnitude of a price movement.
"""
import logging

def check_magnitude(current_price: float, reversal_price: float, signal_settings) -> tuple[bool, float]:
    """
    Checks if the magnitude of a price move meets the minimum requirement.

    Args:
        current_price: The current price of the asset.
        reversal_price: The price at the point of reversal (peak or trough).
        signal_settings: The settings object containing TREND_MINIMUM_MAGNITUDE.

    Returns:
        A tuple containing:
        - bool: True if the magnitude is sufficient, False otherwise.
        - float: The calculated magnitude.
    """
    magnitude = abs(current_price - reversal_price)
    
    min_magnitude = getattr(signal_settings, 'TREND_MINIMUM_MAGNITUDE', 0)
    if min_magnitude == 0:
        return True, round(magnitude, 2) # Magnitude check is disabled, always pass.

    is_sufficient = magnitude >= min_magnitude
    if not is_sufficient:
        logging.debug(f"Magnitude check failed. Current: {magnitude:.2f}, Required: {min_magnitude:.2f}")
        
    return is_sufficient, round(magnitude, 2)
