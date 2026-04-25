# Price Movement Data Flow (Layer 7)


This document provides a conceptual overview of the Price Movement alerting service in Layer 7, focusing on its role in the new type-based, modular notification delivery pipeline.

---

## 🔄 Price Movement Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Notification Delivery Pipeline                       │
└──────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
   [Price Movement Alerter Detects Event]
           │
           ▼
   [Alert Generated for Price Movement]
           │
           ▼
   [Orchestrator Receives Alert]
           │
           ▼
   [Orchestrator Dispatches to Channels]
```

---



## 🧩 Concepts

- **Approach Types:** Each approach is classified by `approach_type` (e.g., `announce`, `trade`) in config.
- **Type-Based Processing:** The orchestrator uses the `ApproachType` enum and type-based filtering to process announce and trade approaches separately.
- **Price Movement as Announcement:** Price Movement is configured with `"approach_type": "announce"` and is processed in a dedicated announcement flow, not scheduled/reminded.
- **Immediate Delivery:** Price Movement alerts are delivered immediately to enabled channels via the orchestrator and ChannelFactory.
- **No Scheduler:** The scheduler is not involved in announcement-type approaches.
- **Modular Structure:** Price Movement logic is implemented as an approach class, registered in the factory, and invoked by the orchestrator.
- **Config-Driven:** All enablement and routing is defined in config, with type-based separation.

---

For a full Layer 7 flow, see [NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md](./NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md).


For implementation details and code examples, see the Implementation Guide. The guide includes configuration examples and code snippets for type-based approach filtering.

---

*Last updated: April 24, 2026*
