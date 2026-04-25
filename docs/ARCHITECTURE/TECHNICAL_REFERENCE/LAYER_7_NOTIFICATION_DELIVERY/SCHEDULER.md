# Scheduler Data Flow (Layer 7)

This document provides a conceptual overview of the Scheduler in Layer 7, focusing on its role in the notification delivery pipeline.

---

## 🔄 Scheduler Data Flow

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Notification Delivery Pipeline                       │
└──────────────────────────────────────────────────────────────────────────────┘
           │
           ▼
   [Alert Received by Orchestrator]
           │
           ▼
   [Scheduler Queues Notification]
           │
           ├───► Tracks alert state (reminder, close position)
           ├───► Applies config-driven delays
           └───► Waits for scheduled time
           │
           ▼
   [Scheduler Triggers Notification]
           │
           ▼
   [Orchestrator Dispatches to Channels]
```

---


## 🧩 Concepts

- The Scheduler manages all time-based notification logic (reminders, close position alerts) for **trade-type approaches only**.
- It tracks the state of each trade alert and determines when to trigger notifications based on configuration.
- The orchestrator delegates scheduling to the Scheduler for trade signals, which then triggers delivery at the correct time.
- Announcement-type approaches (e.g., Price Movement) are **not** scheduled/reminded.

---

For a full Layer 7 flow, see [NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md](./NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md).

For implementation details, see the Implementation Guide.

---

*Last updated: April 24, 2026*
