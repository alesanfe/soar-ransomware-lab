#!/usr/bin/env python3
"""Pytest configuration for SOAR Ransomware Lab Provides common fixtures and
configuration for all tests."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

__all__ = [
    "mock_settings",
    "mock_redis_client",
    "mock_docker_client",
    "sample_alert",
    "temp_backup_dir",
    "temp_results_dir",
    "reset_env_vars",
    "sample_malicious_alert",
    "sample_benign_alert",
    "sample_ioc_package",
    "sample_misp_event",
    "sample_workflow_data",
    "sample_metrics_data",
    "mock_elasticsearch_client",
    "mock_thehive_client",
    "mock_misp_client",
    "mock_shuffle_client",
]

# Register default provider factories for AuthService() so tests can
# instantiate it without explicit providers.  This keeps the application
# layer free of infrastructure imports (hexagonal architecture).
try:
    from soar_lab.application.use_cases.auth_service import set_default_factories
    from soar_lab.infrastructure.auth_defaults import (
        create_default_config_provider_wrapper,
        create_default_token_provider_wrapper,
    )

    set_default_factories(
        config_factory=create_default_config_provider_wrapper,
        token_factory=create_default_token_provider_wrapper,
    )
except Exception:  # pragma: no cover
    pass


# Auto-mark tests based on their directory path.
# This avoids needing @pytest.mark.xxx on every single test file.
_DIR_MARKERS = {
    "atomic": "atomic",
    "e2e": "e2e",
    "general": "quality",
    "integration": "integration",
    "performance": "performance",
    "quality": "quality",
    "security": "security",
    "unit": "unit",
    "architecture": "architecture",
}

# Extra markers applied to ALL tests in a directory (in addition to _DIR_MARKERS).
# e2e tests require Docker + external services and are slow (minutes each).
# performance tests are slow by nature.
_DIR_EXTRA_MARKERS = {
    "e2e": ["requires_docker", "requires_external", "slow"],
    "performance": ["slow"],
}


def pytest_collection_modifyitems(items):
    """Auto-apply markers based on test directory."""
    for item in items:
        parts = item.fspath.strpath.replace("\\", "/").split("/tests/")
        if len(parts) < 2:
            continue
        rel = parts[1]
        top_dir = rel.split("/")[0]
        marker = _DIR_MARKERS.get(top_dir)
        if marker:
            item.add_marker(getattr(pytest.mark, marker))
        for extra in _DIR_EXTRA_MARKERS.get(top_dir, []):
            item.add_marker(getattr(pytest.mark, extra))


# Set BASE_DIR at module load time so that imports of soar_lab.api (which
# instantiate Settings() eagerly) do not fail during test collection.
os.environ.setdefault("BASE_DIR", str(Path(__file__).parent.parent))

# Disable eager instantiation in soar_lab.api.__init__ to allow tests to
# configure environment before app creation
os.environ.setdefault("SOAR_SKIP_EAGER_INIT", "1")

# Load .env.full so e2e tests can pick up real tokens (SIEM_WEBHOOK_TOKEN, etc.)
try:
    from dotenv import load_dotenv

    _env_file = Path(__file__).parent.parent / ".env.full"
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
        "mitre_techniques": ["T1059"],
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
    os.environ.setdefault("BASE_DIR", str(Path(__file__).parent.parent))
    # Reload .env.full to ensure correct API keys are used
    try:
        from dotenv import load_dotenv

        _env_file = Path(__file__).parent.parent / ".env.full"
        if _env_file.exists():
            load_dotenv(_env_file, override=True)
    except ImportError:
        pass
    yield
    os.environ.clear()
    os.environ.update(original_env)


# Additional shared fixtures for test data


@pytest.fixture
def sample_malicious_alert():
    """Sample malicious alert payload for testing."""
    return {
        "alert_id": "MALICIOUS-001",
        "hostname": "infected-host",
        "src_ip": "10.0.0.50",
        "hash": {"sha256": "a" * 64},
        "severity": 3,
        "event_type": "ransomware_detection",
        "timestamp": "2024-01-01T00:00:00Z",
        "process_name": "encrypt.exe",
        "mitre_techniques": ["T1486", "T1059"],
        "description": "Ransomware encryption detected",
    }


@pytest.fixture
def sample_benign_alert():
    """Sample benign alert payload for testing."""
    return {
        "alert_id": "BENIGN-001",
        "hostname": "clean-host",
        "src_ip": "192.168.1.10",
        "hash": {"sha256": "b" * 64},
        "severity": 0,
        "event_type": "system_event",
        "timestamp": "2024-01-01T00:00:00Z",
        "process_name": "notepad.exe",
        "mitre_techniques": [],
        "description": "Normal system event",
    }


@pytest.fixture
def sample_ioc_package():
    """Sample IOC package for testing."""
    return {
        "ioc_id": "IOC-001",
        "ioc_type": "hash",
        "value": "d41d8cd98f00b204e9800998ecf8427e" * 2,
        "source": "misp",
        "confidence": 0.9,
        "timestamp": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_misp_event():
    """Sample MISP event for testing."""
    return {
        "Event": {
            "id": "1",
            "uuid": "test-uuid-001",
            "info": "Test Event",
            "threat_level_id": 3,
            "distribution": 1,
            "date": "2024-01-01",
        },
        "Attribute": [
            {"id": "1", "type": "sha256", "value": "a" * 64, "category": "Payload delivery"}
        ],
    }


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing."""
    return {
        "workflow_id": "workflow-001",
        "execution_id": "exec-001",
        "status": "completed",
        "start_time": "2024-01-01T00:00:00Z",
        "end_time": "2024-01-01T00:05:00Z",
        "duration_seconds": 300,
        "input_data": {"alert_id": "TEST-001"},
        "output_data": {"result": "success"},
    }


@pytest.fixture
def sample_metrics_data():
    """Sample metrics data for testing."""
    return {
        "timestamp": "2024-01-01T00:00:00Z",
        "metric_type": "alert_processed",
        "value": 100,
        "labels": {"severity": "high", "source": "siem"},
    }


@pytest.fixture
def mock_elasticsearch_client():
    """Mock Elasticsearch client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.indices = Mock()
    client.indices.create.return_value = True
    client.indices.exists.return_value = False
    client.search.return_value = {"hits": {"total": {"value": 0}, "hits": []}}
    client.index.return_value = {"result": "created"}
    client.bulk.return_value = {"errors": False}
    return client


@pytest.fixture
def mock_thehive_client():
    """Mock TheHive client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.create_case.return_value = {"id": "case-001"}
    client.create_alert.return_value = {"id": "alert-001"}
    client.search_cases.return_value = []
    client.search_alerts.return_value = []
    return client


@pytest.fixture
def mock_misp_client():
    """Mock MISP client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.get_event.return_value = {"Event": {"id": "1"}}
    client.create_event.return_value = {"Event": {"id": "1"}}
    client.add_attribute.return_value = {"Attribute": {"id": "1"}}
    return client


@pytest.fixture
def mock_shuffle_client():
    """Mock Shuffle client for testing."""
    client = Mock()
    client.ping.return_value = True
    client.execute_workflow.return_value = {"execution_id": "exec-001", "status": "completed"}
    client.get_workflow.return_value = {"id": "workflow-001", "name": "Test Workflow"}
    return client
