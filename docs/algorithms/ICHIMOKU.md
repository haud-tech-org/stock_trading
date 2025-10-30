# ICHIMOKU

## Objective

The **Ichimoku Cloud** strategy is a comprehensive, all-in-one indicator that provides information about support/resistance, trend direction, and momentum. The goal of this approach is to identify strong, high-probability trades by waiting for all major components of the Ichimoku system to align, signaling a clear and confirmed trend.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py` and uses the following parameters:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `TENKAN_PERIOD` | 9 | The lookback period for the Tenkan-sen (Conversion Line), representing short-term momentum. |
| `KIJUN_PERIOD` | 26 | The lookback period for the Kijun-sen (Base Line), representing mid-term momentum. |
| `SENKOU_B_PERIOD` | 52 | The lookback period for the Senkou Span B (Leading Span B), representing the slowest component and long-term support/resistance. |
| `CHIKOU_LAG` | 26 | The number of periods the Chikou Span (Lagging Span) is shifted back in time. |
| `USE_VOLUME_CONFIRMATION` | `True` | If `True`, requires the signal candle to have a significant volume spike. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires volume to be increasing over the last two candles. |

## Step-by-Step Logic

The core logic resides in the `_find_ichimoku_alerts` function in `src/stockreports/alert/approach/ICHIMOKU/executor.py`. For a signal to be generated, a series of strict conditions must be met simultaneously on the current candle.

### Indicator Calculation

First, the algorithm calculates the five core components of the Ichimoku system:

1.  **Tenkan-sen (Conversion Line):** The midpoint of the 9-period high and low.
2.  **Kijun-sen (Base Line):** The midpoint of the 26-period high and low.
3.  **Senkou Span A (Leading Span A):** The midpoint of the Tenkan-sen and Kijun-sen, plotted 26 periods into the future.
4.  **Senkou Span B (Leading Span B):** The midpoint of the 52-period high and low, plotted 26 periods into the future.
5.  **Kumo (Cloud):** The area between Senkou Span A and Senkou Span B.
6.  **Chikou Span (Lagging Span):** The current closing price, plotted 26 periods in the *past*.

### Signal Generation Conditions

The algorithm then checks for a "perfect" bullish or bearish signal where all components align.

#### Bullish Signal (`BUY`)

A `BUY` signal is generated if **all three** of the following conditions are true on the current candle:

1.  **Tenkan/Kijun Cross:** The Tenkan-sen (faster line) crosses **above** the Kijun-sen (slower line). This is the primary momentum trigger.
2.  **Price Above Kumo:** The current closing price is **above** both Senkou Span A and Senkou Span B, confirming the price is in bullish territory.
3.  **Chikou Confirmation:** The Chikou Span (price from 26 periods ago) is **above the price** from that same period (`df_indexed.iloc[i - chikou_lag]['high']`). This confirms there are no major resistance levels in the recent past.

#### Bearish Signal (`SELL`)

A `SELL` signal is generated if **all three** of the following conditions are true:

1.  **Tenkan/Kijun Cross:** The Tenkan-sen crosses **below** the Kijun-sen.
2.  **Price Below Kumo:** The current closing price is **below** both Senkou Span A and Senkou Span B.
3.  **Chikou Confirmation:** The Chikou Span is **below the price** from 26 periods ago.

### Final Validation

If a `BUY` or `SELL` signal is triggered, it undergoes a final, optional volume check before an alert is created:

*   **Volume Check:** If enabled, it verifies that the signal candle was accompanied by a volume spike or that volume has been increasing.

If all conditions are met, an `AlertData` object is created.
