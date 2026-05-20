
# Notification Channel Implementation Guide (Layer 7, Modular, Type-Based)

## Purpose
This guide provides practical instructions for working with Notification Channels in Layer 7, including adding new channels, configuring, and troubleshooting.

## Key Components
- **BaseNotificationChannel**: Abstract base class for all channels.
- **EmailNotificationChannel**: Email delivery via SMTP.
- **SMSNotificationChannel**: SMS delivery via Twilio or similar.
- **NtfyNotificationChannel**: Web push delivery via ntfy.sh.
- **SlackNotificationChannel**: Slack delivery via Incoming Webhook (Block Kit payload, colour-coded signal bar, multi-URL fan-out, exponential-backoff retry).
- **ChannelFactory**: Instantiates and manages channel objects. Registered channel types: `EMAIL`, `SMS`, `NTFY`, `SLACK` (via `ChannelType` enum).


## How to Add or Modify a Channel
1. **Create a new channel class** in `src/stockreports/services/external/notification_services/_internal/channels/`.
   - Subclass `BaseNotificationChannel`.
   - Implement `_send` and `validate_config` methods.
2. **Register the channel** in `ChannelFactory` (`channel_factory.py`).
3. **Update configuration** to enable and route alerts to the new channel, per approach and `approach_type` (type-aware enablement).
4. **Test** by sending a notification through the orchestrator (ensure correct type-based routing).


## Code Locations
- Channel base and implementations: `src/stockreports/services/external/notification_services/_internal/channels/`
  - `base_channel.py` — `BaseNotificationChannel` ABC
  - `email_channel.py` — `EmailNotificationChannel`
  - `sms_channel.py` — `SMSNotificationChannel`
  - `ntfy_channel.py` — `NtfyNotificationChannel`
  - `slack_channel.py` — `SlackNotificationChannel`
- Channel factory: `src/stockreports/services/external/notification_services/_internal/channel_factory.py`
- Channel type enum: `src/stockreports/services/external/notification_services/_internal/channel_type.py`
- Credentials: `src/stockreports/config/notification_settings.py` (`SLACK_WEBHOOK_URLS` via `SecretsLoader`)
- Enablement config: `src/stockreports/config/notification_service_config.json` (per symbol/approach/signal)


## Troubleshooting
- Ensure configuration is valid and credentials are set.
- Check logs for errors in channel send methods.
- If a channel is not used, check that it is enabled for the correct approach and `approach_type` in config.
- **Slack-specific**: Verify `SLACK_WEBHOOK_URLS` is set (non-empty). Confirm the webhook URL is active (Slack App → Incoming Webhooks). Expected response: HTTP 200 + body text `"ok"`. If you receive HTTP 403/404 or body `"no_service"`, the webhook URL may be revoked — regenerate it from the Slack App settings.

---

*Last updated: May 20, 2026*
