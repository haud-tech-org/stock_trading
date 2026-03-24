"""
Configuration for integration tests.

Provides fixtures and utilities for integration testing of the stockreports package.
"""

import pytest
import tempfile
import json
from pathlib import Path


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for integration tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        
        # Create standard directory structure
        (workspace / "har_files").mkdir()
        (workspace / "responses").mkdir()
        (workspace / "reports").mkdir()
        (workspace / "reports_replay").mkdir()  # For REPLAY mode tests
        
        yield workspace


@pytest.fixture
def sample_har_data():
    """Provide sample HAR data for testing."""
    return {
        "log": {
            "entries": [
                {
                    "request": {"url": "https://example.com/api/stock/VNINDEX"},
                    "response": {
                        "content": {
                            "text": json.dumps({
                                "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00"],
                                "o": [1500.0, 1502.0],
                                "h": [1505.0, 1507.0],
                                "l": [1498.0, 1500.0],
                                "c": [1502.0, 1505.0],
                                "v": [1000, 1200]
                            })
                        }
                    }
                },
                {
                    "request": {"url": "https://example.com/api/stock/VN30"},
                    "response": {
                        "content": {
                            "text": json.dumps({
                                "t": ["2025-09-03 09:25:00", "2025-09-03 09:30:00"],
                                "o": [800.0, 802.0],
                                "h": [805.0, 807.0],
                                "l": [798.0, 800.0],
                                "c": [802.0, 805.0],
                                "v": [2000, 2200]
                            })
                        }
                    }
                }
            ]
        }
    }


@pytest.fixture
def sample_response_data():
    """Provide sample response data for testing."""
    return {
        "t": ["2025-09-03 09:15:00", "2025-09-03 09:20:00", "2025-09-03 09:25:00"],
        "o": [1500.0, 1502.0, 1504.0],
        "h": [1505.0, 1507.0, 1509.0],
        "l": [1498.0, 1500.0, 1502.0],
        "c": [1502.0, 1505.0, 1507.0],
        "v": [1000, 1200, 1400]
    }


@pytest.fixture
def real_data_available():
    """Check if real test data is available."""
    test_dirs = [
        Path("final_validation_reports/responses/har_responses"),
        Path("project/sources/har"),
        Path("project/data/har_responses"),
    ]
    
    for test_dir in test_dirs:
        if test_dir.exists():
            files = list(test_dir.glob("*.json" if "responses" in str(test_dir) else "*.har"))
            if files:
                return test_dir
    
    return None


# Integration test markers
integration_markers = [
    "integration: marks tests as integration tests",
    "slow: marks tests as slow running",
    "requires_data: marks tests that require real data files"
]
