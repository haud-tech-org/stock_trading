
# Scheduler Implementation Guide (Layer 7, Modular, Type-Based)

## Purpose
This guide provides practical instructions for working with the Scheduler in Layer 7, including extending, configuring, and troubleshooting scheduled notifications.

## Key Components
- **NotificationScheduler**: Manages scheduled reminders and close position notifications.
- **NotificationSchedulerState**: Tracks state for each alert.


## How to Extend or Modify Scheduler Logic
1. **Update or subclass `NotificationScheduler`** in `src/stockreports/services/external/notification_services/_internal/scheduler.py` (trade-type approaches only).
2. **Adjust configuration** for new timing, reminder, or close position rules (per approach/type).
3. **Integrate** with orchestrator if new scheduling triggers are needed (trade-type only).
4. **Test** by simulating alert flows and verifying scheduled notifications (ensure only trade-type approaches are scheduled).


## Code Locations
- Scheduler logic: `src/stockreports/services/external/notification_services/_internal/scheduler.py`
- Config: `executor_approach_configuration.json` (trade-type only)


## Troubleshooting
- Check logs for scheduling errors or missed notifications.
- Validate configuration for correct delay and enablement settings.
- Ensure only trade-type approaches are scheduled/reminded; announcement-type approaches are delivered immediately.

---

*Last updated: April 24, 2026*
