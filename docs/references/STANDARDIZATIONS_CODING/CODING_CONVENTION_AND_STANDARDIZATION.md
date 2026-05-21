# Coding Convention and Standardization Rules

## Purpose
This document defines the core coding conventions and standardization rules for all scripts in this repository. These rules are mandatory and must be followed for every script, regardless of its business logic or purpose.

---

## 1. Import Statement Standardization
- **Order and Grouping:**
  1. Standard Library Imports (Python built-ins)
  2. Third-Party Imports (external packages, e.g., pandas, numpy)
  3. Project Imports (internal modules/packages)
- **Blank Lines:**
  - Separate each group with a single blank line.
- **No Unused Imports:**
  - Remove all unused imports.
- **No Wildcard Imports:**
  - Do not use `from module import *`.
- **Placement Principle Rule:**
  - Always place all import statements at the very top of the file, before any other code (except for module-level docstrings or comments).
  - Do not place imports inside functions, methods, or classes unless absolutely necessary (e.g., to avoid circular dependencies or for documented performance reasons).
  - This ensures clarity, maintainability, and compliance with Python best practices.
- **Example:**
  ```python
  # --- Standard Library Imports ---
  import os
  import sys
  from datetime import datetime

  # --- Third-Party Imports ---
  import pandas as pd
  import numpy as np

  # --- Project Imports ---
  from src.mymodule import my_function
  from .utils import helper
  ```

---


## 2. File, Directory, and Class Structure
- Each file should start with a module-level docstring describing its purpose.
- Classes and functions must have docstrings explaining their intent and usage.
- Use type hints for all function arguments and return values.
- **Every directory in the codebase must contain an `__init__.py` file.**
  - This marks the directory as a Python package and ensures imports work reliably.
  - Even if the file is empty, add a comment explaining its purpose (e.g., `"""This file marks this directory as a Python package."""`).

---

## 3. Naming Conventions
- Use `snake_case` for variables, functions, and methods.
- Use `PascalCase` for class names.
- Use `UPPER_CASE` for constants.

---

## 4. Code Formatting
- Follow [PEP 8](https://peps.python.org/pep-0008/) for Python code style.
- Indent with 4 spaces (no tabs).
- Limit lines to 120 characters.

---

## 5. Error Handling
- Use explicit exception handling (`try`/`except`) where appropriate.
- Always log errors with meaningful messages.

---

## 6. Testing
- All new code must include unit tests.
- Tests should follow the same import and formatting conventions as main code.

---

## 7. Documentation
- Update this document if new conventions are adopted.
- All code changes must comply with the latest version of this document.

---

*Last updated: April 25, 2026*
