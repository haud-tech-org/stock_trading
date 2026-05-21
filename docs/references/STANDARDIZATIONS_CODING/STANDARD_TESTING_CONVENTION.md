# Test Naming Convention - Standardized Structure

## Overview

Fixed test file naming to follow the **standard pytest auto-discovery convention**. Test files are now properly named using the `test_<module_name>.py` pattern.

**Date Fixed:** March 15, 2026

---

## Naming Convention Fix

### Before (❌ Non-Standard)
```
Source Module                                  Test File
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
src/stockreports/alert/common/
  └─ environment.py                  ────────→ test_environment_type.py  ❌ WRONG
                                                (extra "_type" suffix)
```

### After (✅ Standard)
```
Source Module                                  Test File
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
src/stockreports/alert/common/
  └─ environment.py                  ────────→ test_environment.py  ✅ CORRECT

src/stockreports/config/
  └─ secrets_loader.py               ────────→ test_secrets_loader.py  ✅ CORRECT
```

---

## Standard Python Testing Conventions

### pytest Auto-Discovery Rules

pytest automatically discovers and runs tests that follow these patterns:

```python
# ✅ CORRECT - pytest will auto-discover and run
tests/
├── test_<module_name>.py           # Top-level test files
├── test_<name>.py
└── package/
    ├── test_<module_name>.py       # Nested test files
    └── sub_package/
        └── test_<module_name>.py

# Test Classes (must start with "Test")
class TestXxx:
    pass

# Test Methods (must start with "test_")
def test_something():
    pass
```

### Naming Rules Summary

| Element | Rule | Example | Standard? |
|---------|------|---------|-----------|
| **Test File** | `test_<module_name>.py` | `test_environment.py` | ✅ YES |
| **Test Class** | `Test<ModuleName>` | `TestEnvironmentType` | ✅ YES |
| **Test Method** | `test_<functionality>` | `test_constants_defined` | ✅ YES |

---

## Directory Structure (Mirror Pattern)

```
src/stockreports/                          tests/unit/stockreports/
├── __init__.py                            ├── __init__.py
├── alert/                                 ├── alert/
│   ├── __init__.py                        │   ├── __init__.py
│   └── common/                            │   └── common/
│       ├── __init__.py                    │       ├── __init__.py
│       └── environment.py        ────────→│       └── test_environment.py
│                                          │
├── config/                                ├── config/
│   ├── __init__.py                        │   ├── __init__.py
│   └── secrets_loader.py         ────────→│   └── test_secrets_loader.py
│                                          │
└── utils/                                 └── utils/
    └── ...                                    └── ...
```

---

## Test File Organization

### Current Test Files (✅ Correct)

```
tests/unit/stockreports/alert/common/test_environment.py
├── Class: TestEnvironmentType
├── Methods:
│   ├── test_constants_defined()
│   ├── test_get_display_name()
│   ├── test_get_display_name_invalid()
│   ├── test_all_types()
│   ├── test_is_cloud_environment()
│   ├── test_is_containerized()
│   ├── test_is_production()
│   ├── test_validate()
│   ├── test_environment_characteristics()
│   └── test_display_names_mapping()
└── Total Tests: 10

tests/unit/stockreports/config/test_secrets_loader.py
├── Class: TestSecretsLoaderEnvironmentType
├── Methods:
│   ├── test_local_environment_detection()
│   ├── test_gcp_environment_detection()
│   ├── test_azure_environment_detection()
│   ├── test_kubernetes_environment_detection()
│   ├── test_docker_environment_detection()
│   └── test_environment_type_property()
└── Total Tests: 6
```

---

## Why This Matters

### pytest Auto-Discovery

```bash
# This command will find and run tests:
$ pytest tests/unit/

# pytest looks for:
# 1. Files matching: test_*.py or *_test.py
# 2. Classes matching: Test*
# 3. Methods matching: test_*

# Your files now follow pattern #1:
# tests/unit/stockreports/alert/common/test_environment.py ✅
# tests/unit/stockreports/config/test_secrets_loader.py ✅
```

### Test Discovery Output

```
$ pytest tests/unit/ -v

tests/unit/stockreports/alert/common/test_environment.py::TestEnvironmentType::test_constants_defined PASSED
tests/unit/stockreports/alert/common/test_environment.py::TestEnvironmentType::test_get_display_name PASSED
tests/unit/stockreports/alert/common/test_environment.py::TestEnvironmentType::test_get_display_name_invalid PASSED
...
tests/unit/stockreports/config/test_secrets_loader.py::TestSecretsLoaderEnvironmentType::test_local_environment_detection PASSED
...

======================== 16 passed in 1.44s ========================
```

---

## Test Execution

### Run All Unit Tests
```bash
pytest tests/unit/ -v
```

### Run Specific Test File
```bash
pytest tests/unit/stockreports/alert/common/test_environment.py -v
pytest tests/unit/stockreports/config/test_secrets_loader.py -v
```

### Run Specific Test Class
```bash
pytest tests/unit/stockreports/alert/common/test_environment.py::TestEnvironmentType -v
```

### Run Specific Test Method
```bash
pytest tests/unit/stockreports/alert/common/test_environment.py::TestEnvironmentType::test_constants_defined -v
```

---

## Best Practices Applied

✅ **Standard Naming Convention**
- Test files use `test_<module_name>.py` pattern
- Test classes use `Test<Name>` pattern
- Test methods use `test_<functionality>` pattern

✅ **Mirror Source Structure**
- `tests/unit/` mirrors `src/stockreports/` structure
- Easy to find tests for any module
- Consistent organization

✅ **pytest Auto-Discovery**
- No configuration needed for test discovery
- Automatic test collection
- Works with CI/CD pipelines

✅ **PEP 8 Compliance**
- Follows Python Enhancement Proposal 8
- Industry standard conventions
- Professional code organization

---

## Verification Checklist

- ✅ Test files renamed to `test_<module_name>.py`
- ✅ Directory structure mirrors src structure
- ✅ All 16 tests pass
- ✅ pytest auto-discovers all tests
- ✅ Follows PEP 8 and pytest conventions
- ✅ Ready for CI/CD integration

---

## Summary

All test files now follow the **standardized pytest convention**:

| File | Status |
|------|--------|
| `tests/unit/stockreports/alert/common/test_environment.py` | ✅ Correct |
| `tests/unit/stockreports/config/test_secrets_loader.py` | ✅ Correct |

The naming convention is now:
- **Standard** for pytest auto-discovery
- **Consistent** with Python conventions
- **Professional** and maintainable
- **Ready for production**
