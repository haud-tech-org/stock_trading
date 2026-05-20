# Layer 7: Notification Delivery - Tier 2 Reference

**Layer Number**: 7  
**Layer Name**: Notification Delivery  
**Tier**: 2 (Reference & Theory)  
**Purpose**: Understanding user notification systems and delivery channels  

---

## 🎯 Layer Responsibility


Layer 7 delivers **trading alerts and announcements to users** through multiple channels (Email, SMS, Ntfy web push, and Slack) using a modular, config-driven, and type-based architecture. Notification routing, formatting, and delivery reliability are handled by a central orchestrator, with pluggable channels and a scheduler for trade signals.

**Key Concepts:**
- Modular, type-based notification system: all approaches are classified by `approach_type` (e.g., `announce`, `trade`) using the `ApproachType` enum.
- The orchestrator is the single entry point for all notification delivery, delegating to enabled channels and, for trade signals, the scheduler.
- Announcement and trade approaches are processed separately: announcements are delivered immediately, while trade signals may be scheduled/reminded.

---

## 🔄 Notification Service Data Flow Diagram


See [NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md](./NOTIFICATION_SERVICE_DATA_FLOW_DIAGRAM.md) for the complete data flow diagram reflecting the current modular, type-based notification service architecture, including orchestrator, channel factory, and scheduler roles.

---

## 📖 Contents at This Layer



## 🆕 New Architecture (2026)


Layer 7 is powered by a modular, config-driven notification orchestrator. It supports multiple pluggable channels (Email, SMS, Ntfy/web, **Slack**), robust deduplication, and a scheduler for reminders and close position alerts. All logic is driven by a hierarchical configuration, with type-based filtering (`announce` vs `trade`) and error handling built in. The orchestrator uses the `ApproachType` enum to route each alert to the correct delivery flow.

- **Slack channel** (`SlackNotificationChannel`): Delivers alerts via Incoming Webhook using Slack Block Kit attachments with colour-coded signal sidebar (green = BUY/REMINDER, red = SELL/CLOSE, blue = other). Supports multiple webhook URLs (comma-separated `SLACK_WEBHOOK_URLS`), exponential-backoff retry (3 retries), and multi-URL fan-out. Credentials loaded via `SecretsLoader` — no separate `SLACK_ENABLED` env flag; enablement is entirely controlled by `notification_service_config.json` per symbol/approach/signal.

**For implementation details, code locations, and how-to guides, see the [Layer 7 Implementation Guide](../../../IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/README.md).**

---


---

## Key Architectural Aspects (2026)

- **Type-based Routing:** All approaches are classified by `approach_type` in config. The orchestrator uses this to separate announcement and trade flows.
- **Orchestrator:** The only public entry point for notification delivery. Handles deduplication, config-driven enablement, and delegates to channels and scheduler.
- **ChannelFactory:** Instantiates and manages all enabled channels per approach, as defined in config.
- **Scheduler:** Handles reminders and close notifications for trade-type approaches only.
- **Announcement Flow:** Announcement approaches (e.g., Price Movement) are delivered immediately via enabled channels.
- **Trade Flow:** Trade approaches are delivered and may be scheduled for reminders/close notifications.

---

---

## 🏗️ How This Layer Works

### Notification Delivery Pipeline

```
Stored Alerts (Layer 6)
  ↓
Notification Filter
  ├─ Check alert thresholds
  ├─ Apply user preferences
  └─ Determine recipients
  ↓
Notification Formatter
  ├─ Email format
  ├─ SMS format
  └─ Web format
  ↓
Delivery Channels
  ├─ Email Service
  ├─ SMS Service
  └─ Web Push/WebSocket
  ↓
User Device
```

### Notification Channels

**Email**:
- Formatted message with alert details
- Rich formatting with strategy info
- Historical context and recommendations
- Batch or immediate delivery

**SMS**:
- Concise alert summary
- Symbol, signal type, and price
- Time-critical trading opportunities
- Optional confirmation link

