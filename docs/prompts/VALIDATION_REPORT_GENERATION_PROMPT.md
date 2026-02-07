# Validation Report Generation Prompt

## Overview

This prompt provides a detailed framework for generating comprehensive validation reports after running the generic debug script (`tests/debug/alert/approach/generic_debug_executor.py`) for any alert approach test case.

Use this prompt when:
- Testing a new alert approach for the first time
- Validating refactored approaches
- Running integration tests on specific symbols and time ranges
- Documenting test execution and results for stakeholder review

---

## Template Prompt

### When Running Tests and Generating Reports

**You are a technical testing and documentation expert responsible for creating comprehensive validation reports based on alert approach test execution results. Your task is to generate a detailed validation report that documents:**

1. **Complete test execution details** including:
   - Exact command used (with all flags)
   - Input parameters (symbol, date range, time, data points)
   - Execution environment details
   - Actual file paths where outputs were saved
   - Execution time and performance metrics

2. **Full alert results** including:
   - Alert summary table with all key properties
   - Complete JSON output of generated alerts
   - Alert price, signal, trend, magnitude, and all details
   - Timestamps in ISO format
   - Validation tracking embedded in alert details

3. **Step-by-step validation analysis** for each step in the approach:
   - Status (PASSED/FAILED)
   - Actual values from the test execution
   - Configuration parameter values and comparisons
   - Exact log messages from the executor
   - Detailed interpretation of what passed/failed and why

4. **Validation checklist** covering:
   - Code quality (error-free execution, proper use of utilities)
   - Logic correctness (calculations, trend determination, validations)
   - Type safety (Enum handling, string formatting, JSON serialization)
   - Output quality (data formatting, completeness, serialization)

5. **Performance and quality metrics**:
   - Execution time
   - Data points processed
   - Alerts generated count
   - Alert quality assessment (confidence rating)
   - Code efficiency notes

6. **Signal quality assessment**:
   - Confidence rating (1-5 stars)
   - Strengths of the generated signal
   - Recommendation for the alert
   - Technical analysis of consolidation, breakout, volume

7. **Chart analysis**:
   - Confirmation that chart was generated
   - File location
   - Description of what the chart visualizes

8. **Configuration review**:
   - All parameters used in the test (as a code block)
   - Whether each parameter value was optimal
   - Whether results align with parameter settings

9. **Logging output summary**:
   - List of INFO, WARNING, ERROR messages encountered
   - Confirmation of clean execution (no errors)

10. **Comprehensive conclusion**:
    - Final validation result (PASSED/FAILED with confidence level)
    - Functional validation checklist (5+ items)
    - Logic validation checklist (5+ items)
    - Type safety validation checklist (4+ items)
    - Code quality validation checklist (4+ items)
    - Documentation accuracy validation checklist (4+ items)
    - Deployment recommendations
    - Specific next steps
    - Production readiness status with recommendation (DEPLOY/DO NOT DEPLOY/CONDITIONAL)

11. **Test environment documentation**:
    - Python version
    - Project root path
    - Test execution timestamp
    - Market and timezone
    - Data source

---

## Step-by-Step Instructions

### 1. Capture Test Execution Information

When you run the generic debug script, extract and document:

```
Command:
export PYTHONPATH=$(pwd) && python3 tests/debug/alert/approach/generic_debug_executor.py \
    --approach [APPROACH_NAME] \
    --symbol "[SYMBOL]" \
    --start-time "[YYYY-MM-DD HH:MM:SS]" \
    --end-time "[YYYY-MM-DD HH:MM:SS]" \
    --save-to-file --generate-chart

Execution Status:
- Configuration loading: [SUCCESS/FAILURE]
- Data fetching: [SUCCESS/FAILURE with X data points]
- Executor run: [SUCCESS/FAILURE]
- Alert generation: [NUMBER of alerts]
- Chart generation: [SUCCESS/FAILURE]
```

