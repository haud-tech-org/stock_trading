# VOLUME_SPIKE_CONFIRMATION

## Objective

The **Volume Spike Confirmation** strategy is designed to identify potentially significant market moves that are initiated by a sudden surge in trading volume and immediately confirmed by a strong follow-up candle. The core idea is to filter out random noise by requiring two distinct events in sequence: a volume anomaly followed by price conviction.

## Key Parameters

This approach is configured in `src/stockreports/config/signal_settings.py`. A dedicated settings class, `VolumeSpikeConfirmationSettings`, in `src/stockreports/alert/approach/VOLUME_SPIKE_CONFIRMATION/settings.py` loads these parameters.

| Parameter | Default | Description |
| :--- | :--- | :--- |
| `SIGNAL_LOOKBACK_PERIOD` | 3 | The number of candles to look back from the confirmation candle to find the signal candle (the one with the highest volume). |
| `VOLUME_SPIKE_MULTIPLIER` | 2.5 | The volume of the "signal candle" must be at least this many times greater than the average intraday volume calculated up to that point. |
| `MIN_CONFIRMATION_BODY_SIZE` | 1.0 | The minimum absolute size (in price points) of the body of the "confirmation candle". |
| `MIN_CONFIRMATION_BODY_RATIO` | 0.6 | The minimum ratio of the confirmation candle's body to its total range (`body / (high - low)`). This ensures the candle is decisive. |
| `PEAK_TROUGH_PROMINENCE` | 0.5 | The prominence required for the peak/trough detection algorithm to identify a valid reversal point within the window. |
| `COOLDOWN_PERIOD` | 2 | The number of minutes to wait after *any* alert before firing another one. |
| `MIN_LOOKBACK_DATA` | 30 | The minimum number of candles required in the dataset to ensure a reliable average volume calculation. |

## Step-by-Step Logic (Backward Loop)

The core logic resides in the `VolumeSpikeConfirmationExecutor` class. It uses a reverse loop for real-time efficiency. For each candle `i`, it treats it as a potential "confirmation candle" and analyzes a window of preceding candles.

The process begins with a data sufficiency check:
- **Minimum Data Check:** Before any analysis, the executor verifies that it has at least `MIN_LOOKBACK_DATA` candles. If not, it logs a warning and exits.

The pattern analysis involves a window defined by `SIGNAL_LOOKBACK_PERIOD`. Let's denote the window ending at the confirmation candle `i` as the "Analysis Window".

### Signal Generation Conditions

1.  **Identify Signal Candle:**
    *   The algorithm looks at the window excluding the confirmation candle (indices `i-lookback` to `i-1`).
    *   It identifies the candle with the highest volume in this sub-window as the `signal_candle`.
    *   **Position Constraint:** The `signal_candle` must **not** be the very first candle of the sub-window, nor the last one (immediately preceding the confirmation candle). It must be "sandwiched" within the lookback period.

2.  **Check for Volume Spike:**
    *   The algorithm calculates the average volume of all candles in the dataset *prior* to the `signal_candle`.
    *   It checks if the volume of the `signal_candle` is greater than or equal to this average volume multiplied by `VOLUME_SPIKE_MULTIPLIER`.

3.  **Validate Confirmation Candle:**
    *   The confirmation candle (at index `i`) is validated for shape:
        *   **Body Size:** Its absolute body size (`abs(close - open)`) must be greater than or equal to `MIN_CONFIRMATION_BODY_SIZE`.
        *   **Body-to-Range Ratio:** Its body must make up at least `MIN_CONFIRMATION_BODY_RATIO` of its total range.

4.  **Determine Signal Direction & Structural Reversal:**
    *   The algorithm determines the potential signal based on the confirmation candle's color:
        *   **Green Confirmation** -> Potential **BUY**.
        *   **Red Confirmation** -> Potential **SELL**.
    
    *   **Reversal Validation (Peak/Trough):**
        *   It uses a peak-finding algorithm (`scipy.signal.find_peaks`) on the closing prices within the Analysis Window.
        *   **For BUY:** It looks for a **Trough** (local minimum) in the closing prices.
        *   **For SELL:** It looks for a **Peak** (local maximum) in the closing prices.
        *   The identified Peak or Trough must **not** be at the very start or end of the Analysis Window.

5.  **Validate Pre-Spike Trend:**
    *   The algorithm examines the candles in the window *strictly before* the `signal_candle`.
    *   **For BUY:** All pre-spike candles must be **Red** (indicating a downward trend leading into the spike).
    *   **For SELL:** All pre-spike candles must be **Green** (indicating an upward trend leading into the spike).

    If all conditions are met, an `AlertData` object is created.

## Cooldown Logic

To prevent alert spam, a cooldown mechanism is implemented:
- The executor tracks the timestamp of the last generated alert.
- If a new alert is detected, it checks the time elapsed since the last alert.
- If this duration is less than `COOLDOWN_PERIOD` minutes, the new alert is suppressed.
- This cooldown applies globally to the strategy instance, regardless of signal direction.

## Flow Diagram

```mermaid
graph TD
    A[Start Loop at candle `i`] --> B_CHECK{Data > MIN_LOOKBACK_DATA?};
    B_CHECK -- No --> X[Continue Loop];
    B_CHECK -- Yes --> B{Find Signal Candle in Lookback Window};
    B --> C{1. Signal Candle Position Valid?};
    C -- No --> X;
    C -- Yes --> D{2. Volume Spike on Signal Candle?};
    D -- No --> X;
    D -- Yes --> E{3. Confirmation Candle Shape Valid?};
    E -- No --> X;
    E -- Yes --> F{4. Structural Reversal (Peak/Trough) Found?};
    F -- No --> X;
    F -- Yes --> G{5. Pre-Spike Trend Valid?};
    G -- No --> X;
    G -- Yes --> H{6. Cooldown Active?};
    H -- Yes --> X;
    H -- No --> Z[Generate Alert];
    X --> A;
```
