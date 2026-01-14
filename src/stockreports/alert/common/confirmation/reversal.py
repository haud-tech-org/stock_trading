import pandas as pd
from src.stockreports.alert.common.constants import Signal
from typing import Tuple, Optional

def validate_reversal_confirmation(
    confirmation_df: pd.DataFrame, 
    reversal_signal: Signal, 
    min_alert_body_size: float,
    max_distance_close_price: float = 2.0
) -> Optional[Tuple[pd.Series, pd.Series]]:
    """
    Validates the reversal confirmation logic, focusing on identifying the
    alert and anchor candles within a given confirmation window.

    Args:
        confirmation_df: The DataFrame for the confirmation window.
        reversal_signal: The potential signal (BUY or SELL).
        min_alert_body_size: The minimum required body size for the alert candle.
        max_distance_close_price: The max distance between the anchor and alert candle close prices. Defaults to 2.0.

    Returns:
        A tuple of (alert_candle, anchor_candle) if validation passes,
        otherwise None.
    """
    alert_candle = confirmation_df.iloc[-1]

    # Alert Candle Validation (Cheap Checks)
    if reversal_signal == Signal.SELL and not (alert_candle['close'] < alert_candle['open']):
        return None
    if reversal_signal == Signal.BUY and not (alert_candle['close'] > alert_candle['open']):
        return None
    
    if abs(alert_candle['close'] - alert_candle['open']) < min_alert_body_size:
        return None

    # Anchor Candle Identification (More Expensive)
    if reversal_signal == Signal.SELL:
        trend_candles_df = confirmation_df[confirmation_df['close'] > confirmation_df['open']]
        if trend_candles_df.empty:
            return None
        anchor_candle_idx = trend_candles_df['close'].idxmax()
    else:  # BUY
        trend_candles_df = confirmation_df[confirmation_df['close'] < confirmation_df['open']]
        if trend_candles_df.empty:
            return None
        anchor_candle_idx = trend_candles_df['close'].idxmin()
    
    if anchor_candle_idx >= alert_candle.name:
        return None
    
    anchor_candle = confirmation_df.loc[anchor_candle_idx]

    # New Validation: Check distance between anchor and alert close prices
    if abs(alert_candle['close'] - anchor_candle['close']) > max_distance_close_price:
        return None

    # Final Reversal Check (Complex)
    anchor_body_avg = (anchor_candle['open'] + anchor_candle['close']) / 2
    reversal_confirmed = False
    if reversal_signal == Signal.SELL:
        if alert_candle['close'] < anchor_body_avg:
            reversal_confirmed = True
    else:  # BUY
        if alert_candle['close'] > anchor_body_avg:
            reversal_confirmed = True
    
    if not reversal_confirmed:
        return None

    return alert_candle, anchor_candle
