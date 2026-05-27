"""Unit test configuration with hexagonal architecture adapters.

This conftest provides in-memory implementations of domain ports
for fast, isolated unit tests that require no disk, no database,
and no external dependencies.
"""

import pytest
import sys

from soar_lab.infrastructure.in_memory_alert_repository import InMemoryAlertRepository
from soar_lab.infrastructure.in_memory_storage import InMemoryStorage


@pytest.fixture
def in_memory_alert_repository():
    """In-memory AlertRepository for unit tests."""
    repo = InMemoryAlertRepository()
    yield repo
    repo.clear()


@pytest.fixture
def in_memory_storage():
    """In-memory StorageProvider for unit tests."""
    storage = InMemoryStorage()
    yield storage
    storage.clear()


@pytest.fixture
def fake_backup_driver():
    """Fake BackupDriver for unit tests (no subprocess)."""

    class FakeBackupDriver:
        def __init__(self):
            self.created = []
            self.extracted = []

        def create(self, source_dir: str, dest_path: str) -> None:
            self.created.append((source_dir, dest_path))

        def extract(self, archive_path: str, dest_dir: str) -> None:
            self.extracted.append((archive_path, dest_dir))

    return FakeBackupDriver()


@pytest.fixture
def fake_test_runner():
    """Fake TestRunner for unit tests (no subprocess)."""

    class FakeTestRunner:
        def __init__(self):
            self.ran = []

        def run_suite(self, suite: str, coverage: bool = True):
            self.ran.append((suite, coverage))
            return {
                'status': 'success',
                'output': 'All tests passed',
                'error': '',
                'duration': 1.0,
                'returncode': 0
            }

        def get_coverage(self):
            return {"unit": 85.0, "integration": 90.0, "overall": 87.5}

    return FakeTestRunner()


def pytest_collection_modifyitems(items):
    """Prevent unit tests from importing forbidden modules.

    Unit tests should not import subprocess, docker, or sqlite3 directly.
    Those are infrastructure details that belong in integration tests.
    """
    import ast
    forbidden_modules = {'subprocess', 'docker', 'sqlite3'}

    for item in items:
        # Only apply guard to tests in tests/unit/
        if not item.nodeid.startswith('tests/unit/'):
            continue

        # Get the source file path
        module = item.module
        if not hasattr(module, '__file__'):
            continue

        source_file = module.__file__
        if not source_file:
            continue

        # Read and parse the source file
        try:
            with open(source_file, 'r', encoding='utf-8') as f:
                source = f.read()
        except (IOError, OSError):
            continue

        # Check for forbidden imports using AST
        try:
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        module_name = alias.name.split('.')[0]
                        if module_name in forbidden_modules:
                            pytest.fail(
                                f"{item.nodeid}: imports '{module_name}' — "
                                f"move to tests/integration/ or use InMemory* adapters"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        module_name = node.module.split('.')[0]
                        if module_name in forbidden_modules:
                            pytest.fail(
                                f"{item.nodeid}: imports '{module_name}' — "
                                f"move to tests/integration/ or use InMemory* adapters"
                            )
        except SyntaxError:
            # If we can't parse the file, skip the check
            pass
