# STRONG_CANDLE Visual Architecture

## Architecture Overview

The STRONG_CANDLE approach is structured as a modular pipeline:

- **Executor**: Orchestrates the detection process, manages windowing, and coordinates analysis and validation steps.
- **Analyzer**: Provides pure calculation functions for body size, volume, and trend context.
- **Validator**: Implements all validation logic for strong candle detection, volume checks, and trend context.
- **Settings**: Loads all configurable parameters from `signal_settings.py`.

### Data Flow

1. **Input**: OHLCV DataFrame
2. **Executor**: Loops through data, extracts lookback windows
3. **Analyzer**: Calculates body size, volume, and trend context
4. **Validator**: Validates strong candle, volume, and context
5. **Executor**: Issues alert if all validations pass

---

*This architecture mirrors the VRA approach structure for clarity and maintainability.*