**Web Notifications**:
- Real-time push notifications
- Web dashboard updates
- In-app messaging
- Rich media support

**Slack**:
- Incoming Webhook delivery (no bot token required)
- Block Kit attachment format with colour-coded signal bar
  - 🟢 Green (`#00B050`) — BUY / ORDER_REMINDER
  - 🔴 Red (`#FF0000`) — SELL / CLOSE_POSITION
  - 🔵 Blue (`#0078D4`) — Other signals
- Fields: symbol, approach, signal price, suggested entry, profit threshold, time
- Multi-URL fan-out: multiple webhooks supported (comma-separated `SLACK_WEBHOOK_URLS`)
- Exponential-backoff retry: 3 retries, doubling delay starting at 1 s
- Success detection: HTTP 200 + body text `"ok"`

### Notification Filtering

Users can configure:
- Which symbols trigger notifications
- Which signal types (BUY, SELL, HOLD)
- Notification frequency (immediate, hourly, daily)
- Channel preferences (email, SMS, web)
- Alert thresholds (confidence level, price change, etc.)

### Delivery Reliability

Features:
- Retry mechanism for failed sends
- Fallback channels if primary fails
- Delivery status tracking
- User preference updates in real-time

---

## 🔗 Layer Connections

| Direction | Connected Layer | Purpose |
|-----------|-----------------|---------|
| **← Prev** | Layer 6: Alert Aggregation | Receives alerts to deliver |
| **← Prev** | Layer 9: Operational Support | Logs notification status |

---

## 💡 Who Should Read This

### 👨‍💻 Developers
- **Use Case**: Add new notification channel or modify message format
- **Key Learning**: Notification routing and formatting patterns
- **Next Step**: IMPLEMENTATION_GUIDES/LAYER_7 for how-to

### 🏗️ Architects
- **Use Case**: Design reliable notification system and channel management
- **Key Learning**: Multi-channel delivery and retry patterns
- **Next Step**: Consider delivery guarantees and scalability

### 🚀 Operations/DevOps
- **Use Case**: Configure notification channels and delivery settings
- **Key Learning**: Service dependencies and delivery configuration
- **Next Step**: LAYER_9 for monitoring notification delivery

---

## 🚀 Quick Navigation by Use Case

### **"How do users receive alerts?"**
→ Multiple channels: Email, SMS, Web notifications with customizable preferences

### **"Can I change the message format?"**
→ Yes - modify formatters for each channel type

### **"What if email delivery fails?"**
→ Retry mechanism activates; can fallback to SMS if configured

### **"How do users configure their preferences?"**
→ Settings interface allows channel selection, symbol filtering, frequency control

---

## 📚 Related Documentation

- **System Overview**: [SYSTEM_ARCHITECTURE_OVERVIEW.md](../../SYSTEM_ARCHITECTURE_OVERVIEW.md) - Complete architecture
- **Previous Layer**: [Layer 6 README](../LAYER_6_ALERT_AGGREGATION/README.md) - Alert storage
- **Implementation Guide**: [IMPLEMENTATION_GUIDES Layer 7](../../../IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/README.md)
- **Operational Support**: [Layer 9 README](../LAYER_9_OPERATIONAL_SUPPORT/README.md) - Monitoring

---

## 🔍 Key Concepts

**Multi-Channel Delivery**: Email, SMS, Web push (Ntfy), Slack Incoming Webhook  
**User Preferences**: Customizable filtering and channel selection  
**Message Formatting**: Channel-specific alert formatting  
**Delivery Reliability**: Retry mechanisms and fallback channels  
**Notification Routing**: Intelligent recipient determination  

---

## 📞 Need More Information?

- **How to add new notification channel**: See IMPLEMENTATION_GUIDES/LAYER_7
- **Message formatting**: See IMPLEMENTATION_GUIDES/LAYER_7
- **Monitoring delivery**: See LAYER_9
- **Back to beginning**: [Root README](../../README.md)

---

*Last Updated: May 20, 2026*  
*Part of Tier 2 Documentation - Reference & Theory*
