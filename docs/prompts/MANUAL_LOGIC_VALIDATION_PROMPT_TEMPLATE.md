# Prompt Template: Manual Code Logic Validation

## Objective
Perform a manual, step-by-step execution trace of a specific function to understand why it produced a certain result.

## 1. Target Logic to Analyze
*   **File Path:** `[Provide the full path to the file, e.g., src/stockreports/alert/approach/CONSISTENT_MOMENTUM/executor.py]`
*   **Function(s):** `[List the specific function(s) to trace, e.g., _confirm_short_window_reversal]`

## 2. Execution Context & Assumptions
*   **Starting Point:** `[e.g., Assume a valid momentum window was found, and the alert candle is at 'YYYY-MM-DD HH:MM:SS']`
*   **Initial State:** `[e.g., The initial signal is 'BUY', and we are looking for a 'SELL' reversal]`
*   **Other Settings:** `[Mention any non-default settings I should be aware of, otherwise I will use the defaults]`

## 3. Data for Analysis
Please use the exact data provided below for the trace.

```
[Paste the relevant data here, preferably in CSV or a markdown table format. Include headers.]
```

## 4. Your Task
1.  Trace the execution flow starting from the specified function.
2.  For each validation step inside the function, detail the following:
    *   **Validation Step:** What is being checked?
    *   **Analysis:** What are the specific data values being used in the check?
    *   **Result:** Did the check **PASS** or **FAIL**?
    *   **Reason:** Explain briefly why it passed or failed based on the data and thresholds.
3.  Provide a final conclusion summarizing the single, definitive reason for the outcome.
