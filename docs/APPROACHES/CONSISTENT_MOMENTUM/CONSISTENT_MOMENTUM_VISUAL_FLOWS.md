# CONSISTENT_MOMENTUM Visual Flows

## Flow Diagram

```mermaid
graph TD
	A[Start CONSISTENT_MOMENTUM Execution] --> B{Loop through candles backwards};
	B --> C{Enough data in window?};
	C -- No --> B;
	C -- Yes --> D[Step 1: Window Setup];
	D --> E[Step 2: Signal Determination];
	E --> F[Step 3: Anchor Candle Identification];
	F --> G[Step 4: Momentum & Consistency Validation];
	G --> H{All Validations Pass?};
	H -- No --> B;
	H -- Yes --> I[Step 5: Cooldown Check];
	I --> J{Is in Cooldown?};
	J -- Yes --> B;
	J -- No --> K[Step 6: Create AlertData];
	K --> L{Deployment Mode?};
	L -- Yes --> M[Return Alert];
	L -- No --> B;
	B -- End of Loop --> N[End Execution];
```

---

*This flow diagram is modeled after the VRA approach for consistency.*
