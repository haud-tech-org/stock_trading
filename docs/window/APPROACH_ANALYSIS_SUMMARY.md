# Approach Analysis Summary

This document summarizes the analysis of each alert approach, focusing on the time periods used for lookback (analyzing past data) and confirmation (waiting for a signal to mature). This is critical for understanding potential delays in alert generation and for preventing missed alerts in real-time deployment.

## Key Concepts

*   **Lookback Period:** The maximum number of past candles an approach looks at to establish historical context (e.g., to find a support level or calculate a moving average). This defines the "memory" of the algorithm.
*   **Confirmation Window (Pattern Length):** The number of candles that constitute a full pattern, from the initial event to the final confirmation candle. This is the primary factor determining how "old" a detected signal can be. A longer pattern means an alert can mature several candles after its initial trigger.

## Analysis Summary Table

The following table details the maximum lookback and the length of the pattern for each approach. The "Max Pattern Length" is the most critical value for deployment logic, as it dictates the buffer needed to catch recently matured alerts.

| Approach Name              | Max Lookback Period                 | Max Pattern Length (Delay) | How it Works                                                                                                                            |
| :------------------------- | :---------------------------------- | :------------------------------ | :-------------------------------------------------------------------------------------------------------------------------------------- |
| **`SUPPORT_RESISTANCE_BREAK`** | 60 periods (`LOOKBACK_PERIOD`)      | **4 candles** (`CONFIRMATION_WINDOW` + 1) | A level is established over 60 candles. A break occurs on candle `i-3`, and the pattern is confirmed over the next 3 candles, alerting on candle `i`. |
| **`STRONG_CANDLE`**        | ~26 periods (for MACD/RSI) + 4      | **~5 candles** (`CONFIRMATION_WINDOW` + 2) | A strong candle appears, then it waits up to 4 candles for an indicator confirmation, and the alert triggers on the next momentum candle. |
| **`RCM`**                  | Full history (for peaks) + 3        | **4 candles** (`CONFIRMATION_WINDOW` + 1) | A reversal peak/trough is found, and the system waits up to 3 candles for a confirmation signal, alerting on the 4th. |
| **`CONSISTENT_MOMENTUM`**  | 30 periods (`PEAK_BOTTOM_LOOKBACK_PERIOD`) | **3 candles** (`CONFIRMATION_WINDOW`) | The alert triggers on the last candle of a 3-candle consistent momentum window.                                                         |
| **`MOMENTUM_EXHAUSTION`**  | 4 periods (`MOMENTUM` + `EXHAUSTION`) | **4 candles** (Full pattern length) | A 2-candle momentum phase is followed by a 2-candle exhaustion phase, reversal, and confirmation. The alert triggers on the final candle. |
| **`CONSOLIDATION_BREAKOUT`** | 50 periods (`CONSOLIDATION_LOOKBACK`) | **2 candles** (`BREAKOUT_CONFIRMATION_CANDLES` + 1) | After a 50-candle consolidation, a break occurs, and the alert triggers on the next confirmation candle. |
| **`ICHIMOKU`**             | 52 periods (`SENKOU_B_PERIOD`)      | **1 candle** (Optional: + `CONFIRMATION_CANDLE_COUNT`) | The alert is nearly immediate. It triggers on the candle of the cross event. An optional look-forward can add a small delay. |
| **`CONSECUTIVE_POWER_CANDLES`** | 3 periods (`CANDLE_COUNT`)          | **3 candles** (Full pattern length) | The alert triggers on the 3rd consecutive power candle. |
| **`COMPARISON`**           | 10 periods (`LOOKBACK_WINDOW`)      | **1 candle**                    | The alert triggers on the single candle where the divergence condition is met. |
| **`VOLUME_SPIKE_CONFIRMATION`** | 2 periods (`SIGNAL_LOOKBACK_PERIOD`) | **3 candles** (`SIGNAL_LOOKBACK_PERIOD` + 1) | A signal candle is found in a 2-candle lookback, and the alert triggers on the next confirmation candle. |
| **`PRICE_GAP`**            | 20 periods (`LOOKBACK_PERIOD`)      | **1 candle**                    | The alert triggers immediately on the candle where the gap occurs. |

## Conclusion for Deployment Logic

The analysis shows that the longest possible pattern length is approximately **5 candles**, originating from the `STRONG_CANDLE` approach. This means an alert's initial trigger could have occurred 5 candles before the final confirmation.

To guarantee that no recently-matured alerts are missed in `DEPLOYMENT` mode, a "grace period" buffer must be added to the `active_region_start` calculation. Based on this analysis, the recommended buffer size is **5**.

The corrected logic for defining the active scan region should be:
`active_region_start = len(df_indexed) - new_candle_count - 5`

This ensures that even the slowest-to-confirm alert is captured and processed correctly if its pattern completes within the newly arrived data.