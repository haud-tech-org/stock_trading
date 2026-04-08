"""
Data Services Package - Clean Public API for Data Operations

This package provides a unified, clean API for all data services operations
including fetching, processing, caching, and provider coordination.

PUBLIC API
==========
The only export from this package is DataServiceOrchestrator. All other
internal implementations are hidden under _internal/.

Usage:
    >>> from src.stockreports.data_services import DataServiceOrchestrator
    >>> orchestrator = DataServiceOrchestrator()
    >>> data = orchestrator.fetch_and_process('VCB', '2024-01-01', '2024-12-31')

INTERNAL STRUCTURE (Private - Do not use directly)
===================================================
All internal implementations are located under _internal/ with names
prefixed with underscore (_) to indicate they should not be imported
directly by external code:

- _internal/fetching/_manager.py: Historical data fetching & caching
- _internal/processing/_processor.py: Data transformations
- _internal/processing/_settings.py: Processing configuration
- _internal/providing/_coordinator.py: Provider coordination
- _internal/providing/_base_provider.py: Provider abstract base
- _internal/providing/_provider_factory.py: Provider instantiation
- _internal/providing/_providers.py: Provider enum
- _internal/providing/_registry.py: Provider registration
- _internal/providing/binance/*: Binance provider implementation
- _internal/providing/vietstock/*: Vietstock provider implementation
- _internal/providing/validation/*: Symbol validation

ARCHITECTURE
============
This package follows the Facade pattern:
- Public API (orchestrator.py) provides a clean, unified interface
- Internal modules (_internal/) handle all implementation details
- Python naming convention (_ prefix) indicates private modules
- Single entry point reduces external coupling
- Easy to refactor internals without breaking external code

MIGRATION NOTES
===============
This package was created during a refactoring to consolidate scattered
data services modules. Previous imports from:
- src.stockreports.utils.historical_data_manager
- src.stockreports.data_processor
- src.stockreports.data_provider

Should now use:
- from src.stockreports.data_services import DataServiceOrchestrator
"""

from src.stockreports.data_services.orchestrator import DataServiceOrchestrator

__all__ = [
    "DataServiceOrchestrator",
]
