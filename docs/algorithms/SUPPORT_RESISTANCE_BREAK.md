# SUPPORT_RESISTANCE_BREAK

## Objective

The **Support/Resistance Break** strategy is designed to identify significant price breakouts or breakdowns from established consolidation zones. It operates by defining a historical price range and then watching for a decisive move beyond that range, confirmed by sustained momentum and other indicators.

-   **Breakout (BUY Signal):** Identifies a "resistance ceiling" and generates a `BUY` signal when the price breaks above it and stays there.
-   **Breakdown (SELL Signal):** Identifies a "support shelf" and generates a `SELL` signal when the price breaks below it and holds.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py` and uses the following parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `LOOKBACK_PERIOD` | 50 | The number of candles used to define the historical price range (the support/resistance zone). |
| `CONFIRMATION_WINDOW` | 3 | The number of candles after the initial break during which the price must consistently stay outside the broken level. |
| `CONSISTENCY_THRESHOLD` | 2 | The minimum number of candles within the `CONFIRMATION_WINDOW` that must close beyond the broken level to confirm the break. |
| `USE_VOLUME_CONFIRMATION` | `True` | If `True`, requires the initial break candle to have a significant volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `True` | If `True`, requires volume to be generally increasing during the `CONFIRMATION_WINDOW`. |
| `USE_BB_SQUEEZE_CONFIRMATION` | `True` | If `True`, requires the market to be in a state of low volatility (a "Bollinger Band Squeeze") *before* the break occurs. This identifies breaks from quiet periods, which are often more powerful. |
| `ADX_CONFIRMATION_THRESHOLD` | 21 | The minimum ADX value required on the final confirmation candle, ensuring the trend has sufficient strength. |

## Step-by-Step Logic

The core logic resides in the `_find_break_alerts` function in `src/stockreports/alert/approach/SUPPORT_RESISTANCE_BREAK/executor.py`. It operates as a state machine (`NEUTRAL` -> `AWAITING_CONFIRMATION`).

### Step 1: Look for a Potential Break (`NEUTRAL` State)

The algorithm iterates through each candle, treating it as a potential "break candle."

1.  **Define the Price Range:** For the current candle, it looks back over the last `LOOKBACK_PERIOD` candles to find the **highest high** (resistance ceiling) and the **lowest low** (support shelf).

2.  **Check for Pre-Break Squeeze (Optional):** If `USE_BB_SQUEEZE_CONFIRMATION` is `True`, it first checks if the market was in a low-volatility state (a Bollinger Band Squeeze) in the period *just before* the potential break. If not, it ignores any break, assuming the market is too choppy.

3.  **Identify the Initial Break:**
    *   **Breakout (Potential BUY):** It checks if the current candle's closing price is **above the resistance ceiling**.
    *   **Breakdown (Potential SELL):** It checks if the current candle's closing price is **below the support shelf**.

4.  **Initial Volume Check:** If a break is detected, and `USE_VOLUME_CONFIRMATION` is `True`, it immediately checks if the break candle was accompanied by a significant volume spike.

5.  **Transition State:** If a valid break with sufficient volume occurs, the state machine transitions to `AWAITING_CONFIRMATION`.

### Step 2: Confirm the Break (`AWAITING_CONFIRMATION` State)

Once a potential break is identified, the algorithm waits to see if the move is genuine.

1.  **Open Confirmation Window:** It observes the next `CONFIRMATION_WINDOW` candles.

2.  **Check for Consistency:** It counts how many of these confirmation candles also close beyond the broken level (above resistance or below support). This count must be greater than or equal to `CONSISTENCY_THRESHOLD`.

3.  **Check for Increasing Volume (Optional):** If `USE_INCREASING_VOLUME_CONFIRMATION` is `True`, it verifies that volume was generally rising during the confirmation window, indicating growing conviction behind the move.

4.  **Check Trend Strength (ADX):** It checks the ADX value on the *final* confirmation candle. The value must be above `ADX_CONFIRMATION_THRESHOLD`, which proves that a strong, directional trend is now in place.

### Step 3: Signal Generation

If all confirmation checks (consistency, volume, and ADX) pass, an `AlertData` object is created, and a `BUY` (for a resistance breakout) or `SELL` (for a support breakdown) signal is generated. The algorithm then enters a cooldown period to avoid generating duplicate alerts.
