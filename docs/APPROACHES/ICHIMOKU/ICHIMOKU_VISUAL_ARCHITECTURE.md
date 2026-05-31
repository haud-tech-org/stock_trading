# ICHIMOKU Visual Architecture

## Architecture Overview

The ICHIMOKU approach is structured as a modular pipeline:

- **Executor**: Orchestrates the detection process, manages windowing, and coordinates indicator calculation and validation steps.
- **Analyzer**: Provides pure calculation functions for Ichimoku components (Tenkan-sen, Kijun-sen, Senkou Span A/B, Chikou Span).
- **Validator**: Implements all validation logic for crossovers, cloud breakouts, and trend confirmation.
- **Settings**: Loads all configurable parameters from `signal_settings.py`.

### Data Flow

1. **Input**: OHLCV DataFrame
2. **Executor**: Loops through data, extracts lookback windows
3. **Analyzer**: Calculates Ichimoku indicator values
4. **Validator**: Validates crossovers, cloud breakouts, and trend context
5. **Executor**: Issues alert if all validations pass

---

*This architecture mirrors the VRA approach structure for clarity and maintainability.*
