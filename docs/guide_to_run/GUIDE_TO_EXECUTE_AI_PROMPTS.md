## 🚀 How to Use The Refactoring Code by using Prompt with AI

### Direct Prompt Usage

```
Copy docs/PROMPTS/REFACTORING_CODE/REFACTORING_AI_PROMPT.md into Claude/ChatGPT with your code:

"Please refactor this legacy approach using the Executor → Analyzer → 
Validator pattern. Follow ALL rules in the attached REFACTORING_AI_PROMPT.md 
document. Reference the examples in REFACTORING_EXAMPLES.md. Preserve 
100% of business logic."
```

---

## Prompts

### Update approach's documentation

```txt
Please review the documentation and code for the [APPROACH_NAME] approach. Double-check that every validation and parameter described in the documentation matches the actual implementation in the codebase. If there are any mismatches, update the documentation to accurately reflect the code, ensuring all steps, parameters, and logic are consistent and correct.
```

### Summary of changes in Staged

```txt
git diff in staged and provide a short description of changes into a new markdown for a new commit.

Reference
docs/references/COMMIT_SUMMARY_CVA.md
```