#!/usr/bin/env python3
"""Unit tests for clients.py Tests Docker and Redis client factories."""

from unittest.mock import Mock, patch

from soar_lab.infrastructure.clients import (
    DefaultFromEnvStrategy,
    GatewayIPStrategy,
    UnixSocketStrategy,
    create_docker_client,
    create_redis_client,
)


class TestGatewayIPStrategy:
    """Test GatewayIPStrategy."""

    def test_initialization(self):
        """Test successful initialization."""
        strategy = GatewayIPStrategy(gateway_ip="192.168.1.1")

        assert strategy.gateway_ip == "192.168.1.1"

    @patch("builtins.__import__")
    def test_connect_success(self, mock_import):
        """Test successful connection via gateway IP."""
        mock_docker_module = Mock()
        mock_client = Mock()
        mock_docker_module.DockerClient.return_value = mock_client
        mock_client.ping.return_value = True
        mock_import.return_value = mock_docker_module

        strategy = GatewayIPStrategy(gateway_ip="192.168.1.1")
        result = strategy.connect("/var/run/docker.sock")

        assert result == mock_client
        mock_docker_module.DockerClient.assert_called_once_with(
            base_url="tcp://192.168.1.1:2375", version="auto"
        )

    @patch("builtins.__import__")
    def test_connect_failure(self, mock_import):
        """Test connection failure via gateway IP."""
        mock_import.side_effect = Exception("Connection failed")

        strategy = GatewayIPStrategy(gateway_ip="192.168.1.1")
        result = strategy.connect("/var/run/docker.sock")

        assert result is None


class TestUnixSocketStrategy:
    """Test UnixSocketStrategy."""

    @patch("builtins.__import__")
    def test_connect_success(self, mock_import):
        """Test successful connection via unix socket."""
        mock_docker_module = Mock()
        mock_client = Mock()
        mock_docker_module.DockerClient.return_value = mock_client
        mock_client.ping.return_value = True
        mock_import.return_value = mock_docker_module

        strategy = UnixSocketStrategy()
        result = strategy.connect("/var/run/docker.sock")

        assert result == mock_client
        mock_docker_module.DockerClient.assert_called_once_with(
            base_url="unix:///var/run/docker.sock", version="auto"
        )

    @patch("builtins.__import__")
    def test_connect_failure(self, mock_import):
        """Test connection failure via unix socket."""
        mock_import.side_effect = Exception("Connection failed")

        strategy = UnixSocketStrategy()
        result = strategy.connect("/var/run/docker.sock")

        assert result is None


class TestDefaultFromEnvStrategy:
    """Test DefaultFromEnvStrategy."""

    @patch("builtins.__import__")
    def test_connect_success(self, mock_import):
        """Test successful connection via from_env."""
        mock_docker_module = Mock()
        mock_client = Mock()
        mock_docker_module.from_env.return_value = mock_client
        mock_client.ping.return_value = True
        mock_import.return_value = mock_docker_module

        strategy = DefaultFromEnvStrategy()
        result = strategy.connect("/var/run/docker.sock")

        assert result == mock_client
        mock_docker_module.from_env.assert_called_once_with(version="auto")

    @patch("builtins.__import__")
    def test_connect_failure(self, mock_import):
        """Test connection failure via from_env."""
        mock_import.side_effect = Exception("Connection failed")

        strategy = DefaultFromEnvStrategy()
        result = strategy.connect("/var/run/docker.sock")

        assert result is None


class TestCreateRedisClient:
    """Test create_redis_client function."""

    def test_requires_config_provider(self):
        """Test that config_provider is required."""
        result = create_redis_client(config_provider=None)
        assert result is None

    @patch("builtins.__import__")
    def test_redis_url_not_set(self, mock_import):
        """Test when REDIS_URL is not set."""
        mock_config = Mock()
        mock_config.get.return_value = None

        result = create_redis_client(config_provider=mock_config)

        assert result is None

    @patch("builtins.__import__")
    def test_redis_connection_success(self, mock_import):
        """Test successful Redis connection."""
        mock_redis_module = Mock()
        mock_client = Mock()
        mock_redis_module.from_url.return_value = mock_client
        mock_client.ping.return_value = True
        mock_import.return_value = mock_redis_module

        mock_config = Mock()
        mock_config.get.return_value = "redis://localhost:6379"

        result = create_redis_client(config_provider=mock_config)

        assert result == mock_client
        mock_redis_module.from_url.assert_called_once_with("redis://localhost:6379")

    @patch("builtins.__import__")
    def test_redis_connection_failure(self, mock_import):
        """Test Redis connection failure."""
        mock_redis_module = Mock()
        mock_redis_module.from_url.side_effect = Exception("Connection failed")
        mock_import.return_value = mock_redis_module

        mock_config = Mock()
        mock_config.get.return_value = "redis://localhost:6379"

        result = create_redis_client(config_provider=mock_config)

        assert result is None


