# STRONG_CANDLE

## Objective

The **Strong Candle** strategy is designed to identify moments of decisive, high-conviction momentum. It does not just look for a single strong candle, but for a specific three-step sequence: a powerful initial move, confirmation from technical indicators, and immediate follow-through. This ensures the signal is not just a random spike but the start of a potentially sustainable move.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py` and uses the following parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `CONFIRMATION_WINDOW` | 2 | The maximum number of candles to wait after the initial "Strong Candle" for an advanced confirmation signal to appear. |
| `USE_VOLUME_CONFIRMATION` | `True` | If `True`, requires the final momentum candle to have a significant volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires volume to be generally increasing across the entire sequence (from strong candle to momentum candle). |
| `TREND_STRENGTH_STRONG_CLOSE_TAIL_RATIO` | 0.4 | A global setting that defines how small a candle's wick must be relative to its body to be considered "strong." A smaller ratio means a more decisive candle is required. |

## Step-by-Step Logic

The core logic resides in the `_find_strong_candle_alerts` function in `src/stockreports/alert/approach/STRONG_CANDLE/executor.py`. It operates as a three-stage state machine (`NEUTRAL` -> `AWAITING_CONFIRMATION` -> `AWAITING_MOMENTUM`). An alert is only generated if the sequence completes successfully.

### Step 1: Find the "Strong Candle" (`NEUTRAL` State)

The algorithm first looks for the entry point of the sequence: a single, powerful, and decisive candle.

1.  **Identify a Strong Body:** The candle's body size must be larger than the minimum expected profit/loss, ensuring it's a significant move.
2.  **Check for a Small Wick:** The candle's "tail" (the wick opposing the direction of the move) must be very small relative to its body.
    *   For a bullish (green) candle, the **upper wick** must be small.
    *   For a bearish (red) candle, the **lower wick** must be small.
3.  **Transition State:** If a candle meets these criteria, it is marked as the "Strong Candle," and the state transitions to `AWAITING_CONFIRMATION`.

### Step 2: Wait for Advanced Confirmation (`AWAITING_CONFIRMATION` State)

After identifying the initial burst of momentum, the algorithm waits for confirmation from other technical indicators.

1.  **Open Confirmation Window:** The algorithm looks at the next `CONFIRMATION_WINDOW` candles.
2.  **Check for Indicator Signal:** On each of these candles, it runs `check_advanced_confirmation`, which looks for a `BUY` or `SELL` signal from a combination of indicators (like MACD, RSI, and ADX).
3.  **Match Signal Direction:** The signal from the indicators must match the direction of the initial "Strong Candle" (e.g., a `BUY` signal after a strong bullish candle).
4.  **Transition State:** If a matching confirmation signal is found, that candle is marked as the "Confirmation Candle," and the state transitions to `AWAITING_MOMENTUM`. If the window closes without a signal, the sequence is aborted, and the state resets to `NEUTRAL`.

### Step 3: Final Momentum Check (`AWAITING_MOMENTUM` State)

This is the final, immediate check for follow-through.

1.  **Immediate Follow-Through:** The algorithm looks at the very next candle after the "Confirmation Candle."
2.  **Confirm Direction:** This final "Momentum Candle" must continue in the same direction (e.g., its closing price must be higher than the previous close for a `BUY` signal).
3.  **Final Validation:** If momentum is confirmed, the algorithm performs final checks:
    *   **Magnitude Check:** Ensures the total move from the start of the sequence is significant.
    *   **Volume Check (Optional):** Verifies a volume spike or increasing volume if configured.

### Step 4: Signal Generation

If this three-step sequence (Strong Candle -> Advanced Confirmation -> Momentum Follow-Through) completes successfully, an `AlertData` object is created, and a signal is generated. The state then resets to `NEUTRAL` to look for the next sequence.