### 2. Extract Alert Details

From the terminal output showing "Found X [APPROACH] Alerts", extract:
- Alert ID, signal, alert price, alert time
- Start price, start time
- Magnitude, trend, symbol
- All properties from the alert DataFrame

Format as:
```json
{
  "approach": "[APPROACH]",
  "id": "[ALERT_ID]",
  "signal": "[BUY/SELL]",
  "alert_price": [PRICE],
  "alert_time": "[ISO_TIMESTAMP]",
  ...
}
```

Include the full "details" JSON field with all validations.

### 3. Document Each Validation Step

For each step in the approach (typically 4-8 steps), document:

**Format**:
```
### ✅ Step [N]: [Step Name]

**Status**: PASSED / FAILED

**Validation Details**:
- Requirement: [What was checked]
- [Param1]: [Actual Value]
- [Param2]: [Actual Value]
- Test Result: ✅ [Comparison Result]

**Message from Execution**:
[Exact log message from executor output]

**Interpretation**: [What this means, why it passed/failed]
```

### 4. Create Validation Checklist

Document all validations that passed:

```
### Code Quality
- ✅ All [N] steps executed in correct sequence
- ✅ No exceptions or errors during execution
- ✅ [Specific utility] used correctly
- ✅ Logging output comprehensive
- ✅ All validations tracked properly

### Logic Correctness
- ✅ [Logic validation 1]
- ✅ [Logic validation 2]
- ✅ [Logic validation 3]

### Type Safety
- ✅ [Type validation 1]
- ✅ [Type validation 2]

### Output Quality
- ✅ [Output validation 1]
- ✅ [Output validation 2]
```

### 5. Assess Signal Quality

Rate the alert from 1-5 stars based on:
- How well it meets all validation criteria
- Strength of technical factors (body ratio, magnitude, etc.)
- Quality of consolidation/trend setup
- Absence of counter-trend resistance

### 6. Write Conclusion

Format:
```
## Conclusion

### ✅ Final Validation Result: [PASSED/FAILED] - [BRIEF STATEMENT]

#### ✅ Functional Validation
1. [Item 1]
2. [Item 2]
... (5+ items)

#### ✅ Logic Validation
1. [Item 1]
2. [Item 2]
... (5+ items)

#### ✅ Type Safety Validation
1. [Item 1]
2. [Item 2]
... (4+ items)

#### ✅ Code Quality Validation
1. [Item 1]
2. [Item 2]
... (4+ items)

#### ✅ Documentation Accuracy
1. [Item 1]
2. [Item 2]
... (4+ items)

### Deployment Recommendations
**✅ Status**: [PRODUCTION READY / NEEDS FIXES / CONDITIONAL]
**Recommendation**: [DEPLOY / DO NOT DEPLOY / TEST FURTHER]
```

### 7. Include Test Environment

```
## Test Environment

| Item | Value |
|------|-------|
| Python Version | [e.g., 3.10+] |
| Project Root | [Full path] |
| Test Date | [YYYY-MM-DD HH:MM:SS] |
| Market | [e.g., Vietnam (VN)] |
| Timezone | [e.g., Asia/Ho_Chi_Minh (+07:00)] |
| Data Source | [e.g., Live API - VietStock] |
```

---

## File Naming Convention

```
tests/debug/validation_reports/[APPROACH_NAME]_Validation_[DATE].md
```

Examples:
```
tests/debug/validation_reports/STRONG_CANDLE_Validation_20260206.md
tests/debug/validation_reports/VRA_Validation_20260207.md
tests/debug/validation_reports/TREND_REVERSAL_Validation_20260205.md
tests/debug/validation_reports/CVA_Validation_20260207.md
```

---

## Key Information to Extract from Terminal Output

### Configuration Loaded
```
Look for: "Running '[APPROACH]' approach for symbol [SYMBOL]..."
Extract: Approach initialized correctly
```

