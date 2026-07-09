"""Unit tests for infrastructure.clients module."""

import pytest

from soar_lab.infrastructure.clients import (
    GatewayIPStrategy,
    UnixSocketStrategy,
    DefaultFromEnvStrategy,
    create_redis_client,
    create_docker_client,
)


class TestGatewayIPStrategy:
    """Tests for GatewayIPStrategy."""

    def test_gateway_ip_strategy_init(self):
        """Test GatewayIPStrategy initialization."""
        strategy = GatewayIPStrategy(gateway_ip="192.168.1.1")
        assert strategy.gateway_ip == "192.168.1.1"

    def test_gateway_ip_strategy_connect_failure(self):
        """Test GatewayIPStrategy connect when Docker is not available."""
        strategy = GatewayIPStrategy(gateway_ip="192.168.1.1")
        result = strategy.connect("/var/run/docker.sock")
        assert result is None


class TestUnixSocketStrategy:
    """Tests for UnixSocketStrategy."""

    def test_unix_socket_strategy_connect_failure(self):
        """Test UnixSocketStrategy connect when Docker is not available."""
        strategy = UnixSocketStrategy()
        result = strategy.connect("/var/run/docker.sock")
        assert result is None


class TestDefaultFromEnvStrategy:
    """Tests for DefaultFromEnvStrategy."""

    def test_default_from_env_strategy_connect_failure(self):
        """Test DefaultFromEnvStrategy connect when Docker is not available."""
        strategy = DefaultFromEnvStrategy()
        result = strategy.connect("/var/run/docker.sock")
        assert result is None


class TestCreateRedisClient:
    """Tests for create_redis_client function."""

    def test_create_redis_client_no_config_provider(self):
        """Test create_redis_client returns None when config_provider is None."""
        result = create_redis_client(None)
        assert result is None

    def test_create_redis_client_no_redis_url(self):
        """Test create_redis_client returns None when REDIS_URL is not set."""
        mock_config = MockConfigProvider({"REDIS_URL": None})
        result = create_redis_client(mock_config)
        assert result is None

    def test_create_redis_client_connection_failure(self):
        """Test create_redis_client returns None when Redis connection fails."""
        mock_config = MockConfigProvider({"REDIS_URL": "redis://localhost:6379"})
        result = create_redis_client(mock_config)
        assert result is None


class TestCreateDockerClient:
    """Tests for create_docker_client function."""

    def test_create_docker_client_no_config_provider(self):
        """Test create_docker_client returns None when config_provider is None."""
        result = create_docker_client(None)
        assert result is None

    def test_create_docker_client_all_strategies_fail(self):
        """Test create_docker_client returns None when all strategies fail."""
        mock_config = MockConfigProvider({
            "docker_socket_path": "/var/run/docker.sock",
            "docker_gateway_ip": None
        })
        result = create_docker_client(mock_config)
        assert result is None

    def test_create_docker_client_with_gateway_ip(self):
        """Test create_docker_client with gateway_ip configured."""
        mock_config = MockConfigProvider({
            "docker_socket_path": "/var/run/docker.sock",
            "docker_gateway_ip": "192.168.1.1"
        })
        result = create_docker_client(mock_config)
        assert result is None


class MockConfigProvider:
    """Mock config provider for testing."""

    def __init__(self, config_dict):
        self.config = config_dict

    def get(self, key, default=None):
        """Get config value."""
        return self.config.get(key, default)
