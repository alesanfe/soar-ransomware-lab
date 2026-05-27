#!/usr/bin/env python3
"""
SOAR Ransomware Lab - Shared Test Mocks
Reusable pytest fixtures for Docker, Redis and HTTP clients.
Import in test files or add to conftest.py as needed.
"""

import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Docker mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_docker_container():
    """Return a mock Docker container with status='running'."""
    container = MagicMock()
    container.status = "running"
    container.name = "soar_thehive"
    container.id = "abc123"
    return container


@pytest.fixture
def mock_docker_client(mock_docker_container):
    """Return a mock DockerClient whose containers.get() returns a running container."""
    client = MagicMock()
    client.containers.get.return_value = mock_docker_container
    return client


@pytest.fixture
def patched_docker_client(mock_docker_client):
    """Patch soar_lab.infrastructure.clients so Docker is replaced by the mock."""
    with patch("soar_lab.infrastructure.clients._docker_client", mock_docker_client):
        yield mock_docker_client


# ---------------------------------------------------------------------------
# Redis mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_redis_client():
    """Return a mock Redis client that behaves like a simple key-value store."""
    store: dict = {}

    client = MagicMock()
    client.ping.return_value = True

    def _get(key):
        return store.get(key)

    def _set(key, value):
        store[key] = value
        return True

    def _setex(key, ttl, value):
        store[key] = value
        return True

    def _delete(key):
        store.pop(key, None)

    client.get.side_effect = _get
    client.set.side_effect = _set
    client.setex.side_effect = _setex
    client.delete.side_effect = _delete
    client._store = store
    return client


@pytest.fixture
def patched_redis_client(mock_redis_client):
    """Patch soar_lab.infrastructure.clients so Redis is replaced by the mock."""
    with patch("soar_lab.infrastructure.clients._redis_client", mock_redis_client):
        yield mock_redis_client


# ---------------------------------------------------------------------------
# HTTP / requests mock
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_http_response():
    """Return a factory that builds mock requests.Response objects."""

    def _factory(status_code: int = 200, json_data: dict = None, text: str = ""):
        response = MagicMock()
        response.status_code = status_code
        response.text = text or json.dumps(json_data or {})
        response.content = response.text.encode()
        response.json.return_value = json_data or {}
        response.raise_for_status = MagicMock()
        if status_code >= 400:
            from requests.exceptions import HTTPError
            response.raise_for_status.side_effect = HTTPError(
                f"HTTP {status_code}", response=response
            )
        return response

    return _factory
