"""
Main configuration for all stockreports tests.

This file configures pytest for the entire test suite, including
markers, fixtures, and global test settings.
"""

import pytest
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests (deselect with '-m \"not performance\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "requires_data: marks tests that require real data files"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker to performance tests
        if "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
            item.add_marker(pytest.mark.slow)
        
        # Add slow marker to tests that might take time
        if any(keyword in item.name.lower() for keyword in ["full_pipeline", "real_data", "large"]):
            item.add_marker(pytest.mark.slow)


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session") 
def project_root():
    """Provide path to project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def skip_if_no_imports():
    """Skip test if stockreports imports are not available."""
    try:
        import stockreports
        return False
    except ImportError:
        pytest.skip("stockreports package not available for import")


# Global test settings
pytest_plugins = [
    "tests.integration.conftest",
    "tests.performance.conftest", 
]
