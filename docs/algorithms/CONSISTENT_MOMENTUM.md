# CONSISTENT_MOMENTUM

## Objective

The **Consistent Momentum** strategy is designed to identify periods of strong, sustained, and high-quality directional movement. Unlike reversal strategies, its goal is to join a trend that is already demonstrating clear and consistent strength, confirmed by a breakout past a recent price structure. It validates this momentum through a series of strict checks, including candle patterns, breakout confirmation, volume, and optional indicator alignment.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py`. A dedicated settings class, `ConsistentMomentumSettings`, in `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/settings.py` loads these parameters.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `CONFIRMATION_WINDOW` | 3 | The number of consecutive candles that must all show consistent directional momentum. |
| `PEAK_BOTTOM_LOOKBACK_PERIOD` | `None` | The number of minutes to look back from the start of the momentum window to find a recent peak/trough. If `None`, it looks back through all available history. |
| `PEAK_TROUGH_PROMINENCE` | 1 | The prominence value used to detect peaks and troughs. A higher value requires a peak/trough to be more significant relative to its neighbors. |
| `BODY_TO_RANGE_MIN_RATIO` | 0.5 | The minimum ratio of the **final candle's** body to its total range. This ensures the breakout candle is decisive. |
| `STRONG_CLOSE_THRESHOLD_RANGE` | `(0.7, 0.3)` | The final candle must close in the top 70% of its range for a BUY, or bottom 30% for a SELL. |
| `USE_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final candle in the window to have a volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires the volume to be generally increasing across the confirmation window. |
| `USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final candle's volume to be the highest within the window. |
| `USE_REALTIME_REVERSAL_CONFIRMATION` | `False` | If `True`, looks at the next candle(s) to ensure no immediate strong reversal occurs, invalidating the signal. |

## Step-by-Step Logic

The core logic resides in the `ConsistentMomentumExecutor` class in `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py`. The algorithm analyzes a rolling window of `CONFIRMATION_WINDOW` candles. For a signal to be generated, **all** of the following checks must pass:

1.  **Basic Momentum Check:**
    *   All candles within the window must be bullish (`close > open`) for a `BUY` signal.
    *   All candles must be bearish (`close < open`) for a `SELL` signal.

2.  **Consistent Trend (Average Price):**
    *   The average price `(High + Low + Close) / 3` is calculated for each candle in the window.
    *   For a `BUY` signal, this average price must be consistently increasing or flat from one candle to the next.
    *   For a `SELL` signal, it must be consistently decreasing or flat.

3.  **Strong Close Check:**
    *   The final candle in the window must close "strongly," as defined by `STRONG_CLOSE_THRESHOLD_RANGE`. For a `BUY`, it must close in the upper portion of its range. For a `SELL`, it must close in the lower portion.

4.  **Peak/Trough Breakout Confirmation (Key Logic):**
    *   This is a critical check to ensure the momentum is breaking out of a recent price structure.
    *   The algorithm looks back in time from the *start* of the momentum window (`PEAK_BOTTOM_LOOKBACK_PERIOD`).
    *   It identifies all significant historical peaks (for a `BUY`) or troughs (for a `SELL`) using the `scipy.signal.find_peaks` function with the configured `PEAK_TROUGH_PROMINENCE`.
    *   For a `BUY` signal, the closing price of the final candle must be **higher than the most recent peak** found in that lookback period.
    *   For a `SELL` signal, the closing price must be **lower than the most recent trough**.

5.  **Volume Confirmation (Optional):**
    *   The logic checks up to three volume conditions on the momentum window if their respective flags are `True`:
        *   `USE_VOLUME_CONFIRMATION`: The final candle must have a volume spike.
        *   `USE_INCREASING_VOLUME_CONFIRMATION`: Volume must be trending upwards across the window.
        *   `USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION`: The final candle must have the highest volume in the window.

6.  **Final Candle Quality (Body-to-Range Ratio):**
    *   The body of the **final candle** must be at least `BODY_TO_RANGE_MIN_RATIO` of its total range. This ensures the breakout candle itself is strong and decisive.

7.  **Body Dominance Check:**
    *   The sum of the absolute body sizes of all candles in the window must be greater than the sum of all their wicks (upper and lower shadows combined). This ensures the overall move was driven by price conviction, not indecision.

8.  **Indicator Confirmation (Optional):**
    *   If enabled, standard indicators are used for final validation.
    *   **RSI Exhaustion:** The RSI is checked on the *start and end* candles of the momentum window to ensure the move isn't starting from or ending in an overbought/oversold state.
    *   **Other Indicators:** MACD, MA, etc., are checked on the **final candle** to confirm they align with the signal.

9.  **Real-time Reversal Confirmation (Optional Look-Forward):**
    *   If `USE_REALTIME_REVERSAL_CONFIRMATION` is `True`, the algorithm peeks at the candle(s) immediately *following* the signal candle.
    *   If a strong reversal candle appears within this look-ahead window, the original signal is invalidated and discarded.

If all configured checks pass, an `AlertData` object is created to signal the detected momentum.

## Flow Diagram

```mermaid
graph TD
    A[Start] --> B{Analyze Rolling Window of `CONFIRMATION_WINDOW`};
    B --> C{1. Basic Momentum?};
    C -- No --> X[Discard Window];
    C -- Yes --> D{2. Consistent Trend (Avg Price)?};
    D -- No --> X;
    D -- Yes --> E{3. Strong Close?};
    E -- No --> X;
    E -- Yes --> F{4. Breakout Confirmed?};
    F -- No --> X;
    F -- Yes --> G{"Optional Filters Enabled?"};
    G -- No --> Z[Generate Alert];
    G -- Yes --> H{5. Volume Confirmed?};
    H -- No --> X;
    H -- Yes --> I{6. Final Candle Quality?};
    I -- No --> X;
    I -- Yes --> J{7. Body Dominance?};
    J -- No --> X;
    J -- Yes --> K{8. Indicators Confirmed?};
    K -- No --> X;
    K -- Yes --> L{9. No Immediate Reversal?};
    L -- No --> X;
    L -- Yes --> Z;
    X --> B;
```

### Diagram Explanation

1.  **Analyze Rolling Window**: The algorithm processes data in rolling windows of `CONFIRMATION_WINDOW` size.
2.  **Basic Momentum?**: Checks if all candles in the window share the same direction (all bullish or all bearish).
3.  **Consistent Trend (Avg Price)?**: Ensures the average price of the candles is consistently increasing (for a BUY) or decreasing (for a SELL).
4.  **Strong Close?**: Validates that the final candle closes in the upper (BUY) or lower (SELL) portion of its range.
5.  **Breakout Confirmed?**: The key logic step. Checks if the final candle's close has broken past the most recent significant peak (BUY) or trough (SELL).
6.  **Optional Filters**: If the core pattern is valid, it proceeds to a series of optional validation filters.
7.  **Volume/Quality/Dominance/Indicators/Reversal**: These steps check for various volume patterns, ensure the final candle is decisive, check that total body size outweighs wicks, validate with standard indicators (RSI, MACD, etc.), and finally peek ahead to ensure no immediate reversal invalidates the signal.
8.  **Generate Alert**: If all mandatory and enabled optional checks pass, an alert is generated.
9.  **Discard Window**: If any check fails, the current window is discarded.
