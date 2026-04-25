
# Notification Channel Implementation Guide (Layer 7, Modular, Type-Based)

## Purpose
This guide provides practical instructions for working with Notification Channels in Layer 7, including adding new channels, configuring, and troubleshooting.

## Key Components
- **BaseNotificationChannel**: Abstract base class for all channels.
- **EmailNotificationChannel**: Email delivery implementation.
- **SMSNotificationChannel**: SMS delivery implementation.
- **NtfyNotificationChannel**: Web push delivery implementation.
- **ChannelFactory**: Instantiates and manages channel objects.


## How to Add or Modify a Channel
1. **Create a new channel class** in `src/stockreports/services/external/notification_services/_internal/channels/`.
   - Subclass `BaseNotificationChannel`.
   - Implement `_send` and `validate_config` methods.
2. **Register the channel** in `ChannelFactory` (`channel_factory.py`).
3. **Update configuration** to enable and route alerts to the new channel, per approach and `approach_type` (type-aware enablement).
4. **Test** by sending a notification through the orchestrator (ensure correct type-based routing).


## Code Locations
- Channel base and implementations: `src/stockreports/services/external/notification_services/_internal/channels/`
- Channel factory: `src/stockreports/services/external/notification_services/_internal/channel_factory.py`
- Config: `executor_approach_configuration.json` (enable per approach/type)


## Troubleshooting
- Ensure configuration is valid and credentials are set.
- Check logs for errors in channel send methods.
- If a channel is not used, check that it is enabled for the correct approach and `approach_type` in config.

---

*Last updated: April 24, 2026*
