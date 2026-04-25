
# Large Candle Announce Approach (2026)

## Conceptual Overview

The Large Candle Announce Approach is a modular, config-driven method for delivering immediate notifications when a large candle event is detected (absolute body |close - open| >= threshold).

- **Type:** Announce (immediate delivery)
- **Integration:** Registered in the notification architecture as an announce approach
- **Configurable:** Enable/disable per symbol/channel, threshold per symbol

## Architectural Role
- Implements the announcement approach interface
- Registered in the announce approach factory
- Routed by the orchestrator using type-based filtering (`ApproachType.ANNOUNCE`)
- Delivers alerts immediately to enabled channels (no scheduling/reminders)

## Example Configuration Concept
- Enable/disable per symbol and channel
- Set threshold for what constitutes a "large candle"

## Related Concepts
- Modular, type-based notification delivery
- Immediate delivery for announce approaches
- Config-driven enablement and routing

*Last updated: April 25, 2026*
