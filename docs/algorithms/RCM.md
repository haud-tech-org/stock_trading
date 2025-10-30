# RCM (Reversal Confirmation Model)

## Objective

The **Reversal Confirmation Model (RCM)** is a trend-following strategy designed to identify and act on significant market reversals. Its primary goal is to detect when a prevailing trend has likely ended and a new trend in the opposite direction is beginning. It does this by first identifying a potential reversal point (a significant peak or trough) and then waiting for a confirmation of momentum in the new direction before generating a signal.

## Key Parameters

The behavior of the RCM is controlled by several key parameters found in `src/stockreports/config/signal_settings.py`:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `PEAK_TROUGH_PROMINENCE` | 5 | **(Crucial)** The minimum price change (in points) required to classify a price swing as a significant peak or trough. A higher value filters out minor fluctuations, making the algorithm more selective. |
| `CONFIRMATION_WINDOW` | 3 | The number of candles after a peak or trough during which the algorithm will look for a confirmation signal. If no confirmation occurs within this window, the potential reversal is ignored. |
| `CONFIRMATION_MIN_CONSISTENCY` | 2 | **(Simple Mode Only)** The minimum number of candles that must move in the new direction within the `CONFIRMATION_WINDOW` to confirm a reversal. |
| `USE_VOLUME_CONFIRMATION` | `False` | If `True`, requires the confirmation candle's volume to be significantly higher than the recent average volume. |
| `USE_INCREASING_VOLUME_CONFIRMATION` | `False` | If `True`, requires the volume during the confirmation window to be generally increasing. |

## Step-by-Step Logic

The RCM operates as a state machine that processes each candle in the time series. The core logic is implemented in `_find_rcm_alerts` within `src/stockreports/alert/approach/RCM/executor.py`.

### Step 1: Identify Potential Reversal Points

1.  **Find Peaks and Troughs:** The algorithm first scans the entire historical price data (`high` and `low` series) to identify all potential reversal points.
2.  **Apply Prominence Filter:** It uses the `scipy.signal.find_peaks` function with the `PEAK_TROUGH_PROMINENCE` setting. This is the most important filtering step. Only price swings that are more significant than this threshold are kept; all smaller fluctuations are discarded as market noise.

### Step 2: State-Based Signal Detection

The algorithm iterates through the candles, operating in one of four states: `NEUTRAL`, `CONFIRMING`, `IN_UPTREND`, or `IN_DOWNTREND`.

1.  **`NEUTRAL` State (Looking for a Reversal):**
    *   The algorithm is waiting for a new, significant reversal point (a peak or trough identified in Step 1).
    *   If a **trough** is detected, it transitions to the `CONFIRMING` state, sets the `last_reversal_type` to 'trough', and opens a `CONFIRMATION_WINDOW` of N candles to look for a `BUY` signal.
    *   If a **peak** is detected, it does the same but prepares to look for a `SELL` signal.

2.  **`CONFIRMING` State (Looking for Confirmation):**
    *   The algorithm now actively looks for proof that the reversal is genuine. This check happens on every candle within the `CONFIRMATION_WINDOW`.
    *   **Confirmation Logic:**
        *   If sufficient data is available (`can_apply_advanced_confirmation`), it uses `check_advanced_confirmation`, which looks for bullish/bearish signals from indicators like MACD, RSI, and ADX.
        *   Otherwise, it uses a "simple confirmation": it checks if at least `CONFIRMATION_MIN_CONSISTENCY` candles have closed in the new direction.
    *   If the confirmation criteria are met, it proceeds to the final validation checks.
    *   If the `CONFIRMATION_WINDOW` closes without a signal, the state returns to `NEUTRAL`.

3.  **Final Validation & Signal Generation:**
    *   **Magnitude Check:** It verifies that the price movement from the reversal point to the current confirmation candle is significant enough, using the global `TREND_MINIMUM_MAGNITUDE` setting.
    *   **Volume Check:** If enabled, it checks for a volume spike or increasing volume to support the signal.
    *   If all checks pass, an `AlertData` object is created with the signal (`BUY` or `SELL`), and the state transitions to `IN_UPTREND` or `IN_DOWNTREND` to prevent generating duplicate signals for the same trend.

4.  **`IN_TREND` State (Waiting for the Next Reversal):**
    *   The algorithm remains in this state until it detects an *opposing* reversal signal (a peak during an uptrend or a trough during a downtrend), at which point it resets back to the `NEUTRAL` state to begin the cycle again.
