"""Test configuration and fixtures."""

import sys
from pathlib import Path

# Add the src directory to the path so imports work during testing
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
