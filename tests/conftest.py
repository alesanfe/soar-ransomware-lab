#!/usr/bin/env python3
"""
pytest configuration for SOAR Ransomware Lab
Provides common fixtures and configuration for all tests
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock


# Pytest markers for test categorization
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (no external dependencies)")
    config.addinivalue_line("markers", "integration: Integration tests (require external services)")
    config.addinivalue_line("markers", "e2e: End-to-end tests (full system)")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "contract: Contract tests (API compliance)")
    config.addinivalue_line("markers", "docker_runtime: Docker runtime tests")
    config.addinivalue_line("markers", "live: Tests requiring live services")
    config.addinivalue_line("markers", "offline: Tests that can run without external services")
    config.addinivalue_line("markers", "smoke: Smoke tests (quick validation)")
    config.addinivalue_line("markers", "regression: Regression tests")


# Set BASE_DIR at module load time so that imports of soar_lab.api (which
# instantiate Settings() eagerly) do not fail during test collection.
os.environ.setdefault('BASE_DIR', str(Path(__file__).parent.parent))

# Disable eager instantiation in soar_lab.api.__init__ to allow tests to
# configure environment before app creation
os.environ.setdefault('SOAR_SKIP_EAGER_INIT', '1')

# Load .env.full so e2e tests can pick up real tokens (SIEM_WEBHOOK_TOKEN, etc.)
try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).parent.parent / '.env.full'
    if _env_file.exists():
        load_dotenv(_env_file, override=True)
except ImportError:
    pass


@pytest.fixture
def mock_settings():
    """Mock settings object for testing."""
    settings = Mock()
    settings.API_HOST = "127.0.0.1"
    settings.API_PORT = 8000
    settings.REDIS_URL = None
    settings.BACKUP_DIR = "/tmp/test_backups"
    settings.TEST_TIMEOUT_SECONDS = 300
    settings.TEST_COVERAGE_PATH = "src/soar_lab"
    settings.JWT_SECRET_KEY = "test-secret-key-min-32-chars-long"
    settings.JWT_EXPIRATION_MINUTES = 60
    settings.CORS_ORIGINS = ["http://localhost:8086"]
    return settings


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = True
    return client


@pytest.fixture
def mock_docker_client():
    """Mock Docker client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.containers = Mock()
    client.containers.list.return_value = []
    return client


@pytest.fixture
def sample_alert():
    """Sample alert payload for testing."""
    return {
        "alert_id": "TEST-001",
        "hostname": "test-host",
        "src_ip": "192.168.1.100",
        "hash": "5d41402abc4b2a76b9719d911017c592",
        "severity": 1,
        "event_type": "ransomware",
        "timestamp": "2024-01-01T00:00:00Z",
        "process_name": "malicious.exe",
        "mitre_techniques": ["T1059"]
    }


@pytest.fixture
def temp_backup_dir(tmp_path):
    """Temporary backup directory for testing."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return str(backup_dir)


@pytest.fixture
def temp_results_dir(tmp_path):
    """Temporary results directory for testing."""
    results_dir = tmp_path / "results"
    results_dir.mkdir()
    return str(results_dir)


@pytest.fixture(autouse=True)
def reset_env_vars():
    """Reset environment variables before each test."""
    original_env = os.environ.copy()
    # Set BASE_DIR for tests that import modules that require it
    os.environ.setdefault('BASE_DIR', str(Path(__file__).parent.parent))
    # Reload .env.full to ensure correct API keys are used
    try:
        from dotenv import load_dotenv
        _env_file = Path(__file__).parent.parent / '.env.full'
        if _env_file.exists():
            load_dotenv(_env_file, override=True)
    except ImportError:
        pass
    yield
    os.environ.clear()
    os.environ.update(original_env)
