"""Pytest configuration for Ago test suite."""
import sys
from pathlib import Path

# Add project root to Python path for imports
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Add the test dir so shared helpers (e.g. ago_build) import as top-level
# modules. Using the `test.` package prefix would clash with the stdlib `test`
# package, so we import them flat instead.
test_dir = project_root / "test"
if str(test_dir) not in sys.path:
    sys.path.insert(0, str(test_dir))
