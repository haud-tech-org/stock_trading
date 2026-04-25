# Executor Approach Configuration

This document describes the structure and requirements for the executor approach configuration file, which defines the available alerting approaches per symbol. Each approach must now include an `approach_type` field to indicate whether it is a trade or announce approach.

## Approach Entry Example

Announcement-type approach (e.g., Price Movement):

```json
{
  "approach_name": "PRICE_MOVEMENT",
  "approach_type": "announce",
  "enabled": true,
  "channels": ["email", "ntfy"]
}
```

Trade-type approach (e.g., BUY):

```json
{
  "approach_name": "BUY",
  "approach_type": "trade",
  "enabled": true,
  "channels": ["email", "sms"]
}
```

## Required Fields

- `approach_name`: The name of the approach (e.g., BUY, SELL, PRICE_MOVEMENT)
- `approach_type`: The type of the approach. Must be one of:
  - `trade`: For trade signal approaches (BUY, SELL, etc.)
  - `announce`: For announcement-type approaches (PRICE_MOVEMENT, etc.)
- `enabled`: Whether this approach is enabled for the symbol
- `channels`: List of enabled notification channels for this approach

## Type-Based Processing

The alerting system uses the `approach_type` field to filter and process approaches. Announcement-type approaches are delivered immediately; trade-type approaches are scheduled for reminders and close notifications. This ensures robust, type-safe handling of all alerting logic.
