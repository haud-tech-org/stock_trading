
# Notification Service Data Flow Diagram


This document provides a detailed data flow diagram for the Notification Service (Layer 7), reflecting the current modular, config-driven, and type-based architecture. The system now processes approaches by `approach_type` (`announce`, `trade`, etc.) using the `ApproachType` enum and type-based filtering in the orchestrator. Announcements are delivered immediately; trade signals may be scheduled/reminded.

---

## 🔄 Data Flow Diagram

```

┌──────────────────────────────────────────────────────────────────────────────┐
│                        Application / Alert System                            │
│                  (Executors, Strategies, SymbolAlerter)                      │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                    [A] SEND ANNOUNCEMENT (AlertNotification, approach_type=announce)
                                │
┌──────────────────────────────────────────────────────────────────────────────┐
│              NotificationServiceOrchestrator (Config-Driven, Type-Based)     │
│  - Deduplication, config-driven enablement                                   │
│  - Type-based routing (announce/trade)                                      │
│  - Dispatch to enabled channels (announce)                                  │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                    [B] SEND TRADE SIGNAL (AlertNotification, approach_type=trade)
                                │
┌──────────────────────────────────────────────────────────────────────────────┐
│              NotificationServiceOrchestrator (Config-Driven, Type-Based)     │
│  - Deduplication, config-driven enablement                                   │
│  - Type-based routing (announce/trade)                                      │
│  - Dispatch to enabled channels (trade)                                     │
│  - Append to scheduler if trade signal                                       │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                    [2] CHANNEL FACTORY & DELIVERY
                                │
┌──────────────────────────────────────────────────────────────────────────────┐
│                  ChannelFactory (Instantiates Channels)                      │
│  - EmailNotificationChannel                                                  │
│  - SMSNotificationChannel                                                    │
│  - NtfyNotificationChannel                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                    [3] CHANNEL SEND
                                │
┌──────────────────────────────────────────────────────────────────────────────┐
│                Channel (Email/SMS/Ntfy)                                     │
│  - Format and send notification                                             │
└──────────────────────────────────────────────────────────────────────────────┘
                                │
                    [4] SCHEDULER (Reminders/Close, only for trade signals)
                                │
┌──────────────────────────────────────────────────────────────────────────────┐
│                NotificationScheduler                                         │
│  - Tracks state for trade signals                                            │
│  - Triggers reminders/close notifications                                   │
│  - Sends scheduled notifications via orchestrator                            │
└──────────────────────────────────────────────────────────────────────────────┘

---

## Key Points
- **Type-based Routing:** The orchestrator uses `approach_type` to separate announcement and trade flows.
- **Announcement approaches** (e.g., Price Movement) are delivered immediately via enabled channels.
- **Trade approaches** are delivered and may be scheduled for reminders/close notifications.
- **Scheduler** only processes trade-type approaches.
│                  (PriceMovementAlerter, Announcement Services)               │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                    [A] SEND ANNOUNCEMENT (AlertNotification)
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│              NotificationServiceOrchestrator (Config-Driven)                 │
│  - Deduplication, config-driven enablement                                   │
│  - Dispatch to enabled channels                                              │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                    [B] CHANNEL FACTORY & DELIVERY
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│                  ChannelFactory (Instantiates Channels)                      │
│  - EmailNotificationChannel                                                  │
│  - SMSNotificationChannel                                                    │
│  - NtfyNotificationChannel                                                   │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │
                    [C] CHANNEL SEND
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│                Channel (Email/SMS/Ntfy)                                     │
│  - Format and send announcement                                             │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

For conceptual overview, see the Layer 7 section in [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md).

For implementation details, see the relevant modules in `src/stockreports/services/external/notification_services/`.
