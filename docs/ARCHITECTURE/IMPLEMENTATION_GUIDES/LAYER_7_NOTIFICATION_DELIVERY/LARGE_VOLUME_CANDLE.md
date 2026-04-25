# Large Volume Candle Announce Approach (LARGE_VOLUME_CANDLE)

## Overview
This document describes the `LargeVolumeCandleAlerter` announce approach for Layer 7 notification delivery. It is modular, config-driven, and follows all project coding conventions and architecture standards.

## Technical Details
- **Implements:** `LargeVolumeCandleAlerter` for detecting large volume spikes (latest volume >= MULTIPLIER_VOLUME × previous volume).
- **Integration:**
  - Inherits from `AnnouncementAlerterBase`.
  - Registered in the announce approach factory and orchestrator.
  - Fully config-driven (see `executor_approach_configuration.json`).
- **Code Structure:**
  - Module: `src/stockreports/alert/announce/approach/LARGE_VOLUME_CANDLE/alerter.py`
  - Factory: `src/stockreports/alert/announce/factory.py`
  - Base: `src/stockreports/alert/announce/announcement_alerter.py`
  - Package marker: `__init__.py`
- **Configuration:**
  - Added to `notification_service_config.json` and `executor_approach_configuration.json`.
  - Uses `MULTIPLIER_VOLUME` parameter for alert logic.
  - Enum updated in `src/stockreports/alert/common/constants.py`.
- **Testing:**
  - Unit tests in `tests/unit/stockreports/alert/announce/approach/large_volume_candle/test_alerter.py`.
  - Tests cover alerting and non-alerting scenarios.
- **Documentation:**
  - Technical reference, implementation guide, and prompt template updated.
  - All code and docs comply with `CODING_CONVENTION_AND_STANDARDIZATION.md`.

## Data Flow Diagram
```mermaid
graph TD
    A[SymbolAlerter] --> B[ExecutorConfigurationOrchestrator]
    B --> C[_AnnouncementAlertFactory]
    C --> D[LargeVolumeCandleAlerter]
    D --> E[AnnouncementAlertOrchestrator]
    E --> F[NotificationServiceOrchestrator]
    F --> G[ChannelFactory]
    G --> H[Notification Channel(s): Email, Ntfy, etc.]
    H --> I[User Device]
```

## Checklist
- [x] New approach module created and implemented
- [x] Registered in factory, orchestrator, and config files
- [x] Unit test added with correct test data
- [x] Log messages use canonical enum values
- [x] Documentation updated

---
*Generated on April 25, 2026*
