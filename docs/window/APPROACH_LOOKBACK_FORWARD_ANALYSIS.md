# Analysis of Lookback and Lookforward Behavior in Alerting Approaches

This document details which alerting approaches require looking at past data (lookback) or future data (lookforward) to generate signals. Understanding this is crucial for backtesting and performance analysis, as lookforward logic can introduce bias.

## Summary Table

| Approach                     | Requires Lookback | Requires Look Forward |
| :--------------------------- | :---------------: | :-------------------: |
| `COMPARISON`                 |      **Yes**      |          No           |
| `CONSECUTIVE_POWER_CANDLES`  |      **Yes**      |          No           |
| `CONSISTENT_MOMENTUM`        |      **Yes**      |  **Yes** (Optional)   |
| `CONSOLIDATION_BREAKOUT`     |      **Yes**      |          No           |
| `ICHIMOKU`                   |      **Yes**      |  **Yes** (Optional)   |
| `MOMENTUM_EXHAUSTION`        |      **Yes**      |          No           |
| `RCM`                        |      **Yes**      |          No           |
| `STRONG_CANDLE`              |      **Yes**      |          No           |
| `SUPPORT_RESISTANCE_BREAK`   |      **Yes**      |          No           |
| `VOLUME_SPIKE_CONFIRMATION`  |      **Yes**      |          No           |

---

## Detailed Configuration Breakdown

### `COMPARISON`

*   **Lookback**:
    *   `ma_short_period`: Used for a rolling MA on both primary and reference symbols.
    *   `lookback_window`: Used within the `ComparisonConfirmation` logic to check for trend divergence over a specified period.
    *   The analysis aligns data from the start to the end of the provided DataFrame.

### `CONSECUTIVE_POWER_CANDLES`

*   **Lookback**:
    *   `CANDLE_COUNT`: Defines the size of the sliding window used to find the pattern (e.g., 3 candles).
    *   The logic also looks back one additional candle *before* the pattern starts for the optional RSI exhaustion check.

### `CONSISTENT_MOMENTUM`

*   **Lookback**:
    *   `CONFIRMATION_WINDOW`: The number of candles that must show consistent momentum.
    *   `PEAK_BOTTOM_LOOKBACK_PERIOD`: The lookback period used to find recent peaks or troughs for the breakout confirmation. If `None`, it looks across all available history.
    *   Implicit lookbacks for standard confirmation indicators (e.g., RSI, MACD periods).
*   **Lookforward (Optional)**:
    *   `USE_REALTIME_REVERSAL_CONFIRMATION`: If `True`, the executor looks at the next `REALTIME_REVERSAL_CONFIRMATION_WINDOW` candle(s) to ensure no immediate strong reversal occurs.

### `CONSOLIDATION_BREAKOUT`

*   **Lookback**:
    *   `CONSOLIDATION_LOOKBACK`: A list of lookback periods to define the consolidation channel (e.g., `[50]`).
    *   `BREAKOUT_CONFIRMATION_CANDLES`: The number of candles that form the breakout window *after* the consolidation period. The total lookback for a single check is `lookback + confirmation_candles`.

### `ICHIMOKU`

*   **Lookback**:
    *   `TENKAN_PERIOD`, `KIJUN_PERIOD`, `SENKOU_B_PERIOD`: Standard lookback periods for Ichimoku calculations. `SENKOU_B_PERIOD` (default 52) is typically the largest.
    *   `CHIKOU_LAG`: Defines how far back the Chikou Span (Lagging Span) is plotted, requiring a lookback to compare its position relative to historical prices.
*   **Lookforward (Optional)**:
    *   `USE_CONFIRMATION_CANDLE_FILTER`: If `True`, enables a lookforward check.
    *   `CONFIRMATION_CANDLE_COUNT`: The number of candles to look forward to confirm that the price continues in the signal's direction.

### `MOMENTUM_EXHAUSTION`

*   **Lookback**:
    *   The total pattern lookback is `MOMENTUM_CANDLE_COUNT` + `EXHAUSTION_CANDLE_COUNT` + 2 (for the reversal and confirmation candles).

### `RCM` (Reversal Confirmation Model)

*   **Lookback**:
    *   The entire dataset is scanned first to identify all significant peaks and troughs based on `PEAK_TROUGH_PROMINENCE`.
    *   The main loop then looks back `CONFIRMATION_WINDOW` candles from a potential confirmation candle to find a prior peak/trough.
    *   `PEAK_BOTTOM_LOOKBACK_PERIOD`: If set, adds another lookback from the reversal point to check for a breakout.

### `STRONG_CANDLE`

*   **Lookback**:
    *   The pattern consists of a "Momentum Candle" (at index `i`), a "Confirmation Candle" (at `i-1`), and a "Strong Candle" found by searching backward from `i-2` for `CONFIRMATION_WINDOW` candles.
    *   The total lookback is `1 (confirmation) + 1 (gap) + CONFIRMATION_WINDOW`.

### `SUPPORT_RESISTANCE_BREAK`

*   **Lookback**:
    *   The pattern is identified in reverse. From a final confirmation candle at index `i`, the logic looks back:
        *   `CONFIRMATION_WINDOW` candles to find the "Break Candle".
        *   `LOOKBACK_PERIOD` candles *before* the "Break Candle" to establish the support/resistance level.
    *   The total lookback is `LOOKBACK_PERIOD + 1 (break) + CONFIRMATION_WINDOW`.
*   **Lookforward**:
    *   None. The confirmation window is part of the historical pattern being identified, not a forward-looking check.

### `VOLUME_SPIKE_CONFIRMATION`

*   **Lookback**:
    *   The pattern is identified in reverse. From a confirmation candle at index `i`, the logic looks back `SIGNAL_LOOKBACK_PERIOD` candles to find the signal candle with the highest volume.
    *   The total lookback is `1 (confirmation) + SIGNAL_LOOKBACK_PERIOD`.
*   **Lookforward**:
    *   None.