"""Pytest configuration for Ago test suite."""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))
