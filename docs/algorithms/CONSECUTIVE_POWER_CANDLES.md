# CONSECUTIVE_POWER_CANDLES

## Objective

The **Consecutive Power Candles** strategy is a strong momentum-following pattern, often associated with the "Three White Soldiers" (bullish) or "Three Black Crows" (bearish) formations. It aims to identify a decisive and powerful start to a new short-term trend by looking for a specific sequence of three strong, consecutive, and directionally aligned candles.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py` and uses the following parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `CANDLE_COUNT` | 3 | The number of consecutive candles required for the pattern. This is hard-coded to 3 in the logic. |
| `MIN_BODY_TO_RANGE_RATIO` | 0.7 | The minimum ratio of the candle's body to its total range. This ensures each candle is a "power candle" with small wicks and a decisive body. |
| `MIN_BODY_SIZE_T_MINUS_2` | 2.0 | The minimum body size (in points) for the first candle in the sequence (T-2). |
| `MIN_BODY_SIZE_T_MINUS_1` | 2.0 | The minimum body size (in points) for the second candle in the sequence (T-1). |
| `USE_VOLUME_CONFIRMATION` | `False` | If `True`, requires the final candle in the sequence to be accompanied by a significant volume spike. |

## Step-by-Step Logic

The core logic resides in the `_analyze_window` function in `src/stockreports/alert/approach/CONSECUTIVE_POWER_CANDLES/executor.py`. The algorithm analyzes a rolling window of 3 candles (T-2, T-1, and T). For a signal to be generated, all of the following checks must pass.

1.  **Consistent Direction:**
    *   All three candles must be bullish (`close > open`) for a `BUY` signal.
    *   All three candles must be bearish (`close < open`) for a `SELL` signal.

2.  **Power Candle Confirmation:**
    *   Each of the three candles must be a "power candle," meaning its body must make up at least 70% of its total range (`MIN_BODY_TO_RANGE_RATIO`). This filters out indecisive candles with long wicks.

3.  **Minimum Body Size:**
    *   The body of the first candle (T-2) must be larger than `MIN_BODY_SIZE_T_MINUS_2`.
    *   The body of the second candle (T-1) must be larger than `MIN_BODY_SIZE_T_MINUS_1`.
    *   This ensures the initial move has sufficient force.

4.  **Progressive Opening Price (Key Logic):**
    *   This check confirms that the momentum is being sustained without significant pullbacks.
    *   **For a Bullish Pattern (Three White Soldiers):**
        *   The second candle (T-1) must open **above the midpoint** of the first candle's body.
        *   The third candle (T) must open **above the midpoint** of the second candle's body.
    *   **For a Bearish Pattern (Three Black Crows):**
        *   The second candle (T-1) must open **below the midpoint** of the first candle's body.
        *   The third candle (T) must open **below the midpoint** of the second candle's body.

5.  **Volume Confirmation (Optional):**
    *   If `USE_VOLUME_CONFIRMATION` is `True`, the algorithm performs a final check to ensure the third and final candle (T) is accompanied by a significant volume spike.

If this sequence of three candles successfully passes all these checks, an `AlertData` object is created, and a signal is generated.
