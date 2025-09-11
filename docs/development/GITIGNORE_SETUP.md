# .gitignore Configuration Documentation

## 📁 What's Being Ignored

### 🐍 **Python Standard Ignores**
- `__pycache__/` - Python bytecode cache directories
- `*.py[cod]` - Compiled Python files (.pyc, .pyo, .pyd)
- `*.egg-info/` - Package metadata
- `dist/`, `build/` - Distribution and build directories

### 🧪 **Testing & Coverage**
- `.pytest_cache/` - Pytest cache
- `htmlcov/` - HTML coverage reports
- `.coverage` - Coverage data files
- `coverage.xml` - Coverage XML reports

### 🔧 **Development Tools**
- `.venv/`, `venv/` - Virtual environments
- `.idea/`, `.vscode/` - IDE configuration files
- `*.swp`, `*.swo` - Editor temporary files

### 💾 **Operating System Files**
- `.DS_Store` - macOS metadata files
- `Thumbs.db` - Windows thumbnail cache
- `*~` - Linux backup files

### 📊 **Project-Specific Data**
- `project/data/har_requests/` - HAR request data
- `project/data/har_responses/` - HAR response data
- `project/data/summary_reports/` - Generated reports
- `*.har` - HTTP Archive files
- `*test_reports*/` - All test report directories

### 📝 **Analysis & Documentation**
- `*SUMMARY.md` - Analysis summary files
- `*ANALYSIS.md` - Analysis documentation
- `*RESTRUCTURING*.md` - Restructuring documentation
- `cleanup_legacy.*` - Cleanup scripts

### 🔄 **Temporary & Backup Files**
- `*.log` - Log files
- `*.tmp`, `*.temp` - Temporary files
- `*_backup_*/` - Backup directories
- `*.bak` - Backup files

## ✅ **What's Tracked**

### 📦 **Core Package**
- `src/stockreports/` - Main package code
- `tests/` - Test files
- `pyproject.toml` - Project configuration
- `README.md` - Documentation

### 🗂️ **Project Structure**
- Essential documentation files
- Configuration files
- Source code and tests

## 🔧 **Customization Notes**

### **To Track Analysis Files**
If you want to track analysis files, comment out these lines:
```gitignore
# *SUMMARY.md
# *ANALYSIS.md
# *RESTRUCTURING*.md
```

### **To Track JSON Data**
If JSON files contain non-sensitive data, comment out:
```gitignore
# *.json
```

### **To Track HAR Files**
If you want to version control HAR files, comment out:
```gitignore
# *.har
```

## 📋 **Git Status Check**

After setup, ignored files include:
- ✅ All Python cache files
- ✅ Virtual environment
- ✅ Test reports and coverage
- ✅ Data directories
- ✅ Temporary analysis files
- ✅ OS-specific files

## 🚀 **Next Steps**

1. **Add core files**: `git add src/ tests/ pyproject.toml README.md`
2. **Initial commit**: `git commit -m "Initial commit: Core package structure"`
3. **Verify ignores**: `git status --ignored`

---

**Note**: This `.gitignore` is designed for a Python data analysis project with HAR file processing. Adjust patterns based on your specific needs.
