# Notification Service Data Flow Diagram

This document provides a detailed data flow diagram for the Notification Service (Layer 7), reflecting the current modular, config-driven, and scheduler-integrated architecture.

---

## 🔄 Data Flow Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        Application / Alert System                            │
│                  (Executors, Strategies, SymbolAlerter)                      │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                    [1] SEND NOTIFICATION (AlertNotification)
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────┐
│              NotificationServiceOrchestrator (Config-Driven)                 │
│  - Deduplication, config-driven enablement                                   │
│  - Dispatch to enabled channels                                              │
│  - Append to scheduler if trade signal                                       │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                    [2] CHANNEL FACTORY & DELIVERY
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────┐
│                  ChannelFactory (Instantiates Channels)                      │
│  - EmailNotificationChannel                                                  │
│  - SMSNotificationChannel                                                    │
│  - NtfyNotificationChannel                                                   │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                    [3] CHANNEL SEND
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────┐
│                Channel (Email/SMS/Ntfy)                                     │
│  - Format and send notification                                             │
└────────────────────────────────┬─────────────────────────────────────────────┘
                                 │
                    [4] SCHEDULER (Reminders/Close)
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────┐
│                NotificationScheduler                                         │
│  - Tracks state for trade signals                                            │
│  - Triggers reminders/close notifications                                   │
│  - Sends scheduled notifications via orchestrator                            │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

For conceptual overview, see the Layer 7 section in [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md).

For implementation details, see the relevant modules in `src/stockreports/services/external/notification_services/`.
