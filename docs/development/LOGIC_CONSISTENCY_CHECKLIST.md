# Logic Consistency Checklist: `validate_alerts.py` vs. `realtime_monitor.py`

**Objective:** To ensure that every piece of signal generation logic, from indicator calculation to final filtering, is identical between the backtesting environment (`validate_alerts.py`) and the live trading environment (`realtime_monitor.py`).

**Instructions:** For each item, verify that the code and corresponding settings are exactly the same in both `tests/manual/validate_alerts.py` and `src/stockreports/monitoring/realtime_monitor.py`. All settings should be sourced from `src/stockreports/config/signal_settings.py`.

---

### ✅ 1. Global Data Preparation

| Item to Check                                      | `validate_alerts.py` Logic (`prepare_data`) | `realtime_monitor.py` Logic (`prepare_data`) | Status |
| :------------------------------------------------- | :------------------------------------------ | :------------------------------------------- | :----- |
| **ADX Calculation**                                | `ADXIndicator(..., window=14)`              | `ADXIndicator(..., window=14)`               | `[x]`  |
| **Bollinger Bands Window**                         | `rolling(window=TREND_SQUEEZE_LOOKBACK_PERIOD)` | `rolling(window=TREND_SQUEEZE_LOOKBACK_PERIOD)` | `[x]`  |
| **Bollinger Bands Std Dev**                        | `std_dev = 2`                               | `std_dev = 2`                                | `[x]`  |
| **Ichimoku: Tenkan-sen**                           | `rolling(window=9)`                         | `rolling(window=9)`                          | `[x]`  |
| **Ichimoku: Kijun-sen**                            | `rolling(window=26)`                        | `rolling(window=26)`                         | `[x]`  |
| **Ichimoku: Senkou Span B**                        | `rolling(window=52)`                        | `rolling(window=52)`                         | `[x]`  |
| **Moving Average Short**                           | `rolling(window=MA_SHORT_PERIOD)`           | `rolling(window=MA_SHORT_PERIOD)`            | `[x]`  |
| **Moving Average Long**                            | `rolling(window=MA_LONG_PERIOD)`            | `rolling(window=MA_LONG_PERIOD)`             | `[x]`  |
| **Average Volume**                                 | `rolling(window=AVG_VOLUME_PERIOD)`         | `rolling(window=AVG_VOLUME_PERIOD)`          | `[x]`  |
| **Kumo Trend Calculation**                         | `kumo_is_bullish` / `kumo_is_bearish` logic matches | `kumo_is_bullish` / `kumo_is_bearish` logic matches | `[x]` |

---

### ✅ 2. MA Cross Signal

| Item to Check                                      | `validate_alerts.py` Logic (`find_alerts`) | `realtime_monitor.py` Logic (`analyze_live_data`) | Status |
| :------------------------------------------------- | :----------------------------------------- | :------------------------------------------------ | :----- |
| **Cross Detection Logic**                          | `(MA_short > MA_long) & (MA_short.shift(1) < MA_long.shift(1))` | `(MA_short > MA_long) & (MA_short.shift(1) < MA_long.shift(1))` | `[x]` |
| **Price Action Filter (Bullish)**                  | `close > MA_long`                          | `close > MA_long`                                 | `[x]`  |
| **Price Action Filter (Bearish)**                  | `close < MA_long`                          | `close < MA_long`                                 | `[x]`  |
| **ADX Filter**                                     | `(adx >= min) & (adx <= max)` from `ADX_THRESHOLD_RANGE` | `(adx >= min) & (adx <= max)` from `ADX_THRESHOLD_RANGE` | `[x]` |
| **Kumo Filter (Bullish)**                          | `price_above_kumo or kumo_is_bullish`    | `price_above_kumo or kumo_is_bullish`           | `[x]`  |
| **Kumo Filter (Bearish)**                          | `price_below_kumo or kumo_is_bearish`    | `price_below_kumo or kumo_is_bearish`           | `[x]`  |

---

### ✅ 3. Ichimoku Signal

| Item to Check                                      | `validate_alerts.py` Logic (`find_alerts`) | `realtime_monitor.py` Logic (`analyze_live_data`) | Status |
| :------------------------------------------------- | :----------------------------------------- | :------------------------------------------------ | :----- |
| **TK Cross Logic**                                 | `(tenkan > kijun) & (tenkan.shift(1) < kijun.shift(1))` | `(tenkan > kijun) & (tenkan.shift(1) < kijun.shift(1))` | `[x]` |
| **Kumo Filter (Bullish)**                          | `price_above_kumo or kumo_is_bullish`    | `price_above_kumo or kumo_is_bullish`           | `[x]`  |
| **Kumo Filter (Bearish)**                          | `price_below_kumo or kumo_is_bearish`    | `price_below_kumo or kumo_is_bearish`           | `[x]`  |
| **Chikou Span Filter (Bullish)**                   | `close > close.shift(-26)`                 | `close > close.shift(-26)`                        | `[x]`  |
| **Chikou Span Filter (Bearish)**                   | `close < close.shift(-26)`                 | `close < close.shift(-26)`                        | `[x]`  |
| **Kijun Distance Filter**                          | `(dist >= min) & (dist <= max)` from `ICHI_MAX_KIJUN_DISTANCE_PCT_RANGE` | `(dist >= min) & (dist <= max)` from `ICHI_MAX_KIJUN_DISTANCE_PCT_RANGE` | `[x]` |

