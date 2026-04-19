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
git diff in staged and provide a short description of changes into a new markdown for a new commit. The purpose for development teams in the life cycle, not supporting for the business or marketing teams. So populate compatible summary.

Reference
docs/references/COMMIT_SUMMARY_CVA.md
```

### Description for a new PR

```txt
git diff between the 2 commits
commit 1: 77d715fa4e5b164b3ea58fe169636e33fe688897

commit 2: cd7c7e6e0c821fb866556e480f29275781eeb56e

review and re-analyze deep dive the code changes. Then, propose a summary in details of the code changes for a new PR created from the code changes.
```