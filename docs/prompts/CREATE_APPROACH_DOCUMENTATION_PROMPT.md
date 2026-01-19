### Prompt Template: Create New Approach Documentation

**User Request:**

Create new documentation for the `[APPROACH_NAME]` approach.

**Instructions for the AI:**

Your task is to create a comprehensive and accurate documentation file for the specified trading approach, reflecting its current implementation in the codebase. The new file should be named `docs/algorithms/[APPROACH_NAME].md`.

To do this, you must follow these steps:

1.  **Analyze the Source Code**:
    *   Thoroughly read and understand the logic within the primary executor file: `src/stockreports/alert/approach/[APPROACH_NAME]/executor.py`.
    *   Identify all configurable parameters by cross-referencing the approach's `settings.py` file and the main `src/stockreports/config/signal_settings.py`.

2.  **Generate Documentation Content**:
    *   Based on your analysis, generate a new markdown document that strictly follows the structure below.
    *   Use the existing `docs/algorithms/VRA.md` file as a reference for tone and formatting.

3.  **Required Documentation Structure**:

    *   **`## 1. Objective`**: Write a concise, high-level paragraph explaining what the approach is designed to do and its core strategy.

    *   **`## 2. Key Parameters`**: Create a markdown table listing all configurable parameters for the approach. The table must have the following columns:
        *   `Parameter`: The name of the setting (e.g., `LOOKBACK_WINDOW`).
        *   `Default Value`: The default value as defined in the approach's `settings.py`.
        *   `Description`: A clear explanation of what the parameter controls.

    *   **`## 3. Step-by-Step Logic`**: Provide a numbered list that breaks down the main execution flow of the `_find_*_alerts` method. Each step should correspond to a major validation check (e.g., Magnitude Validation, Volume Validation, Reversal Confirmation). Clearly state the conditions for passing or failing each step.

    *   **`## 4. Flow Diagram`**: Create a `mermaid` flow diagram (`graph TD`) that visually represents the step-by-step logic. The diagram must accurately reflect the decision points and flow of the executor.

---
**How to use it:**

Simply replace `[APPROACH_NAME]` with the name of the approach you want documented, for example: `PRICE_GAP`, `COMPARISON`, etc.
