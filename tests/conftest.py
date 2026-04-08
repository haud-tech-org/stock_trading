"""
Pytest configuration file.

Configures pytest to properly handle the project structure and imports.
"""

import sys
from pathlib import Path

# Add project root to sys.path so tests can import src.stockreports modules
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
