
**Prompt for Creating a New Announce Approach Alerter (Layer 7)**

Use this prompt to request a new announce approach alerter. All requirements are mandatory. All checklist items must be completed and verified before PR approval. Documentation updates are required and must be explicit.


**Prompt:**

Please create a new announce approach alerter for Layer 7 notification delivery.

**Requirements:**
- Strictly follow the architecture and guidelines in the Layer 7 documentation ([Technical Reference](../../../ARCHITECTURE/TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md), [Implementation Guide](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/README.md)).
- Use [PriceMovementAlerter](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/PRICE_MOVEMENT.md) and [LargeCandleAlerter](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/LARGE_CANDLE.md) as templates for structure, modularity, and integration (base, factory, orchestrator).
- All code must comply with [CODING_CONVENTION_AND_STANDARDIZATION.md](../../STANDARDIZATIONS/CODING_CONVENTION_AND_STANDARDIZATION.md) (import order, docstrings, naming, formatting, etc.).
- The new approach must be fully encapsulated, registered in the factory, orchestrator, and all relevant configuration files: [notification_service_config.json](../../../src/stockreports/config/notification_service_config.json), [executor_approach_configuration.json](../../../src/stockreports/config/executor_approach_configuration.json).
- Ensure all log messages and alert details use canonical enum values (e.g., trend, signal) as defined in the constants.
- Include a minimal unit test with test data that matches the expected DataFrame schema (all required columns).
- Handle and report any integration or import errors encountered.
- **Documentation updates are required**: update all of the following if relevant:
	- [Technical Reference](../../../ARCHITECTURE/TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md)
	- [Implementation Guide](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/README.md)
	- [Prompt Template](./ANNOUNCE_APPROACH_ALERTER_AI_GEN_CODE.md)
	- [Approach-specific doc](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/NEW_APPROACH.md)
	- [Coding Conventions](../../STANDARDIZATIONS/CODING_CONVENTION_AND_STANDARDIZATION.md)
- Do not include any business logic not relevant to the new approach.



## Checklist (must be completed for PR approval)
- [ ] New approach module created and implemented ([alerter.py](../../../src/stockreports/alert/announce/approach/NEW_APPROACH/alerter.py)).
- [ ] Registered in [factory.py](../../../src/stockreports/alert/announce/factory.py), orchestrator, and all relevant config files ([notification_service_config.json](../../../src/stockreports/config/notification_service_config.json), [executor_approach_configuration.json](../../../src/stockreports/config/executor_approach_configuration.json)).
- [ ] Base class and package markers present ([announcement_alerter.py](../../../src/stockreports/alert/announce/announcement_alerter.py), `__init__.py`).
- [ ] Constants updated (e.g., `Approach` enum in [constants.py](../../../src/stockreports/alert/common/constants.py)).
- [ ] Unit test added with correct DataFrame schema and both alerting/non-alerting scenarios ([test_alerter.py](../../../tests/unit/stockreports/alert/announce/approach/NEW_APPROACH/test_alerter.py)).
- [ ] Log messages and alert details use canonical enum values (trend, signal, etc.).
- [ ] Documentation updated:
	- [Technical Reference](../../../ARCHITECTURE/TECHNICAL_REFERENCE/LAYER_7_NOTIFICATION_DELIVERY/README.md)
	- [Implementation Guide](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/README.md)
	- [Prompt Template](./ANNOUNCE_APPROACH_ALERTER_AI_GEN_CODE.md)
	- [Approach-specific doc](../../../ARCHITECTURE/IMPLEMENTATION_GUIDES/LAYER_7_NOTIFICATION_DELIVERY/NEW_APPROACH.md)
	- [Coding Conventions](../../STANDARDIZATIONS/CODING_CONVENTION_AND_STANDARDIZATION.md)
- [ ] Data flow diagram included ([SymbolAlerter](../../../src/stockreports/alert/symbol_alerter.py) → [NotificationServiceOrchestrator](../../../src/stockreports/services/external/notification_services/orchestrator.py) → Channel → User).
- [ ] All code and docs comply with [CODING_CONVENTION_AND_STANDARDIZATION.md](../../STANDARDIZATIONS/CODING_CONVENTION_AND_STANDARDIZATION.md).
- [ ] **PR must not be approved unless all boxes are checked and all referenced docs are updated.**