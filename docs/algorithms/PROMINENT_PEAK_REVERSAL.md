# Prominent Peak Reversal (`PROMINENT_PEAK_REVERSAL`)

## Overview

The **Prominent Peak Reversal** approach is a sophisticated pattern recognition strategy designed to identify high-probability trend reversals. It operates by detecting a single, significant peak (for a `SELL` signal) or trough (for a `BUY` signal) within a defined `CONFIRMATION_WINDOW` and then validating a strict set of criteria to confirm that a reversal is underway.

The core idea is to filter out minor fluctuations and focus only on substantial price movements that are followed by a confirmed change in direction, supported by specific candle patterns and volume behavior.

## How It Works

The logic is symmetrical for `BUY` and `SELL` signals. The following describes the process for a `SELL` signal (peak reversal).

### Step 1: Identify a Single Significant Peak

The algorithm first scans the `CONFIRMATION_WINDOW` to find peaks in the **opening prices**.

- **Rule 1a**: It finds all local maxima in the window.
- **Rule 1b**: It selects the peak with the highest price.
- **Rule 1c**: The highest peak must also be the **last** peak found in the window.
- **Rule 1d**: The peak cannot be the **first** candle in the window.
- **Rule 1e**: The peak must have a "left prominence" greater than `PEAK_PROMINENCE`. Left prominence is the vertical distance between the peak and the lowest point in the interval to its left, bounded by the nearest higher point.

### Step 2: Validate the Peak's Significance (Optional)

- **Rule 2**: If `USE_PEAK_IN_LOOKBACK_VALIDATION` is `True`, the algorithm checks if the opening price of the peak candle is the absolute highest opening price within the larger `LOOKBACK_WINDOW`. This ensures the peak is not just a local event but a significant high over a longer period.

### Step 3: Confirm Reversal with Wick Patterns

- **Rule 3**: The algorithm looks for signs of price rejection at the peak. It checks if the peak candle, the candle immediately before it, or the candle immediately following it has a **long upper wick**.
- A wick is considered "long" if its length is greater than the candle's body length multiplied by the `WICK_TO_BODY_RATIO`. The candle body must be greater than zero.

### Step 4: Confirm the Preceding Uptrend

- **Rule 4**: To ensure the peak is the culmination of a genuine uptrend, the algorithm checks the trend leading up to the peak.
- It calculates the average price `(Open + Close) / 2` of the first candle in the window.
- It compares this to the median of the average prices of all candles between the first candle and the peak.
- For a `SELL` signal, the first candle's average price must be **lower** than the median of the preceding candles, indicating an upward trend.

### Step 5: Confirm the Subsequent Downtrend (Reversal Candle)

- **Rule 5**: The final confirmation comes from the very last candle in the `CONFIRMATION_WINDOW`.
- **Body Size**: Its body size `abs(Open - Close)` must be greater than `MIN_BODY_POINT_PRICE`.
- **Price Difference**:
    - If the peak is **not** the last candle: The difference between the peak's body top (max of Open/Close) and the last candle's Close must be at least `MIN_REVERSAL_PRICE_DIFF`.
    - If the peak **is** the last candle: The absolute body size of the last candle must be at least `MIN_REVERSAL_PRICE_DIFF`.
- **Trend Consistency (Last Candle Check)**:
    - If the peak is the last candle, it must match the signal direction (Bearish for Sell, Bullish for Buy).
- **Median Comparison**:
    - If the peak is **not** the last candle, the algorithm compares the last candle's average price to the median average price of all "subsequent candles" (candles from the peak up to the second-to-last candle).
    - For a `SELL` signal, the last candle's average price must be **lower** than the median of the subsequent candles.

### Step 6: Volume Confirmation

- **Rule 6**: As a final check, the algorithm validates volume behavior.
- **Peak Volume**: It finds the maximum volume among the peak candle and its immediate neighbors (T-1, T, T+1).
- **Volume Spike**: This maximum volume must be greater than the average volume of the `LOOKBACK_WINDOW` multiplied by `VOLUME_MULTIPLIER`.
- **Subsequent Volume Drop**: (Currently disabled/commented out in code) All subsequent candles must have volume lower than the peak region's maximum volume.

---

## BUY Signal (Trough Reversal)

The logic for a `BUY` signal is the mirror opposite:
1.  Find a single significant **trough** using **opening prices**.
2.  Validate that the trough is the **lowest** point in the `LOOKBACK_WINDOW`.
3.  Check for a long **lower wick** on the trough candle or its neighbors.
4.  Confirm the preceding downtrend by checking that the first candle's average price was **higher** than the median of preceding candles.
5.  Confirm the subsequent uptrend:
    - Last candle body > `MIN_BODY_POINT_PRICE`.
    - Price difference from trough body bottom to last close > `MIN_REVERSAL_PRICE_DIFF`.
    - Last candle average price **higher** than median of subsequent candles.
6.  Confirm that the volume around the trough is a significant spike compared to the lookback average.

## Configuration Parameters

| Parameter                           | Type    | Description                                                                                                                             | Default Value |
| ----------------------------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------------- |
| `LOOKBACK_WINDOW`                   | Integer | The number of candles to look back for the peak/trough validation (Rule 2).                                                              | `50`          |
| `CONFIRMATION_WINDOW`               | Integer | The primary window size (in candles) for the entire analysis.                                                                               | `10`          |
| `PEAK_PROMINENCE`                   | Float   | The minimum prominence (in price points) for a peak/trough to be considered significant. Higher values are less sensitive.                  | `3.0`         |
| `USE_PEAK_IN_LOOKBACK_VALIDATION`   | Boolean | If `True`, enables the check that the peak/trough is the highest/lowest in the `LOOKBACK_WINDOW`.                                           | `True`        |
| `WICK_TO_BODY_RATIO`                | Float   | The multiplier used to define a "long" wick. (e.g., `1.5` means the wick must be > 1.5x the body size).                                     | `1.5`         |
| `MIN_BODY_POINT_PRICE`              | Float   | The minimum price point size of the body for the final reversal candle (Rule 5).                                                            | `0.5`         |
| `MIN_REVERSAL_PRICE_DIFF`           | Float   | The minimum absolute price difference required between the peak/trough body and the final reversal candle's close.                         | `1.0`         |
| `VOLUME_MULTIPLIER`                 | Float   | The multiplier for volume spike validation. Peak volume must be > Average Lookback Volume * Multiplier.                                     | `1.5`         |
| `COOLDOWN_WINDOW`                   | Integer | The minimum time (in minutes) to wait after an alert before generating another one for the same symbol.                                     | `60`          |
| `DISABLE_SELL_SIGNAL`               | Boolean | If `True`, the approach will not generate any `SELL` signals.                                                                               | `False`       |
| `DISABLE_BUY_SIGNAL`                | Boolean | If `True`, the approach will not generate any `BUY` signals.                                                                                | `False`       |
