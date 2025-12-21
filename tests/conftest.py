"""
Test Configuration File

Unified setup for Python path, avoiding sys.path.insert in each test file.
Provides the QApplication fixture required for PyQt6 tests.
"""

import sys
from pathlib import Path

import pytest

# Add the src directory to the Python path
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def qapp():
    """
    Create QApplication for all tests.
    
    Uses session scope to avoid creating multiple QApplication instances.
    """
    from PyQt6.QtWidgets import QApplication
    
    # Check if a QApplication instance already exists
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app
