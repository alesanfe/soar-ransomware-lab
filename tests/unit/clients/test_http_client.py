#!/usr/bin/env python3
"""Unit tests for http_client.py."""

import ssl
from unittest.mock import AsyncMock, Mock, patch

import pytest

from soar_lab.infrastructure.http_client import AioHTTPClient


class TestAioHTTPClient:
    """Test AioHTTPClient infrastructure adapter."""

    def test_initialization(self):
        """Test successful initialization."""
        client = AioHTTPClient(default_timeout=10, default_verify_ssl=False)

        assert client.default_timeout == 10
        assert client.default_verify_ssl == False

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        client = AioHTTPClient()

        assert client.default_timeout == 5
        assert client.default_verify_ssl == True

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_success(self, mock_aiohttp):
        """Test successful GET request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient()
        status = await client.get("http://example.com")

        assert status == 200

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_with_custom_timeout(self, mock_aiohttp):
        """Test GET request with custom timeout."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient(default_timeout=5)
        status = await client.get("http://example.com", timeout=10)

        assert status == 200

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    @patch("soar_lab.infrastructure.http_client.ssl")
    async def test_get_without_ssl_verification(self, mock_ssl, mock_aiohttp):
        """Test GET request without SSL verification."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        mock_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        mock_ssl_context.check_hostname = False
        mock_ssl_context.verify_mode = ssl.CERT_NONE
        mock_ssl.create_default_context.return_value = mock_ssl_context

        client = AioHTTPClient()
        status = await client.get("http://example.com", verify_ssl=False)

        assert status == 200
        mock_ssl.create_default_context.assert_called_once()

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_json_success(self, mock_aiohttp):
        """Test successful GET JSON request."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient()
        data = await client.get_json("http://example.com")

        assert data == {"key": "value"}

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_json_with_custom_timeout(self, mock_aiohttp):
        """Test GET JSON request with custom timeout."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient()
        data = await client.get_json("http://example.com", timeout=10)

        assert data == {"key": "value"}

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    @patch("soar_lab.infrastructure.http_client.ssl")
    async def test_get_json_without_ssl_verification(self, mock_ssl, mock_aiohttp):
        """Test GET JSON request without SSL verification."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"key": "value"})
        mock_response.raise_for_status = Mock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)

        mock_session = AsyncMock()
        mock_session.get = Mock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        mock_ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        mock_ssl_context.check_hostname = False
        mock_ssl_context.verify_mode = ssl.CERT_NONE
        mock_ssl.create_default_context.return_value = mock_ssl_context

        client = AioHTTPClient()
        data = await client.get_json("http://example.com", verify_ssl=False)

        assert data == {"key": "value"}
        mock_ssl.create_default_context.assert_called_once()

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_raises_exception_on_error(self, mock_aiohttp):
        """Test GET request raises exception on error."""
        mock_session = AsyncMock()
        mock_session.get = Mock(side_effect=Exception("Connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient()

        with pytest.raises(Exception, match="Connection error"):
            await client.get("http://example.com")

    @pytest.mark.asyncio
    @patch("soar_lab.infrastructure.http_client.aiohttp")
    async def test_get_json_raises_exception_on_error(self, mock_aiohttp):
        """Test GET JSON request raises exception on error."""
        mock_session = AsyncMock()
        mock_session.get = Mock(side_effect=Exception("Connection error"))
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        mock_aiohttp.ClientSession = Mock(return_value=mock_session)
        mock_aiohttp.ClientTimeout = Mock()
        mock_aiohttp.TCPConnector = Mock()

        client = AioHTTPClient()

        with pytest.raises(Exception, match="Connection error"):
            await client.get_json("http://example.com")
