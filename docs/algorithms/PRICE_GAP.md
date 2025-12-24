# Price Gap Approach

## Overview
The **Price Gap** approach identifies significant price gaps between the previous candle's close and the current candle's open. It detects both **Gap Up (BUY)** and **Gap Down (SELL)** patterns. The approach includes optional breakout confirmation and a mandatory forward window confirmation to validate the signal strength and progression.

## Logic

The analysis is performed on a candle-by-candle basis. For a given candle at time `T` (Signal Candle) and previous candle at `T-1`:

### 1. Gap Detection
First, the system checks for a significant price gap.

*   **BUY Signal (Gap Up)**:
    *   Condition: `Open(T) - Close(T-1) >= MIN_GAP_SIZE`
*   **SELL Signal (Gap Down)**:
    *   Condition: `Close(T-1) - Open(T) >= MIN_GAP_SIZE`

### 2. Breakout Confirmation (Optional)
If `USE_BREAKOUT_CONFIRMATION` is enabled, the signal candle's close is compared against a historical lookback window (size `LOOKBACK_PERIOD`) ending at `T-1`.

*   **BUY Signal**:
    *   Condition: `Close(T) > Max(Close in Lookback Window)`
    *   *The current close must be strictly higher than the highest close in the previous window.*
*   **SELL Signal**:
    *   Condition: `Close(T) < Min(Close in Lookback Window)`
    *   *The current close must be strictly lower than the lowest close in the previous window.*

### 3. Forward Window Confirmation
If the Gap (and optional Breakout) conditions are met, the system scans a **Forward Window** starting from the Signal Candle `T` up to `T + CONFIRMATION_FORWARD_WINDOW - 1`.

The system looks for a valid **Confirmation Candle** within this window. It scans in reverse (from the end of the window back to `T`) to find the latest valid confirmation.

A candle in the forward window is considered a valid confirmation if:

1.  **Direction**:
    *   **BUY**: The candle is Green (`Close > Open`).
    *   **SELL**: The candle is Red (`Open > Close`).
2.  **Body Size**:
    *   The absolute difference between Open and Close is at least `MIN_CONFIRMATION_BODY_SIZE`.
3.  **Progression** (if the Confirmation Candle is *after* the Signal Candle `T`):
    *   **BUY**: `Open(Confirmation) > Open(Signal Candle)`
    *   **SELL**: `Open(Confirmation) < Open(Signal Candle)`
    *   *This ensures the trend is continuing in the expected direction.*

## Alert Generation
If a valid Confirmation Candle is found:
*   **Alert Time**: The timestamp of the **Confirmation Candle**.
*   **Alert Price**: The close price of the **Confirmation Candle**.
*   **Start Time**: The timestamp of the candle *before* the gap (`T-1`).
*   **Start Price**: The close price of the candle *before* the gap (`T-1`).

## Configuration
Settings are managed via the `PriceGapSettings` class (typically loaded from `src/stockreports/alert/approach/PRICE_GAP/settings.py` or shared settings).

| Setting | Description |
| :--- | :--- |
| `MIN_GAP_SIZE` | The minimum price difference required between `Close(T-1)` and `Open(T)` to trigger a potential signal. |
| `USE_BREAKOUT_CONFIRMATION` | Boolean flag to enable/disable the historical lookback check. |
| `LOOKBACK_PERIOD` | Number of previous candles to check for Breakout Confirmation. |
| `CONFIRMATION_FORWARD_WINDOW` | Number of candles (including the signal candle) to scan forward for a valid confirmation. |
| `MIN_CONFIRMATION_BODY_SIZE` | Minimum body size (`abs(Close - Open)`) required for a Confirmation Candle. |
| `COOLDOWN_WINDOW` | Minimum time (in minutes) required between consecutive alerts to prevent spamming. |
