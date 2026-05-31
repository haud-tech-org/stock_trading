# REVERSAL_ANCHOR_SIGNAL_CANDLE Visual Architecture

## Architecture Overview

The REVERSAL_ANCHOR_SIGNAL_CANDLE approach is structured as a modular pipeline:

- **Executor**: Orchestrates the detection process, manages windowing, and coordinates analysis and validation steps.
- **Analyzer**: Provides pure calculation functions for anchor, signal, and alert candle detection, as well as trend and volume analysis.
- **Validator**: Implements all validation logic for window size, anchor, signal, alert candle, and cooldown.
- **Settings**: Loads all configurable parameters from `signal_settings.py`.

### Data Flow

1. **Input**: OHLCV DataFrame
2. **Executor**: Loops through data, extracts lookback windows
3. **Analyzer**: Calculates anchor, signal, alert candle, trend, and volume
4. **Validator**: Validates window size, anchor, signal, alert candle, and cooldown
5. **Executor**: Issues alert if all validations pass

---

*This architecture mirrors the VRA approach structure for clarity and maintainability.*
