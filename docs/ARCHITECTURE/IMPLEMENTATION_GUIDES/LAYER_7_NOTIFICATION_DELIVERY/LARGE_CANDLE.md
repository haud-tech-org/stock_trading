# Large Candle Announce Approach (2026)

## Overview

The `LargeCandleAlerter` is a new announce approach for Layer 7 notification delivery. It detects large candle events (where the absolute body, |close - open|, is greater than or equal to a configurable threshold) and delivers immediate notifications via enabled channels (e.g., Email, Ntfy).

- **Type:** Announce (not scheduled/reminded)
- **Integration:** Fully modular, config-driven, and registered in the orchestrator and factory
- **Channels:** All enabled channels per config (Email, Ntfy, etc.)
- **Config:** Enable/disable per symbol and channel in `notification_service_config.json`

## Architecture & Flow

- Implements the `AnnouncementAlerterBase` interface
- Registered in the announce approach factory
- Routed by the orchestrator using `ApproachType.ANNOUNCE`
- Alerts are delivered immediately to enabled channels


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


## Code Location
- Main logic: `src/stockreports/alert/announce/approach/LARGE_CANDLE/alerter.py`
- Factory registration: `src/stockreports/alert/announce/factory.py`
- Orchestrator: `src/stockreports/alert/announce/orchestrator.py`
- Config: `src/stockreports/config/notification_service_config.json`

## Example Config Snippet
```json
"LARGE_CANDLE": {
  "channels": {
    "EMAIL": {
      "enabled": true,
      "signals": {
        "PRICE_UP": {"enabled": true},
        "PRICE_DOWN": {"enabled": true}
      }
    },
    "NTFY": {
      "enabled": false,
      "signals": {
        "PRICE_UP": {"enabled": true},
        "PRICE_DOWN": {"enabled": true}
      }
    }
  }
}
```

## How to Add/Modify
- To enable/disable: update the config for each symbol/channel
- To change threshold: update the approach config for the symbol
- To extend: follow the modular approach pattern (see `PriceMovementAlerter`)

## See Also
- [Layer 7 Technical Reference](../../TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md)
- [Layer 7 Implementation Guide](../README.md)
- [PriceMovementAlerter](../PRICE_MOVEMENT.md)

*Last updated: April 25, 2026*
