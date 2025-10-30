# CONSISTENT_MOMENTUM

## Objective

The **Consistent Momentum** strategy is designed to identify periods of strong, sustained, and high-quality directional movement. Unlike reversal strategies, its goal is to join a trend that is already demonstrating clear and consistent strength. It validates this momentum through a series of strict checks, including candle patterns, breakout confirmation, volume, and indicator alignment.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py` and uses the following parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `CONFIRMATION_WINDOW` | 3 | The number of consecutive candles that must all show consistent directional momentum. |
| `PEAK_BOTTOM_LOOKBACK_PERIOD` | 30 | The number of minutes to look back from the start of the momentum window to find a recent peak or trough to break. |
| `BODY_TO_RANGE_MIN_RATIO` | 0.7 | The minimum average ratio of the candle's body to its total range (body + wick) across the window. This ensures the candles are decisive and not mostly wick. |
| `USE_VOLUME_CONFIRMATION` | `True` | If `True`, requires the final candle in the window to have a volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires the volume to be generally increasing across the confirmation window. |

## Step-by-Step Logic

The core logic resides in the `_analyze_window` function in `src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py`. The algorithm analyzes a rolling window of `CONFIRMATION_WINDOW` candles. For a signal to be generated, **all** of the following checks must pass:

1.  **Basic Momentum Check:**
    *   All candles within the window must be bullish (`close > open`) for a `BUY` signal.
    *   All candles must be bearish (`close < open`) for a `SELL` signal.
    *   If there is any mix, the window is invalid.

2.  **Consistent Trend Check:**
    *   For a `BUY` signal, each candle in the window must have a higher high AND a higher low than the previous candle.
    *   For a `SELL` signal, each candle must have a lower high AND a lower low.
    *   This confirms a smooth, non-volatile trend.

3.  **Strong Close Check:**
    *   The final candle in the window must close "strongly." For a `BUY`, it must close in the upper half of its range. For a `SELL`, it must close in the lower half. This is controlled by the global `STRONG_CLOSE_THRESHOLD_RANGE` setting.

4.  **Peak/Trough Breakout Confirmation:**
    *   This is a critical check to ensure the momentum is breaking out of a recent consolidation range.
    *   The algorithm looks back `PEAK_BOTTOM_LOOKBACK_PERIOD` minutes from the *start* of the momentum window.
    *   For a `BUY` signal, the closing price of the final candle must be **higher than the highest peak** found in that lookback period.
    *   For a `SELL` signal, the closing price must be **lower than the lowest trough**.

5.  **Volume Confirmation:**
    *   If enabled, the volume of the final candle in the window is checked for a significant spike compared to recent averages (`is_volume_spike_confirmed`).
    *   If enabled, the volume across the entire window is checked to ensure it is generally increasing (`is_volume_increasing`).

6.  **Candle Quality Check (Body-to-Range Ratio):**
    *   The algorithm calculates the average ratio of the candle body to the total candle range for all candles in the window.
    *   This average must be greater than `BODY_TO_RANGE_MIN_RATIO`. This filters out windows of indecisive candles (like dojis) that have long wicks and small bodies.

7.  **Body Dominance Check:**
    *   The sum of the bodies of all candles in the window must be greater than the sum of all their wicks. This is another check to ensure the directional move is decisive.

8.  **Advanced Indicator Confirmation (Optional):**
    *   If enough data is available, the algorithm will perform a final check using indicators like MACD, RSI, and ADX (`check_advanced_confirmation`).
    *   The signal from these indicators must match the direction of the momentum (e.g., a `BUY` signal from indicators for a bullish momentum window).

If a window of candles successfully passes every single one of these checks, an `AlertData` object is generated.
