#!/usr/bin/env python3
"""Unit tests for health_check_adapter.py."""

from unittest.mock import AsyncMock, Mock

import pytest

from soar_lab.infrastructure.monitoring.health_check_adapter import (
    HTTPHealthCheckAdapter,
)


class TestHTTPHealthCheckAdapter:
    """Test HTTPHealthCheckAdapter infrastructure adapter."""

    def test_initialization_success(self):
        """Test successful initialization with http_client."""
        mock_http_client = Mock()

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client)

        assert adapter.http_client == mock_http_client
        assert adapter.verify_ssl_config == {}

    def test_initialization_with_ssl_config(self):
        """Test initialization with SSL verification config."""
        mock_http_client = Mock()
        ssl_config = {"service1": False, "service2": True}

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client, verify_ssl_config=ssl_config)

        assert adapter.http_client == mock_http_client
        assert adapter.verify_ssl_config == ssl_config

    def test_requires_http_client(self):
        """Test that http_client is required."""
        with pytest.raises(ValueError, match="http_client is required"):
            HTTPHealthCheckAdapter(http_client=None)

    @pytest.mark.asyncio
    async def test_check_service_success(self):
        """Test successful service health check."""
        mock_http_client = Mock()
        mock_http_client.get = AsyncMock(return_value=200)

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client)

        result = await adapter.check_service("service1", "http://service1.local/health")

        assert result == True
        mock_http_client.get.assert_called_once_with(
            "http://service1.local/health", verify_ssl=True
        )

    @pytest.mark.asyncio
    async def test_check_service_failure_status(self):
        """Test service health check with failure status code."""
        mock_http_client = Mock()
        mock_http_client.get = AsyncMock(return_value=500)

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client)

        result = await adapter.check_service("service1", "http://service1.local/health")

        assert result == False

    @pytest.mark.asyncio
    async def test_check_service_no_url(self):
        """Test service health check with no URL."""
        mock_http_client = Mock()

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client)

        result = await adapter.check_service("service1", "")

        assert result == False
        mock_http_client.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_service_exception(self):
        """Test service health check with exception."""
        mock_http_client = Mock()
        mock_http_client.get = AsyncMock(side_effect=Exception("Connection error"))

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client)

        result = await adapter.check_service("service1", "http://service1.local/health")

        assert result == False

    @pytest.mark.asyncio
    async def test_check_service_with_ssl_disabled(self):
        """Test service health check with SSL verification disabled."""
        mock_http_client = Mock()
        mock_http_client.get = AsyncMock(return_value=200)
        ssl_config = {"service1": False}

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client, verify_ssl_config=ssl_config)

        result = await adapter.check_service("service1", "http://service1.local/health")

        assert result == True
        mock_http_client.get.assert_called_once_with(
            "http://service1.local/health", verify_ssl=False
        )

    @pytest.mark.asyncio
    async def test_check_service_ssl_config_not_found(self):
        """Test service health check when service not in SSL config."""
        mock_http_client = Mock()
        mock_http_client.get = AsyncMock(return_value=200)
        ssl_config = {"service2": False}

        adapter = HTTPHealthCheckAdapter(http_client=mock_http_client, verify_ssl_config=ssl_config)

        result = await adapter.check_service("service1", "http://service1.local/health")

        assert result == True
        mock_http_client.get.assert_called_once_with(
            "http://service1.local/health", verify_ssl=True
        )
