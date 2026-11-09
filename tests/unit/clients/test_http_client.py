#!/usr/bin/env python3
"""Unit tests for http_client.py (async facade over requests)."""

from unittest.mock import Mock, patch

import pytest

from soar_lab.infrastructure.http_client import AioHTTPClient


def _client_with_mock_session(status_code=200, json_payload=None):
    """Return (client, session_mock) with _pooled_session mocked out."""
    client = AioHTTPClient()
    session = Mock()
    response = Mock()
    response.status_code = status_code
    response.json = Mock(return_value=json_payload or {})
    session.get = Mock(return_value=response)
    client._pooled_session = Mock(return_value=session)
    return client, session, response


class TestAioHTTPClient:
    """Test AioHTTPClient infrastructure adapter."""

    def test_initialization(self):
        """Test successful initialization."""
        client = AioHTTPClient(default_timeout=10, default_verify_ssl=False)

        assert client.default_timeout == 10
        assert client.default_verify_ssl is False

    def test_initialization_defaults(self):
        """Test initialization with default values."""
        client = AioHTTPClient()

        assert client.default_timeout == 5
        assert client.default_verify_ssl

    @pytest.mark.asyncio
    async def test_get_success(self):
        """Test successful GET request."""
        client, session, _resp = _client_with_mock_session(status_code=200)
        status = await client.get("http://example.com")

        assert status == 200
        session.get.assert_called_once()
        args, kwargs = session.get.call_args
        assert args[0] == "http://example.com"
        assert kwargs["allow_redirects"] is True

    @pytest.mark.asyncio
    async def test_get_with_custom_timeout(self):
        """Test GET request with custom timeout."""
        client, session, _resp = _client_with_mock_session()
        client.default_timeout = 5
        await client.get("http://example.com", timeout=10)

        assert session.get.call_args.kwargs["timeout"] == 10

    @pytest.mark.asyncio
    async def test_get_without_ssl_verification(self):
        """Test GET request routes to the verify_ssl=False pooled session."""
        client, session, _resp = _client_with_mock_session()
        await client.get("http://example.com", verify_ssl=False)

        client._pooled_session.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_get_json_success(self):
        """Test successful GET JSON request."""
        client, _session, resp = _client_with_mock_session(json_payload={"key": "value"})
        data = await client.get_json("http://example.com")

        assert data == {"key": "value"}
        resp.raise_for_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_json_with_custom_timeout(self):
        """Test GET JSON request with custom timeout."""
        client, session, _resp = _client_with_mock_session(json_payload={"key": "value"})
        data = await client.get_json("http://example.com", timeout=10)

        assert data == {"key": "value"}
        assert session.get.call_args.kwargs["timeout"] == 10

    @pytest.mark.asyncio
    async def test_get_json_without_ssl_verification(self):
        """Test GET JSON request routes to the verify_ssl=False session."""
        client, _session, _resp = _client_with_mock_session(json_payload={})
        await client.get_json("http://example.com", verify_ssl=False)

        client._pooled_session.assert_called_once_with(False)

    @pytest.mark.asyncio
    async def test_get_raises_exception_on_error(self):
        """Test GET request raises exception on error."""
        client = AioHTTPClient()
        client._pooled_session = Mock(
            return_value=Mock(get=Mock(side_effect=Exception("Connection error")))
        )

        with pytest.raises(Exception, match="Connection error"):
            await client.get("http://example.com")

    @pytest.mark.asyncio
    async def test_get_json_raises_exception_on_error(self):
        """Test GET JSON request raises exception on error."""
        client = AioHTTPClient()
        client._pooled_session = Mock(
            return_value=Mock(get=Mock(side_effect=Exception("Connection error")))
        )

        with pytest.raises(Exception, match="Connection error"):
            await client.get_json("http://example.com")

    @pytest.mark.asyncio
    async def test_get_runs_off_event_loop(self):
        """The blocking call must go through asyncio.to_thread."""
        client, _session, _resp = _client_with_mock_session(status_code=204)
        with patch("soar_lab.infrastructure.http_client.asyncio.to_thread") as mock_thread:
            mock_thread.side_effect = lambda fn, *a: fn(*a)
            status = await client.get("http://example.com")
        assert status == 204
        mock_thread.assert_called_once()

    def test_sessions_pooled_per_verify_mode(self):
        """Sessions are pooled per verify_ssl mode."""
        client = AioHTTPClient()
        s1 = client._pooled_session(True)
        assert client._pooled_session(True) is s1
        assert client._pooled_session(False) is not s1
