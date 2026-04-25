# Large Volume Candle Announce Approach (LARGE_VOLUME_CANDLE)

## Overview
This document describes the `LargeVolumeCandleAlerter` announce approach for Layer 7 notification delivery. It is modular, config-driven, and follows all project coding conventions and architecture standards.


## Technical Concepts
- **Purpose:** Detects large volume spikes in trading data (where the latest volume is greater than or equal to a configurable multiple of the previous volume).
- **Type:** Announce approach (immediate notification delivery).
- **Config-Driven:** All logic and thresholds are controlled by configuration, not hardcoded.
- **Encapsulation:** The approach is modular and encapsulated, following Layer 7's type-based architecture.
- **Integration:** Works with the orchestrator, factory, and notification channels as part of the Layer 7 pipeline.
- **Testing:** Must be covered by unit tests for both alerting and non-alerting scenarios.
- **Documentation:** All changes must comply with project coding conventions and be fully documented.

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
