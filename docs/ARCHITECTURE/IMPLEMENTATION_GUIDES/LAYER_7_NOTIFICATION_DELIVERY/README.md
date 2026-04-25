
# Layer 7: Notification Delivery - Tier 3 Implementation Guide (2026 Modular, Type-Based)

**Layer Number**: 7  
**Layer Name**: Notification Delivery  
**Tier**: 3 (Implementation & How-To)  
**Purpose**: Practical guides for implementing notification channels  

---

## 🎯 Layer Responsibility


Layer 7 implementation focuses on **modular, type-based notification delivery across multiple channels**. All notification logic is routed by `approach_type` (e.g., `announce`, `trade`) using the `ApproachType` enum. The orchestrator is the single entry point for all notification delivery, with pluggable channels and a scheduler for trade signals.

---

## 📖 Contents at This Layer


## 🆕 New Implementation (2026)


### [NotificationServiceOrchestrator](../../../../src/stockreports/services/external/notification_services/orchestrator.py)
- **Location:** [`src/stockreports/services/external/notification_services/orchestrator.py`](../../../../src/stockreports/services/external/notification_services/orchestrator.py)
- **How to Use:**
	- Use as the only public entry point for all notification delivery (announcements and trade signals)
	- All logic is routed by `approach_type` (e.g., `announce`, `trade`)
	- Configure via hierarchical JSON config (see [config loader](../../../../src/stockreports/services/external/notification_services/_internal/config/loader.py))
	- Use `send_notification()` for all alert delivery; orchestrator will delegate to enabled channels and, for trade signals, the scheduler


### Adding/Modifying Channels
- **[ChannelFactory](../../../../src/stockreports/services/external/notification_services/_internal/channel_factory.py):**
	- Add new channel by implementing the channel interface and registering in the factory
	- Channel enablement is type-aware and config-driven (per approach, by `approach_type`)
	- Supported: [EmailNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/email_channel.py), [SMSNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/sms_channel.py), [NtfyNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/ntfy_channel.py) (web push)


### Scheduler/Reminders
- **[NotificationScheduler](../../../../src/stockreports/services/external/notification_services/_internal/scheduler.py):**
	- Handles scheduled reminders and close position notifications for **trade-type approaches only**
	- Announcement-type approaches (e.g., Price Movement) are **not** scheduled/reminded
	- Configure delays per symbol/approach in config


### Configuration
- **[Config Loader](../../../../src/stockreports/services/external/notification_services/_internal/config/loader.py):**
	- All enablement and routing is config-driven, with type-based separation (`announce` vs `trade`)
	- Validate config at startup for errors


### Practical How-To
- To add a new channel: implement channel class, register in ChannelFactory, update config (enable per approach/type)
- To change enablement: update config JSON (per approach, by `approach_type`)
- To extend scheduler: subclass or update NotificationScheduler logic (trade-type only)

---

| File | Purpose | Read Time | Level |
|------|---------|-----------|-------|
| (No files) | Notification delivery implementation guides | - | Ready for docs |

---

## 🚀 Quick Navigation by Use Case


### **"How do I configure email notifications?"**
→ See LAYER_9 configuration section for email service setup. Enable email per approach/type in config.

### **"How do I add SMS support?"**
→ Implement SMS channel handler, register in ChannelFactory, and enable for desired approaches/types in config.

### **"How do I customize alert messages?"**
→ Modify message formatters for each channel type. Use orchestrator to route by type.

---

## 🔗 Related Documentation

- **Theory**: [Layer 7 Reference](../../TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md)
- **Previous Layer**: [Layer 6 Implementation](../LAYER_6_ALERT_AGGREGATION/README.md)
- **Next Layer**: [Layer 8 Implementation](../LAYER_8_PERFORMANCE_ANALYSIS/README.md)
- **Configuration**: LAYER_9_OPERATIONAL_SUPPORT - Notification settings

---


---

*Last Updated: April 25, 2026*  
*Part of Tier 3 Documentation - Implementation & How-To (2026 Modular, Type-Based)*
