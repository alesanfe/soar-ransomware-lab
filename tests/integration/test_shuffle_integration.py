#!/usr/bin/env python3
"""
Integration tests for Shuffle client.
Tests Shuffle client functionality using mocks when service is not available.
"""

import os
import pytest
import requests
from soar_lab.common.exceptions import IntegrationError
from soar_lab.infrastructure.external.integrations.shuffle_client import ShuffleClient
from unittest.mock import patch, MagicMock

SHUFFLE_URL = os.getenv("SHUFFLE_URL", "http://localhost:5001")
SHUFFLE_API_KEY = os.getenv("SHUFFLE_DEFAULT_APIKEY", "")
SHUFFLE_WEBHOOK_ID = os.getenv("SHUFFLE_TEST_WEBHOOK_ID", "test-webhook-id")


@pytest.fixture(scope="module")
def shuffle_client():
    return ShuffleClient(base_url=SHUFFLE_URL, api_key=SHUFFLE_API_KEY)


@pytest.mark.integration
class TestShuffleHealth:
    def test_health_check_returns_bool(self, shuffle_client):
        with patch.object(shuffle_client._session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_get.return_value = mock_response
            result = shuffle_client.health_check()
            assert isinstance(result, bool)


@pytest.mark.integration
class TestShuffleWorkflows:
    def test_list_workflows_returns_list(self, shuffle_client):
        with patch.object(shuffle_client._session, 'get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = []
            mock_get.return_value = mock_response
            workflows = shuffle_client.list_workflows()
            assert isinstance(workflows, list)


@pytest.mark.integration
class TestShuffleWebhook:
    def test_send_webhook_returns_dict(self, shuffle_client):
        with patch.object(shuffle_client._session, 'post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"success": True}
            mock_post.return_value = mock_response
            payload = {
                "alert_id": "INT-TEST-001",
                "event_type": "integration_test",
                "severity": 1,
            }
            response = shuffle_client.send_webhook(SHUFFLE_WEBHOOK_ID, payload)
            assert isinstance(response, dict)


@pytest.mark.integration
class TestShuffleErrorHandling:
    def test_unreachable_host_raises_integration_error(self):
        client = ShuffleClient(base_url="http://localhost:19999", api_key="bad")
        with pytest.raises(IntegrationError):
            client.list_workflows()