class TestCreateDockerClient:
    """Test create_docker_client function."""

    def test_requires_config_provider(self):
        """Test that config_provider is required."""
        result = create_docker_client(config_provider=None)
        assert result is None

    @patch("soar_lab.infrastructure.clients.UnixSocketStrategy")
    @patch("soar_lab.infrastructure.clients.DefaultFromEnvStrategy")
    def test_unix_socket_success(self, mock_default_strategy, mock_unix_strategy):
        """Test successful connection via unix socket."""
        mock_client = Mock()
        mock_unix_instance = Mock()
        mock_unix_strategy.return_value = mock_unix_instance
        mock_unix_instance.connect.return_value = mock_client

        mock_config = Mock()
        mock_config.get.side_effect = lambda k, d=None: (
            d if k == "docker_gateway_ip" else "/var/run/docker.sock"
        )

        result = create_docker_client(config_provider=mock_config)

        assert result == mock_client
        mock_unix_instance.connect.assert_called_once_with("/var/run/docker.sock")

    @patch("soar_lab.infrastructure.clients.UnixSocketStrategy")
    @patch("soar_lab.infrastructure.clients.DefaultFromEnvStrategy")
    @patch("soar_lab.infrastructure.clients.GatewayIPStrategy")
    def test_gateway_ip_success(
        self, mock_gateway_strategy, mock_default_strategy, mock_unix_strategy
    ):
        """Test successful connection via gateway IP."""
        mock_client = Mock()
        mock_unix_instance = Mock()
        mock_unix_strategy.return_value = mock_unix_instance
        mock_unix_instance.connect.return_value = None

        mock_gateway_instance = Mock()
        mock_gateway_strategy.return_value = mock_gateway_instance
        mock_gateway_instance.connect.return_value = mock_client

        mock_config = Mock()
        mock_config.get.side_effect = lambda k, d=None: (
            "192.168.1.1" if k == "docker_gateway_ip" else "/var/run/docker.sock"
        )

        result = create_docker_client(config_provider=mock_config)

        assert result == mock_client
        mock_gateway_instance.connect.assert_called_once_with("/var/run/docker.sock")

    @patch("soar_lab.infrastructure.clients.UnixSocketStrategy")
    @patch("soar_lab.infrastructure.clients.DefaultFromEnvStrategy")
    def test_default_from_env_success(self, mock_default_strategy, mock_unix_strategy):
        """Test successful connection via default from_env."""
        mock_client = Mock()
        mock_unix_instance = Mock()
        mock_unix_strategy.return_value = mock_unix_instance
        mock_unix_instance.connect.return_value = None

        mock_default_instance = Mock()
        mock_default_strategy.return_value = mock_default_instance
        mock_default_instance.connect.return_value = mock_client

        mock_config = Mock()
        mock_config.get.side_effect = lambda k, d=None: (
            d if k == "docker_gateway_ip" else "/var/run/docker.sock"
        )

        result = create_docker_client(config_provider=mock_config)

        assert result == mock_client
        mock_default_instance.connect.assert_called_once_with("/var/run/docker.sock")

    @patch("soar_lab.infrastructure.clients.UnixSocketStrategy")
    @patch("soar_lab.infrastructure.clients.DefaultFromEnvStrategy")
    def test_all_strategies_fail(self, mock_default_strategy, mock_unix_strategy):
        """Test when all connection strategies fail."""
        mock_unix_instance = Mock()
        mock_unix_strategy.return_value = mock_unix_instance
        mock_unix_instance.connect.return_value = None

        mock_default_instance = Mock()
        mock_default_strategy.return_value = mock_default_instance
        mock_default_instance.connect.return_value = None

        mock_config = Mock()
        mock_config.get.side_effect = lambda k, d=None: (
            d if k == "docker_gateway_ip" else "/var/run/docker.sock"
        )

        result = create_docker_client(config_provider=mock_config)

        assert result is None

    def test_exception_handling(self):
        """Test exception handling in create_docker_client."""
        mock_config = Mock()
        mock_config.get.side_effect = Exception("Config error")

        result = create_docker_client(config_provider=mock_config)

        assert result is None
