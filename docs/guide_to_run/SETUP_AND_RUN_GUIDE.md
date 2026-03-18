# Project Setup and Run Guide

**Last Updated**: March 18, 2026  
**Python Version**: 3.12.12  
**Status**: Production Ready

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step-by-Step Setup](#step-by-step-setup)
3. [Project Activation](#project-activation)
4. [Running the Project](#running-the-project)
5. [Verification Commands](#verification-commands)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

Before starting, ensure you have:
- ✅ macOS with Homebrew installed
- ✅ Git configured
- ✅ pyenv installed (Python version manager)
- ✅ Project cloned from repository

---

## Step-by-Step Setup

### Step 1: Navigate to Project Directory

```bash
cd /Users/tech/dev/development/stock_trading
```

**Explanation**:
- Changes your current working directory to the project root
- Required before running any project-specific commands
- Replace `/Users/tech/dev/development/stock_trading` with your actual project path

---

### Step 2: Check Installed Python Versions

```bash
pyenv versions
```

**Explanation**:
- Lists all Python versions installed via pyenv
- Shows which version is currently set as default (marked with `*`)
- Output example:
  ```
    system
    3.9.25
    3.10.13
  * 3.12.12 (set by /Users/haudo/.pyenv/version)
  ```

**Expected Output**:
- You should see `3.12.12` in the list
- If not present, install it with the next command

---

### Step 3: Install Python 3.12.12 (if not already installed)

```bash
pyenv install 3.12.12
```

**Explanation**:
- Downloads and compiles Python 3.12.12 from source
- Takes 5-15 minutes depending on system speed
- Uses Homebrew dependencies (openssl@3, readline, zlib)
- Installation location: `/Users/haudo/.pyenv/versions/3.12.12`
- Only run if `3.12.12` is NOT in the output from Step 2

**When to skip**: If `pyenv versions` shows `3.12.12` already installed, skip this step

---

### Step 4: Set Python 3.12.12 as Global Default

```bash
pyenv global 3.12.12
```

**Explanation**:
- Sets Python 3.12.12 as the system-wide default Python version
- Updates `~/.pyenv/version` file
- Affects all new shell sessions and commands using `python3`
- Ensures consistency across your development environment

**Verify**:
```bash
pyenv versions
# Should show: * 3.12.12 (set by /Users/haudo/.pyenv/version)
```

---

### Step 5: Remove Old Virtual Environment (if exists)

```bash
rm -rf .venv
```

**Explanation**:
- Removes the existing `.venv` directory if it exists
- Necessary because it may contain old Python 3.9 or 3.10 binaries
- Safe to run even if `.venv` doesn't exist
- Cleans up stale dependencies from previous Python versions

**When to skip**: If this is a fresh clone without an existing `.venv`

---

### Step 6: Create New Virtual Environment with Python 3.12.12

```bash
/Users/haudo/.pyenv/versions/3.12.12/bin/python3 -m venv .venv
```

**Explanation**:
- Creates a new virtual environment named `.venv` in the project directory
- Uses the full path to Python 3.12.12 to ensure correct version
- `-m venv` invokes Python's venv module
- Creates isolated Python environment for this project only
- Generated files:
  - `.venv/bin/python` → executable
  - `.venv/bin/activate` → activation script
  - `.venv/lib/python3.12/site-packages/` → dependency storage

**What gets created**:
```
.venv/
├── bin/
│   ├── python → /Users/haudo/.pyenv/versions/3.12.12/bin/python3
│   ├── python3 → /Users/haudo/.pyenv/versions/3.12.12/bin/python3
│   ├── python3.12 → python3
│   ├── pip
│   └── activate
├── lib/
│   └── python3.12/
│       └── site-packages/
├── pyvenv.cfg
└── include/
```

---

### Step 7: Activate Virtual Environment

```bash
source .venv/bin/activate
```

**Explanation**:
- Activates the virtual environment for your current shell session
- Modifies `PATH` to prioritize `.venv/bin/` executables
- Changes your shell prompt to show `(.venv)` prefix
- All subsequent `python`, `pip`, and package commands use this isolated environment

**What changes**:
```bash
# Before activation:
$ which python
/Users/haudo/.pyenv/shims/python3

# After activation:
(.venv) $ which python
/Users/tech/dev/development/stock_trading/.venv/bin/python
```

**Note**: You must activate in each new terminal session, or add to shell config:
```bash
# Add to ~/.zshrc (for zsh) to auto-activate
cd /Users/tech/dev/development/stock_trading && source .venv/bin/activate
```

---

### Step 8: Upgrade pip, setuptools, and wheel

```bash
.venv/bin/pip install --upgrade pip setuptools wheel
```

**Explanation**:
- Upgrades Python package management tools to latest versions
- **pip**: Package installer for Python
- **setuptools**: Tool for packaging Python projects
- **wheel**: Binary package format for faster installation
- Ensures compatibility with modern package repositories
- Typically upgrades:
  - pip: 25.0.1 → 26.0.1
  - setuptools: 24.2.0 → 82.0.1
  - wheel: 0.42.0 → 0.46.3

**Why important**:
- Older versions may have bugs or compatibility issues
- Required for installing packages with modern metadata
- Improves installation speed

---

### Step 9: Install Project Dependencies

```bash
.venv/bin/pip install -r requirements.txt
```

**Explanation**:
- Installs all Python packages listed in `requirements.txt`
- Reads from `requirements.txt` file in project root
- Installs to `.venv/lib/python3.12/site-packages/`
- Takes 10-30 minutes depending on packages and network speed

**Requirements installed** (57 total packages):
```
Core Data Science:
- numpy==2.0.2
- pandas==2.3.3
- scipy==1.13.1

Technical Analysis:
- ta==0.11.0
- mplfinance==0.12.10b0

Web Framework:
- Flask==2.3.0
- gunicorn==23.0.0

Async/HTTP:
- aiohttp==3.13.0
- aiohttp-retry==2.9.1

Google Cloud:
- google-cloud-storage==3.9.0

Testing:
- pytest==8.4.2
- pytest-cov==7.0.0
- coverage==7.10.7

Code Quality:
- black==25.9.0
- flake8==7.3.0
- mypy==1.18.2
- isort==6.1.0

Utilities:
- requests==2.32.5
- varname==0.15.1
- twilio==9.8.3
- plotly==6.5.2
- matplotlib==3.9.0

(And 30+ more dependencies...)
```

**Progress indicators**:
```
Collecting google-cloud-storage (from -r requirements.txt (line 1))
Downloading numpy-2.0.2-cp312-cp312-macosx_14_0_arm64.whl
Installing collected packages: numpy, pandas, scipy, ...
Successfully installed ...
```

---

### Step 10: Verify Installation

```bash
.venv/bin/python --version
```

**Explanation**:
- Displays the Python version in your virtual environment
- Confirms correct Python 3.12.12 is being used
- Should output: `Python 3.12.12`

**Quick package verification**:
```bash
.venv/bin/python -c "import pandas; import numpy; import flask; print('✅ All major packages installed!')"
```

**Explanation**:
- Tests if critical packages are importable
- `-c` flag allows inline Python code
- Verifies pandas, numpy, and flask work correctly
- Output: `✅ All major packages installed!`

---

## Project Activation

### Quick Activation (Every New Terminal)

```bash
cd /Users/tech/dev/development/stock_trading && source .venv/bin/activate
```

**Explanation**:
- Two-part command using `&&` (run second only if first succeeds)
- `cd` changes to project directory
- `source .venv/bin/activate` activates the virtual environment
- Results in prompt: `(.venv) $ `

### Alternative: Using Python Directly (No Activation Needed)

```bash
.venv/bin/python script.py
```

**Explanation**:
- Runs Python script using the full path to `.venv/bin/python`
- Works without activating the virtual environment
- Useful for automation and scripting
- Ensures correct Python version is used

### Alternative: Using pip Directly (No Activation Needed)

```bash
.venv/bin/pip install package_name
```

**Explanation**:
- Installs packages to `.venv` without activation
- Full path ensures correct pip is used
- Equivalent to `pip install` when venv is activated

---

## Running the Project

### Option 1: Run with Activated Virtual Environment

```bash
# Step 1: Activate venv (if not already active)
source .venv/bin/activate

# Step 2: Run Python script
python src/stockreports/main.py

# Or run with Flask development server
python -m flask --app src.stockreports.app run

# Or run with pytest
pytest tests/
```

**Explanation**:
- After activation, `python` and `pip` commands automatically use `.venv`
- No path prefix needed
- Simpler to type for multiple commands
- Recommended for interactive development

---

### Option 2: Run Without Activation (Direct Path)

```bash
# Run Python script
.venv/bin/python src/stockreports/main.py

# Install new package
.venv/bin/pip install requests

# Run tests
.venv/bin/python -m pytest tests/
```

**Explanation**:
- Uses full path to `.venv/bin/python` and `.venv/bin/pip`
- Works without activation
- Preferred for CI/CD pipelines and automation
- More explicit about which Python is used

---

### Option 3: Run with Docker (If Dockerfile exists)

```bash
# Build image
docker build -t stock-trading:latest .

# Run container
docker run -p 5000:5000 stock-trading:latest

# Run tests in container
docker run stock-trading:latest pytest tests/
```

**Explanation**:
- Containerized Python environment isolated from system
- Ensures identical setup across machines
- Useful for production deployment
- Check `Dockerfile` in project root for details

---

## Verification Commands

### Verify Virtual Environment is Active

```bash
echo $VIRTUAL_ENV
```

**Expected output**: `/Users/tech/dev/development/stock_trading/.venv`  
**If empty**: Virtual environment is NOT active, run `source .venv/bin/activate`

---

### Verify Python Version

```bash
python --version
```

**Expected output**: `Python 3.12.12`

---

### Verify Python Executable Path

```bash
which python
```

**Expected output**: `/Users/tech/dev/development/stock_trading/.venv/bin/python`  
**If different path**: Wrong Python version, activate venv or use full path

---

### List All Installed Packages

```bash
pip list
```

**Output**: Shows all 57+ installed packages with versions

**Count packages**:
```bash
pip list | wc -l
```

**Expected output**: Around 60 (57 packages + 2 header lines)

---

### Check Specific Package

```bash
pip show pandas
```

**Output example**:
```
Name: pandas
Version: 2.3.3
Summary: Powerful data structures for data analysis, time series, and statistics
Home-page: https://pandas.pydata.org
Author: The Pandas Development Team
Location: /Users/tech/dev/development/stock_trading/.venv/lib/python3.12/site-packages
Requires: numpy, python-dateutil, pytz, tzdata
```

---

### Check for Outdated Packages

```bash
pip list --outdated
```

**Explanation**:
- Shows packages with newer versions available
- Useful for dependency updates
- Run `pip install --upgrade package_name` to update

---

### Run Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/unit/test_alerts.py

# With coverage report
pytest --cov=src tests/

# Verbose output
pytest -v

# Stop on first failure
pytest -x
```

**Explanation**:
- `pytest` discovers and runs all test files
- `tests/` directory structure:
  ```
  tests/
  ├── unit/          # Fast unit tests
  ├── integration/   # Slower integration tests
  └── debug/         # Manual testing scripts
  ```

---

### Run Linting and Code Quality

```bash
# Check code style (PEP 8)
flake8 src/

# Auto-format code
black src/

# Check type hints
mypy src/

# Sort imports
isort src/

# All checks together
black src/ && isort src/ && flake8 src/ && mypy src/
```

**Explanation**:
- **flake8**: Checks for style issues and errors
- **black**: Auto-formats code to consistent style
- **mypy**: Checks Python type hints
- **isort**: Sorts imports in consistent order

---

## Troubleshooting

### Problem: "python: command not found"

**Solution 1**: Activate virtual environment
```bash
source .venv/bin/activate
```

**Solution 2**: Use full path
```bash
.venv/bin/python --version
```

**Solution 3**: Check venv exists
```bash
ls -la .venv/bin/python
# If not found, recreate venv (see Step 6)
```

---

### Problem: "ModuleNotFoundError: No module named 'pandas'"

**Solution 1**: Activate virtual environment
```bash
source .venv/bin/activate
```

**Solution 2**: Reinstall dependencies
```bash
.venv/bin/pip install -r requirements.txt
```

**Solution 3**: Check Python version matches
```bash
.venv/bin/python --version  # Should be 3.12.12
```

---

### Problem: "pyenv: command not found"

**Solution**: Install pyenv via Homebrew
```bash
brew install pyenv
```

Then add to `~/.zshrc`:
```bash
eval "$(pyenv init -)"
```

Then restart terminal or run:
```bash
source ~/.zshrc
```

---

### Problem: "Python 3.12.12 not installed"

**Solution**: Install via pyenv
```bash
pyenv install 3.12.12
pyenv global 3.12.12
```

---

### Problem: Virtual Environment Corrupted

**Solution**: Recreate from scratch
```bash
rm -rf .venv
.venv/bin/python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Problem: Slow Package Installation

**Explanation**: 
- First installation takes 10-30 minutes
- Large packages like scipy, pandas, numpy compile from source on ARM64 Mac
- Subsequent installations are cached and faster

**Solution**: Be patient and keep terminal open during installation

---

## Quick Reference Cheatsheet

```bash
# One-time setup (from zero)
cd /Users/tech/dev/development/stock_trading
pyenv install 3.12.12
pyenv global 3.12.12
rm -rf .venv
/Users/haudo/.pyenv/versions/3.12.12/bin/python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Every new terminal session
cd /Users/tech/dev/development/stock_trading
source .venv/bin/activate

# Run project
python src/stockreports/main.py

# Install new package
pip install new_package

# Run tests
pytest

# Code quality
black src/ && isort src/ && flake8 src/
```

---

## Environment Summary

| Item | Value |
|------|-------|
| **Project Path** | `/Users/tech/dev/development/stock_trading` |
| **Python Version** | 3.12.12 |
| **Virtual Env** | `.venv/` |
| **Python Executable** | `.venv/bin/python` |
| **pip Executable** | `.venv/bin/pip` |
| **Dependencies** | 57+ packages in requirements.txt |
| **Python Manager** | pyenv |
| **OS** | macOS |
| **Shell** | zsh |

---

## Next Steps After Setup

1. **Activate virtual environment**
   ```bash
   source .venv/bin/activate
   ```

2. **Run tests to verify everything works**
   ```bash
   pytest
   ```

3. **Review project structure**
   ```bash
   ls -la src/
   ```

4. **Check git status**
   ```bash
   git status
   ```

5. **Start development**
   ```bash
   python src/stockreports/main.py
   ```

---

## Additional Resources

- **pyenv Documentation**: https://github.com/pyenv/pyenv
- **Python venv Documentation**: https://docs.python.org/3/library/venv.html
- **pip Documentation**: https://pip.pypa.io/
- **Project Git Branch**: `optimize-code-for-alert-notification-and-retry-of-sending-mail-approach`

---

**Last Updated**: March 18, 2026  
**Maintained By**: Development Team  
**Status**: ✅ Production Ready

