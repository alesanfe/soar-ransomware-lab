#!/usr/bin/env python3
"""Unit tests for integrations/base_client.py Tests BaseHTTPClient class."""

from unittest.mock import Mock, patch

import pytest
import requests

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.base_client import BaseHTTPClient


class TestBaseHTTPClient:
    """Test BaseHTTPClient class."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        client = BaseHTTPClient("http://example.com", api_key="test-key")
        assert client.base_url == "http://example.com"
        assert client.timeout == 10
        assert "Authorization" in client._session.headers
        assert client._session.headers["Authorization"] == "Bearer test-key"

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        client = BaseHTTPClient("http://example.com")
        assert client.base_url == "http://example.com"
        assert "Authorization" not in client._session.headers

    def test_init_with_custom_timeout(self):
        """Test initialization with custom timeout."""
        client = BaseHTTPClient("http://example.com", timeout=30)
        assert client.timeout == 30

    def test_init_with_custom_retries(self):
        """Test initialization with custom retries."""
        client = BaseHTTPClient("http://example.com", retries=5)
        assert client is not None

    def test_init_with_verify_ssl_false(self):
        """Test initialization with SSL verification disabled."""
        client = BaseHTTPClient("http://example.com", verify_ssl=False)
        assert client._session.verify is False

    def test_base_url_trailing_slash(self):
        """Test that trailing slash is removed from base URL."""
        client = BaseHTTPClient("http://example.com/")
        assert client.base_url == "http://example.com"

    def test_url_method(self):
        """Test _url method."""
        client = BaseHTTPClient("http://example.com")
        assert client._url("api/test") == "http://example.com/api/test"
        assert client._url("/api/test") == "http://example.com/api/test"

    def test_get_success(self):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.content = b'{"key": "value"}'
        mock_response.json.return_value = {"key": "value"}
        mock_response.raise_for_status.return_value = None

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.headers = {}
            mock_session.get.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            result = client.get("api/test")
            assert result == {"key": "value"}

    def test_get_empty_response(self):
        """Test GET request with empty response."""
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.headers = {}
            mock_session.get.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            result = client.get("api/test")
            assert result == {}

    def test_get_http_error(self):
        """Test GET request with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("404 Not Found")

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.headers = {}
            mock_session.get.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            with pytest.raises(IntegrationError):
                client.get("api/test")

    def test_get_request_exception(self):
        """Test GET request with connection error."""
        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.headers = {}
            mock_session.get.side_effect = requests.ConnectionError("Connection failed")
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            # ConnectionError is wrapped in IntegrationError
            with pytest.raises(IntegrationError):
                client.get("api/test")

    def test_post_success(self):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.content = b'{"result": "success"}'
        mock_response.json.return_value = {"result": "success"}
        mock_response.raise_for_status.return_value = None

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.post.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            result = client.post("api/test", data={"key": "value"})
            assert result == {"result": "success"}

    def test_post_empty_response(self):
        """Test POST request with empty response."""
        mock_response = Mock()
        mock_response.content = b""
        mock_response.raise_for_status.return_value = None

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.post.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            result = client.post("api/test")
            assert result == {}

    def test_post_http_error(self):
        """Test POST request with HTTP error."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("500 Internal Server Error")

        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.post.return_value = mock_response
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            with pytest.raises(IntegrationError):
                client.post("api/test", data={"key": "value"})

    def test_post_request_exception(self):
        """Test POST request with connection error."""
        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.post.side_effect = requests.ConnectionError("Connection failed")
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            # ConnectionError is wrapped in IntegrationError
            with pytest.raises(IntegrationError):
                client.post("api/test", data={"key": "value"})

    def test_health_check_success(self):
        """Test health check with successful response."""
        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.get.return_value = Mock()
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            assert client.health_check() is True

    def test_health_check_failure(self):
        """Test health check with failed response."""
        with patch.object(BaseHTTPClient, "_build_session") as mock_build:
            mock_session = Mock()
            mock_session.get.side_effect = Exception("Connection failed")
            mock_build.return_value = mock_session

            client = BaseHTTPClient("http://example.com")
            assert client.health_check() is False

    def test_default_headers_with_api_key(self):
        """Test _default_headers with API key."""
        client = BaseHTTPClient("http://example.com", api_key="test-key")
        headers = client._default_headers("test-key")
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"

    def test_default_headers_without_api_key(self):
        """Test _default_headers without API key."""
        client = BaseHTTPClient("http://example.com")
        headers = client._default_headers(None)
        assert headers["Content-Type"] == "application/json"
        assert headers["Accept"] == "application/json"
        assert "Authorization" not in headers
