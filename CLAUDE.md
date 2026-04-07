# CLAUDE.md - AI Assistant Development Guide

This is the orchestration document for AI assistants working with this codebase. It provides navigation and high-level context, with detailed information in separate focused documents.

## Quick Navigation

### Core Concepts (Start Here)
- **Project Type:** Python multi-provider data retrieval system
- **Main Technologies:** Python 3.10+, pytest 8.4.2+, data providers (Vietstock, Binance)
- **Key Architecture:** Factory + Registry + Coordinator + Loader pattern
- **Status:** 55% complete (Phases 1-2 done, 27/27 tests passing ✅)

### Essential Documentation

#### General (Apply to All Code)
| Topic | Document | Purpose |
|-------|----------|---------|
| **Code Style** | [docs/CODE_STYLE.md](docs/CODE_STYLE.md) | Naming conventions, type hints, imports, docstrings, formatting |
| **Testing** | [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | Test organization, coverage, fixtures, mocking strategies, patterns |
| **Implementation** | [docs/IMPLEMENTATION_PATTERNS.md](docs/IMPLEMENTATION_PATTERNS.md) | Common patterns, best practices, design principles |

#### Data Provider Module (Provider-Specific)
| Topic | Document | Purpose |
|-------|----------|---------|
| **Quick Start** | [docs/data_provider/QUICK_REFERENCE.md](docs/data_provider/QUICK_REFERENCE.md) | Status, roadmap, quick code examples, Phases 1-4 overview |
| **Architecture** | [docs/data_provider/ARCHITECTURE.md](docs/data_provider/ARCHITECTURE.md) | Provider architecture, design patterns, component overview, data flow |
| **Configuration** | [docs/data_provider/CONFIGURATION.md](docs/data_provider/CONFIGURATION.md) | Settings management, loader pattern, auto-sync, environment setup |
| **Questions** | [docs/data_provider/FAQ.md](docs/data_provider/FAQ.md) | Troubleshooting, common issues, performance, getting help |

## Project Structure

```
stock_trading/
├── src/stockreports/
│   ├── data_provider/
│   │   ├── coordinator.py              # Central orchestration
│   │   ├── factory.py                  # Provider creation
│   │   ├── base.py                     # Abstract interface
│   │   ├── providers/                  # Implementation
│   │   │   ├── vietstock.py
│   │   │   ├── binance_api.py
│   │   │   └── binance_ccxt.py
│   │   ├── normalizers/                # Format conversion
│   │   └── exceptions.py               # Error types
│   └── config/
│       ├── settings.py                 # Configuration values
│       └── loader.py                   # Dynamic loading
├── tests/
│   └── data_provider/
│       ├── test_phase1_integration.py
│       └── test_phase2_integration.py
└── docs/
    ├── ARCHITECTURE.md
    ├── CODE_STYLE.md
    ├── TESTING_GUIDE.md
    ├── CONFIGURATION.md
    ├── IMPLEMENTATION_PATTERNS.md
    └── FAQ.md
```

## Key Information at a Glance

### Core Principles

1. **Loader Pattern for Configuration**
   - Always use `get_settings()` from loader, never direct imports
   - Supports runtime changes needed for testing
   - Reads fresh each time, no caching issues

2. **Auto-Sync Enabled Fields**
   - Single source of truth: `ENABLED_DATA_PROVIDERS`
   - Enabled fields auto-sync: `"enabled": "provider_name" in ENABLED_DATA_PROVIDERS`
   - Only ever modify `ENABLED_DATA_PROVIDERS`

3. **Provider Framework**
   - All providers inherit from `BaseDataProvider`
   - Each has provider-specific normalizer
   - Factory manages singleton instances
   - Coordinator enforces enabled status

4. **Configuration Hierarchy**
   ```
   ENABLED_DATA_PROVIDERS (single source of truth)
         ↓
   DATA_PROVIDER_CONFIG (auto-synced enabled fields)
         ↓
   Global settings (timeouts, limits, etc.)
         ↓
   get_settings() (centralized access function)
   ```

### Common Tasks

**Enable a Provider:**
```python
ENABLED_DATA_PROVIDERS = ["vietstock", "binance"]  # That's it!
```

**Access Configuration:**
```python
from src.stockreports.config.loader import get_settings
settings = get_settings()
enabled = settings.ENABLED_DATA_PROVIDERS
```

**Use Coordinator:**
```python
coordinator = DataProviderCoordinator()
data = coordinator.fetch_ohlcv("BNBUSD", "1h")
results = coordinator.fetch_ohlcv_multi_provider("BNBUSD")
```

**Test with Modified Settings:**
```python
original = settings.ENABLED_DATA_PROVIDERS.copy()
try:
    settings.ENABLED_DATA_PROVIDERS[:] = ["vietstock"]
    # test code
finally:
    settings.ENABLED_DATA_PROVIDERS[:] = original
```

## Implementation Checklist

### Before You Code
- [ ] Read [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) to understand design
- [ ] Review [docs/CODE_STYLE.md](docs/CODE_STYLE.md) for conventions
- [ ] Check [docs/IMPLEMENTATION_PATTERNS.md](docs/IMPLEMENTATION_PATTERNS.md) for similar tasks
- [ ] Look at existing tests in [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)

### When Adding a Provider
→ See [docs/IMPLEMENTATION_PATTERNS.md](docs/IMPLEMENTATION_PATTERNS.md) - Adding a New Data Provider

Steps:
1. Create provider class
2. Create normalizer
3. Register in factory
4. Add to settings
5. Write tests
6. Update documentation

### When Modifying Configuration
→ See [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Modifying Configuration

Rules:
- Only edit `ENABLED_DATA_PROVIDERS`
- Auto-sync handles the rest
- Use `get_settings()` to access
- Save/restore in tests

### When Writing Tests
→ See [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)

Pattern:
- Use AAA (Arrange-Act-Assert)
- Mock external APIs
- Modify settings with save/restore
- Target ≥90% coverage

## Performance & Scalability

| Operation | Time | Notes |
|-----------|------|-------|
| Provider creation | ~10ms | Singleton cached |
| Single fetch | ~200-500ms | API dependent |
| Multi-provider fetch | ~400-1500ms | Sequential |
| Settings load | ~1ms | Very fast |

**See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for more details.**

## Troubleshooting

**Settings not updating?**
→ Use `get_settings()`, not direct imports (see [docs/CONFIGURATION.md](docs/CONFIGURATION.md))

**Provider not found?**
→ Check enabled in `ENABLED_DATA_PROVIDERS` (see [docs/FAQ.md](docs/FAQ.md))

**Tests failing with settings?**
→ Save/restore settings in tests (see [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md))

**Need more help?**
→ See [docs/FAQ.md](docs/FAQ.md) for comprehensive troubleshooting

## Project Status

### Completed ✅

- **Phase 1:** Provider framework (10/10 tasks)
- **Phase 2:** Binance integration (5/5 tasks)
- **Configuration:** Auto-sync + Loader (3/3 tasks)
- **Documentation:** Comprehensive guides (6 docs)
- **Tests:** 27/27 passing, 0 errors

### Pending

- **Phase 3:** Testing & Validation (awaiting request)
- **Phase 4:** Documentation & Deployment (awaiting request)

**Overall Completion: 55%**

## Quick Command Reference

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/data_provider/test_phase1_integration.py

# Run specific test function
pytest tests/data_provider/test_phase1_integration.py::test_coordinator_initializes

# Check for errors
python -m pylint src/

# Format code
black src/
```

## Moving Forward

### To Proceed with Next Phase

Ask for Phase 3 or 4:

> "Proceed with Phase 3" - Testing & Validation
> 
> "Proceed with Phase 4" - Documentation & Deployment
> 
> "Execute all phases" - Run remaining phases

### To Make Changes Now

Request any of these:
- Add a feature (describe what)
- Fix a bug (describe the issue)
- Add a new provider (name and source)
- Modify configuration (what settings to change)
- Improve tests (what to test)
- Update documentation (what's unclear)

---

## Documentation Index

| Document | Lines | Topics |
|----------|-------|--------|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | ~354 | System design, patterns, components, data flow, scalability |
| [docs/CODE_STYLE.md](docs/CODE_STYLE.md) | ~536 | Naming, type hints, imports, docstrings, layout, testing |
| [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md) | ~590 | Test organization, patterns, fixtures, mocking, coverage |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | ~555 | Settings management, loader, auto-sync, validation, patterns |
| [docs/IMPLEMENTATION_PATTERNS.md](docs/IMPLEMENTATION_PATTERNS.md) | ~561 | Adding providers, modifying code, error handling, logging |
| [docs/FAQ.md](docs/FAQ.md) | ~580 | Troubleshooting, questions, debugging, performance |

**Total documentation: ~3,176 lines of focused, organized reference material**

---

## Summary

This CLAUDE.md is an orchestration document that points you to the right place for:
- **Understanding the system:** → [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Writing code:** → [docs/CODE_STYLE.md](docs/CODE_STYLE.md)
- **Writing tests:** → [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- **Managing configuration:** → [docs/CONFIGURATION.md](docs/CONFIGURATION.md)
- **Implementing features:** → [docs/IMPLEMENTATION_PATTERNS.md](docs/IMPLEMENTATION_PATTERNS.md)
- **Solving problems:** → [docs/FAQ.md](docs/FAQ.md)

All information is organized by topic in focused documents. Start with the guide relevant to your task, then reference others as needed.
