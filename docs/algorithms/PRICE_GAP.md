# Price Gap Approach

## Overview
The **Price Gap** approach identifies significant price gaps between the previous candle's close and the current candle's open. A gap up (Open > Previous Close) is generally considered a bullish signal, indicating strong buying pressure at the open.

## Logic
1.  **Gap Detection**:
    *   Calculates the difference: `Gap = Open(T) - Close(T-1)`.
    *   Checks if `Gap >= MIN_GAP_SIZE`.
    *   **Signal**: BUY (Bullish).

2.  **Breakout Confirmation (Optional)**:
    *   If enabled (`USE_BREAKOUT_CONFIRMATION = True`), the current candle's close must be higher than the highest close in the lookback window.
    *   Condition: `Close(T) > Max(Close[T-Lookback : T-1])`.

## Configuration
Settings are defined in `src/stockreports/config/signal_settings.py`:

*   `MIN_GAP_SIZE`: The minimum price difference required to trigger an alert.
*   `USE_BREAKOUT_CONFIRMATION`: Enable/disable the lookback window check.
*   `LOOKBACK_PERIOD`: The number of previous candles to check for the breakout confirmation.

## Alert Details
*   **Alert Time**: The time of the current candle (T).
*   **Start Time**: The time of the previous candle (T-1).
*   **Magnitude**: The absolute size of the gap.
