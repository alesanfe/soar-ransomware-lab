"""Unit tests for api.dependencies module."""

import pytest

from soar_lab.api.dependencies import (
    get_composition_root,
    get_config_provider,
    get_redis,
    get_docker,
    get_analytics_service,
    get_backup_service,
    get_test_service,
    get_health_service,
)


class TestGetCompositionRoot:
    """Tests for get_composition_root dependency."""

    def test_get_composition_root_with_none(self):
        """Test that get_composition_root raises ValueError when composition_root is None."""
        with pytest.raises(ValueError, match="composition_root must be provided"):
            get_composition_root(None)

    def test_get_composition_root_with_value(self):
        """Test that get_composition_root returns the provided composition root."""
        mock_root = MockCompositionRoot()
        result = get_composition_root(mock_root)
        assert result == mock_root


class TestGetConfigProvider:
    """Tests for get_config_provider dependency."""

    def test_get_config_provider(self):
        """Test that get_config_provider returns config_provider from composition root."""
        mock_root = MockCompositionRoot()
        result = get_config_provider(mock_root)
        assert result == mock_root.config_provider


class TestGetRedis:
    """Tests for get_redis dependency."""

    def test_get_redis(self):
        """Test that get_redis returns redis_client from composition root."""
        mock_root = MockCompositionRoot()
        result = get_redis(mock_root)
        assert result == mock_root.redis_client


class TestGetDocker:
    """Tests for get_docker dependency."""

    def test_get_docker(self):
        """Test that get_docker returns docker_client from composition root."""
        mock_root = MockCompositionRoot()
        result = get_docker(mock_root)
        assert result == mock_root.docker_client


class TestGetAnalyticsService:
    """Tests for get_analytics_service dependency."""

    def test_get_analytics_service(self):
        """Test that get_analytics_service returns analytics_service from composition root."""
        mock_root = MockCompositionRoot()
        result = get_analytics_service(mock_root)
        assert result == mock_root.analytics_service


class TestGetBackupService:
    """Tests for get_backup_service dependency."""

    def test_get_backup_service(self):
        """Test that get_backup_service returns backup_service from composition root."""
        mock_root = MockCompositionRoot()
        result = get_backup_service(mock_root)
        assert result == mock_root.backup_service


class TestGetTestService:
    """Tests for get_test_service dependency."""

    def test_get_test_service(self):
        """Test that get_test_service returns test_service from composition root."""
        mock_root = MockCompositionRoot()
        result = get_test_service(mock_root)
        assert result == mock_root.test_service


class TestGetHealthService:
    """Tests for get_health_service dependency."""

    def test_get_health_service(self):
        """Test that get_health_service returns health_service from composition root."""
        mock_root = MockCompositionRoot()
        result = get_health_service(mock_root)
        assert result == mock_root.health_service


class MockCompositionRoot:
    """Mock composition root for testing."""

    def __init__(self):
        self.config_provider = {"API_TITLE": "Test API"}
        self.redis_client = "mock_redis"
        self.docker_client = "mock_docker"
        self.analytics_service = "mock_analytics"
        self.backup_service = "mock_backup"
        self.test_service = "mock_test"
        self.health_service = "mock_health"
