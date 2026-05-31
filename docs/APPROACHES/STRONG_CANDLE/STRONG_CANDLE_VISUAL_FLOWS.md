# STRONG_CANDLE Visual Flows

## Flow Diagram

```mermaid
graph TD
	A[Start STRONG_CANDLE Execution] --> B{Loop through candles backwards};
	B --> C{Enough data in window?};
	C -- No --> B;
	C -- Yes --> D[Step 1: Window Setup];
	D --> E[Step 2: Strong Candle Identification];
	E --> F[Step 3: Trend Context Validation];
	F --> G[Step 4: Cooldown Check];
	G --> H{Is in Cooldown?};
	H -- Yes --> B;
	H -- No --> I[Step 5: Create AlertData];
	I --> J{Deployment Mode?};
	J -- Yes --> K[Return Alert];
	J -- No --> B;
	B -- End of Loop --> L[End Execution];
```

---

*This flow diagram is modeled after the VRA approach for consistency.*
