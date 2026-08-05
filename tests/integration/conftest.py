#!/usr/bin/env python3
"""
pytest configuration for integration tests
"""

import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Set BASE_DIR at module load time
os.environ.setdefault('BASE_DIR', str(Path(__file__).parent.parent))

# Patch StaticFiles at module load time to allow non-existent directories
from fastapi import staticfiles

original_staticfiles = staticfiles.StaticFiles


class MockStaticFiles:
    def __init__(self, directory, name=None):
        self.directory = directory
        self.name = name


staticfiles.StaticFiles = MockStaticFiles


def pytest_collection_modifyitems(items):
    """Add @pytest.mark.integration to all integration tests automatically."""
    for item in items:
        if item.nodeid.startswith('tests/integration/'):
            item.add_marker(pytest.mark.integration)
