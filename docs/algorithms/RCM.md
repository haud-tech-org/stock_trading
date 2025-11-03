# RCM (Reversal Confirmation Model)

## Objective

The **Reversal Confirmation Model (RCM)** is a trend-following strategy designed to identify and act on significant market reversals. Its primary goal is to detect when a prevailing trend has likely ended and a new trend in the opposite direction is beginning. It does this by first identifying a potential reversal point (a significant peak or trough) and then waiting for a confirmation of momentum in the new direction before generating a signal.

## Key Parameters

The behavior of the RCM is controlled by several key parameters found in `src/stockreports/config/signal_settings.py`:

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `PEAK_TROUGH_PROMINENCE` | 5 | **(Crucial)** The minimum price change (in points) required to classify a price swing as a significant peak or trough. A higher value filters out minor fluctuations, making the algorithm more selective. |
| `CONFIRMATION_WINDOW` | 5 | The number of candles after a peak or trough during which the algorithm will look for a confirmation signal. If no confirmation occurs within this window, the potential reversal is ignored. |
| `CONFIRMATION_MIN_CONSISTENCY` | 3 | The minimum number of candles that must move in the signal's direction within the `CONFIRMATION_WINDOW`. This acts as a mandatory filter for all signals. |
| `PEAK_BOTTOM_LOOKBACK_PERIOD` | 60 | The number of past candles to look at to confirm a breakout. The current price must be higher than the highest high (for a BUY) or lower than the lowest low (for a SELL) in this period. |
| `MIN_ALERT_MAGNITUDE` | 4 | The minimum price change (in points) required between the reversal point and the confirmation candle for an alert to be considered significant. |
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
        *   The algorithm first attempts to get a potential signal. If sufficient data is available (`can_apply_advanced_confirmation`), it uses `check_advanced_confirmation` (based on indicators like MACD, RSI, ADX).
        *   If not, it generates a basic signal based purely on the reversal type ('BUY' for a trough, 'SELL' for a peak).
    *   If a potential signal is found by either method, it proceeds to the final validation checks.
    *   If the `CONFIRMATION_WINDOW` closes without a signal, the state returns to `NEUTRAL`.

3.  **Final Validation & Signal Generation:**
    *   If a potential confirmation signal is received, a final series of checks is performed in a specific order:
    *   **1. Consistency Check:** It first verifies that at least `CONFIRMATION_MIN_CONSISTENCY` candles within the confirmation window have moved in the direction of the signal. This is a mandatory check for all signals.
    *   **2. Breakout Check:** If consistent, it then verifies that the current price has decisively broken out of the recent trading range, controlled by `PEAK_BOTTOM_LOOKBACK_PERIOD`.
    *   **3. Magnitude Check:** If the breakout is confirmed, it checks that the price movement from the initial reversal point to the current candle is significant enough, using the approach-specific `MIN_ALERT_MAGNITUDE`.
    *   **4. Volume Check:** If enabled, it performs a final check for a volume spike or increasing volume to support the signal's strength.
    *   If all checks pass, an `AlertData` object is created with the signal (`BUY` or `SELL`), and the state transitions to `IN_UPTREND` or `IN_DOWNTREND` to prevent generating duplicate signals for the same trend.

4.  **`IN_TREND` State (Waiting for the Next Reversal):**
    *   The algorithm remains in this state until it detects an *opposing* reversal signal (a peak during an uptrend or a trough during a downtrend), at which point it resets back to the `NEUTRAL` state to begin the cycle again.
