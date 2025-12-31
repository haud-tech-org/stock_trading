# VOLUME_SPIKE_CONFIRMATION

## Objective

The **Volume Spike Confirmation** strategy is a two-phase approach designed to identify potential trend reversals. It first identifies a historical "climax event" characterized by a significant volume spike at the end of a confirmed trend. Then, it actively searches all subsequent data for a specific "reversal candle" that confirms the new trend has begun.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py`.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `LOOKBACK_WINDOW` | 30 | The number of past candles to analyze to find a climax event. |
| `COOLDOWN_PERIOD` | 10 | The minimum time (in minutes) between consecutive alerts of the same signal direction. |
| `PREVIOUS_CANDLES_VOLUME_MULTIPLIER` | 2.0 | The climax candle's volume must be at least this many times greater than the volume of at least one of the two preceding candles. |
| `AVG_VOLUME_MULTIPLIER` | 3.0 | The climax candle's volume must be at least this many times greater than the average volume of its lookback window. |
| `PEAK_TROUGH_PROMINENCE` | 2.0 | The prominence value for detecting peaks/troughs to confirm the prior trend leading up to the climax candle. Set to `null` or `0.0` to disable the prominence constraint. |
| `MIN_REVERSAL_BODY_SIZE` | 1.0 | The minimum absolute body size of the **reversal candle** found after the climax event. |
| `DISABLE_BUY_SIGNAL` | `False` | If `True`, the strategy will not generate any BUY signals. |
| `DISABLE_SELL_SIGNAL` | `False` | If `True`, the strategy will not generate any SELL signals. |

## Step-by-Step Logic

The algorithm operates in a rolling fashion, analyzing the most recent data first. It is divided into two distinct phases. The process for a **BUY signal** (reversing a prior downtrend) is detailed below.

### Phase 1: Climax Event Identification

The algorithm first analyzes a rolling `LOOKBACK_WINDOW` to find a valid climax event.

1.  **Find Max Volume Candle**: It identifies the candle with the maximum volume within the `LOOKBACK_WINDOW`. This is our potential **climax candle**.
2.  **Volume Validation**: The climax candle's volume must meet two criteria:
    *   It must be at least `PREVIOUS_CANDLES_VOLUME_MULTIPLIER` times the volume of at least one of the two candles that came before it.
    *   It must be at least `AVG_VOLUME_MULTIPLIER` times the average volume of the entire `LOOKBACK_WINDOW`.
3.  **Downtrend Confirmation**: The algorithm confirms that the climax candle occurred at the end of a valid downtrend.
    *   **Find Peaks**: It uses `scipy.signal.find_peaks` to identify all significant price peaks on the closing prices in the window *leading up to and including the climax candle*.
    *   **Build Trend Sequence**: It creates an ordered sequence of prices: [first candle's close, all peak closes, climax candle's close].
    *   **Verify Trend**: It checks if this sequence is **monotonically decreasing**, confirming a consistent downtrend.

If a valid climax event is found, the algorithm proceeds to Phase 2. Otherwise, it moves to the next window.

### Phase 2: Reversal Confirmation Validation

Once a climax event is identified, the algorithm validates if the most recent candle in the dataset confirms the reversal.

1.  **Define Validation Window**: The validation takes place in a window that starts from the climax candle and extends to the **very end of the available dataset**.
2.  **Validate Last Candle**: The algorithm checks **only the last candle** in this window to see if it's a valid reversal signal.
3.  **Reversal Candle Validation**: The last candle is considered a valid **BUY reversal** if it meets all the following conditions:
    *   It must be a **bullish candle** (`close > open`).
    *   Its closing price must be **higher than the closing price of the immediately preceding candle**.
    *   Its absolute body size (`close - open`) must be greater than or equal to `MIN_REVERSAL_BODY_SIZE`.

If the last candle is a valid reversal, a **BUY** alert is generated, timestamped at the time of that candle.

### Cooldown

The cooldown check is the very first step in the process. Before any analysis runs, the algorithm checks a class-level timestamp that records when the last alert was processed. If the time elapsed since that timestamp is less than the `COOLDOWN_PERIOD`, the entire execution for the current symbol is skipped to prevent duplicate alerts and save resources. This timestamp is updated whenever a new alert is generated.

## Flow Diagram

```mermaid
graph TD
    A[Start] --> B{Cooldown Active?};
    B -- Yes --> Z[End];
    B -- No --> C{Analyze Rolling Lookback Window};
    C --> D{Phase 1: Climax Event Found?};
    D -- No --> X[Discard & Move to Next Window];
    D -- Yes --> E{Phase 2: Define Validation Window (Climax to End of Data)};
    E --> F{Is Last Candle a Valid Reversal?};
    F -- No --> X;
    F -- Yes --> G[Generate Reversal Alert];
    G --> H[Update Last Alert Timestamp];
    H --> Z;
    X --> Z;
```
