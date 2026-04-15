"""
Coordination package - Maps approaches to their configured resolutions.

Provides lazy singleton ResolutionCoordinator via get_coordinator().

Usage:
    from src.stockreports.coordination import get_coordinator
    
    coordinator = get_coordinator()  # Lazy singleton creation
    resolution = coordinator.get_resolutions(approach)
"""

from .resolution_coordinator import get_coordinator

__all__ = ["get_coordinator"]
