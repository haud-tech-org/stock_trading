# Algorithm: Consolidation Breakout

## 1. Overview

The **Consolidation Breakout** strategy identifies periods of price consolidation (sideways movement within a tight range) and generates alerts when the price breaks out of this range, signaling a potential new trend. The core idea is that a consolidation period represents market indecision, and a breakout indicates a decisive move in one direction, often accompanied by increased momentum.

This approach is highly configurable and uses a combination of price action, volatility, and optional indicators to accurately identify consolidation zones and validate breakouts.

## 2. Core Logic

The executor analyzes the data using a rolling window approach. For each candle, it looks back over a specified `CONSOLIDATION_LOOKBACK` period to determine if a consolidation pattern exists. If it does, it then checks the subsequent candle(s) for a breakout.

### 2.1. Identifying the Consolidation Zone

A time window is identified as a "consolidation zone" if it meets several configurable criteria designed to filter out trending or overly volatile periods.

1.  **Price Clustering (Core Requirement)**:
    *   A `center_price` is calculated as the median of the `close` prices within the lookback period.
    *   The algorithm checks how many candles have their `close` price within a `MAX_DEVIATION_FROM_CENTER` from this median price.
    *   To qualify as consolidation, the ratio of these "clustered" candles must exceed `MIN_CLUSTERED_CANDLE_RATIO`. This ensures the price is truly trading sideways around a central point.

2.  **Channel Consistency Check (Optional)**:
    *   If `USE_CHANNEL_CONSISTENCY_CHECK` is enabled, the logic becomes stricter.
    *   It defines a "core channel" using the highest high and lowest low of only the clustered candles.
    *   It then checks for outliers—candles from the entire lookback period that fall outside this core channel.
    *   If the ratio of outliers exceeds `MAX_CHANNEL_OUTLIER_RATIO`, the period is invalidated. This filters out periods with significant spikes.

3.  **Balanced Sideways Movement Check (Optional)**:
    *   If `USE_BALANCED_SIDEWAYS_CHECK` is enabled, two conditions are checked:
        *   **Flat Trend**: A linear regression is performed on the `close` prices. If the absolute slope of the trend line exceeds `MAX_REGRESSION_SLOPE`, the period is considered too directional.
        *   **Time Balance**: It counts the number of candles closing above versus below the `center_price`. If the distribution is too skewed (i.e., the price spends most of its time on one side of the median), it's not a balanced consolidation. The imbalance is checked against `MAX_TIME_BALANCE_DEVIATION_RATIO`.

4.  **Consecutive Trend Check (Optional)**:
    *   If `USE_CONSECUTIVE_TREND_CHECK` is enabled, the algorithm looks for sustained micro-trends within the consolidation window.
    *   It counts the longest sequence of consecutive bullish (green) or bearish (red) candles.
    *   If this run exceeds `MAX_CONSECUTIVE_TREND_CANDLES`, the period is invalidated, as it suggests underlying directional pressure rather than true consolidation.

5.  **Peak & Trough Analysis (Optional)**:
    *   If `MIN_PEAKS_TROUGHS` is greater than zero, the algorithm identifies significant local highs (peaks) and lows (troughs) within the window.
    *   It requires a minimum number of these turning points to be present, ensuring the price is oscillating.
    *   An additional `USE_ALTERNATING_PEAKS_TROUGHS_CHECK` can enforce that these peaks and troughs alternate, which is a classic characteristic of a sideways channel.

### 2.2. Indicator-Based Filters (Optional)

These filters use standard technical indicators to further qualify the consolidation zone.

1.  **ADX Filter**:
    *   If `USE_ADX_FILTER` is enabled, the Average Directional Index (ADX) is used to measure trend strength.
    *   The algorithm requires a significant portion of the consolidation window (defined by `ADX_CONFIRMATION_RATIO`) to have an ADX value below `ADX_THRESHOLD`, confirming a non-trending or weak-trending state.

2.  **Bollinger Bands® Width Filter**:
    *   If `USE_BB_WIDTH_FILTER` is enabled, it checks for a "squeeze," which often precedes a volatile breakout.
    *   It measures the Bollinger Band® width as a percentage of the middle band.
    *   A large portion of the window (defined by `BB_SQUEEZE_CONFIRMATION_RATIO`) must have a width percentage below `BB_WIDTH_THRESHOLD_PERCENT`.

### 2.3. Detecting the Breakout

Once a valid consolidation zone is identified, the algorithm defines a `resistance` level (highest high of clustered candles) and a `support` level (lowest low of clustered candles).

A breakout occurs if the candle immediately following the consolidation window closes **above the resistance** (for a BUY signal) or **below the support** (for a SELL signal).

### 2.4. Confirming the Breakout

Several final checks are performed to validate the breakout's strength and reduce false signals.

1.  **Pre-Breakout Candle Direction**: The candle immediately *before* the breakout candle must show intent. For a BUY signal, the last candle in the consolidation window must be bullish (`close >= open`). For a SELL signal, it must be bearish (`close <= open`).

2.  **Volume Spike Confirmation (Optional)**:
    *   If `USE_VOLUME_SPIKE_CONFIRMATION` is enabled, the breakout must be supported by a surge in volume.
    *   It checks if the volume of the breakout candle OR the pre-breakout candle is significantly higher (by a `VOLUME_SPIKE_MULTIPLIER`) than the average volume during the consolidation period.

3.  **Standard Confirmation (Optional)**:
    *   If `USE_CONFIRMATION` is enabled, it calls the shared `is_signal_confirmed` function, which can be configured to check indicators like RSI, MACD, or Stochastics on the breakout candle to ensure they align with the breakout direction.

## 3. Alert Generation

If a breakout is identified and confirmed, an `AlertData` object is created with the following key details:
-   **Approach**: `CONSOLIDATION_BREAKOUT`
-   **Signal**: `BUY` or `SELL`
-   **Reason**: A summary message indicating the length of the consolidation channel that was broken.
-   **Details**: A JSON object containing the exact `resistance` and `support` levels, breakout candle metrics, and the clustered candle ratio.

## 4. Configuration

All parameters are configured in `signal_settings.py` under the `APPROACH_CONFIG["CONSOLIDATION_BREAKOUT"]` dictionary. This allows for fine-tuning the strategy for different symbols or market conditions without changing the code.

### Key Configuration Parameters:

-   `CONSOLIDATION_LOOKBACK`: A list of lookback periods to check for consolidation.
-   `MAX_DEVIATION_FROM_CENTER`: The percentage deviation allowed from the median price for a candle to be "clustered".
-   `MIN_CLUSTERED_CANDLE_RATIO`: The minimum ratio of clustered candles required to define a consolidation zone.
-   `USE_*_CHECK` / `USE_*_FILTER`: Boolean flags to enable or disable the various optional checks described above.
-   Thresholds and multipliers for each of the optional checks (e.g., `ADX_THRESHOLD`, `VOLUME_SPIKE_MULTIPLIER`).
