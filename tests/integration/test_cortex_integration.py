#!/usr/bin/env python3
"""Integration tests for Cortex client.

Tests Cortex client functionality using mocks when service is not
available.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.integrations.cortex.client import CortexClient

CORTEX_URL = os.getenv("CORTEX_URL", "http://localhost:9001")
CORTEX_API_KEY = os.getenv("CORTEX_API_KEY", "")


@pytest.fixture(scope="module")
def cortex_client():
    return CortexClient(base_url=CORTEX_URL, api_key=CORTEX_API_KEY)


@pytest.mark.integration
class TestCortexHealth:
    def test_health_check_returns_bool(self, cortex_client):
        with patch.object(cortex_client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            result = cortex_client.health_check()
            assert isinstance(result, bool)


@pytest.mark.integration
class TestCortexAnalyzers:
    def test_list_analyzers_returns_list(self, cortex_client):
        with patch.object(cortex_client._session, "post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_post.return_value = mock_response
            analyzers = cortex_client.list_analyzers()
            assert isinstance(analyzers, list)


@pytest.mark.integration
class TestCortexErrorHandling:
    def test_unreachable_host_raises_integration_error(self):
        client = CortexClient(base_url="http://localhost:19999", api_key="bad")
        with pytest.raises(IntegrationError):
            client.list_analyzers()
