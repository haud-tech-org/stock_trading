# SUPPORT_RESISTANCE_BREAK

## Objective

The **Support/Resistance Break** strategy is designed to identify significant price breakouts or breakdowns from established consolidation zones. It operates by defining a historical price range and then watching for a decisive move beyond that range, confirmed by sustained momentum and other indicators.

-   **Breakout (BUY Signal):** Identifies a "resistance ceiling" and generates a `BUY` signal when the price breaks above it and stays there.
-   **Breakdown (SELL Signal):** Identifies a "support shelf" and generates a `SELL` signal when the price breaks below it and holds.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py`. A dedicated settings class, `SupportResistanceBreakSettings`, in `src/stockreports/alert/approach/SUPPORT_RESISTANCE_BREAK/settings.py` loads these parameters.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `LOOKBACK_PERIOD` | 50 | The number of candles used to define the historical price range (the support/resistance zone). |
| `CONFIRMATION_WINDOW` | 3 | The number of candles *after* the initial break during which the price must consistently stay outside the broken level. |
| `CONSISTENCY_THRESHOLD` | 2 | The minimum number of candles within the `CONFIRMATION_WINDOW` that must close beyond the broken level to confirm the break. |
| `USE_BB_SQUEEZE_CONFIRMATION` | `False` | If `True`, requires the market to be in a state of low volatility (a "Bollinger Band Squeeze") *before* the break occurs. |
| `BB_SQUEEZE_LOOKBACK` | 40 | The lookback period for calculating the Bollinger Band Squeeze. |
| `BB_SQUEEZE_THRESHOLD_RATIO` | 0.08 | The threshold for determining if a Bollinger Band Squeeze is active. |
| `USE_VOLUME_CONFIRMATION` | `False` | If `True`, requires the initial **break candle** to have a significant volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires volume to be generally increasing during the `CONFIRMATION_WINDOW`. |
| `USE_LAST_CANDLE_MAX_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final confirmation candle to have the highest volume in its window. |
| `ADX_CONFIRMATION_THRESHOLD` | 20 | The minimum ADX value required on the **final confirmation candle**, ensuring the trend has sufficient strength. |
| `USE_RSI_EXHAUSTION_FILTER`, `USE_MA_CONFIRMATION`, etc. | `False` | Standard confirmation flags. These are checked on the **break candle** to validate the initial move. |

## Step-by-Step Logic (Backward Loop)

The core logic resides in the `SupportResistanceBreakExecutor` class in `src/stockreports/alert/approach/SUPPORT_RESISTANCE_BREAK/executor.py`. It uses a backward loop, starting from the most recent candle and working backward to find a completed break-and-confirmation pattern.

### The Three-Part Pattern (Identified in Reverse)

1.  **The Confirmation Window:** A sequence of `CONFIRMATION_WINDOW` candles, ending at the current loop index `i`.
2.  **The Break Candle:** The single candle immediately preceding the confirmation window.
3.  **The Lookback Window:** A sequence of `LOOKBACK_PERIOD` candles preceding the break candle, used to define the support/resistance level.

### Signal Generation Conditions

1.  **Define Windows and Levels:** For each potential final candle `i`, the algorithm defines the three windows. It then finds the `highest_peak` (resistance) and `lowest_trough` (support) within the **Lookback Window**.

2.  **Check for Pre-Break Squeeze (Optional):** If `USE_BB_SQUEEZE_CONFIRMATION` is `True`, it first checks if the **Lookback Window** was in a low-volatility state (a Bollinger Band Squeeze). If not, it ignores any break, assuming the market is too choppy.

3.  **Identify the Initial Break:** The algorithm checks if the **Break Candle** closed above the `highest_peak` (for a `BUY`) or below the `lowest_trough` (for a `SELL`). If no break occurred, the pattern is invalid.

4.  **Validate the Break Candle:** If a break is found, the **Break Candle** is immediately subjected to several filters:
    *   **Indicator Confirmation (Optional):** It is checked against standard indicators (`is_signal_confirmed`) like MA, MACD, etc., if enabled.
    *   **RSI Exhaustion Filter (Optional):** It is checked to ensure the break is not happening from an already overbought/oversold level.
    *   **Volume Spike (Optional):** If `USE_VOLUME_CONFIRMATION` is `True`, it must be accompanied by a significant volume spike.

5.  **Validate the Confirmation Window:** If the break candle is valid, the algorithm examines the **Confirmation Window**:
    *   **Consistency Check:** It counts how many candles in this window also close beyond the broken level. This count must meet or exceed `CONSISTENCY_THRESHOLD`.
    *   **ADX Trend Strength:** The ADX value on the *final* candle of the window must be above `ADX_CONFIRMATION_THRESHOLD`.
    *   **Volume Profile (Optional):** It checks for increasing volume or a max volume candle within the window if the respective flags are enabled.

### Signal Generation

If all parts of the pattern are identified and all configured validation checks pass, an `AlertData` object is created, and a signal is generated. The algorithm then enters a cooldown period to avoid generating duplicate alerts from the same breakout event.

## Flow Diagram

```mermaid
graph TD
    subgraph "Backward Loop (for each candle 'i')"
        A[Start Loop at Latest Candle] --> B{Define Lookback, Break, & Confirmation Windows};
        B --> C{1. Pre-Break Squeeze Active? (Optional)};
        C -- No (if enabled) --> X[Continue to Next Candle 'i-1'];
        C -- Yes / Disabled --> D{2. Is it a Break Candle?};
        D -- No --> X;
        D -- Yes --> E{3. Break Candle Validated?};
        E -- No --> X;
        E -- Yes --> F{4. Confirmation Window Validated?};
        F -- No --> X;
        F -- Yes --> Z[Generate Alert];
    end

    subgraph "Validation Steps"
        E --> E1{Indicators Confirmed?};
        E1 --> E2{RSI Not Exhausted?};
        E2 --> E3{Volume Spike?};

        F --> F1{Consistency Met?};
        F1 --> F2{ADX Strength?};
        F2 --> F3{Volume Profile OK?};
    end
```

### Diagram Explanation

1.  **Start Loop at Latest Candle**: The algorithm begins at the most recent candle and works backward, treating each candle `i` as the potential final confirmation of a breakout.
2.  **Define Windows**: For each loop, it defines the three key periods based on the current candle `i`: the Lookback Window (for setting the level), the Break Candle, and the Confirmation Window.
3.  **Pre-Break Squeeze?**: An optional check to ensure the market was in a low-volatility state *before* the break, which often leads to stronger moves.
4.  **Is it a Break Candle?**: Checks if the designated "Break Candle" actually closed above the resistance or below the support established by the "Lookback Window".
5.  **Break Candle Validated?**: If a break occurred, the break candle itself is immediately validated with optional checks for indicator alignment, non-exhausted RSI, and a volume spike.
6.  **Confirmation Window Validated?**: If the break candle is valid, the final "Confirmation Window" is checked for sustained momentum (consistency), trend strength (ADX), and confirming volume patterns.
7.  **Generate Alert**: If all mandatory and enabled optional checks pass, an alert is generated.
8.  **Continue to Next Candle**: If any check fails, the algorithm moves to the previous candle (`i-1`) and repeats the process.
