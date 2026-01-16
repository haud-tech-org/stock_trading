import pandas as pd
from src.stockreports.alert.common.constants import Signal
from typing import Tuple, Optional
import logging

from src.stockreports.config.signal_settings import VOLUME_MULTIPLIER

logger = logging.getLogger(__name__)

def validate_reversal_confirmation(
    confirmation_df: pd.DataFrame, 
    reversal_signal: Signal, 
    min_alert_body_size: float,
    max_distance_close_price: float = 2.0,
    min_volume_multiplier: float = VOLUME_MULTIPLIER
) -> Optional[Tuple[pd.Series, pd.Series]]:
    """
    Validates the reversal confirmation logic, focusing on identifying the
    alert and anchor candles within a given confirmation window.

    Args:
        confirmation_df: The DataFrame for the confirmation window.
        reversal_signal: The potential signal (BUY or SELL).
        min_alert_body_size: The minimum required body size for the alert candle.
        max_distance_close_price: The max distance between the anchor and alert candle close prices. Defaults to 2.0.
        min_volume_multiplier: The minimum volume multiplier for volume profile validation. Defaults to global setting.

    Returns:
        A tuple of (alert_candle, anchor_candle) if validation passes,
        otherwise None.
    """
    alert_candle = confirmation_df.iloc[-1]
    alert_time = alert_candle['time']

    # Step 1: Validate Alert Candle Direction
    if reversal_signal == Signal.SELL and not (alert_candle['close'] < alert_candle['open']):
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 1): Alert candle is not bearish for a SELL signal.")
        return None
    if reversal_signal == Signal.BUY and not (alert_candle['close'] > alert_candle['open']):
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 1): Alert candle is not bullish for a BUY signal.")
        return None
    
    # Step 2: Validate Alert Candle Body Size
    alert_body_size = abs(alert_candle['close'] - alert_candle['open'])
    if alert_body_size < min_alert_body_size:
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 2): Alert candle body size ({alert_body_size:.2f}) is less than min ({min_alert_body_size}).")
        return None

    # Step 3: Volume Profile Validation
    if len(confirmation_df) >= 3:
        # Find the candles with minimum and maximum volume.
        min_vol_candle = confirmation_df.loc[confirmation_df['volume'].idxmin()]
        max_vol_candle = confirmation_df.loc[confirmation_df['volume'].idxmax()]

        # Validation 1: Max volume must be significantly larger than min volume.
        if not (max_vol_candle['volume'] >= min_vol_candle['volume'] * min_volume_multiplier):
            logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Volume Validation): Max volume ({max_vol_candle['volume']}) is not >= {min_volume_multiplier}x the min volume ({min_vol_candle['volume']}).")
            return None

        # Validation 2: Min volume must occur before max volume.
        if not (min_vol_candle['time'] < max_vol_candle['time']):
            logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Volume Validation): Minimum volume at {min_vol_candle['time']} did not occur before maximum volume at {max_vol_candle['time']}.")
            return None

        # Validation 3: The alert candle must occur after the min volume candle.
        if not (alert_candle['time'] > min_vol_candle['time']):
            logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Volume Validation): Alert candle at {alert_candle['time']} did not occur after the minimum volume candle at {min_vol_candle['time']}.")
            return None

    # Step 4: Identify Anchor Candle
    if reversal_signal == Signal.SELL:
        # For a SELL reversal, the anchor is the highest-closing green candle in the confirmation window.
        trend_candles_df = confirmation_df[confirmation_df['close'] > confirmation_df['open']]
        if trend_candles_df.empty:
            logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 4): No bullish candles found to serve as an anchor for a SELL signal.")
            return None
        anchor_candle_idx = trend_candles_df['close'].idxmax()
    else:  # BUY
        # For a BUY reversal, the anchor is the lowest-closing red candle in the confirmation window.
        trend_candles_df = confirmation_df[confirmation_df['close'] < confirmation_df['open']]
        if trend_candles_df.empty:
            logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 4): No bearish candles found to serve as an anchor for a BUY signal.")
            return None
        anchor_candle_idx = trend_candles_df['close'].idxmin()
    
    # The anchor must appear before the alert candle.
    if anchor_candle_idx >= alert_candle.name:
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 4): Identified anchor is not before the alert candle.")
        return None
    
    anchor_candle = confirmation_df.loc[anchor_candle_idx]

    # Step 5: Validate Distance Between Anchor and Alert Close Prices
    distance = abs(alert_candle['close'] - anchor_candle['close'])
    if distance > max_distance_close_price:
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 5): Distance between closes ({distance:.2f}) exceeds max ({max_distance_close_price}).")
        return None

    # Step 6: Final Reversal Confirmation (Engulfing/Piercing Logic)
    anchor_body_avg = (anchor_candle['open'] + anchor_candle['close']) / 2
    reversal_confirmed = False
    if reversal_signal == Signal.SELL:
        # For a SELL, the alert candle's close must be below the midpoint of the anchor candle's body.
        if alert_candle['close'] < anchor_body_avg:
            reversal_confirmed = True
    else:  # BUY
        # For a BUY, the alert candle's close must be above the midpoint of the anchor candle's body.
        if alert_candle['close'] > anchor_body_avg:
            reversal_confirmed = True
    
    if not reversal_confirmed:
        logger.debug(f"[{__name__}] [{alert_time}] Reversal Fail (Step 6): Final confirmation failed. Alert close {alert_candle['close']:.2f} did not pass anchor midpoint {anchor_body_avg:.2f}.")
        return None

    logger.debug(f"[{__name__}] [{alert_time}] Reversal validation passed.")
    return alert_candle, anchor_candle
