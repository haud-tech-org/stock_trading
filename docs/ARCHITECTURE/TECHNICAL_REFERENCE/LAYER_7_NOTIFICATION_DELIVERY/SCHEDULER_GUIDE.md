# Scheduler Guide

This guide describes the Notification Scheduler at Layer 7, its responsibilities, and how it interacts with the main alerting flow. The scheduler now only processes trade-type approaches, as determined by the `approach_type` field in the approach configuration.

## Responsibilities

- Track state for trade signals (e.g., open/close/reminder)
- Trigger reminders and close notifications
- Send scheduled notifications via the orchestrator

The scheduler does **not** process announcement-type approaches (such as Price Movement). Only approaches with `"approach_type": "trade"` are scheduled.

## Integration with Main Alerting Flow

The main alerting flow appends trade signals (approaches with `approach_type=trade`) to the scheduler for state tracking and future reminders. Announcement-type approaches (e.g., Price Movement) are delivered immediately and are not scheduled.

## Example: Trade vs Announce

- Trade approach (BUY/SELL): scheduled for reminders/close (`approach_type=trade`)
- Announce approach (PRICE_MOVEMENT): delivered immediately, not scheduled (`approach_type=announce`)
