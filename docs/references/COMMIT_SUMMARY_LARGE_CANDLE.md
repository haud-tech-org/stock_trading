# Commit Summary: Add Large Candle Announce Approach (LARGE_CANDLE)

## Overview
This commit introduces the `LargeCandleAlerter` as a new announce approach for Layer 7 notification delivery. The implementation is modular, config-driven, and follows the project's coding conventions and architecture standards.

## Technical Details
- **New Approach:**
  - Implements `LargeCandleAlerter` for detecting large candle events (|close - open| >= threshold) and immediate notification delivery.
  - Inherits from `AnnouncementAlerterBase` and is registered in the announce approach factory.
  - Fully integrated with orchestrator and config-driven enablement.
- **Code Structure:**
  - New module: `src/stockreports/alert/announce/approach/LARGE_CANDLE/alerter.py`
  - Factory registration: `src/stockreports/alert/announce/factory.py`
  - Base class: `src/stockreports/alert/announce/announcement_alerter.py`
  - Package marker: `__init__.py` in approach and test directories.
- **Configuration:**
  - Added `LARGE_CANDLE` to `notification_service_config.json` for relevant symbols and channels.
  - Added `LARGE_CANDLE` to `executor_approach_configuration.json` with approach type, resolution, and threshold.
  - Updated constants to include `LARGE_CANDLE` in the `Approach` enum.
- **Testing:**
  - Added unit tests in `tests/unit/stockreports/alert/announce/approach/LARGE_CANDLE/test_alerter.py`.
  - Tests cover both alert-triggering and non-triggering scenarios with correct DataFrame schema.
- **Documentation:**
  - Added technical reference and implementation guide documentation for the new approach.
  - Updated announce approach prompt to reflect new standards and integration requirements.
  - All code and documentation changes comply with `CODING_CONVENTION_AND_STANDARDIZATION.md`.

## Architecture
- The new approach is fully encapsulated, type-based, and only accessible via the orchestrator and factory.
- All log messages and alert details use canonical enum values.
- No business logic outside the scope of the new approach is included.

## Data Flow Diagram: SymbolAlerter to Notification Sent

```mermaid
graph TD
    A[SymbolAlerter] --> B[ExecutorConfigurationOrchestrator]
    B --> C[_AnnouncementAlertFactory]
    C --> D[LargeCandleAlerter]
    D --> E[AnnouncementAlertOrchestrator]
    E --> F[NotificationServiceOrchestrator]
    F --> G[ChannelFactory]
    G --> H[Notification Channel(s): Email, Ntfy, etc.]
    H --> I[User Device]
```

**Description:**
- The `SymbolAlerter` triggers the alerting process for a symbol.
- `ExecutorConfigurationOrchestrator` loads the approach configuration.
- `_AnnouncementAlertFactory` instantiates the correct announce approach (`LargeCandleAlerter`).
- `LargeCandleAlerter` executes the business logic and generates alert(s).
- `AnnouncementAlertOrchestrator` coordinates the announce alert flow.
- `NotificationServiceOrchestrator` routes the alert to enabled channels via `ChannelFactory`.
- Channels (Email, Ntfy, etc.) deliver the notification to the user device.

## Checklist
- [x] New approach module created and implemented
- [x] Registered in factory, orchestrator, and config files
- [x] Unit test added with correct test data
- [x] Log messages use canonical enum values
- [x] Documentation updated

---
*Generated on April 25, 2026*
