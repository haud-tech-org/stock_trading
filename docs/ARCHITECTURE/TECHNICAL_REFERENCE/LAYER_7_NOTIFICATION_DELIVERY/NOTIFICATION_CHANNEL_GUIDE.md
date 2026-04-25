# Notification Channel Guide

This guide describes the supported notification channels at Layer 7, their configuration, and how they are enabled for different alert types. The system now uses the `approach_type` field to distinguish between announcement and trade approaches, and channel enablement is type-aware.

## Supported Channels

- EmailNotificationChannel
- SMSNotificationChannel
- NtfyNotificationChannel

Each channel can be enabled or disabled per approach in the configuration. The `approach_type` field in the approach configuration determines whether the channel is enabled for announcement-type (e.g., Price Movement) or trade-type (e.g., Buy/Sell) notifications.

## Channel Enablement Example

```json
{
  "approach_name": "PRICE_MOVEMENT",
  "approach_type": "announce",
  "enabled": true,
  "channels": ["email", "ntfy"]
}
```

This enables the Email and Ntfy channels for the PRICE_MOVEMENT approach, which is an announcement-type notification. Trade-type approaches (e.g., BUY, SELL) would use `"approach_type": "trade"` and can have different channel enablement.

## Type-Based Channel Processing

Channels are instantiated and used based on the enabled configuration for each approach. The main alerting flow uses the `approach_type` to filter and process approaches accordingly. Announcement-type approaches (such as Price Movement) are processed separately from trade-type approaches, and only the enabled channels for each type are used.