---

### ✅ 4. Trend Strength Signal (BB Squeeze)

| Item to Check                                      | `validate_alerts.py` Logic (`find_alerts`) | `realtime_monitor.py` Logic (`analyze_live_data`) | Status |
| :------------------------------------------------- | :----------------------------------------- | :------------------------------------------------ | :----- |
| **Squeeze Condition**                              | `(width.shift(1) > min) & (width.shift(1) < max)` from `TREND_SQUEEZE_BB_WIDTH_RANGE` | `(width.shift(1) > min) & (width.shift(1) < max)` from `TREND_SQUEEZE_BB_WIDTH_RANGE` | `[x]` |
| **Breakout Condition (Bullish)**                   | `close >= bb_upper * (1 - nearness_factor)` | `close >= bb_upper * (1 - nearness_factor)` | `[x]` |
| **Breakout Condition (Bearish)**                   | `close <= bb_lower * (1 + nearness_factor)` | `close <= bb_lower * (1 + nearness_factor)` | `[x]` |
| **Strong Close Filter (Bullish)**                  | `(close - low) / range >= min` from `STRONG_CLOSE_THRESHOLD_RANGE` | `(close - low) / range >= min` from `STRONG_CLOSE_THRESHOLD_RANGE` | `[x]` |
| **Strong Close Filter (Bearish)**                  | `(high - close) / range >= min` from `STRONG_CLOSE_THRESHOLD_RANGE` | `(high - close) / range >= min` from `STRONG_CLOSE_THRESHOLD_RANGE` | `[x]` |
| **Signal Handling**                                | High-priority, independent signal that bypasses other checks | High-priority, independent signal that bypasses other checks | `[x]` |

---

### ✅ 5. Volume Spike Signal

| Item to Check                                      | `validate_alerts.py` Logic (`find_alerts`) | `realtime_monitor.py` Logic (`analyze_live_data`) | Status |
| :------------------------------------------------- | :----------------------------------------- | :------------------------------------------------ | :----- |
| **Spike Detection Logic**                          | `(vol > min) & (vol < max)` from `VOLUME_SPIKE_MULTIPLIER_RANGE` | `(vol > min) & (vol < max)` from `VOLUME_SPIKE_MULTIPLIER_RANGE` | `[x]` |
| **Directional Confirmation (Bullish)**             | Not used for alert generation              | Not used for alert generation                     | `[x]`  |
| **Directional Confirmation (Bearish)**             | Not used for alert generation              | Not used for alert generation                     | `[x]`  |
| **Integration Logic**                              | Not integrated into primary alerts         | Not integrated into primary alerts                | `[x]` |

---

### ✅ 6. "Big Trend" Confirmation

| Item to Check                                      | `validate_alerts.py` Logic (`check_big_trend_confirmation`) | `realtime_monitor.py` Logic (`check_big_trend_confirmation`) | Status |
| :------------------------------------------------- | :---------------------------------------------------------- | :----------------------------------------------------------- | :----- |
| **Lookback Logic**                                 | `current_index - pd.Timedelta(minutes=...)` or start of day | `current_index - pd.Timedelta(minutes=...)` or start of day  | `[x]`  |
| **Highest/Lowest Price Breakout**                  | `current_price >= lookback_df.iloc[:-1]['high'].max()`      | `current_price >= lookback_df.iloc[:-1]['high'].max()`       | `[x]`  |
| **Breakout Confirmation**                          | `current_price > max_price + (price_range * threshold)`     | `current_price > max_price + (price_range * threshold)`      | `[x]`  |
| **Reversal Confirmation**                          | `reversal_min <= current_price <= reversal_max`             | `reversal_min <= current_price <= reversal_max`              | `[x]`  |
| **Momentum Confirmation**                          | `all(momentum_candles['close'] > momentum_candles['open'])` | `all(momentum_candles['close'] > momentum_candles['open'])`  | `[x]`  |
| **Signal Handling**                                | Bypassed by BB Squeeze Breakout signal                      | Bypassed by BB Squeeze Breakout signal                       | `[x]`  |

