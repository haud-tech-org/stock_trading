# Layer 7: Notification Delivery - Tier 3 Implementation Guide

**Layer Number**: 7  
**Layer Name**: Notification Delivery  
**Tier**: 3 (Implementation & How-To)  
**Purpose**: Practical guides for implementing notification channels  

---

## 🎯 Layer Responsibility

Layer 7 implementation focuses on **notification delivery across multiple channels**.

---

## 📖 Contents at This Layer


## 🆕 New Implementation (2026)

### [NotificationServiceOrchestrator](../../../../src/stockreports/services/external/notification_services/orchestrator.py)
- **Location:** [`src/stockreports/services/external/notification_services/orchestrator.py`](../../../../src/stockreports/services/external/notification_services/orchestrator.py)
- **How to Use:**
	- Instantiate or use as singleton for all notification dispatch
	- Configure via hierarchical JSON config (see [config loader](../../../../src/stockreports/services/external/notification_services/_internal/config/loader.py))
	- Use `send_notification()` for all alert delivery

### Adding/Modifying Channels
- **[ChannelFactory](../../../../src/stockreports/services/external/notification_services/_internal/channel_factory.py):**
	- Add new channel by implementing the channel interface and registering in the factory
	- Supported: [EmailNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/email_channel.py), [SMSNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/sms_channel.py), [NtfyNotificationChannel](../../../../src/stockreports/services/external/notification_services/_internal/channels/ntfy_channel.py) (web push)

### Scheduler/Reminders
- **[NotificationScheduler](../../../../src/stockreports/services/external/notification_services/_internal/scheduler.py):**
	- Handles scheduled reminders and close position notifications
	- Configure delays per symbol/approach in config

### Configuration
- **[Config Loader](../../../../src/stockreports/services/external/notification_services/_internal/config/loader.py):**
	- All enablement and routing is config-driven
	- Validate config at startup for errors

### Practical How-To
- To add a new channel: implement channel class, register in ChannelFactory, update config
- To change enablement: update config JSON
- To extend scheduler: subclass or update NotificationScheduler logic

---

| File | Purpose | Read Time | Level |
|------|---------|-----------|-------|
| (No files) | Notification delivery implementation guides | - | Ready for docs |

---

## 🚀 Quick Navigation by Use Case

### **"How do I configure email notifications?"**
→ See LAYER_9 configuration section for email service setup

### **"How do I add SMS support?"**
→ Implement SMS channel handler and configure SMS service credentials

### **"How do I customize alert messages?"**
→ Modify message formatters for each channel type

---

## 🔗 Related Documentation

- **Theory**: [Layer 7 Reference](../../TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md)
- **Previous Layer**: [Layer 6 Implementation](../LAYER_6_ALERT_AGGREGATION/README.md)
- **Next Layer**: [Layer 8 Implementation](../LAYER_8_PERFORMANCE_ANALYSIS/README.md)
- **Configuration**: LAYER_9_OPERATIONAL_SUPPORT - Notification settings

---

*Last Updated: April 10, 2026*  
*Part of Tier 3 Documentation - Implementation & How-To*
