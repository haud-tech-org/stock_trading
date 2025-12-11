# CONSISTENT_MOMENTUM

## Objective

The **Consistent Momentum** strategy is designed to identify periods of strong, sustained, and high-quality directional movement. Unlike reversal strategies, its goal is to join a trend that is already demonstrating clear and consistent strength, confirmed by a breakout past a recent price structure. It validates this momentum through a series of strict checks, including candle patterns, breakout confirmation, volume, and optional indicator alignment.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py`. A dedicated settings class, `ConsistentMomentumSettings`, in `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/settings.py` loads these parameters.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `WINDOW_SIZE` | 3 | The number of consecutive candles that must all show consistent directional momentum. |
| `USE_BREAKOUT_CONFIRMATION` | `True` | If `True`, enables the Peak/Trough Breakout Confirmation step. |
| `BREAKOUT_FORWARD_WINDOW` | 3 | The maximum number of candles to look ahead for breakout confirmation after the momentum window. |
| `PEAK_BOTTOM_LOOKBACK_PERIOD` | `None` | The number of minutes to look back from the start of the momentum window to find a recent peak/trough. If `None`, it looks back through all available history. Only used if `USE_BREAKOUT_CONFIRMATION` is `True`. |
| `PEAK_TROUGH_PROMINENCE` | 5 | The prominence value used to detect peaks and troughs. A higher value requires a peak/trough to be more significant relative to its neighbors. Only used if `USE_BREAKOUT_CONFIRMATION` is `True`. |
| `BODY_TO_RANGE_MIN_RATIO` | 0.5 | The minimum ratio of the breakout candle's **body to its total range**. E.g., a value of 0.5 means the body must be at least 50% of the candle's full range. |
| `STRONG_CLOSE_THRESHOLD_RANGE` | `(0.7, 0.3)` | The minimum ratio of the final candle's **body to its total range**. E.g., a value of 0.7 means the body must be at least 70% of the candle's full range. |
| `USE_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final candle in the window to have a volume spike. |
| `USE_VOLUME_INCREASING_CONFIRMATION` | `False` | If `True`, requires the volume to be generally increasing across the confirmation window. |
| `USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final candle's volume to be the highest within the window. |
| `COOLDOWN_PERIOD` | 10 | The minimum time (in minutes) between consecutive alerts of the same direction. |

## Step-by-Step Logic

The core logic resides in the `ConsistentMomentumExecutor` class in `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py`. The algorithm analyzes a rolling window of `CONFIRMATION_WINDOW` candles. For a signal to be generated, **all** of the following checks must pass:

1.  **Basic Momentum Check:**
    *   All candles within the window must be bullish (`close > open`) for a `BUY` signal.
    *   All candles must be bearish (`close < open`) for a `SELL` signal.

2.  **Consistent Trend (Average Price):**
    *   The average price `(open + close) / 2` is calculated for each candle in the window. This focuses on the midpoint of the candle's body.
    *   For a `BUY` signal, this average price must be consistently increasing or flat from one candle to the next.
    *   For a `SELL` signal, it must be consistently decreasing or flat.

3.  **Strong Close Check:**
    *   The final candle in the window must have a body that is a significant portion of its total range.
    *   For a `BUY` signal, the ratio `(close - open) / (high - low)` must be greater than or equal to the `strong_close_min` threshold.
    *   For a `SELL` signal, the ratio `(open - close) / (high - low)` must be greater than or equal to the `strong_close_min` threshold.

4.  **Peak/Trough Breakout Confirmation (Optional):**
    *   This step is controlled by the `USE_BREAKOUT_CONFIRMATION` flag.
    *   It is a critical check to ensure the momentum is breaking out of a recent price structure.
    *   The algorithm looks back in time from the *start* of the momentum window (`PEAK_BOTTOM_LOOKBACK_PERIOD`).
    *   It identifies the **Highest Peak** (for a `BUY`) or **Lowest Trough** (for a `SELL`) on the **closing prices** using `scipy.signal.find_peaks`.
    *   **Breakout Candle (B):** The algorithm scans the `BREAKOUT_FORWARD_WINDOW` (candles immediately following the momentum window) for the first candle that closes beyond the identified peak/trough AND meets the `BODY_TO_RANGE_MIN_RATIO`.
    *   **Confirmation:**
        *   **Immediate:** If the candle immediately following B (B+1) has higher volume than B and the same trend direction, the alert is confirmed at B+1.
        *   **Delayed:** If immediate confirmation fails, the algorithm scans subsequent candles. It looks for a candle with volume higher than the reference candle (initially B+1), same trend direction, and a close beyond the breakout price. If found, the alert is confirmed at that candle.
    *   **Important:** If no relevant peak or trough is found in the lookback period, this condition is automatically considered **confirmed**. It only fails if a peak/trough exists and the price fails to break it.

5.  **Volume Confirmation (Optional):**
    *   The logic checks up to three volume conditions on the momentum window if their respective flags are `True`:
        *   `USE_VOLUME_CONFIRMATION`: The final candle must have a volume spike.
        *   `USE_VOLUME_INCREASING_CONFIRMATION`: Volume must be trending upwards across the window.
        *   `USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION`: The final candle must have the highest volume in the window.

6.  **Body Dominance Check:**
    *   The sum of the absolute body sizes of all candles in the window must be greater than the sum of all their wicks (upper and lower shadows combined). This ensures the overall move was driven by price conviction, not indecision.

7.  **Indicator Confirmation (Optional):**
    *   If enabled, standard indicators are used for final validation.
    *   **RSI Exhaustion:** The RSI is checked on the *start and end* candles of the momentum window to ensure the move isn't starting from or ending in an overbought/oversold state.
    *   **Other Indicators:** MACD, MA, etc., are checked on the **final candle** to confirm they align with the signal.

8.  **Cooldown Period:**
    *   If an alert is generated, a cooldown period of `COOLDOWN_PERIOD` minutes is applied.
    *   Any subsequent alert within this period that has the **same signal direction** (BUY/BUY or SELL/SELL) is ignored.

If all configured checks pass, an `AlertData` object is created to signal the detected momentum.

## Flow Diagram

```mermaid
graph TD
    A[Start] --> B{Analyze Rolling Window of `WINDOW_SIZE`};
    B --> C{1. Basic Momentum?};
    C -- No --> X[Discard Window];
    C -- Yes --> D{2. Consistent Trend (Avg Price)?};
    D -- No --> X;
    D -- Yes --> E{3. Strong Close?};
    E -- No --> X;
    E -- Yes --> F{4. Breakout Confirmed? (Optional)};
    F -- No --> X;
    F -- Yes --> G{"Optional Filters Enabled?"};
    G -- No --> Z[Generate Alert];
    G -- Yes --> H{5. Volume Confirmed?};
    H -- No --> X;
    H -- Yes --> I{6. Body Dominance?};
    I -- No --> X;
    I -- Yes --> J{7. Indicators Confirmed?};
    J -- No --> X;
    J -- Yes --> K{8. Cooldown Check?};
    K -- Fail --> X;
    K -- Pass --> Z;
    X --> B;
```

### Diagram Explanation

1.  **Analyze Rolling Window**: The algorithm processes data in rolling windows of `WINDOW_SIZE` size.
2.  **Basic Momentum?**: Checks if all candles in the window share the same direction (all bullish or all bearish).
3.  **Consistent Trend (Avg Price)?**: Ensures the average price (midpoint of the body) of the candles is consistently increasing (for a BUY) or decreasing (for a SELL).
4.  **Strong Close?**: Validates that the final candle's body is a significant portion of its total range.
5.  **Breakout Confirmed? (Optional)**: If enabled, this key logic step checks if the final candle's close has broken past the most recent significant peak/trough. If no peak/trough exists, this passes.
6.  **Optional Filters**: If the core pattern is valid, it proceeds to a series of other optional validation filters.
7.  **Volume/Quality/Dominance/Indicators**: These steps check for various volume patterns, ensure the final candle is decisive, check that total body size outweighs wicks, validate with standard indicators (RSI, MACD, etc.), and finally apply a cooldown period to prevent duplicate alerts.
8.  **Generate Alert**: If all mandatory and enabled optional checks pass, an alert is generated.
9.  **Discard Window**: If any check fails, the current window is discarded.
