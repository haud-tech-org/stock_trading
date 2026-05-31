# CONSISTENT_MOMENTUM Visual Architecture

## Architecture Overview

The CONSISTENT_MOMENTUM approach is structured as a modular pipeline:

- **Executor**: Orchestrates the detection process, manages windowing, and coordinates analysis and validation steps.
- **Analyzer**: Provides pure calculation functions for body size, color consistency, anchor detection, and volume.
- **Validator**: Implements all validation logic for color consistency, anchor position, magnitude, volume, and price range.
- **Settings**: Loads all configurable parameters from `signal_settings.py`.

### Data Flow

1. **Input**: OHLCV DataFrame
2. **Executor**: Loops through data, extracts lookback windows
3. **Analyzer**: Calculates color, anchor, magnitude, and volume
4. **Validator**: Validates color consistency, anchor, magnitude, volume, and price range
5. **Executor**: Issues alert if all validations pass

---

*This architecture mirrors the VRA approach structure for clarity and maintainability.*
