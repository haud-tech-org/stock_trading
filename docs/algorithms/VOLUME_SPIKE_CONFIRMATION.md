# VOLUME_SPIKE_CONFIRMATION

## Objective

The **Volume Spike Confirmation** strategy is a two-phase approach designed to identify potential trend reversals. It first identifies a historical "climax event" characterized by a significant volume spike at the end of a confirmed trend. Then, it actively searches all subsequent data for a specific "reversal candle" that confirms the new trend has begun.

## Key Parameters

All parameters are defined in `src/stockreports/config/signal_settings.py` under the `VOLUME_SPIKE_CONFIRMATION` section and loaded via the settings class. No magic numbers are used in the logic.

| Parameter                 | Default | Description                                                                                       |
|---------------------------|---------|---------------------------------------------------------------------------------------------------|
| `LOOKBACK_WINDOW`         | 5       | Number of candles to analyze for trend and volume spike.                                          |
| `COOLDOWN_WINDOW`         | 3       | Minimum time (in minutes) between consecutive alerts of the same signal.                          |
| `MIN_TREND_WINDOW_SIZE`   | 6.5     | Minimum price change for the trend window to be considered valid.                                 |
| `MIN_TREND_CANDLE_SLICE`  | 3       | Minimum number of consecutive same-color candles to define a trend window.                        |
| `TREND_VOLUME_MULTIPLIER` | 4.5     | Max-volume candle must be at least this many times the min-volume candle in the trend window.     |

## Step-by-Step Logic

The algorithm operates in a rolling fashion, analyzing the most recent data first. It is divided into two distinct phases. The process for a **BUY signal** (reversing a prior downtrend) is detailed below.

### Phase 1: Climax Event Identification

The algorithm first analyzes a rolling `LOOKBACK_WINDOW` to find a valid climax event.


1.  **Find Max Volume Candle**: Identify the candle with the maximum volume within the `LOOKBACK_WINDOW`. This is the potential **climax candle**.
2.  **Volume Validation**: The climax candle's volume must be at least `TREND_VOLUME_MULTIPLIER` times the minimum volume candle in the same window.
3.  **Downtrend Confirmation**: The algorithm checks for a valid trend window by requiring at least `MIN_TREND_CANDLE_SLICE` consecutive same-color candles (all bullish or all bearish) and a minimum price change of `MIN_TREND_WINDOW_SIZE`.

If a valid climax event is found, the algorithm proceeds to Phase 2. Otherwise, it moves to the next window.

### Phase 2: Reversal Confirmation Validation

Once a climax event is identified, the algorithm validates if the most recent candle in the dataset confirms the reversal.

1.  **Define Validation Window**: The validation takes place in a window that starts from the climax candle and extends to the **very end of the available dataset**.
2.  **Validate Last Candle**: The algorithm checks **only the last candle** in this window to see if it's a valid reversal signal.
3.  **Reversal Candle Validation**: The last candle is considered a valid **BUY reversal** if it is a **bullish candle** (`close > open`). (No check is performed for closing price relative to the previous candle, and no minimum body size threshold is enforced.)

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