### Data Fetching
```
Look for: "Successfully fetched [N] data points for [SYMBOL]"
Extract: Number of data points, success confirmation
```

### Alert Count
```
Look for: "Found [N] [APPROACH] Alerts" or "No [APPROACH] Alerts Found"
Extract: Number of alerts generated
```

### Validation Messages
```
Look for log messages like:
"Body ratio [X] is >= [Y]"
"Alert candle volume [X] <= max conditional window volume [Y] * [Z]"
"Window price range [X] <= [Y]"
"Alert candle color is consistent with [TREND] trend"
Extract: Exact validation messages with values
```

### Chart Generation
```
Look for: "Chart saved to [PATH]"
Extract: Confirmation and file path
```

---

## Quality Checklist for Your Report

Before finalizing the validation report, verify:

- ✅ All input parameters are documented
- ✅ All step validations are documented with actual values
- ✅ All validation messages from executor are included verbatim
- ✅ Alert JSON output is complete and properly formatted
- ✅ Configuration parameters are shown with values
- ✅ Confidence rating is justified
- ✅ Conclusion section has 5+ validation categories
- ✅ File paths are absolute and correct
- ✅ Timestamps are in ISO format where applicable
- ✅ Test environment is fully documented
- ✅ Deployment recommendation is clear and justified
- ✅ No vague or generic language - all details are specific

---

## Example Use Case

**When you receive a request like**:
```
"Run the generic debug script to validate STRONG_CANDLE 
on VN30 for 2026-02-06 from 13:00:00 to 14:10:00 
and generate a comprehensive validation report"
```

**You should**:
1. Run the script with the exact parameters
2. Capture all terminal output
3. Extract alert details and validation messages
4. Create a structured markdown report following this template
5. Save it to: `tests/debug/validation_reports/STRONG_CANDLE_Validation_20260206.md`
6. Include all sections from this prompt
7. Verify all quality checklist items
8. Provide a summary of results

---

## Additional Context to Include

### For Each Step Validation

Include:
- **Requirement**: What configuration parameter or rule was checked
- **Actual Values**: The real numbers/results from the test
- **Expected Range/Value**: What was required
- **Test Result**: How the actual compared to expected (✅ PASSED or ❌ FAILED)
- **Executor Message**: Verbatim log message if available
- **Technical Interpretation**: Why this matters, what it means

### For Alert Quality Assessment

Consider:
- **Body Ratio**: Is it strong? (1.0 = perfect)
- **Magnitude**: Is the move significant?
- **Consolidation**: Is the price range tight?
- **Volume**: Is it controlled or a spike?
- **Trend Match**: Does alert color match detected trend?
- **Opposition**: Are counter-trend candles weak?

### For Deployment Readiness

Verify:
- All validations passed (0 failures)
- No errors or exceptions in logging
- Code executed efficiently
- All output files were generated correctly
- Alert data is complete and properly formatted
- Confidence in signal quality is high (4-5 stars)
- No configuration changes needed
- No code issues detected

---

## Summary

This prompt template provides a structured approach to generating professional, comprehensive validation reports for any alert approach test case. Use it to:

1. **Capture complete test execution details**
2. **Document all validations with actual values**
3. **Assess signal quality objectively**
4. **Verify production readiness**
5. **Provide clear deployment recommendations**

By following this template, your validation reports will be thorough, professional, and suitable for stakeholder review and decision-making.

---

## Customization Notes

This template is designed to be flexible:

- **Number of steps**: Different approaches have different step counts (6-9 typical)
- **Validation count**: Each step may have 1-3 validations
- **Alert count**: Report may document 1 or multiple alerts
- **Parameters**: Configuration parameters vary by approach
- **Confidence rating**: Adjust star rating based on approach-specific signal quality

Always adapt the report structure to match the specific approach being tested while maintaining the same level of detail and professionalism shown in this template.
